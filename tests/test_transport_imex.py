"""Tests for the semi-implicit (IMEX) vertical-diffusion fix in transport.py.

The explicit `vertical_diffusion` silently NaNs / blows up above the CFL limit
`kz*dt/dz^2 < 0.5` (deep review 2026-07-07). This suite covers the fix:
`thomas_solve` (batched tridiagonal), `vertical_diffusion_implicit` (backward-Euler,
unconditionally stable, mass-conserving, autograd-clean), the `assert_vertical_cfl`
guard on the explicit path, the `include_vdiff` split flag, and `imex_rollout`
(explicit advection/BGC + implicit vertical diffusion, checkpointable).
"""
from __future__ import annotations

import pytest
import torch

from darwindiff.transport import (
    assert_vertical_cfl,
    column_tendency,
    grid_tendency,
    imex_rollout,
    thomas_solve,
    vertical_cfl_number,
    vertical_diffusion,
    vertical_diffusion_implicit,
)

F64 = torch.float64


def _dense_tridiag(a, b, c):
    n = b.shape[0]
    M = torch.zeros(n, n, dtype=b.dtype)
    for i in range(n):
        M[i, i] = b[i]
        if i > 0:
            M[i, i - 1] = a[i]
        if i < n - 1:
            M[i, i + 1] = c[i]
    return M


class TestThomasSolve:
    def test_matches_dense_solve(self) -> None:
        torch.manual_seed(0)
        n = 8
        a = torch.randn(n, dtype=F64)
        b = torch.tensor([5.0 + 0.1 * i for i in range(n)], dtype=F64)  # diag-dominant
        c = torch.randn(n, dtype=F64)
        a[0] = 0.0
        c[-1] = 0.0
        d = torch.randn(2, 3, n, 4, dtype=F64)  # [..., Z, tracer]
        x = thomas_solve(a, b, c, d)
        M = _dense_tridiag(a, b, c)
        xd = torch.linalg.solve(M, d.movedim(-2, -1).unsqueeze(-1)).squeeze(-1).movedim(-1, -2)
        assert torch.allclose(x, xd, atol=1e-12)

    def test_single_row(self) -> None:
        a = torch.zeros(1, dtype=F64)
        b = torch.tensor([2.0], dtype=F64)
        c = torch.zeros(1, dtype=F64)
        d = torch.tensor([[[4.0]]], dtype=F64)  # [.., Z=1, tracer=1]
        assert torch.allclose(thomas_solve(a, b, c, d), d / 2.0)


class TestImplicitVerticalDiffusion:
    def test_conserves_column_mass(self) -> None:
        st = torch.rand(4, 10, 5, dtype=F64)
        out = vertical_diffusion_implicit(st, kz=1.0, dz=10.0, dt=100.0)  # r=1.0
        drift = (out.sum(dim=-2) - st.sum(dim=-2)).abs().max()
        assert float(drift) < 1e-12

    def test_matches_explicit_at_small_dt(self) -> None:
        st = torch.rand(3, 8, 5, dtype=F64)
        kz, dz, dt = 0.1, 10.0, 1.0e-3  # r = kz*dt/dz^2 = 1e-6, deep in the stable regime
        expl = st + dt * vertical_diffusion(st, kz, dz)
        impl = vertical_diffusion_implicit(st, kz, dz, dt)
        # backward vs forward Euler differ at O(dt^2); tiny here. rtol=0 so atol actually
        # binds and this genuinely pins the operator (incl. no-flux boundary rows) -- a
        # dropped-no-flux boundary bug (top row 1+2r instead of 1+r) fails this.
        assert torch.allclose(expl, impl, atol=1e-8, rtol=0.0)

    def test_stable_where_explicit_blows_up(self) -> None:
        st = torch.rand(3, 10, 5, dtype=F64)
        kz, dz = 0.1, 10.0
        dt_big = 1.25 * dz * dz / kz  # r=1.25 (explicit unstable)
        x = st.clone()
        for _ in range(50):
            x = x + dt_big * vertical_diffusion(x, kz, dz)  # explicit
        y = st.clone()
        for _ in range(50):
            y = vertical_diffusion_implicit(y, kz, dz, dt_big)  # implicit
        expl_growth = float(x.abs().max() / st.abs().max())
        impl_growth = float(y.abs().max() / st.abs().max())
        assert expl_growth > 1.0e6   # explicit blows up (measured ~6e28)
        assert impl_growth < 2.0     # implicit bounded (diffusion decays)
        assert torch.isfinite(y).all()

    def test_single_layer_identity(self) -> None:
        st = torch.rand(2, 1, 5, dtype=F64)
        out = vertical_diffusion_implicit(st, kz=1.0, dz=10.0, dt=100.0)
        assert torch.allclose(out, st)

    def test_uniform_field_unchanged(self) -> None:
        # A vertically-uniform column has zero diffusive tendency -> implicit is identity.
        st = torch.ones(2, 7, 3, dtype=F64) * 0.3
        out = vertical_diffusion_implicit(st, kz=0.5, dz=10.0, dt=50.0)
        assert torch.allclose(out, st, atol=1e-12)

    def test_gradcheck(self) -> None:
        s = torch.rand(2, 6, 3, dtype=F64, requires_grad=True)
        assert torch.autograd.gradcheck(
            lambda z: vertical_diffusion_implicit(z, 0.5, 10.0, 20.0), (s,), atol=1e-6
        )


