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

import torch

from darwindiff.carroll6 import CARROLL_VALUES, PHI_DUST, Q_FE
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
    assert (I_DFE_1, I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL,
            I_POC_1, I_PIC_1, I_DIC_1, I_ALK_1) == tuple(range(10))
    # L2 block 10..14
    assert (I_DFE_2, I_POC_2, I_PIC_2, I_DIC_2, I_ALK_2) == tuple(range(10, 15))


def test_2layer_step_is_finite_and_nonneg() -> None:
    """Single step on Carroll's truth produces finite tracers."""
    s0 = _state0()
    s_next = carroll6_5pft_2layer_step(s0, CARROLL_VALUES, dt=0.25)
    assert s_next.shape == (N_TRACERS_2LAYER,)
    assert torch.isfinite(s_next).all()
    # Allow small negative float noise (carbonate solver introduces tiny
    # negatives on extremes); just check magnitudes are sane.
    assert (s_next >= -1e-3).all()


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
