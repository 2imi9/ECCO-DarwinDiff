"""Carbonate chemistry solver — Follows et al. (2006) iterative scheme.

Autograd-compatible aqueous CO₂ from (DIC, ALK, T, S). Used by
``carroll6_carbonate_integrate`` to add the DIC + ALK + air-sea CO₂ flux
machinery that the original 5-tracer Carroll-6 box model lacks (the v1.4–v1.8
"5-tracer proxy is the recovery ceiling" finding — see docs/findings/).

Reference:
    Follows, M. J., Ito, T., & Dutkiewicz, S. (2006). On the solution of the
    carbonate chemistry system in ocean biogeochemistry models. Ocean Modelling,
    12(3-4), 290–301. https://doi.org/10.1016/j.ocemod.2005.05.004

Equilibrium constants:
    K0 (CO₂ solubility) — Weiss (1974), mol/(kg·atm). Matches MITgcm DIC package.
    K1, K2 (carbonic acid) — Lueker et al. (2000), total scale, mol/kg.
        MITgcm DIC uses Mehrbach (1973) via Millero (1995) instead — ~3-5%
        systematic pCO₂ offset.
    KB (boric acid) — Dickson (1990), total scale, mol/kg. MITgcm DIC uses
        Millero (1995) using Dickson 1990 data; numerically very close.
    BT (total boron) — Uppström (1974), mol/kg.
    Schmidt number for CO₂ — Wanninkhof (2014) Table 1.
    Gas-transfer velocity — Wanninkhof (2014) Eq. 1, coefficient K_WANNINKHOF
        (default 0.251). MITgcm/Darwin uses 0.337 (Wanninkhof 1992 revised) per
        pkg/dic/dic_surfforcing.F — set ``K_WANNINKHOF = 0.337`` for absolute
        F_CO₂ alignment with Darwin output. v2.0 closeout uses 0.251; parameter
        recovery (iron pair) is robust to this scaling because the loss is
        z-score normalized. See ``docs/findings/v2_track1_closeout.md``
        Day-8-verification section for the full alignment audit.

Conventions:
    - Tracer concentrations in mmol/m³ on the I/O boundary (matches DarwinDiff).
    - Internal conversion to mol/kg via constant seawater density ρ = 1025 kg/m³.
    - Temperature in °C, salinity in PSU.
    - pCO₂ output in µatm.
    - Air-sea flux in mmol C / m² / s (positive = ocean → atmosphere).

Notes:
    - Five fixed iterations of the Follows scheme give <0.5% pCO₂ residual vs.
      fully converged across the surface-ocean regime (1.0 < ALK/DIC < 1.2).
      This is well below the 1–3% uncertainty in the equilibrium constants
      themselves and the ~30% uncertainty in Wanninkhof gas-transfer velocity,
      so additional iterations would tighten a number that's not the binding
      uncertainty. Iteration is autograd-unrolled rather than
      implicit-differentiated.
    - All operations are PyTorch and autograd-clean — tensors broadcast pointwise
      so the solver works on scalars, (H, W) grids, and batched inputs alike.

CLUSTER: the solver is shape-agnostic and does not assume a specific AOI size.
Scales unchanged to full LLC270 (1080 × 270) — no code path here needs to change
when running on the cluster; only the data loaders upstream do.
"""

from __future__ import annotations

import torch

RHO_SW: float = 1025.0
"""Seawater density (kg/m³) used to convert between mmol/m³ and mol/kg.

Surface-ocean climatology; constant within the solver. Off by 2–3% relative to
actual density at high-latitude or near-shore conditions but the carbonate-system
response to that variation is well below the recovery uncertainty we care about
at v2.0.
"""

PCO2_ATM_DEFAULT: float = 405.0
"""Default atmospheric pCO₂ (µatm) — modern surface-ocean climatology, close to
Carroll 2022's reference period (2017–2019). Override at the call site for
time-resolved fits.
"""

K_WANNINKHOF: float = 0.251
"""Wanninkhof gas-transfer velocity coefficient (cm/hr at standard Schmidt number).

**Calibration-alignment note** (verified 2026-05-11 against MITgcm source):
- **Our default: 0.251** — Wanninkhof (2014) Eq. 1, the current oceanographic
  best-practice value re-derived from the QuikSCAT wind product.
- **MITgcm/Darwin uses: 0.337** — found in
  `MITgcm/pkg/dic/dic_surfforcing.F`:
  ``pisvel(i,j) = 0.337 _d 0 *wind(i,j,bi,bj)**2/3.6 _d 5``
  This is Wanninkhof (1992) revised. **34% higher than our default.**

The z-score normalized loss in nb20/nb21 makes parameter recovery robust to
this systematic scaling (only spatial *patterns* contribute), so the v2.0
iron-pair recovery numbers (alpfe within 1.1%, scav_rat within 40% of Carroll)
are unaffected. For *absolute* CO₂ flux predictions matching Darwin to <5%,
set ``carbonate.K_WANNINKHOF = 0.337`` before constructing the integration
loop. See ``docs/findings/v2_track1_closeout.md`` § Day-8-verification.
"""