class TestCflGuard:
    def test_cfl_number(self) -> None:
        assert vertical_cfl_number(0.1, 10.0, 50.0) == pytest.approx(0.1 * 50.0 / 100.0)

    def test_assert_fires_at_limit(self) -> None:
        with pytest.raises(ValueError, match="unstable"):
            assert_vertical_cfl(kz=0.1, dz=10.0, dt=1.25 * 100.0 / 0.1)

    def test_assert_passes_below_limit(self) -> None:
        assert_vertical_cfl(kz=0.1, dz=10.0, dt=0.25)  # r=0.000625, fine

    def test_explicit_opt_in_guard(self) -> None:
        st = torch.rand(2, 5, 3, dtype=F64)
        # dt within CFL: no raise
        _ = vertical_diffusion(st, 0.1, 10.0, dt=0.25)
        # dt above CFL: raise instead of silent blow-up
        with pytest.raises(ValueError, match="unstable"):
            vertical_diffusion(st, 0.1, 10.0, dt=1.25 * 100.0 / 0.1)

    def test_explicit_unguarded_by_default(self) -> None:
        st = torch.rand(2, 5, 3, dtype=F64)
        # dt omitted -> no guard (back-compat with the tendency-only call path)
        out = vertical_diffusion(st, 0.1, 10.0)
        assert out.shape == st.shape


class TestIncludeVdiffFlag:
    def test_column_tendency_excludes_vdiff(self) -> None:
        st = torch.rand(3, 6, 5, dtype=F64)
        params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425], dtype=F64)
        full = column_tendency(st, params, kz=0.5, dz=10.0)
        no_vd = column_tendency(st, params, kz=0.5, dz=10.0, include_vdiff=False)
        vd = vertical_diffusion(st, 0.5, 10.0)
        assert torch.allclose(full - no_vd, vd, atol=1e-12)

    def test_grid_tendency_excludes_vdiff(self) -> None:
        st = torch.rand(2, 2, 6, 5, dtype=F64)
        params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425], dtype=F64)
        u = torch.zeros(2, 2, dtype=F64)
        v = torch.zeros(2, 2, dtype=F64)
        kw = dict(u=u, v=v, dx=1e5, dy=1e5, kz=0.5, dz=10.0, kh=50.0)
        full = grid_tendency(st, params, **kw)
        no_vd = grid_tendency(st, params, include_vdiff=False, **kw)
        # the depth axis is -2 in the [Y, X, Z, tracer] state
        vd = vertical_diffusion(st, 0.5, 10.0)
        assert torch.allclose(full - no_vd, vd, atol=1e-12)


