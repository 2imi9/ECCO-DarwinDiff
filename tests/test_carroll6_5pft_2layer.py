"""2-layer Carroll-6 / 5-PFT box-model tests (v2.7).

Validates the 15-tracer 2-layer extension of ``carroll6_5pft``. Focuses
on the new state-vector layout, the L1↔L2 vertical-coupling fluxes
(sinking-POC iron transport, vertical eddy diffusion, subsurface
remineralization), the qualitative DFe profile (subsurface > surface),
and autograd flow to all 6 learnable parameters.

The full GEOTRACES-anchored parameter-recovery experiment lives in
``scripts/run_v2.7_multilayer_quick.py``; these tests cover only the
forward-model behavior.
"""

from __future__ import annotations

import contextlib

import torch

import darwindiff.carroll6_5pft_2layer as c2l
from darwindiff.carroll6 import CARROLL_VALUES, Q_FE
from darwindiff.carroll6_5pft_2layer import (
    H1,
    H2,
    I_ALK_1,
    I_ALK_2,
    I_DFE_1,
    I_DFE_2,
    I_DIATOM,
    I_DIC_1,
    I_DIC_2,
    I_LGE,
    I_PIC_1,
    I_PIC_2,
    I_POC_1,
    I_POC_2,
    I_PROHL,
    I_PROLL,
    I_SYN,
    KZ_M2_PER_DAY,
    N_TRACERS_2LAYER,
    Q_FE_REMIN,
    Q_FE_SINK,
    R_REMIN,
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_step,
)


def _state0() -> torch.Tensor:
    """15-tracer initial state — L1 mirrors v2.6 init; L2 is literature-plausible.

    L2 starting values: DFe_2 = 5e-4 (~0.49 nmol/kg, ferricline-scale),
    POC_2 ~ 0.05 (10% of L1 surface), PIC_2 ~ 0.003, DIC/ALK slightly
    elevated from surface to reflect remineralization-derived enrichment.
    """
    return torch.tensor([
        # L1 (mirrors carroll6_5pft test fixture)
        5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
        0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
        # L2
        5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
    ])


def test_2layer_state_layout() -> None:
    """State-vector indices and counts match the module's named constants."""
    assert N_TRACERS_2LAYER == 15
    # L1 block 0..9 matches v2.6 layout
    assert tuple(range(10)) == (I_DFE_1, I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL,
            I_POC_1, I_PIC_1, I_DIC_1, I_ALK_1)
    # L2 block 10..14
    assert tuple(range(10, 15)) == (I_DFE_2, I_POC_2, I_PIC_2, I_DIC_2, I_ALK_2)


def test_2layer_step_is_finite_and_nonneg() -> None:
    """Single step on Carroll's truth produces finite tracers."""
    s0 = _state0()
    s_next = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25)
    assert s_next.shape == (N_TRACERS_2LAYER,)
    assert torch.isfinite(s_next).all()
    # The non-negativity floor (clamp(min=0.0)) in carroll6_5pft_2layer_step makes
    # this exact: no tracer can be negative after a step (was -1e-3 pre-clamp).
    assert (s_next >= 0.0).all()


def test_clamp_inert_on_carroll_trajectory() -> None:
    """The non-negativity floor never binds on a Carroll-range trajectory: every
    tracer stays strictly positive over 200 steps, so the clamp is a no-op in the
    operating regime and only guards the param-bound extremes (cf.
    test_param_bound_extremes_stay_nonnegative_under_spinup, where it fires)."""
    final = carroll6_5pft_2layer_integrate(
        _state0(), CARROLL_VALUES, dt=0.25, n_steps=200, T=27.0, S=35.0, wind=7.0,
    )
    assert torch.isfinite(final).all()
    assert (final > 0.0).all()


def test_2layer_dfe_profile_qualitative() -> None:
    """After integration, subsurface DFe > surface DFe (HNLC Eq Pac profile).

    GEOTRACES observations show ~3-4x DFe enrichment from surface (0.16
    nmol/kg) to the 50-1000 m subsurface band (mean ~0.36 nmol/kg). The
    2-layer model should reproduce this ordering at Carroll's published
    params, even if the exact ratio is approximate.
    """
    s_final = carroll6_5pft_2layer_integrate(
        _state0(), CARROLL_VALUES, dt=0.25, n_steps=200, T=27.0, S=35.0, wind=7.0,
    )
    assert s_final[I_DFE_2] > s_final[I_DFE_1], (
        f"Expected DFe_2 > DFe_1, got {s_final[I_DFE_2]:.3e} vs "
        f"{s_final[I_DFE_1]:.3e}"
    )
    # Order-of-magnitude check: ratio should be > 1 and < 100 (sanity bounds).
    ratio = float(s_final[I_DFE_2] / s_final[I_DFE_1])
    assert 1.0 < ratio < 100.0, f"DFe_2/DFe_1 ratio out of bounds: {ratio:.2f}"


