"""Tests for the windowed-BPTT UDE-closure trainer (darwindiff.trainer).

The load-bearing test is a **synthetic self-twin**: generate a target field with a
KNOWN non-trivial calcite closure, then fit a fresh (anchored, g==1) closure through the
prescribed-transport rollout and check it (a) drives the training loss down, (b) reaches
POSITIVE held-out R^2 (recovers the environmental dependence at unseen cells -- the E2
signal on synthetic data), and (c) beats the frozen null-closure baseline. This proves
the trainer machinery end-to-end; a real-data E2 number additionally needs staged obs.
"""
from __future__ import annotations

import torch

import pytest

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.closures import EnvCalciteClosure, ScavClosure
from darwindiff.trainer import (
    TransportConfig,
    dfe_observable,
    masked_mse,
    masked_r2,
    picpoc_observable,
    rollout_field,
    train_ude_closure,
)

F64 = torch.float64


def _params() -> torch.Tensor:
    return torch.tensor([CARROLL_VALUES[i] for i in range(6)], dtype=F64)


def _env(ny: int, nx: int, nz: int) -> torch.Tensor:
    yy = torch.linspace(-1, 1, ny, dtype=F64).view(ny, 1, 1)
    xx = torch.linspace(-1, 1, nx, dtype=F64).view(1, nx, 1)
    return (yy + 0.5 * xx).expand(ny, nx, nz).unsqueeze(-1).clone()  # [Y,X,Z,1]


def _truth_closure(env: torch.Tensor) -> EnvCalciteClosure:
    """A calcite closure with KNOWN non-trivial env dependence (g varies ~0.2..6x)."""
    c = EnvCalciteClosure(env, A=1.0)
    with torch.no_grad():
        c.net[0].weight.zero_(); c.net[0].weight[0, 0] = 2.0; c.net[0].bias.zero_()
        c.net[2].weight.zero_(); c.net[2].weight[0, 0] = 1.0; c.net[2].bias.zero_()
        c.net[-1].weight.zero_(); c.net[-1].weight[0, 0] = 1.2; c.net[-1].bias.zero_()
    return c.to(F64)


class TestMetrics:
    def test_masked_mse_perfect(self) -> None:
        a = torch.rand(4, 4, dtype=F64)
        m = torch.ones(4, 4, dtype=torch.bool)
        assert float(masked_mse(a, a.clone(), m)) == 0.0

    def test_masked_r2_perfect_and_mean(self) -> None:
        t = torch.rand(5, 5, dtype=F64)
        m = torch.ones(5, 5, dtype=torch.bool)
        assert float(masked_r2(t.clone(), t, m)) == 1.0
        # predicting the mean everywhere -> R2 == 0
        pred = torch.full_like(t, float(t[m].mean()))
        assert abs(float(masked_r2(pred, t, m))) < 1e-9

    def test_masked_only_counts_true_cells(self) -> None:
        pred = torch.zeros(3, 3, dtype=F64)
        target = torch.zeros(3, 3, dtype=F64)
        target[0, 0] = 100.0  # huge error, but masked out
        m = torch.ones(3, 3, dtype=torch.bool); m[0, 0] = False
        assert float(masked_mse(pred, target, m)) == 0.0


