"""Carroll-6 + carbonate-extension (7-tracer) box-model tests.

Validates the v2.0 capstone extension to ``carroll6.py`` — the integrator that
adds DIC + ALK + air-sea CO₂ flux on top of the original 5-tracer box. Focuses
on the new equations (the original 5 are already exercised by
``test_carroll6_recovery.py``).

Conservation laws checked:
    - ALK changes only via CaCO3 (PIC) formation: dALK/dt = -2 * R_PICPOC * mort_total
    - Total carbon (DIC + Phyto + POC + PIC) changes only via air-sea flux and
      particulate sinking export.
    - Air-sea flux contribution is zero when wind speed is zero — confirms the
      flux path is wired correctly and not double-counted.
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
    PARAM_NAMES,
    W_SINK,
    bounded_params,
    carroll6_carbonate_integrate,
    carroll6_carbonate_step,
)


def _state0() -> torch.Tensor:
    """Initial 7-tracer state — surface-ocean reference matching the carbonate
    solver tests. DIC and ALK are µmol/kg × ρ_sw to convert to mmol/m³."""
    return torch.tensor([
        5.0e-4,           # DFe (mmol Fe/m³)
        1.0,              # Ps  (mmol C/m³)
        1.0,              # Pl
        0.5,              # POC
        0.025,            # PIC
        2050.0 * 1.025,   # DIC ≈ 2050 µmol/kg
        2350.0 * 1.025,   # ALK ≈ 2350 µmol/kg
    ])


def _fixture() -> tuple[torch.Tensor, float, int, list[int]]:
    """Same 50-day spin-up at dt=0.25 d as the 5-tracer tests, 5 snapshots."""
    return _state0(), 0.25, 200, [40, 80, 120, 160, 200]


def test_carroll6_carbonate_step_is_finite_and_positive() -> None:
    """Single step on Carroll's truth produces finite, positive tracers."""
    s0 = _state0()
    s_next = carroll6_carbonate_step(s0, CARROLL_VALUES, dt=0.25)
    assert s_next.shape == s0.shape
    assert torch.isfinite(s_next).all()
    assert (s_next > 0).all(), "All 7 tracers should remain positive after one step."


def test_carroll6_carbonate_integration_stable_at_truth() -> None:
    """200 forward-Euler steps at Carroll's optimum stay finite, positive,
    and pH stays in the surface-ocean range."""
    s0, dt, n_steps, snapshot_indices = _fixture()
    with torch.no_grad():
        traj = carroll6_carbonate_integrate(
            state0=s0, params=CARROLL_VALUES, dt=dt,
            n_steps=n_steps, snapshot_indices=snapshot_indices,
        )
    assert traj.shape == (len(snapshot_indices), 7)
    assert torch.isfinite(traj).all()
    assert (traj > 0).all(), "All tracers should remain positive through the trajectory."
    # ALK/DIC ratio should stay close to 1.0–1.2 (Follows convergence regime).
    final_dic, final_alk = traj[-1, 5], traj[-1, 6]
    assert 0.9 < (final_alk / final_dic).item() < 1.3


def test_carroll6_carbonate_alk_budget_exact() -> None:
    """dALK/dt = -2 · R_PICPOC · mort_total — the only ALK source/sink in the model.

    Tests the chemistry formula directly. Tolerance ~1e-4 absolute accounts for
    the float32 precision floor when subtracting two ~2400-magnitude ALK values
    to get a ~0.03 difference — relative precision is ~1e-7, so the difference
    inherits ~1e-4 absolute noise.
    """
    s0 = _state0()
    Ps, Pl = s0[1].item(), s0[2].item()
    g_diatom = CARROLL_VALUES[4].item()
    R_PICPOC = CARROLL_VALUES[5].item()

    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l
    expected_dALK_per_day = -2.0 * R_PICPOC * mort_total

    dt = 0.25
    s_next = carroll6_carbonate_step(s0, CARROLL_VALUES, dt)
    actual_dALK_per_day = (s_next[6].item() - s0[6].item()) / dt

    # Use relative tolerance — the actual diff magnitude is ~0.1, float32 noise
    # at 2400-scale propagates to ~1e-4 absolute, so 1% relative is comfortable.
    rel_error = abs(actual_dALK_per_day - expected_dALK_per_day) / abs(expected_dALK_per_day)
    assert rel_error < 1.0e-2, (
        f"ALK budget broken: expected {expected_dALK_per_day:.6e}, "
        f"got {actual_dALK_per_day:.6e}, rel_error {rel_error:.2e}"
    )