def test_2layer_autograd_to_all_6_params() -> None:
    """Loss on L1+L2 DFe back-propagates non-zero grad to params [0..4].

    R_PICPOC has no path to DFe (it affects PIC stoichiometry only, which
    doesn't feed back to DFe), so its gradient is expected to be 0 — this
    is intentional and matches v2.6's identifiability of R_PICPOC via PIC
    observations rather than the iron loss.
    """
    params = CARROLL_VALUES.clone().requires_grad_(True)
    s_final = carroll6_5pft_2layer_integrate(
        _state0(), params, dt=0.25, n_steps=50, T=27.0, S=35.0, wind=7.0,
    )
    loss = (s_final[I_DFE_1] - 1e-4) ** 2 + (s_final[I_DFE_2] - 5e-4) ** 2
    loss.backward()
    grad = params.grad
    assert grad is not None
    # alpfe (0), scav_rat (1), Smallgrow (2), Biggrow (3), diatomgraz (4)
    # all influence DFe via biology + iron-budget terms.
    for i, name in enumerate(["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz"]):
        assert grad[i] != 0.0, f"Expected non-zero grad for {name}, got {grad[i]:.3e}"
    # R_PICPOC (5) has no iron path; grad expected to be 0.
    assert grad[5] == 0.0, (
        f"R_PICPOC should have no iron-pathway gradient, got {grad[5]:.3e}"
    )


def test_2layer_kz_affects_dfe_over_time() -> None:
    """Kz contributes a non-zero L1↔L2 iron flux once DFe_1 ≠ DFe_2.

    The starting state has DFe_1 = DFe_2 = 5e-4, so the diffusive flux is
    exactly 0 at t=0. After a few integration steps biology depletes DFe_1
    in L1 while L2 stays high (no biology there), so DFe_2 > DFe_1 and Kz
    diffusion becomes a real flux. Verify the Kz=0 vs Kz=normal cases
    diverge after a 50-step (12.5-day) integration.
    """
    s0 = _state0()
    s_kz_off = carroll6_5pft_2layer_integrate(
        s0, CARROLL_VALUES, dt=0.25, n_steps=50, kz_m2_per_day=0.0,
    )
    s_kz_on = carroll6_5pft_2layer_integrate(
        s0, CARROLL_VALUES, dt=0.25, n_steps=50, kz_m2_per_day=KZ_M2_PER_DAY,
    )
    delta_dfe1 = float((s_kz_on[I_DFE_1] - s_kz_off[I_DFE_1]).abs())
    delta_dfe2 = float((s_kz_on[I_DFE_2] - s_kz_off[I_DFE_2]).abs())
    assert delta_dfe1 > 1e-12 or delta_dfe2 > 1e-12, (
        f"Kz should affect DFe after 50 steps; "
        f"got dDFe1={delta_dfe1:.3e}, dDFe2={delta_dfe2:.3e}"
    )


def test_2layer_remin_releases_iron_to_L2() -> None:
    """With r_remin > 0, POC_2 remineralization should be a positive iron
    source to L2. Compared against r_remin=0, DFe_2 should be larger after
    a few steps (more iron arrives from remineralized POC).
    """
    s0 = _state0()
    s_remin_off = carroll6_5pft_2layer_integrate(
        s0, CARROLL_VALUES, dt=0.25, n_steps=100, r_remin=0.0,
    )
    s_remin_on = carroll6_5pft_2layer_integrate(
        s0, CARROLL_VALUES, dt=0.25, n_steps=100, r_remin=R_REMIN,
    )
    # With remin, DFe_2 should be at least as high as without (iron source).
    assert s_remin_on[I_DFE_2] >= s_remin_off[I_DFE_2] - 1e-12, (
        f"Remineralization should increase DFe_2; "
        f"got remin_on={float(s_remin_on[I_DFE_2]):.3e} vs "
        f"remin_off={float(s_remin_off[I_DFE_2]):.3e}"
    )


def test_2layer_snapshot_indices() -> None:
    """``snapshot_indices`` returns the requested intermediate states."""
    s0 = _state0()
    snaps = carroll6_5pft_2layer_integrate(
        s0, CARROLL_VALUES, dt=0.25, n_steps=10,
        snapshot_indices=[1, 5, 10],
    )
    assert snaps.shape == (3, N_TRACERS_2LAYER)
    assert torch.isfinite(snaps).all()


def test_2layer_geometry_constants_match_scoping_doc() -> None:
    """Layer thicknesses + interface depth match the v2.7 scoping doc."""
    assert H1 == 50.0   # surface layer = v2.6 mixed-layer thickness
    assert H2 == 950.0  # subsurface layer 50-1000 m


def test_2layer_q_fe_stoichiometry_carbon_path() -> None:
    """Sinking-POC iron stoichiometry uses Q_FE (phyto-derived detritus)."""
    assert Q_FE_SINK == Q_FE
    assert Q_FE_REMIN == Q_FE


# --- Environment-dependent rain ratio (USE_ENV_RAIN_RATIO, 2026-06-24) -------------