class TestSyntheticTwin:
    N_STEPS = 30

    def _setup(self):
        torch.manual_seed(0)
        ny, nx, nz, ntr = 5, 5, 3, 5
        env = _env(ny, nx, nz)
        params = _params()
        tc = TransportConfig(dx=1e5, dy=1e5, dz=10.0, dt=0.25, kz=50.0, kh=50.0)
        ic = torch.rand(ny, nx, nz, ntr, dtype=F64) * 0.1 + 0.05
        truth = _truth_closure(env)
        truth_field = rollout_field(ic, params, tc, self.N_STEPS, calcite_closure=truth).detach()
        target = picpoc_observable(truth_field).detach()
        # scattered ~25% held-out split (interpolation within the trained env range --
        # the right robustness test for the MACHINERY; blocked/regime holdout is the
        # separate E2 *scientific* rigor, exercised in scripts/e2_synthetic_twin_h200.py).
        g = torch.Generator().manual_seed(1)
        val_mask = torch.rand(ny, nx, nz, generator=g) < 0.25
        train_mask = ~val_mask
        return env, params, tc, ic, target, train_mask, val_mask

    def test_recovers_heldout_positive_r2(self) -> None:
        env, params, tc, ic, target, train_mask, val_mask = self._setup()
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        res = train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=target,
            train_mask=train_mask, val_mask=val_mask, hook="calcite_closure",
            epochs=45, lr=5e-2, checkpoint_segment=10, log_every=15,
        )
        first, last = res.history[0], res.history[-1]
        assert last["train_loss"] < 0.2 * first["train_loss"]         # loss fell hard
        assert last["val_r2"] > 0.9                                    # recovers held-out (E2 signal)
        assert last["val_r2"] > first["val_r2"]                        # improved from init

    def test_beats_null_closure_baseline(self) -> None:
        # The learned closure must fit the target better than the FROZEN g==1 closure
        # rolled through the identical transport (the E2 primary control).
        env, params, tc, ic, target, train_mask, val_mask = self._setup()
        null = EnvCalciteClosure(env, A=1.0).to(F64)  # never optimized -> stays at g==1
        null_field = rollout_field(ic, params, tc, self.N_STEPS, calcite_closure=null).detach()
        null_loss = float(masked_mse(picpoc_observable(null_field), target, train_mask))
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        res = train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=target,
            train_mask=train_mask, val_mask=val_mask, epochs=60, lr=5e-2,
            checkpoint_segment=10,
        )
        learned_loss = float(masked_mse(picpoc_observable(res.final_field), target, train_mask))
        assert learned_loss < 0.5 * null_loss

    def test_gradient_updates_all_closure_params(self) -> None:
        # Snapshot EVERY parameter and assert each moved -- an optimizer covering only a
        # subset (e.g. freezing hidden layers, or ScavClosure's out-of-.net log_r0/raw_p)
        # would pass a single-tensor check but fail this.
        env, params, tc, ic, target, train_mask, _ = self._setup()
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        before = [p.detach().clone() for p in clo.parameters()]
        train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=target,
            train_mask=train_mask, epochs=5, lr=5e-2, checkpoint_segment=10,
        )
        moved = [not torch.allclose(p.detach(), b) for p, b in zip(clo.parameters(), before)]
        assert all(moved), f"some params never moved: {moved}"

    def test_scav_closure_trains_all_params(self) -> None:
        # ScavClosure's one scientific scalar raw_p (POC exponent) lives OUTSIDE .net; fit
        # it through the trainer on a scav twin and assert it moves. The rate log_r0 is no
        # longer trainable (issue #217: it was a free level, exactly redundant with
        # scav_rat), so the twin must differ in SHAPE -- exponent and readout weight.
        env, params, tc, ic, _, _, _ = self._setup()
        truth = ScavClosure(scav_rat_per_day=None, eps=0.2).to(F64)
        with torch.no_grad():
            truth.raw_p.add_(0.5)
            # A readout *weight*, not a bias: a constant readout is mean-centred away, so
            # perturbing the bias alone would leave truth identical to the untrained
            # closure and this test would pass while comparing nothing.
            truth.net[-1].weight[0, 1] = 1.1
        tgt = dfe_observable(rollout_field(ic, params, tc, self.N_STEPS, scav_closure=truth)).detach()

        clo = ScavClosure(eps=0.2).to(F64)
        base = dfe_observable(rollout_field(ic, params, tc, self.N_STEPS, scav_closure=clo)).detach()
        assert not torch.allclose(tgt, base), "twin must differ from the untrained closure"

        g = torch.Generator().manual_seed(2)
        vm = torch.rand(*tgt.shape, generator=g) < 0.25
        p0 = float(clo.raw_p.detach())
        w0 = clo.net[-1].weight.detach().clone()
        train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=dfe_observable, target=tgt,
            train_mask=~vm, hook="scav_closure", epochs=25, lr=3e-2,
        )
        assert abs(float(clo.raw_p.detach()) - p0) > 1e-4          # POC exponent moved
        assert not torch.allclose(clo.net[-1].weight.detach(), w0)  # shape readout moved
        assert isinstance(clo.log_r0, float)                        # level still not trainable

    def test_tbptt_recovers_and_beats_null(self) -> None:
        # Truncated BPTT (fixed: score only the final, converged window) must recover the
        # closure and beat the frozen null baseline -- not merely trickle loss down.
        env, params, tc, ic, target, train_mask, val_mask = self._setup()
        null = EnvCalciteClosure(env, A=1.0).to(F64)
        r2_null = float(masked_r2(
            picpoc_observable(rollout_field(ic, params, tc, self.N_STEPS, calcite_closure=null)),
            target, val_mask))
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        res = train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=target,
            train_mask=train_mask, val_mask=val_mask, epochs=45, lr=5e-2,
            detach_window=10, log_every=44,
        )
        assert res.history[-1]["val_r2"] > 0.9          # genuinely recovers
        assert res.history[-1]["val_r2"] > r2_null       # beats null baseline
        assert torch.isfinite(res.final_field).all()

    def test_val_cells_excluded_from_gradient(self) -> None:
        # Leakage tripwire: corrupt the target ONLY at held-out cells; an honest trainer
        # (loss on train_mask) must leave the trained field on TRAIN cells bit-invariant.
        env, params, tc, ic, target, train_mask, val_mask = self._setup()

        def train_field(tgt):
            torch.manual_seed(123)  # identical closure init both runs -> only tgt differs
            clo = EnvCalciteClosure(env, A=1.0).to(F64)
            res = train_ude_closure(
                clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=tgt,
                train_mask=train_mask, epochs=20, lr=5e-2, checkpoint_segment=10,
            )
            return picpoc_observable(res.final_field)

        clean = train_field(target)
        corrupt = target.clone(); corrupt[val_mask] += 5.0
        leaked = train_field(corrupt)
        # val-cell corruption must NOT change the trained field on train cells
        assert torch.allclose(clean[train_mask], leaked[train_mask], atol=1e-10)

    def test_coupling_guard_rejects_decoupled_hook(self) -> None:
        # calcite_closure only affects PIC/DIC/ALK, never DFe -> dfe_observable is
        # structurally decoupled -> the trainer must reject it, not train a silent no-op.
        env, params, tc, ic, target, train_mask, _ = self._setup()
        with pytest.raises(ValueError, match="decoupled"):
            train_ude_closure(
                EnvCalciteClosure(env, A=1.0).to(F64), ic, params, tc, self.N_STEPS,
                observable=dfe_observable, target=target, train_mask=train_mask, epochs=2,
            )

    def test_nonfinite_loss_aborts_without_poisoning(self) -> None:
        # A non-finite loss must abort (record aborted=True) with the last-good params
        # intact, not silently NaN-poison every parameter via the clip/step.
        env, params, tc, ic, target, train_mask, val_mask = self._setup()
        clo = EnvCalciteClosure(env, A=1.0).to(F64)
        bad = target.clone(); bad[train_mask] = float("nan")  # loss -> NaN on epoch 0
        res = train_ude_closure(
            clo, ic, params, tc, self.N_STEPS, observable=picpoc_observable, target=bad,
            train_mask=train_mask, val_mask=val_mask, epochs=5, lr=5e-2, checkpoint_segment=10,
        )
        assert res.history[-1].get("aborted") is True
        assert all(torch.isfinite(p).all() for p in clo.parameters())  # not poisoned
