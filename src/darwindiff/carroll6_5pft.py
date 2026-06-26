"""Carroll-6 + 5-PFT box model — Phase 2 of the v2.x calibration arc.

Extends ``carroll6_carbonate_step`` from 2 lumped phytoplankton tracers
(``Ps`` = small, ``Pl`` = large) to 5 phytoplankton functional types matching
the Darwin 3 v05 setup used by Carroll 2022. Addresses the box-model
bottleneck that v2.0 (gradient-based recovery) and v2.1 Phase 1 (GLODAP
real-obs target swap) both confirmed: the 4-of-6 parameter drift is rooted
in lumping species with different physical parameter values into one tracer.

State vector (10 tracers, "large-to-small" ordering per Carroll 2022 abstract;
matches the ``Chl1``..``Chl5`` index convention exposed by
``ecco_darwin_loader.total_chlorophyll``):

    state[0] = DFe       — dissolved iron (mmol Fe/m^3)
    state[1] = P_diatom  — diatoms                        (Chl1)
    state[2] = P_lge     — other large eukaryotes         (Chl2)
    state[3] = P_syn     — Synechococcus                  (Chl3)
    state[4] = P_proLL   — low-light Prochlorococcus      (Chl4)
    state[5] = P_proHL   — high-light Prochlorococcus     (Chl5)
    state[6] = POC, state[7] = PIC, state[8] = DIC, state[9] = ALK

Carroll-6 → PFT mapping (Option A: 6 learnable parameters, each governing
a single specific PFT instead of an average over multiple species):

    1. alpfe       — iron dust solubility               (global, unchanged)
    2. scav_rat    — iron scavenging rate               (global, unchanged)
    3. Smallgrow   — growth rate of **Pro-HL** specifically
                     (dominant small PFT — 47% of total Chl in Eq Pacific
                     surface time-mean per ``scripts/phase2_p4_p5_check.py``)
    4. Biggrow     — growth rate of **other large eukaryotes** specifically
                     (diatoms have their own grazing parameter ``diatomgraz``)
    5. diatomgraz  — diatom palatability/grazing rate
    6. R_PICPOC    — PIC/POC ratio                       (global, unchanged)

The 4 non-learned PFTs (Pro-LL, Syn, diatoms-growth, large-euks-growth-when-
``Biggrow``-is-mapped-elsewhere) use literature default growth rates equal
to the corresponding Carroll-2020 published value. This is the same effective
calibration as the 2-PFT box for those species; the only change is that the
LEARNED parameter now constrains a single specific PFT instead of an average.

Hypothesis (the Phase 2 expected gain): all 4 currently-drifting parameters
(Smallgrow, Biggrow, diatomgraz, R_PICPOC) recover toward calibration-grade
because each governs exactly one species' dynamics — matching the iron-pair
quality (~1% / 40% off Carroll) the v2.0 box achieved for ``alpfe`` /
``scav_rat`` for the same reason.

Background defaults (M_LIN, M_QUAD, G0_GRAZE, W_SINK, K_FE, PHI_DUST, Q_FE,
LIGHT, H_MLD) are shared across all 5 PFTs for the v2.2 minimum-viable scope.
Per-PFT half-saturation constants and per-PFT mortalities are deferred to
v2.2.1 (Dutkiewicz et al. 2009 Table 1) if growth-rate-alone doesn't close
the gap.

Used by notebook 23 (5-PFT recovery on Eq Pacific) — see ``scripts/build_nb23.py``.
"""

from __future__ import annotations

import torch

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate
from darwindiff.carroll6 import (
    G0_GRAZE,
    H_MLD,
    K_FE,
    LIGHT,
    M_LIN,
    M_QUAD,
    PARAM_INDEX,
    PHI_DUST,
    Q_FE,
    W_SINK,
)

# --- State vector layout ------------------------------------------------------