@contextlib.contextmanager
def _env_rain_ratio(**overrides):
    """Set the module-level env-rain-ratio flags, restoring them on exit."""
    keys = ["USE_ENV_RAIN_RATIO", "RPP_T_OPT", "RPP_T_WIDTH",
            "RPP_OMEGA_K", "RPP_OMEGA_P", "RPP_G_NORM"]
    saved = {k: getattr(c2l, k) for k in keys}
    try:
        for k, v in overrides.items():
            setattr(c2l, k, v)
        yield
    finally:
        for k, v in saved.items():
            setattr(c2l, k, v)


def _two_cell_state(T_a: float, T_b: float):
    """A 2-cell state ([15, 2]) with a per-cell temperature field, for testing the
    spatially-varying rain-ratio gate."""
    s0 = _state0().unsqueeze(-1).repeat(1, 2)
    T = torch.tensor([T_a, T_b])
    return s0, T


def test_env_rain_ratio_off_is_inert() -> None:
    """With the flag OFF (default), the gating constants have NO effect: the step is
    bitwise-identical regardless of RPP_* — i.e. legacy behaviour reproduces exactly."""
    s0 = _state0()
    base = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=20.0)
    # Mutate every gating constant while the flag stays OFF; output must not move.
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=False, RPP_T_OPT=5.0, RPP_T_WIDTH=1.0,
                         RPP_G_NORM=0.01, RPP_OMEGA_P=2.0):
        same = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=20.0)
    assert torch.equal(base, same)


def test_env_rain_ratio_on_reduces_to_bare_when_flat() -> None:
    """A degenerate gate (very wide window so g~1 everywhere, G_NORM=1) makes
    R_PICPOC_eff ~ R_PICPOC, so the ON step matches the OFF step. This pins the
    normalization convention: R_PICPOC is the realized rain ratio when the gate is
    flat and unit-normalized."""
    s0 = _state0()
    off = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=18.0)
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=True, RPP_T_OPT=18.0, RPP_T_WIDTH=1.0e6,
                         RPP_G_NORM=1.0, RPP_OMEGA_P=0.0):
        on = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=18.0)
    assert torch.allclose(off, on, atol=1e-6, rtol=1e-5)


def test_env_rain_ratio_on_makes_pic_vary_with_temperature() -> None:
    """With the thermal window ON, a cell AT the optimum produces more PIC than a cell
    far from it — the regional spread the bare scalar cannot make. PIC at t=1 is
    R_PICPOC_eff * calcite_mort_src - sink; with equal state/mort across the two cells,
    a higher gate at T_opt yields strictly higher PIC."""
    s0, T = _two_cell_state(T_a=17.46, T_b=2.0)   # at-optimum vs cold tail
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=True, RPP_T_OPT=17.46, RPP_T_WIDTH=2.33,
                         RPP_G_NORM=0.00373, RPP_OMEGA_P=0.0):
        nxt = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=T, S=35.0)
    pic_opt, pic_cold = float(nxt[I_PIC_1, 0]), float(nxt[I_PIC_1, 1])
    assert pic_opt > pic_cold, (
        f"PIC at T_opt ({pic_opt:.4f}) should exceed cold-tail ({pic_cold:.4f})")


def test_env_rain_ratio_autograd_to_rpicpoc_via_pic() -> None:
    """Under the gate, a PIC loss back-propagates a non-zero gradient to R_PICPOC[5]
    (the calcite path). Confirms the gating is autograd-clean to the base rate."""
    params = CARROLL_VALUES.clone().requires_grad_(True)
    s0, T = _two_cell_state(T_a=17.46, T_b=12.0)
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=True, RPP_T_OPT=17.46, RPP_T_WIDTH=2.33,
                         RPP_G_NORM=0.00373, RPP_OMEGA_P=0.0):
        final = carroll6_5pft_2layer_integrate(
            s0, params, dt=0.25, n_steps=30, T=T, S=35.0, wind=7.0,
        )
        loss = (final[I_PIC_1] ** 2).sum()
        loss.backward()
    assert params.grad is not None
    assert params.grad[5] != 0.0, f"R_PICPOC should get a PIC-path grad, got {params.grad[5]:.3e}"


def test_env_rain_ratio_omega_term_engages() -> None:
    """Enabling the optional Omega_c saturation term (RPP_OMEGA_P > 0) changes the
    result vs temperature-only — i.e. the carbonate-saturation path is wired in."""
    s0, T = _two_cell_state(T_a=17.46, T_b=6.0)
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=True, RPP_T_OPT=17.46, RPP_T_WIDTH=2.33,
                         RPP_G_NORM=0.00373, RPP_OMEGA_P=0.0):
        t_only = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=T, S=35.0)
    with _env_rain_ratio(USE_ENV_RAIN_RATIO=True, RPP_T_OPT=17.46, RPP_T_WIDTH=2.33,
                         RPP_G_NORM=0.00373, RPP_OMEGA_K=0.5, RPP_OMEGA_P=2.0):
        t_omega = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25, T=T, S=35.0)
    assert not torch.allclose(t_only[I_PIC_1], t_omega[I_PIC_1])