def test_carroll6_carbonate_air_sea_flux_path_wired() -> None:
    """DIC change differs between wind=0 and wind=7 m/s — confirms the air-sea
    flux is actually being routed into the DIC tendency.

    At the surface-ocean reference (DIC=2050, ALK=2350 µmol/kg), pCO₂≈269 µatm
    is well below the 405 µatm default atmosphere, so the ocean is taking up
    CO₂ → DIC INCREASES with wind on, relative to wind=0.
    """
    s0 = _state0()
    dt = 0.25
    s_no_wind = carroll6_carbonate_step(s0, CARROLL_VALUES, dt, wind=0.0)
    s_with_wind = carroll6_carbonate_step(s0, CARROLL_VALUES, dt, wind=7.0)
    # DIC with wind > DIC without wind (uptake from undersaturated atmosphere).
    assert s_with_wind[5].item() > s_no_wind[5].item()
    # ALK is unaffected by air-sea flux (gas exchange doesn't touch alkalinity).
    assert abs(s_with_wind[6].item() - s_no_wind[6].item()) < 1.0e-10


def test_carroll6_carbonate_carbon_conservation_per_step() -> None:
    """Per-step total C change = -W_SINK · (POC + PIC) · dt when wind=0.

    Checks the conservation law step-by-step using start-of-step values (what
    forward-Euler actually uses), avoiding cumulative quadrature error. With
    wind=0 there's no air-sea flux, so the only sink of carbon from the box
    is particulate sinking export — the equation must hold exactly modulo
    float precision.
    """
    s0 = _state0()
    dt = 0.25
    s_next = carroll6_carbonate_step(s0, CARROLL_VALUES, dt, wind=0.0)

    # Total carbon in the box: Ps + Pl + POC + PIC + DIC (DFe is tracked separately).
    def total_c(s: torch.Tensor) -> float:
        return (s[1] + s[2] + s[3] + s[4] + s[5]).item()

    delta_c = total_c(s_next) - total_c(s0)
    expected_delta = -W_SINK * (s0[3] + s0[4]).item() * dt  # start-of-step POC + PIC

    # Float32 noise at DIC ~2100 magnitude propagates to absolute ~1e-4 when
    # subtracting; relative against ΔC ~0.025 is ~1%. Tight enough to catch
    # any algebra bug, loose enough to ride out single-precision noise.
    rel_error = abs(delta_c - expected_delta) / abs(expected_delta)
    assert rel_error < 2.0e-2, (
        f"Carbon conservation broken: ΔC={delta_c:.4e}, expected={expected_delta:.4e}, "
        f"rel_error={rel_error:.2e}"
    )


def test_carroll6_carbonate_autograd_flows_to_all_six() -> None:
    """Gradient from the integrated 7-tracer state flows back to all 6 Carroll knobs."""
    s0, dt, n_steps, snapshot_indices = _fixture()
    theta = torch.zeros(6, requires_grad=True)
    params = bounded_params(theta, PARAM_BOUNDS)
    traj = carroll6_carbonate_integrate(
        state0=s0, params=params, dt=dt,
        n_steps=n_steps, snapshot_indices=snapshot_indices,
    )
    traj.sum().backward()
    assert theta.grad is not None
    assert torch.isfinite(theta.grad).all()
    for i, name in enumerate(PARAM_NAMES):
        assert theta.grad[i].abs().item() > 0, (
            f"Parameter {name} (index {i}) received zero gradient — autograd path broken."
        )


def test_carroll6_carbonate_broadcasts_over_2d_grid() -> None:
    """Step + integrator broadcast pointwise over (H, W) — critical for per-cell fits."""
    H, W = 6, 8
    s_field = _state0().reshape(7, 1, 1).expand(7, H, W).contiguous()
    p_field = CARROLL_VALUES.reshape(6, 1, 1).expand(6, H, W).contiguous()
    T_field = torch.full((H, W), 15.0)
    S_field = torch.full((H, W), 35.0)
    wind_field = torch.full((H, W), 7.0)
    pco2_field = torch.full((H, W), PCO2_ATM_DEFAULT)

    s_next = carroll6_carbonate_step(
        s_field, p_field, dt=0.25,
        T=T_field, S=S_field, wind=wind_field, pco2_atm=pco2_field,
    )
    assert s_next.shape == (7, H, W)
    assert torch.isfinite(s_next).all()
    assert (s_next > 0).all()


def test_carroll6_carbonate_step_matches_5_tracer_dynamics_on_first_five() -> None:
    """The first 5 tracers (DFe, Ps, Pl, POC, PIC) follow the SAME dynamics as
    ``carroll6_step`` — the carbonate extension only adds equations, doesn't
    modify the existing ones. Backwards-compatibility guarantee for nb05–19.
    """
    from darwindiff.carroll6 import carroll6_step

    s0 = _state0()
    dt = 0.25
    # carroll6_step expects 5-tracer state — pass the first 5 of our 7-state.
    s5_next = carroll6_step(s0[:5], CARROLL_VALUES, dt)
    s7_next = carroll6_carbonate_step(s0, CARROLL_VALUES, dt)
    # First 5 tracers must agree bit-for-bit.
    assert torch.allclose(s7_next[:5], s5_next, atol=1.0e-10, rtol=0.0), (
        "carbonate extension altered the original 5-tracer dynamics"
    )