I_DFE = 0
I_DIATOM = 1
I_LGE = 2
I_SYN = 3
I_PROLL = 4
I_PROHL = 5
I_POC = 6
I_PIC = 7
I_DIC = 8
I_ALK = 9

N_TRACERS = 10
N_PHYTO = 5

# --- Carroll-6 parameter layout (derived from the carroll6.py registry) -------
# Named param-vector indices, looked up by name from carroll6.PARAMS (the single
# source of truth) so they track the registry order automatically and a reader
# never counts positions. The PFT each learned rate governs is noted alongside.

I_ALPFE = PARAM_INDEX["alpfe"]
I_SCAV_RAT = PARAM_INDEX["scav_rat"]
I_SMALLGROW = PARAM_INDEX["Smallgrow"]    # learned on Pro-HL
I_BIGGROW = PARAM_INDEX["Biggrow"]        # learned on other large euks
I_DIATOMGRAZ = PARAM_INDEX["diatomgraz"]  # learned on diatoms
I_R_PICPOC = PARAM_INDEX["R_PICPOC"]

# --- Default growth rates for the 4 non-learned PFTs --------------------------
# Placeholders matching the Carroll-2020 published optima for the lumped
# species the original calibration averaged over. Replace with Dutkiewicz 2009
# Table 1 per-PFT values in v2.2.1 if a clean source is available.

MU_DEFAULT_DIATOM: float = 0.43148  # Carroll-2020 Biggrow optimum
MU_DEFAULT_SYN: float = 0.66098     # Carroll-2020 Smallgrow optimum
MU_DEFAULT_PROLL: float = 0.66098   # Carroll-2020 Smallgrow optimum


# Per-PFT iron half-saturation constants (v2.2.1 optional override).
#
# v2.2 minimum-viable scope used a shared K_FE = 5e-5 across all 5 PFTs.
# v2.2.1 introduces per-PFT half-saturations following the ocean BGC
# literature convention: small Prochlorococcus are highly Fe-efficient
# (oligotrophic surface specialists with very low K_Fe), diatoms are the
# least Fe-efficient (largest cells, high absolute demand, higher K_Fe).
#
# Values below are literature-PLAUSIBLE order-of-magnitude estimates
# (Pro-HL most efficient -> diatoms least efficient). They are NOT
# verified against Darwin 3 v05's actual data.traits values - that file
# is not on disk locally. The principle (per-PFT K_FE breaks the shared-
# half-saturation aliasing that pushes alpfe / scav_rat off-optimum)
# is what v2.2.1 tests; the exact numbers can be refined to Darwin-exact
# values in a follow-up once the namelist is accessible.
#
# Units: mmol Fe / m^3. For reference: 1 nM Fe = 1e-6 mmol Fe / m^3.

K_FE_PER_PFT_DIATOM: float = 1.0e-4   # ~100 nM (largest cells, highest demand)
K_FE_PER_PFT_LGE: float    = 6.0e-5   # ~60 nM (other large eukaryotes)
K_FE_PER_PFT_SYN: float    = 3.0e-5   # ~30 nM (Synechococcus, intermediate)
K_FE_PER_PFT_PROLL: float  = 1.0e-5   # ~10 nM (Pro low-light)
K_FE_PER_PFT_PROHL: float  = 5.0e-6   # ~5 nM (Pro high-light, oligotrophic)

K_FE_VEC_PERFT: tuple[float, float, float, float, float] = (
    K_FE_PER_PFT_DIATOM,
    K_FE_PER_PFT_LGE,
    K_FE_PER_PFT_SYN,
    K_FE_PER_PFT_PROLL,
    K_FE_PER_PFT_PROHL,
)
"""Per-PFT K_FE in state-vector order (diatom..Pro-HL). v2.2.1 default."""


