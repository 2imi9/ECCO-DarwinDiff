"""Carroll-6 + 5-PFT box model — v2.7 2-layer extension.

Extends ``carroll6_5pft`` from a single surface layer (0-50 m) to a 2-layer
column (surface 0-50 m + subsurface 50-1000 m). The motivation is the v2.6
GEOTRACES finding: ``scav_rat`` sits at 0.89-0.92 off Carroll across all
GEOTRACES surface weights because ``alpfe`` (surface source) and ``scav_rat``
(particle-mediated sink) are linearly degenerate in a surface-only iron budget.
The subsurface DFe gradient is the physics that breaks the degeneracy:
``alpfe`` only injects iron at the surface, while ``scav_rat`` removes iron
throughout the water column wherever POC sinks.

See ``docs/findings/v2.7_multilayer_box_scoping.md`` for the full design.

**State vector (15 tracers).** L1 hosts all biology + surface dust; L2 hosts
only the inorganic tracers (no light at depth, so phytoplankton fixed at 0):

    L1 (surface, 0-50 m):
      state[0] = DFe_1     state[1] = P_diatom   state[2] = P_lge
      state[3] = P_syn     state[4] = P_proLL    state[5] = P_proHL
      state[6] = POC_1     state[7] = PIC_1
      state[8] = DIC_1     state[9] = ALK_1
    L2 (subsurface, 50-1000 m):
      state[10] = DFe_2
      state[11] = POC_2    state[12] = PIC_2
      state[13] = DIC_2    state[14] = ALK_2

The L1 sub-block exactly mirrors ``carroll6_5pft`` (10 tracers) so the
``carroll6_5pft_integrate``-compatible surface diagnostics still work
when L1 alone is read out.

**Vertical coupling (the new physics).**

**Iron accounting (v2.7.1, post-Greptile-P1 fix).** Iron leaves DFe_1 via
biological uptake ``fe_uptake = Q_FE * growth_total`` only. Iron is
NOT also explicitly subtracted at the sinking-POC rate — that would
double-count the same iron pathway, because the model does not track
Fe-on-POC as a separate tracer. The phyto → POC → sinking-POC iron
path is therefore implicit; iron re-enters the dissolved pool ONLY at
L2 remineralisation, via ``fe_remin_L2 = Q_FE_REMIN * R_REMIN * POC_2``.
Whatever fraction of sinking POC does not remineralise in L2 is lost
to deep (consistent with the W_SINK * POC_2 → 0 boundary assumption).
This corrects the v2.7.0 pre-fix integrator that subtracted both
fe_uptake AND fe_sink_out_L1 from DFe_1 and double-counted L2 ingress.

**Vertical eddy diffusion** across the thermocline at ``Kz = 1e-5 m^2/s``
(Whalen et al. 2012 typical thermocline value). Per-area flux =
``Kz * (DFe_2 - DFe_1) / dz_int``, where ``dz_int = (h1+h2)/2``.
Order-of-magnitude check: with the observed Eq Pac gradient of
~0.4 nmol/kg the diffusive flux is ~1000x smaller than the dust source;
included for completeness but not the dominant coupling.

**Remineralization in L2.** Sinking POC is broken down by bacteria at
``R_REMIN = 0.05/day`` (Martin curve b ≈ 0.86; ~200 m remineralization
length scale in the upper twilight zone). Remineralization releases the
iron that was implicit on the sinking POC back to DFe_2 at the rate
``Q_FE_REMIN * R_REMIN * POC_2``. This is the SOLE iron return path to
L2 in v2.7.1.

**Parameter interpretation (unchanged from v2.6).** The 6 learnable params
(``[alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]``) keep their
v2.6 meaning. ``scav_rat`` now acts in BOTH layers (proportional to local
``DFe * POC``); this is the new constraint surface that the subsurface
GEOTRACES loss term targets.

Used by ``scripts/run_v2.7_multilayer_quick.py``.
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
    PHI_DUST,
    Q_FE,
    W_SINK,
)
from darwindiff.carroll6_5pft import (
    I_ALPFE,
    I_BIGGROW,
    I_DIATOMGRAZ,
    I_R_PICPOC,
    I_SCAV_RAT,
    I_SMALLGROW,
    MU_DEFAULT_DIATOM,
    MU_DEFAULT_PROLL,
    MU_DEFAULT_SYN,
)

# --- L1 state indices (mirror carroll6_5pft 0..9 exactly) ---------------------

I_DFE_1 = 0
I_DIATOM = 1
I_LGE = 2
I_SYN = 3
I_PROLL = 4
I_PROHL = 5
I_POC_1 = 6
I_PIC_1 = 7
I_DIC_1 = 8
I_ALK_1 = 9

# --- L2 state indices (5 inorganic tracers) -----------------------------------

I_DFE_2 = 10
I_POC_2 = 11
I_PIC_2 = 12
I_DIC_2 = 13
I_ALK_2 = 14

N_TRACERS_2LAYER = 15
N_PHYTO = 5  # only L1 has biology

# --- Layer geometry -----------------------------------------------------------

H1: float = 50.0   # surface layer thickness (m) — matches v2.6 H_MLD
H2: float = 950.0  # subsurface layer thickness (m), 50-1000 m
DZ_INT: float = (H1 + H2) / 2.0  # vertical distance between layer midpoints (m)

# --- Vertical coupling constants (NEW vs v2.6) --------------------------------

KZ_M2_PER_S: float = 1.0e-5
"""Vertical eddy diffusivity (m^2 / s). Typical thermocline value
(Whalen et al. 2012 Nature)."""

KZ_M2_PER_DAY: float = KZ_M2_PER_S * 86400.0
"""Same as :data:`KZ_M2_PER_S` converted to per-day for consistency with
the rest of the model (all tendencies are in 1/day)."""

R_REMIN: float = 0.05
"""Subsurface POC remineralization rate (1/day). Martin-curve consistent
b≈0.86 with ~200 m remineralization length in the upper twilight zone."""

Q_FE_SINK: float = Q_FE
"""Fe:POC stoichiometry of sinking particles (mol Fe / mol C). Same as the
phytoplankton Fe quota at scoping precision — detritus retains the cell-bound
ratio. v2.7 default; could be refined to a higher remineralized ratio (Boyd
& Ellwood 2010) in a follow-up."""

Q_FE_REMIN: float = Q_FE
"""Fe:POC stoichiometry released by remineralization (mol Fe / mol C). Same
as Q_FE_SINK at scoping precision: iron and carbon return to dissolved phase
in the same proportion they were exported."""

USE_COCCOLITH_ONLY_CALCITE: bool = False
"""Restrict PIC production (and the matching DIC + ALK calcite budget terms)
to the Chl2 = "other large eukaryote" mortality source only, instead of the
sum over all 5 PFTs.

