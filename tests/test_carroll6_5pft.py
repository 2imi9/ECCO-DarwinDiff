"""5-PFT Carroll-6 box-model tests (v2.2 Phase 2).

Validates the 10-tracer / 5-PFT extension of ``carroll6_carbonate_*``. Focuses
on the new state-vector layout, the per-PFT growth-rate mapping
(Smallgrow→Pro-HL, Biggrow→other-large-euks, diatomgraz→diatoms), autograd
flow to all 6 learnable parameters, and the same carbonate conservation
properties the 2-PFT 7-tracer integrator already satisfies.
"""

from __future__ import annotations

import torch

from darwindiff.carbonate import PCO2_ATM_DEFAULT
from darwindiff.carroll6 import (
    CARROLL_VALUES,
    G0_GRAZE,
    H_MLD,
    M_LIN,
    M_QUAD,
    PARAM_BOUNDS,
    W_SINK,
    bounded_params,
)
from darwindiff.carroll6_5pft import (
    I_ALK,
    I_DFE,
    I_DIATOM,
    I_DIC,
    I_LGE,
    I_PIC,
    I_POC,
    I_PROHL,
    I_PROLL,
    I_SYN,
    N_PHYTO,
    N_TRACERS,
    carroll6_5pft_integrate,
    carroll6_5pft_step,
)


def _state0() -> torch.Tensor:
    """10-tracer initial state reflecting Eq Pacific surface biomass partition.

    Phyto fractions follow the empirical Chl1..Chl5 abundance ratios from
    ``scripts/phase2_p4_p5_check.py``: Pro-HL dominates (~47%), Pro-LL ~0
    (deep-adapted, absent at surface), Syn low, diatoms + large euks
    moderate. DIC + ALK at the same carbonate-test reference values.
    """
    return torch.tensor([
        5.0e-4,           # DFe
        0.4,              # P_diatom (Chl1, 29.6%)
        0.3,              # P_lge    (Chl2, 21.5%)
        0.02,             # P_syn    (Chl3, 1.6%)
        0.001,            # P_proLL  (Chl4, ~0% surface)
        0.65,             # P_proHL  (Chl5, 47.2%)
        0.5,              # POC
        0.025,            # PIC
        2050.0 * 1.025,   # DIC ~ 2050 µmol/kg
        2350.0 * 1.025,   # ALK ~ 2350 µmol/kg
    ])


def test_carroll6_5pft_state_layout() -> None:
    """State-vector indices and counts match the module's named constants."""
    assert N_TRACERS == 10
    assert N_PHYTO == 5
    assert (I_DFE, I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL,
            I_POC, I_PIC, I_DIC, I_ALK) == tuple(range(10))


def test_carroll6_5pft_step_is_finite_and_nonneg() -> None:
    """Single step on Carroll's truth produces finite, ~non-negative tracers."""
    s0 = _state0()
    s_next = carroll6_5pft_step(s0, CARROLL_VALUES, dt=0.25)
    assert s_next.shape == (N_TRACERS,)
    assert torch.isfinite(s_next).all()
    # Float-noise tolerance on positivity (the carbonate solver introduces
    # ~1e-7 sign noise on near-zero P_proLL).
    assert (s_next > -1e-6).all()


def test_carroll6_5pft_integration_stable_at_truth() -> None:
    """200 forward-Euler steps at Carroll's optimum reach a finite state."""
    s0 = _state0()
    snapshot_indices = [40, 80, 120, 160, 200]
    with torch.no_grad():
        traj = carroll6_5pft_integrate(
            state0=s0, params=CARROLL_VALUES, dt=0.25,
            n_steps=200, snapshot_indices=snapshot_indices,
        )
    assert traj.shape == (len(snapshot_indices), N_TRACERS)
    assert torch.isfinite(traj).all()
    assert (traj > -1e-6).all()


def test_carroll6_5pft_autograd_flows_to_all_six() -> None:
    """Gradient flows from a 50-step rollout back to all 6 Carroll-6 params."""
    s0 = _state0()
    theta = torch.zeros(6, requires_grad=True)
    params = bounded_params(theta, PARAM_BOUNDS)
    traj = carroll6_5pft_integrate(
        state0=s0, params=params, dt=0.25, n_steps=50,
    )
    loss = traj.sum()
    loss.backward()
    assert theta.grad is not None
    assert torch.isfinite(theta.grad).all()
    assert (theta.grad.abs() > 0).all(), (
        "All 6 Carroll-6 parameters should receive nonzero gradient — if "
        "any are zero, the per-PFT mapping has unwired one of them."
    )