def carroll6_5pft_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h_mld: float = H_MLD,
    k_fe_per_pft: tuple[float, float, float, float, float] | None = None,
    lumped_mapping: bool = False,
) -> torch.Tensor:
    """One forward-Euler step of the 10-tracer 5-PFT Carroll-6 box model.

    Args:
        state: shape ``[10]``, layout per module docstring.
        params: shape ``[6]``, same layout as ``carroll6.carroll6_step``
            (``[alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]``).
            ``Smallgrow`` is applied to Pro-HL only, ``Biggrow`` to other
            large eukaryotes only, ``diatomgraz`` to diatoms only.
        dt: time step in days.
        T, S, wind, pco2_atm, h_mld: identical to
            ``carroll6.carroll6_carbonate_step``.
        k_fe_per_pft: optional per-PFT iron half-saturations in state-vector
            order (diatom, large_euk, Syn, Pro-LL, Pro-HL), mmol Fe / m^3.
            ``None`` -> v2.2 minimum-viable behavior (shared ``K_FE``).
            ``K_FE_VEC_PERFT`` -> v2.2.1 literature-plausible per-PFT values.

    Returns:
        Next state, shape ``[10]``.
    """
    DFe = state[I_DFE]
    P_diatom = state[I_DIATOM]
    P_lge = state[I_LGE]
    P_syn = state[I_SYN]
    P_proLL = state[I_PROLL]
    P_proHL = state[I_PROHL]
    POC = state[I_POC]
    PIC = state[I_PIC]
    DIC = state[I_DIC]
    ALK = state[I_ALK]

    alpfe = params[I_ALPFE]
    scav_rat = params[I_SCAV_RAT]
    mu_proHL = params[I_SMALLGROW]
    mu_lge = params[I_BIGGROW]
    g_diatom = params[I_DIATOMGRAZ]
    R_PICPOC = params[I_R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0

    # Iron half-saturation: shared (v2.2) or per-PFT (v2.2.1).
    if k_fe_per_pft is None:
        f_fe_diatom = f_fe_lge = f_fe_syn = f_fe_proLL = f_fe_proHL = (
            DFe / (DFe + K_FE)
        )
    else:
        f_fe_diatom = DFe / (DFe + k_fe_per_pft[0])
        f_fe_lge    = DFe / (DFe + k_fe_per_pft[1])
        f_fe_syn    = DFe / (DFe + k_fe_per_pft[2])
        f_fe_proLL  = DFe / (DFe + k_fe_per_pft[3])
        f_fe_proHL  = DFe / (DFe + k_fe_per_pft[4])

    # Per-PFT growth:
    # - "specific" (default): Smallgrow learns Pro-HL only; Biggrow learns lge
    #   only; other 3 PFTs use Carroll-2020 defaults. Each Carroll-6 rate
    #   governs ONE species exactly.
    # - "lumped" (Carroll 2020 SI mapping): Smallgrow applies to ALL 3 small
    #   PFTs (Syn + Pro-LL + Pro-HL); Biggrow applies to BOTH large PFTs
    #   (diatoms + lge). This matches how Carroll's published Smallgrow=0.661
    #   and Biggrow=0.431 were calibrated as group-level parameters.
    if lumped_mapping:
        mu_for_diatom = mu_lge       # Biggrow → diatoms too
        mu_for_syn    = mu_proHL     # Smallgrow → Syn
        mu_for_proLL  = mu_proHL     # Smallgrow → Pro-LL
    else:
        mu_for_diatom = MU_DEFAULT_DIATOM
        mu_for_syn    = MU_DEFAULT_SYN
        mu_for_proLL  = MU_DEFAULT_PROLL
    growth_diatom = mu_for_diatom * f_fe_diatom * LIGHT * P_diatom
    growth_lge    = mu_lge         * f_fe_lge    * LIGHT * P_lge
    growth_syn    = mu_for_syn     * f_fe_syn    * LIGHT * P_syn
    growth_proLL  = mu_for_proLL   * f_fe_proLL  * LIGHT * P_proLL
    growth_proHL  = mu_proHL       * f_fe_proHL  * LIGHT * P_proHL
    growth_total = (
        growth_diatom + growth_lge + growth_syn + growth_proLL + growth_proHL
    )
    fe_uptake = Q_FE * growth_total

    # Shared mortality + grazing across 5 PFTs (v2.2 minimum-viable).
    mort_diatom = M_LIN * P_diatom + M_QUAD * P_diatom * P_diatom
    mort_lge = M_LIN * P_lge + M_QUAD * P_lge * P_lge
    mort_syn = M_LIN * P_syn + M_QUAD * P_syn * P_syn
    mort_proLL = M_LIN * P_proLL + M_QUAD * P_proLL * P_proLL
    mort_proHL = M_LIN * P_proHL + M_QUAD * P_proHL * P_proHL
    graze_diatom = g_diatom * G0_GRAZE * P_diatom

    mort_total = (
        mort_diatom + mort_lge + mort_syn + mort_proLL + mort_proHL + graze_diatom
    )

    # Iron + biology tendencies.
    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
    dP_diatom = growth_diatom - mort_diatom - graze_diatom
    dP_lge = growth_lge - mort_lge
    dP_syn = growth_syn - mort_syn
    dP_proLL = growth_proLL - mort_proLL
    dP_proHL = growth_proHL - mort_proHL
    dPOC = mort_total - W_SINK * POC
    dPIC = R_PICPOC * mort_total - W_SINK * PIC

    # Carbonate (identical to carroll6_carbonate_step).
    carb = solve_carbonate(DIC, ALK, T, S)
    F_co2 = co2_flux(carb["pCO2"], pco2_atm, wind, T, S)
    F_per_m3_per_day = F_co2 * 86400.0 / h_mld

    dDIC = (
        -growth_total                 # phyto C fixation across all 5 PFTs
        - R_PICPOC * mort_total       # CaCO3 formation
        - F_per_m3_per_day            # air-sea export
    )
    dALK = -2.0 * R_PICPOC * mort_total

    return torch.stack([
        DFe + dt * dDFe,
        P_diatom + dt * dP_diatom,
        P_lge + dt * dP_lge,
        P_syn + dt * dP_syn,
        P_proLL + dt * dP_proLL,
        P_proHL + dt * dP_proHL,
        POC + dt * dPOC,
        PIC + dt * dPIC,
        DIC + dt * dDIC,
        ALK + dt * dALK,
    ])


def carroll6_5pft_integrate(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int] | None = None,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h_mld: float = H_MLD,
    k_fe_per_pft: tuple[float, float, float, float, float] | None = None,
    lumped_mapping: bool = False,
) -> torch.Tensor:
    """Forward-Euler integration of the 5-PFT 10-tracer Carroll-6 + carbonate box.

    Mirrors ``carroll6.carroll6_carbonate_integrate`` (autograd-clean through
    every step) with the 10-tracer state vector.

    Args:
        state0: initial 10-tracer state.
        params: Carroll-6 parameters, shape ``[6]``.
        dt: time step in days.
        n_steps: number of forward-Euler steps.
        snapshot_indices: 1-indexed steps at which to save state. If ``None``,
            returns only the final state; otherwise returns shape
            ``[len(snapshot_indices), 10]``.
        T, S, wind, pco2_atm, h_mld: forcing — see
            ``carroll6_5pft_step``.
        k_fe_per_pft: optional per-PFT iron half-saturations (v2.2.1).
            ``None`` -> shared K_FE (v2.2 default).

    Returns:
        Final state shape ``[10]`` when ``snapshot_indices is None``, else
        stacked snapshots.
    """
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = carroll6_5pft_step(
                state, params, dt, T, S, wind, pco2_atm, h_mld, k_fe_per_pft, lumped_mapping,
            )
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = carroll6_5pft_step(
            state, params, dt, T, S, wind, pco2_atm, h_mld, k_fe_per_pft, lumped_mapping,
        )
        if step in snapshot_set:
            snaps.append(state)
    return torch.stack(snaps)