In Darwin 3, only coccolithophores produce calcite. The 5-PFT mapping used
here treats Chl2 as the coccolithophore-proxy pool. Empirical Darwin v05
PIC/POC ratio (verified 2026-05-18): eqpac median 0.031, natlsubpolar median
0.722 — a 23x variance that the global ``mort_total_1`` scaling could not
satisfy with a single R_PICPOC scalar. With PFT-specific scaling the cross-AOI
PIC differences come naturally from P_lge abundance.

Module flag (resolved by torch.compile at trace time, so set BEFORE compile).
Default ``False`` -> legacy ``mort_total_1`` behaviour reproduces.
Pair with ``PIC_ABS_W > 0`` to anchor PIC magnitude; otherwise the optimizer
finds a degenerate (R_PICPOC, mort_lge) pair that satisfies the z-scored PIC
loss at any scale."""


def carroll6_5pft_2layer_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h1: float = H1,
    h2: float = H2,
    kz_m2_per_day: float = KZ_M2_PER_DAY,
    r_remin: float = R_REMIN,
) -> torch.Tensor:
    """One forward-Euler step of the 15-tracer 2-layer Carroll-6 box model.

    Args:
        state: shape ``[15]`` (or broadcasted leading dims), layout per
            module docstring.
        params: shape ``[6]``, identical layout to
            ``carroll6_5pft.carroll6_5pft_step``
            (``[alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]``).
        dt: time step in days.
        T, S, wind, pco2_atm: forcing fields (broadcast to spatial shape).
            v2.7 applies the SAME T/S/wind/pco2_atm to both layers — this
            is a deliberate simplification (subsurface T/S/light differ from
            surface but the L2 carbonate solve is decoupled from biology, so
            the effect on the iron recovery is minor). Refine in v2.8 if
            needed.
        h1, h2: layer thicknesses in meters. Default ``(50, 950)``.
        kz_m2_per_day: vertical eddy diffusivity in m^2/day. Default
            :data:`KZ_M2_PER_DAY`.
        r_remin: subsurface POC remineralization rate (1/day). Default
            :data:`R_REMIN`.

    Returns:
        Next state, same shape as ``state``.
    """
    DFe_1 = state[I_DFE_1]
    P_diatom = state[I_DIATOM]
    P_lge = state[I_LGE]
    P_syn = state[I_SYN]
    P_proLL = state[I_PROLL]
    P_proHL = state[I_PROHL]
    POC_1 = state[I_POC_1]
    PIC_1 = state[I_PIC_1]
    DIC_1 = state[I_DIC_1]
    ALK_1 = state[I_ALK_1]

    DFe_2 = state[I_DFE_2]
    POC_2 = state[I_POC_2]
    PIC_2 = state[I_PIC_2]
    DIC_2 = state[I_DIC_2]
    ALK_2 = state[I_ALK_2]

    alpfe = params[I_ALPFE]
    scav_rat = params[I_SCAV_RAT]
    mu_proHL = params[I_SMALLGROW]
    mu_lge = params[I_BIGGROW]
    g_diatom = params[I_DIATOMGRAZ]
    R_PICPOC = params[I_R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0

    # =========================================================================
    # L1 biology + iron + carbonate (mirrors carroll6_5pft_step)
    # =========================================================================

    # Iron limitation factor — shared K_FE across PFTs at scoping precision.
    # (Per-PFT K_FE is the v2.2.1 refinement; not used in v2.7 to keep the
    # multi-layer effect isolated.)
    f_fe = DFe_1 / (DFe_1 + K_FE)

    # Per-PFT growth (default: specific mapping per Carroll-6 → PFT spec).
    growth_diatom = MU_DEFAULT_DIATOM * f_fe * LIGHT * P_diatom
    growth_lge    = mu_lge            * f_fe * LIGHT * P_lge
    growth_syn    = MU_DEFAULT_SYN    * f_fe * LIGHT * P_syn
    growth_proLL  = MU_DEFAULT_PROLL  * f_fe * LIGHT * P_proLL
    growth_proHL  = mu_proHL          * f_fe * LIGHT * P_proHL
    growth_total = (
        growth_diatom + growth_lge + growth_syn + growth_proLL + growth_proHL
    )
    fe_uptake = Q_FE * growth_total

    # Mortality + grazing (shared M_LIN/M_QUAD/G0_GRAZE across 5 PFTs).
    mort_diatom = M_LIN * P_diatom + M_QUAD * P_diatom * P_diatom
    mort_lge    = M_LIN * P_lge    + M_QUAD * P_lge    * P_lge
    mort_syn    = M_LIN * P_syn    + M_QUAD * P_syn    * P_syn
    mort_proLL  = M_LIN * P_proLL  + M_QUAD * P_proLL  * P_proLL
    mort_proHL  = M_LIN * P_proHL  + M_QUAD * P_proHL  * P_proHL
    graze_diatom = g_diatom * G0_GRAZE * P_diatom
    mort_total_1 = (
        mort_diatom + mort_lge + mort_syn + mort_proLL + mort_proHL + graze_diatom
    )

    # =========================================================================
    # L1 ↔ L2 coupling fluxes (the NEW physics)
    # =========================================================================
    #
    # Iron accounting (v2.7.1 — corrects the double-count Greptile flagged
    # on PR #42 at e19a5d0). Iron leaves DFe_1 via biological uptake
    # ``fe_uptake = Q_FE * growth_total`` and is implicitly carried in the
    # phyto → POC → sinking-POC pathway. The model does NOT track Fe-on-POC
    # as a separate tracer, so we MUST NOT also subtract a per-volume
    # sinking-POC iron term from DFe_1 (that double-counts the same iron
    # that ``fe_uptake`` already removed). Symmetrically, L2 must NOT
    # receive a separate sinking-POC iron source -- the iron is implicit
    # in the sinking POC mass, and re-enters DFe_2 only when that POC
    # remineralises (``fe_remin_L2``). At steady state the conservation is:
    #     L1 lost via fe_uptake  ≈  Q_FE * growth_total
    #     L2 gained via fe_remin_L2 = Q_FE_REMIN * r_remin * POC_2
    # Mass that doesn't remineralise in L2 sinks further (lost to deep,
    # consistent with the W_SINK*POC_2 → 0 boundary assumption).

    # (a) Vertical eddy diffusion of DFe across the thermocline.
    fe_diff_flux_per_area = kz_m2_per_day * (DFe_2 - DFe_1) / DZ_INT  # mmol Fe/m^2/d
    fe_diff_L1 = fe_diff_flux_per_area / h1                          # into L1 if DFe_2>DFe_1
    fe_diff_L2 = -fe_diff_flux_per_area / h2                         # out of L2 if DFe_2>DFe_1

    # (b) POC sinking (same as v2.6) routes POC mass into L2. Iron content
    #     of the sinking POC is IMPLICIT — see iron-accounting comment above.
    poc_sink_out_L1 = W_SINK * POC_1                                 # mmol C/m^3/d in L1
    poc_sink_in_L2  = poc_sink_out_L1 * (h1 / h2)                    # into L2

    pic_sink_out_L1 = W_SINK * PIC_1
    pic_sink_in_L2  = pic_sink_out_L1 * (h1 / h2)

    # (c) Subsurface remineralization releases bound iron + carbon. This is
    #     the SOLE iron path back to dissolved phase in L2.
    poc_remin = r_remin * POC_2                                       # mmol C/m^3/d
    pic_dissolve = r_remin * PIC_2                                    # symmetric for PIC
    fe_remin_L2 = Q_FE_REMIN * poc_remin                              # mmol Fe/m^3/d

    # =========================================================================
    # L1 tendencies
    # =========================================================================

    dDFe_1 = (
        alpfe * PHI_DUST                                  # dust source (per-volume in v2.6 convention)
        - scav_rat_per_day * DFe_1 * POC_1                # surface scavenging
        - fe_uptake                                       # biology uptake (carries iron implicitly via POC to L2)
        + fe_diff_L1                                      # diffusive exchange with L2
    )
    dP_diatom = growth_diatom - mort_diatom - graze_diatom
    dP_lge    = growth_lge    - mort_lge
    dP_syn    = growth_syn    - mort_syn
    dP_proLL  = growth_proLL  - mort_proLL
    dP_proHL  = growth_proHL  - mort_proHL

    dPOC_1 = mort_total_1 - poc_sink_out_L1
    # PFT-specific calcite production (Path C, session 2026-05-18):
    # In Darwin 3, only coccolithophores produce calcite. In our 5-PFT mapping
    # Chl2 = "other large eukaryotes" includes the coccolithophore pool. So PIC
    # production scales with mort_lge (Chl2 mortality), NOT mort_total_1 (sum
    # across all 5 PFTs). This fixes the inter-AOI tension diagnosed this
    # session: empirical Darwin v05 PIC/POC ratio varies 23x between eqpac
    # (0.031, no coccolithophores) and natlsubpolar (0.722, coccolithophore
    # bloom zone). With PFT-specific scaling, natlsubpolar's high P_lge
    # naturally produces high PIC at a modest R_PICPOC; eqpac's low P_lge
    # produces low PIC at the SAME R_PICPOC -- removing the cross-AOI tension
    # the global mort_total scaling created. Gated by module-level flag
    # USE_COCCOLITH_ONLY_CALCITE (default False -> legacy mort_total behaviour
    # reproduces). Needs to be PAIRED with PIC_ABS_W > 0 to anchor PIC magnitude,
    # otherwise the optimizer finds a degenerate (R_PICPOC, mort_lge) pair.
    calcite_mort_src = mort_lge if USE_COCCOLITH_ONLY_CALCITE else mort_total_1
    dPIC_1 = R_PICPOC * calcite_mort_src - pic_sink_out_L1

    # L1 carbonate (same surface air-sea CO2 flux as v2.6).
    carb_1 = solve_carbonate(DIC_1, ALK_1, T, S)
    F_co2 = co2_flux(carb_1["pCO2"], pco2_atm, wind, T, S)
    F_per_m3_per_day = F_co2 * 86400.0 / h1

    dDIC_1 = (
        -growth_total                       # phyto C fixation across all 5 PFTs
        - R_PICPOC * calcite_mort_src       # CaCO3 formation
        - F_per_m3_per_day                  # air-sea export
    )
    dALK_1 = -2.0 * R_PICPOC * calcite_mort_src

    # =========================================================================
    # L2 tendencies (no biology — iron, POC/PIC dynamics + carbonate dissolution)
    # =========================================================================

    dDFe_2 = (
        + fe_remin_L2                       # iron released by POC remineralization (the SOLE L2 source)
        - scav_rat_per_day * DFe_2 * POC_2  # subsurface scavenging — the scav_rat anchor
        + fe_diff_L2                        # diffusive exchange with L1
    )

    dPOC_2 = poc_sink_in_L2 - poc_remin - W_SINK * POC_2  # sink to deep (lost)
    dPIC_2 = pic_sink_in_L2 - pic_dissolve - W_SINK * PIC_2

    # L2 carbonate: respiration restores DIC, PIC dissolution restores ALK.
    # No air-sea flux at depth. (Carbonate-system closure is for consistency;
    # L2 DIC/ALK are not used in the v2.7 loss.)
    dDIC_2 = +poc_remin + pic_dissolve           # respiration + carbonate dissolution
    dALK_2 = +2.0 * pic_dissolve                 # carbonate dissolution stoichiometry

    return torch.stack([
        DFe_1 + dt * dDFe_1,
        P_diatom + dt * dP_diatom,
        P_lge    + dt * dP_lge,
        P_syn    + dt * dP_syn,
        P_proLL  + dt * dP_proLL,
        P_proHL  + dt * dP_proHL,
        POC_1 + dt * dPOC_1,
        PIC_1 + dt * dPIC_1,
        DIC_1 + dt * dDIC_1,
        ALK_1 + dt * dALK_1,
        DFe_2 + dt * dDFe_2,
        POC_2 + dt * dPOC_2,
        PIC_2 + dt * dPIC_2,
        DIC_2 + dt * dDIC_2,
        ALK_2 + dt * dALK_2,
    ])


def carroll6_5pft_2layer_integrate(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int] | None = None,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h1: float = H1,
    h2: float = H2,
    kz_m2_per_day: float = KZ_M2_PER_DAY,
    r_remin: float = R_REMIN,
) -> torch.Tensor:
    """Forward-Euler integration of the 15-tracer 2-layer Carroll-6 + carbonate box.

    Mirrors ``carroll6_5pft.carroll6_5pft_integrate`` (autograd-clean through
    every step) with the 15-tracer state vector.

    Args:
        state0: initial 15-tracer state.
        params: Carroll-6 parameters, shape ``[6]``.
        dt: time step in days.
        n_steps: number of forward-Euler steps.
        snapshot_indices: 1-indexed steps at which to save state. If ``None``,
            returns only the final state; otherwise returns shape
            ``[len(snapshot_indices), 15, ...]``.
        T, S, wind, pco2_atm, h1, h2, kz_m2_per_day, r_remin: forcing — see
            :func:`carroll6_5pft_2layer_step`.

    Returns:
        Final state shape ``[15, ...]`` when ``snapshot_indices is None``,
        else stacked snapshots.
    """
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = carroll6_5pft_2layer_step(
                state, params, dt, T, S, wind, pco2_atm, h1, h2, kz_m2_per_day, r_remin,
            )
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = carroll6_5pft_2layer_step(
            state, params, dt, T, S, wind, pco2_atm, h1, h2, kz_m2_per_day, r_remin,
        )
        if step in snapshot_set:
            snaps.append(state)
    return torch.stack(snaps)