def test_alk_conservation_with_zero_R_PICPOC() -> None:
    """ALK is invariant when R_PICPOC = 0 (no CaCO3 stoichiometry)."""
    s0 = _state0()
    # Replace R_PICPOC with 0; keep other params at Carroll truth.
    params = CARROLL_VALUES.clone()
    params[-1] = 0.0
    with torch.no_grad():
        s_final = carroll6_5pft_integrate(
            state0=s0, params=params, dt=0.25, n_steps=20,
        )
    # ALK should be unchanged (no air-sea ALK exchange, no CaCO3 source).
    alk_drift = (s_final[I_ALK] - s0[I_ALK]).abs().item()
    assert alk_drift < 1e-4, f"ALK drifted by {alk_drift} with R_PICPOC=0"


def test_zero_wind_kills_co2_flux() -> None:
    """Wind=0 → no air-sea CO2 flux; total carbon decays only via sinking."""
    s0 = _state0()
    with torch.no_grad():
        s_with_flux = carroll6_5pft_integrate(
            state0=s0, params=CARROLL_VALUES, dt=0.25, n_steps=10, wind=7.0,
        )
        s_no_flux = carroll6_5pft_integrate(
            state0=s0, params=CARROLL_VALUES, dt=0.25, n_steps=10, wind=0.0,
        )
    # DIC with no wind should be different from DIC with wind (wind drives
    # the air-sea component, the only path other than biology).
    dic_with = s_with_flux[I_DIC].item()
    dic_no = s_no_flux[I_DIC].item()
    assert abs(dic_with - dic_no) > 1e-3, (
        f"Disabling wind should change DIC; got {dic_with} vs {dic_no}"
    )


def test_smallgrow_only_affects_proHL() -> None:
    """Wiggling Smallgrow changes Pro-HL but not Syn or Pro-LL.

    Validates the Option A mapping: Smallgrow learns Pro-HL's rate
    specifically, not the average over Syn + Pro-LL + Pro-HL.
    """
    s0 = _state0()
    p_lo = CARROLL_VALUES.clone()
    p_hi = CARROLL_VALUES.clone()
    # Halve and double Smallgrow.
    p_lo[2] = CARROLL_VALUES[2] * 0.5
    p_hi[2] = CARROLL_VALUES[2] * 2.0
    with torch.no_grad():
        s_lo = carroll6_5pft_integrate(s0, p_lo, dt=0.25, n_steps=20)
        s_hi = carroll6_5pft_integrate(s0, p_hi, dt=0.25, n_steps=20)
    # Pro-HL should differ substantially (it's directly governed by Smallgrow).
    proHL_diff = (s_hi[I_PROHL] - s_lo[I_PROHL]).abs().item()
    assert proHL_diff > 1e-3, (
        f"Pro-HL should respond to Smallgrow changes; got diff {proHL_diff}"
    )
    # Pro-LL and Syn use the literature default (MU_DEFAULT_PROLL,
    # MU_DEFAULT_SYN) for their direct growth — but they still see Smallgrow
    # transitively via the shared iron pool (Pro-HL growth changes Fe uptake →
    # DFe → f_Fe → other PFTs' growth). Assert that the DIRECT response on
    # Pro-HL is much stronger than the indirect response on Syn / Pro-LL.
    syn_diff = (s_hi[I_SYN] - s_lo[I_SYN]).abs().item()
    proLL_diff = (s_hi[I_PROLL] - s_lo[I_PROLL]).abs().item()
    assert proHL_diff > 5 * syn_diff, (
        f"Pro-HL should respond ≥5× more than Syn (direct vs Fe-coupled "
        f"transitive); got proHL={proHL_diff} vs syn={syn_diff}"
    )
    assert proHL_diff > 5 * proLL_diff, (
        f"Pro-HL should respond ≥5× more than Pro-LL; got proHL={proHL_diff} "
        f"vs proLL={proLL_diff}"
    )