class TestImexRollout:
    def _tendency(self, params, u, v):
        def tend(t, x):
            return grid_tendency(
                x, params, u=u, v=v, dx=1e5, dy=1e5, kz=0.5, dz=10.0, kh=50.0,
                include_vdiff=False, bgc=True,
            )
        return tend

    def _setup(self):
        ny, nx, nz, ntr = 3, 3, 6, 5
        state = torch.rand(ny, nx, nz, ntr, dtype=F64) * 0.1 + 0.05
        params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425], dtype=F64, requires_grad=True)
        u = torch.zeros(ny, nx, dtype=F64)
        v = torch.zeros(ny, nx, dtype=F64)
        return state, params, u, v

    def test_runs_finite(self) -> None:
        state, params, u, v = self._setup()
        out = imex_rollout(self._tendency(params, u, v), state, dt=0.25, n_steps=8, kz=0.5, dz=10.0)
        assert out.shape == state.shape
        assert torch.isfinite(out).all()

    def test_checkpoint_equivalence(self) -> None:
        state, params, u, v = self._setup()
        tend = self._tendency(params, u, v)
        plain = imex_rollout(tend, state, dt=0.25, n_steps=9, kz=0.5, dz=10.0)
        ckpt = imex_rollout(tend, state, dt=0.25, n_steps=9, kz=0.5, dz=10.0, checkpoint_segment=4)
        assert torch.equal(plain, ckpt)  # deterministic recompute -> bit-identical

    def test_gradient_flows_to_params(self) -> None:
        state, params, u, v = self._setup()
        out = imex_rollout(self._tendency(params, u, v), state, dt=0.25, n_steps=6, kz=0.5, dz=10.0)
        g = torch.autograd.grad(out.sum(), params)[0]
        assert torch.isfinite(g).all()
        assert float(g.norm()) > 0.0

    def test_snapshot_mode(self) -> None:
        state, params, u, v = self._setup()
        snaps = imex_rollout(
            self._tendency(params, u, v), state, dt=0.25, n_steps=8, kz=0.5, dz=10.0,
            snapshot_indices=[4, 8],
        )
        assert snaps.shape == (2, *state.shape)

    def test_pure_diffusion_matches_iterated_implicit(self) -> None:
        # With a zero explicit tendency, imex_rollout == iterated implicit vdiff.
        state = torch.rand(2, 8, 5, dtype=F64)
        def zero_tend(t, x):
            return torch.zeros_like(x)
        out = imex_rollout(zero_tend, state, dt=1.0, n_steps=5, kz=0.7, dz=10.0)
        ref = state.clone()
        for _ in range(5):
            ref = vertical_diffusion_implicit(ref, 0.7, 10.0, 1.0)
        assert torch.allclose(out, ref, atol=1e-12)

    def test_operator_split_applies_vdiff_exactly_once(self) -> None:
        # The whole point of the split: the explicit tendency EXCLUDES vertical diffusion
        # and imex adds it ONCE implicitly. At small dt/r (explicit vdiff CFL-stable) the
        # correct imex rollout must match an all-explicit euler rollout with vdiff INCLUDED
        # (both O(dt), vdiff applied once). A double-count (feeding a vdiff-bearing tendency
        # to imex) or a drop both diverge -- this is the end-to-end guard the flag-level
        # TestIncludeVdiffFlag can't provide.
        state, params, u, v = self._setup()
        p = params.detach()
        kz, dz, dt, n = 0.5, 10.0, 1.0e-3, 20  # r = 5e-6, explicit vdiff stable
        gk = dict(u=u, v=v, dx=1e5, dy=1e5, kz=kz, dz=dz, kh=50.0, bgc=True)
        # correct: explicit part excludes vdiff, imex adds it implicitly (euler to match ref)
        imex = imex_rollout(lambda t, x: grid_tendency(x, p, include_vdiff=False, **gk),
                            state, dt=dt, n_steps=n, kz=kz, dz=dz, method="euler")
        # reference: all-explicit euler rollout with vdiff included exactly once
        ref = state.clone()
        for _ in range(n):
            ref = ref + dt * grid_tendency(ref, p, include_vdiff=True, **gk)
        assert torch.allclose(imex, ref, atol=1e-6, rtol=0.0)  # vdiff applied once
        # DOUBLE-COUNT: feeding the vdiff-bearing tendency to imex is detectably wrong
        imex_double = imex_rollout(lambda t, x: grid_tendency(x, p, include_vdiff=True, **gk),
                                   state, dt=dt, n_steps=n, kz=kz, dz=dz, method="euler")
        assert not torch.allclose(imex_double, ref, atol=1e-6, rtol=0.0)

    def test_legacy_autonomous_tendency(self) -> None:
        # A 1-arg f(x) is accepted (wrapped time-aware).
        state = torch.rand(2, 6, 5, dtype=F64)
        out = imex_rollout(lambda x: torch.zeros_like(x), state, dt=1.0, n_steps=3, kz=0.5, dz=10.0)
        assert torch.isfinite(out).all()

    def test_unknown_method_raises(self) -> None:
        state, params, u, v = self._setup()
        with pytest.raises(ValueError, match="unknown method"):
            imex_rollout(self._tendency(params, u, v), state, dt=0.25, n_steps=2,
                         kz=0.5, dz=10.0, method="midpoint")

    def test_imex_stable_above_cfl_wall(self) -> None:
        # kz=864 m^2/day (~1e-2 m^2/s mixed-layer turbulent diffusivity), dt=0.25 d,
        # dz=10 m -> r = kz*dt/dz^2 = 2.16, WELL above the explicit CFL wall 0.5. An
        # explicit vertical-diffusion rollout blows up here (see
        # test_stable_where_explicit_blows_up); imex_rollout must stay finite, proving
        # the no-CFL-wall property THROUGH the rollout path (not just the bare operator).
        state, params, u, v = self._setup()
        out = imex_rollout(self._tendency(params, u, v), state, dt=0.25, n_steps=20,
                           kz=864.0, dz=10.0)  # r = 2.16
        assert torch.isfinite(out).all()
