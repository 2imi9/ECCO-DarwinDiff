"""Carbonate chemistry solver tests.

Validates equilibrium-constant magnitudes, the Follows 2006 iterative scheme,
autograd flow through DIC + ALK, broadcast over spatial grids, and the
Wanninkhof gas-transfer formula. Surface-ocean reference points come from
Lueker / Dickson / Wanninkhof literature ranges, not from PyCO2SYS (no new
dependency for v2.0).
"""

from __future__ import annotations

import pytest
import torch

from darwindiff.carbonate import (
    PCO2_ATM_DEFAULT,
    BT_total_boron,
    K0_solubility,
    K1_K2_carbonic,
    KB_boric,
    co2_flux,
    schmidt_number_co2,
    solve_carbonate,
)


@pytest.fixture
def surface_ocean_inputs() -> dict[str, torch.Tensor]:
    """Reference surface-ocean conditions, mid-latitude.

    DIC ≈ 2050 µmol/kg, ALK ≈ 2350 µmol/kg — typical surface-ocean climatology.
    Converted to mmol/m³ via ρ = 1025 kg/m³: 2050 × 1.025 ≈ 2101 mmol/m³.
    """
    return {
        "DIC": torch.tensor(2050.0 * 1.025),
        "ALK": torch.tensor(2350.0 * 1.025),
        "T": torch.tensor(15.0),
        "S": torch.tensor(35.0),
    }


def test_K0_solubility_in_expected_range() -> None:
    """K0 ~ 0.03–0.05 mol/(kg·atm) for surface ocean (Weiss 1974)."""
    K0 = K0_solubility(torch.tensor(15.0), torch.tensor(35.0))
    assert 0.03 < K0.item() < 0.06


def test_K1_K2_ordering_and_magnitude() -> None:
    """K1 > K2 always; both in expected surface-ocean magnitudes."""
    K1, K2 = K1_K2_carbonic(torch.tensor(15.0), torch.tensor(35.0))
    assert K1.item() > K2.item()
    assert 1.0e-7 < K1.item() < 1.0e-5
    assert 1.0e-10 < K2.item() < 1.0e-8


def test_KB_and_BT_magnitudes() -> None:
    """KB ~ 2e-9 mol/kg, BT ~ 4e-4 mol/kg at S=35 (Dickson + Uppström)."""
    KB = KB_boric(torch.tensor(15.0), torch.tensor(35.0))
    BT = BT_total_boron(torch.tensor(35.0))
    assert 1.0e-10 < KB.item() < 1.0e-8
    assert 3.0e-4 < BT.item() < 5.0e-4


def test_schmidt_number_in_expected_range() -> None:
    """Sc for CO₂ at T=15°C ≈ 800–1000 (Wanninkhof 2014)."""
    Sc = schmidt_number_co2(torch.tensor(15.0))
    assert 800.0 < Sc.item() < 1000.0