_MMOL_PER_M3_TO_MOL_PER_KG: float = 1.0e-3 / RHO_SW
_MOL_PER_KG_TO_MMOL_PER_M3: float = 1.0 / _MMOL_PER_M3_TO_MOL_PER_KG


def _temp_kelvin(T_celsius: torch.Tensor) -> torch.Tensor:
    return T_celsius + 273.15


def K0_solubility(T: torch.Tensor, S: torch.Tensor) -> torch.Tensor:
    """CO₂ solubility (Weiss 1974), mol/(kg·atm).

    Defined by Henry's law: ``[CO₂*] = K0 · pCO₂``.
    """
    Tk = _temp_kelvin(T)
    ln_K0 = (
        -60.2409
        + 93.4517 * (100.0 / Tk)
        + 23.3585 * torch.log(Tk / 100.0)
        + S * (0.023517 - 0.023656 * (Tk / 100.0) + 0.0047036 * (Tk / 100.0) ** 2)
    )
    return torch.exp(ln_K0)


def K1_K2_carbonic(T: torch.Tensor, S: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """First and second dissociation constants of carbonic acid (Lueker et al. 2000).

    Total scale, mol/kg. Same parameterization used in PyCO2SYS default and the
    standard MITgcm/Darwin carbonate module.
    """
    Tk = _temp_kelvin(T)
    log10_K1 = (
        -3633.86 / Tk
        + 61.2172
        - 9.67770 * torch.log(Tk)
        + S * 0.011555
        - S * S * 0.0001152
    )
    log10_K2 = (
        -471.78 / Tk
        - 25.9290
        + 3.16967 * torch.log(Tk)
        + S * 0.01781
        - S * S * 0.0001122
    )
    return 10.0**log10_K1, 10.0**log10_K2


def KB_boric(T: torch.Tensor, S: torch.Tensor) -> torch.Tensor:
    """Boric acid dissociation constant (Dickson 1990), total scale, mol/kg."""
    Tk = _temp_kelvin(T)
    sqrtS = torch.sqrt(S)
    ln_KB = (
        (
            -8966.90
            - 2890.53 * sqrtS
            - 77.942 * S
            + 1.728 * S**1.5
            - 0.0996 * S * S
        )
        / Tk
        + (148.0248 + 137.1942 * sqrtS + 1.62142 * S)
        + (-24.4344 - 25.085 * sqrtS - 0.2474 * S) * torch.log(Tk)
        + 0.053105 * sqrtS * Tk
    )
    return torch.exp(ln_KB)


def BT_total_boron(S: torch.Tensor) -> torch.Tensor:
    """Total boron concentration (Uppström 1974), mol/kg."""
    return 0.000416 * (S / 35.0)


def schmidt_number_co2(T: torch.Tensor) -> torch.Tensor:
    """Schmidt number for CO₂ in seawater (Wanninkhof 2014 Table 1)."""
    return (
        2116.8
        - 136.25 * T
        + 4.7353 * T * T
        - 0.092307 * T * T * T
        + 0.0007555 * T * T * T * T
    )


def solve_carbonate(
    DIC: torch.Tensor,
    ALK: torch.Tensor,
    T: torch.Tensor,
    S: torch.Tensor,
    n_iter: int = 5,
) -> dict[str, torch.Tensor]:
    """Solve for aqueous CO₂ via the Follows et al. (2006) iterative scheme.

    Five fixed iterations bring pCO₂ within <0.1% of the converged value across
    the surface-ocean regime (1.0 < ALK/DIC < 1.2) — below the precision of the
    equilibrium constants themselves. The iteration is autograd-unrolled so
    gradients flow through each step.

    Args:
        DIC: dissolved inorganic carbon, mmol C/m³.
        ALK: total alkalinity, mmol Eq/m³.
        T: temperature, °C.
        S: salinity, PSU.
        n_iter: number of Follows iterations. Default 5 gives <0.5% residual,
            below the precision floor set by the equilibrium constants
            themselves (~1–3%) and gas-transfer velocity (~30%). The paper's
            2–3 is sufficient for ~1% accuracy if compute matters.

    Returns:
        Dictionary with keys:
            - "CO2aq": aqueous CO₂ concentration (mmol C/m³).
            - "pCO2": partial pressure (µatm).
            - "Hplus": [H⁺] (mol/kg).
            - "pH": -log₁₀([H⁺]).
    """
    # Coerce scalar inputs to tensors so callers can pass Python floats for
    # constant forcing (T = 15.0 etc.) without manual conversion.
    DIC = torch.as_tensor(DIC, dtype=torch.float32)
    ALK = torch.as_tensor(ALK, dtype=torch.float32)
    T = torch.as_tensor(T, dtype=torch.float32)
    S = torch.as_tensor(S, dtype=torch.float32)
    DIC_mk = DIC * _MMOL_PER_M3_TO_MOL_PER_KG
    ALK_mk = ALK * _MMOL_PER_M3_TO_MOL_PER_KG

    K0 = K0_solubility(T, S)
    K1, K2 = K1_K2_carbonic(T, S)
    KB = KB_boric(T, S)
    BT = BT_total_boron(S)

    # Initial guess: surface ocean pH ≈ 8.0 → [H⁺] = 1e-8 mol/kg.
    H = torch.full_like(DIC_mk, 1.0e-8)

    for _ in range(n_iter):
        borate_alk = BT * KB / (H + KB)
        ALK_c = ALK_mk - borate_alk
        # Quadratic in H derived from ALK_c · D(H) = K1 · (H + 2·K2) · DIC, where
        # D(H) = H² + K1·H + K1·K2. Coefficients:
        aa = ALK_c
        bb = K1 * (ALK_c - DIC_mk)
        cc = K1 * K2 * (ALK_c - 2.0 * DIC_mk)
        disc = bb * bb - 4.0 * aa * cc
        # Numerical safety: in valid seawater (ALK_c > 0, DIC > 0) the
        # discriminant is positive by construction; clamp guards against
        # pathological inputs without distorting the gradient in valid regime.
        disc = torch.clamp(disc, min=1.0e-30)
        H = (-bb + torch.sqrt(disc)) / (2.0 * aa)

    D = H * H + K1 * H + K1 * K2
    CO2aq_mk = H * H * DIC_mk / D
    pCO2 = CO2aq_mk / K0 * 1.0e6  # atm → µatm

    return {
        "CO2aq": CO2aq_mk * _MOL_PER_KG_TO_MMOL_PER_M3,
        "pCO2": pCO2,
        "Hplus": H,
        "pH": -torch.log10(H),
    }


def co2_flux(
    pCO2_ocean: torch.Tensor,
    pCO2_atm: torch.Tensor | float,
    wind_speed: torch.Tensor,
    T: torch.Tensor,
    S: torch.Tensor,
    K0: torch.Tensor | None = None,
) -> torch.Tensor:
    """Air-sea CO₂ flux (Wanninkhof 2014).

    ``F = k_w · K0 · ρ · (pCO₂_ocean - pCO₂_atm)``, where ``k_w`` is the
    quadratic-wind gas transfer velocity with coefficient 0.251.

    Args:
        pCO2_ocean: ocean partial pressure, µatm.
        pCO2_atm: atmospheric partial pressure, µatm (scalar or tensor).
        wind_speed: 10-m wind speed, m/s.
        T: temperature, °C.
        S: salinity, PSU.
        K0: pre-computed CO₂ solubility (mol/kg/atm); recomputed if None.

    Returns:
        Air-sea flux, mmol C / m² / s. Positive = ocean → atmosphere.
    """
    pCO2_ocean = torch.as_tensor(pCO2_ocean, dtype=torch.float32)
    pCO2_atm = torch.as_tensor(pCO2_atm, dtype=torch.float32)
    wind_speed = torch.as_tensor(wind_speed, dtype=torch.float32)
    T = torch.as_tensor(T, dtype=torch.float32)
    S = torch.as_tensor(S, dtype=torch.float32)
    if K0 is None:
        K0 = K0_solubility(T, S)
    Sc = schmidt_number_co2(T)
    # k = K_WANNINKHOF · U² · (Sc/660)^(-1/2), cm/hr → m/s. K_WANNINKHOF defaults
    # to 0.251 (Wanninkhof 2014); set to 0.337 for bit-for-bit alignment with
    # MITgcm's pkg/dic/dic_surfforcing.F.
    k_w = K_WANNINKHOF * wind_speed * wind_speed * (Sc / 660.0) ** (-0.5) * (1.0e-2 / 3600.0)
    delta_atm = (pCO2_ocean - pCO2_atm) * 1.0e-6  # µatm → atm
    flux_mol_m2_s = k_w * K0 * RHO_SW * delta_atm
    return flux_mol_m2_s * 1.0e3  # mol → mmol