def test_solve_carbonate_surface_ocean_reference(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Solver returns physically plausible pH and pCO₂ at climatological inputs."""
    out = solve_carbonate(**surface_ocean_inputs)
    assert torch.isfinite(out["pH"]).all()
    assert torch.isfinite(out["pCO2"]).all()
    assert 7.8 < out["pH"].item() < 8.3, f"pH = {out['pH'].item():.3f} outside surface range"
    assert 200.0 < out["pCO2"].item() < 500.0, f"pCO₂ = {out['pCO2'].item():.1f} µatm out of range"


def test_solve_carbonate_pCO2_increases_with_DIC(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Adding DIC at fixed ALK/T/S increases pCO₂ (Revelle-like response)."""
    base = solve_carbonate(**surface_ocean_inputs)
    perturbed = dict(surface_ocean_inputs)
    perturbed["DIC"] = surface_ocean_inputs["DIC"] + 50.0
    out = solve_carbonate(**perturbed)
    assert out["pCO2"].item() > base["pCO2"].item()


def test_solve_carbonate_pCO2_decreases_with_ALK(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Adding ALK at fixed DIC/T/S decreases pCO₂."""
    base = solve_carbonate(**surface_ocean_inputs)
    perturbed = dict(surface_ocean_inputs)
    perturbed["ALK"] = surface_ocean_inputs["ALK"] + 50.0
    out = solve_carbonate(**perturbed)
    assert out["pCO2"].item() < base["pCO2"].item()


def test_solve_carbonate_autograd_flows(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Gradient flows from pCO₂ back to DIC and ALK with correct signs."""
    DIC = surface_ocean_inputs["DIC"].clone().requires_grad_(True)
    ALK = surface_ocean_inputs["ALK"].clone().requires_grad_(True)
    out = solve_carbonate(DIC, ALK, surface_ocean_inputs["T"], surface_ocean_inputs["S"])
    out["pCO2"].backward()
    assert DIC.grad is not None and torch.isfinite(DIC.grad).all()
    assert ALK.grad is not None and torch.isfinite(ALK.grad).all()
    assert DIC.grad.item() > 0.0, "∂pCO₂/∂DIC should be positive"
    assert ALK.grad.item() < 0.0, "∂pCO₂/∂ALK should be negative"


def test_solve_carbonate_broadcasts_over_2d_grid() -> None:
    """Solver handles (H, W) tensors for spatial fits — critical for nb20."""
    H, W = 10, 15
    DIC = torch.full((H, W), 2050.0 * 1.025)
    ALK = torch.full((H, W), 2350.0 * 1.025)
    T = torch.full((H, W), 15.0)
    S = torch.full((H, W), 35.0)
    out = solve_carbonate(DIC, ALK, T, S)
    assert out["pCO2"].shape == (H, W)
    assert torch.isfinite(out["pCO2"]).all()
    assert (out["pH"] > 7.5).all() and (out["pH"] < 8.5).all()


def test_solve_carbonate_iter_convergence(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Default n_iter=5 gives <0.5% pCO₂ residual vs. fully converged.

    Follows 2006 shows geometric convergence; the binding precision floor is the
    1–3% uncertainty in the equilibrium constants themselves, so chasing tighter
    iteration residual is wasted compute. This pins the default n_iter choice
    against that physical accuracy threshold.
    """
    out5 = solve_carbonate(**surface_ocean_inputs, n_iter=5)
    out20 = solve_carbonate(**surface_ocean_inputs, n_iter=20)
    rel_diff = abs(out20["pCO2"].item() - out5["pCO2"].item()) / out5["pCO2"].item()
    assert rel_diff < 5.0e-3, f"5-iter residual {rel_diff:.2e} exceeds 0.5% threshold"


def test_solve_carbonate_monotone_convergence(
    surface_ocean_inputs: dict[str, torch.Tensor],
) -> None:
    """Residual shrinks monotonically with iteration count — the scheme converges."""
    converged = solve_carbonate(**surface_ocean_inputs, n_iter=50)["pCO2"].item()
    residuals = []
    for n in [2, 3, 5, 8, 15]:
        out = solve_carbonate(**surface_ocean_inputs, n_iter=n)
        residuals.append(abs(out["pCO2"].item() - converged) / converged)
    for i in range(len(residuals) - 1):
        assert residuals[i + 1] < residuals[i], (
            f"Residual not monotonically shrinking: {residuals}"
        )


def test_co2_flux_zero_at_equilibrium() -> None:
    """No flux when ocean pCO₂ matches atmospheric (delta = 0)."""
    F = co2_flux(
        pCO2_ocean=torch.tensor(PCO2_ATM_DEFAULT),
        pCO2_atm=PCO2_ATM_DEFAULT,
        wind_speed=torch.tensor(7.0),
        T=torch.tensor(15.0),
        S=torch.tensor(35.0),
    )
    assert abs(F.item()) < 1.0e-12


def test_co2_flux_outgassing_when_supersaturated() -> None:
    """Positive flux (ocean → atmosphere) when ocean pCO₂ exceeds atmospheric."""
    F = co2_flux(
        pCO2_ocean=torch.tensor(500.0),
        pCO2_atm=PCO2_ATM_DEFAULT,
        wind_speed=torch.tensor(7.0),
        T=torch.tensor(15.0),
        S=torch.tensor(35.0),
    )
    assert F.item() > 0.0


def test_co2_flux_uptake_when_undersaturated() -> None:
    """Negative flux (atmosphere → ocean) when ocean pCO₂ below atmospheric."""
    F = co2_flux(
        pCO2_ocean=torch.tensor(300.0),
        pCO2_atm=PCO2_ATM_DEFAULT,
        wind_speed=torch.tensor(7.0),
        T=torch.tensor(15.0),
        S=torch.tensor(35.0),
    )
    assert F.item() < 0.0


def test_co2_flux_magnitude_in_typical_range() -> None:
    """At U=7 m/s and ΔpCO₂ = 100 µatm, flux magnitude is order 1e-4 mmol/m²/s.

    Sanity check against typical air-sea flux values (~few mmol/m²/day).
    """
    F = co2_flux(
        pCO2_ocean=torch.tensor(PCO2_ATM_DEFAULT + 100.0),
        pCO2_atm=PCO2_ATM_DEFAULT,
        wind_speed=torch.tensor(7.0),
        T=torch.tensor(15.0),
        S=torch.tensor(35.0),
    )
    # ~1e-4 mmol/m²/s ≈ 8.6 mmol/m²/day — within the global ocean range
    assert 1.0e-5 < abs(F.item()) < 1.0e-3
