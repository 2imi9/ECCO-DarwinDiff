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

from collections.abc import Callable

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


# --- Forward-model fidelity levers (added 2026-06-11; all default OFF/identity
#     so legacy behaviour reproduces bitwise; resolved at torch.compile trace
#     time, so set BEFORE compile). Grounded in Carroll 2020/2022 + the
#     2026-06-11 utilization audit; targets the stuck R_PICPOC / growth params. ---

W_SINK_PIC: float = W_SINK
"""Calcite (PIC) sinking rate (1/day), SEPARATE from the organic POC rate.
Darwin v05 carries a distinct ``wPIC_sink`` (one of six sinking velocities; see
docs/ecco_darwin_parameter_inventory.md:97) -- calcite is ballasted and typically
sinks faster than organic detritus. Default equals :data:`W_SINK` so legacy
behaviour reproduces bitwise. Targets ``R_PICPOC`` by decoupling the calcite
export length scale from organic remineralization (the binary-PIC-anchor mutex
forbids the absolute-anchor route, so this is the sanctioned forward-model path).
Best paired with USE_COCCOLITH_ONLY_CALCITE."""

R_PIC_DISSOL: float = R_REMIN
"""Subsurface calcite (PIC) dissolution rate (1/day), SEPARATE from organic
remineralization. Default equals :data:`R_REMIN`. NOTE: when set this overrides
the per-call ``r_remin`` argument for the PIC dissolution term ONLY (POC
remineralization still follows the ``r_remin`` argument). No current caller
overrides ``r_remin``, so the default is bitwise-identical."""

USE_EPPLEY_T: bool = False
"""Apply a temperature limitation multiplier to phytoplankton growth.

Darwin parameterizes growth temperature dependence via an Arrhenius coefficient
(``a_phytoTempAe``; docs/ecco_darwin_parameter_inventory.md:245). This is an
**Eppley-style approximation** of that form (exponential in degrees C), NOT the
verbatim v05 namelist value -- :data:`A_E_EPPLEY` is env-overridable and should
be pinned against the v05 ``data.darwin`` before any paper-grounded claim. The
multiplier is **mean-neutralized** over the input T field, so it imposes a pure
warm-vs-cold growth STRUCTURE tied to SST (the DINN's only input channel) rather
than a global magnitude shift the learned mu would re-absorb. Requires T passed
as a field tensor (the production path). Default ``False`` -> bitwise legacy.
Targets Smallgrow / Biggrow (and diatomgraz indirectly via diatom biomass)."""

T_REF_EPPLEY: float = 15.0
"""Reference temperature (degC) for the Eppley growth multiplier."""

A_E_EPPLEY: float = 0.0633
"""Eppley exponential coefficient (1/degC), ~Q10 of 1.88. Textbook Eppley value;
NOT yet pinned to Darwin v05 ``a_phytoTempAe`` -- env-overridable for sweeps."""


def npp_from_state(
    state: torch.Tensor,
    params: torch.Tensor,
    T: torch.Tensor | float = 15.0,
) -> torch.Tensor:
    """Diagnose gross primary production (NPP proxy) from a (converged) box state.

    Returns ``growth_total`` per cell -- the sum of per-PFT growth fluxes,
    computed IDENTICALLY to the growth block in
    :func:`carroll6_5pft_2layer_step` (same ``USE_EPPLEY_T`` gate). This is the
    model side of the ``PRIMPROD_W`` loss against Darwin's diagnosed primary
    production (``PP``). Pure diagnostic -- no state update; inert unless the
    runner adds a PRIMPROD term.
    """
    DFe_1 = state[I_DFE_1]
    P_diatom = state[I_DIATOM]; P_lge = state[I_LGE]; P_syn = state[I_SYN]
    P_proLL = state[I_PROLL]; P_proHL = state[I_PROHL]
    mu_proHL = params[I_SMALLGROW]
    mu_lge = params[I_BIGGROW]
    f_fe = DFe_1 / (DFe_1 + K_FE)
    if USE_EPPLEY_T:
        gamma_T = torch.exp(A_E_EPPLEY * (T - T_REF_EPPLEY))
        gamma_T = gamma_T / gamma_T.mean()
    else:
        gamma_T = 1.0
    growth_total = (
        MU_DEFAULT_DIATOM * P_diatom
        + mu_lge * P_lge
        + MU_DEFAULT_SYN * P_syn
        + MU_DEFAULT_PROLL * P_proLL
        + mu_proHL * P_proHL
    ) * f_fe * LIGHT * gamma_T
    return growth_total


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

    # Optional Eppley temperature limitation (USE_EPPLEY_T, default OFF). Uses the
    # T forcing already threaded in for the carbonate solve. Mean-neutralized so it
    # imposes warm-vs-cold growth STRUCTURE without a global magnitude shift the
    # learned mu would simply re-absorb. gamma_T depends only on forcing (not on
    # params), so it does not alter the parameter gradients' direction.
    if USE_EPPLEY_T:
        gamma_T = torch.exp(A_E_EPPLEY * (T - T_REF_EPPLEY))
        gamma_T = gamma_T / gamma_T.mean()
    else:
        gamma_T = 1.0

    # Per-PFT growth (default: specific mapping per Carroll-6 → PFT spec).
    growth_diatom = MU_DEFAULT_DIATOM * f_fe * LIGHT * gamma_T * P_diatom
    growth_lge    = mu_lge            * f_fe * LIGHT * gamma_T * P_lge
    growth_syn    = MU_DEFAULT_SYN    * f_fe * LIGHT * gamma_T * P_syn
    growth_proLL  = MU_DEFAULT_PROLL  * f_fe * LIGHT * gamma_T * P_proLL
    growth_proHL  = mu_proHL          * f_fe * LIGHT * gamma_T * P_proHL
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

    pic_sink_out_L1 = W_SINK_PIC * PIC_1                             # separate calcite sinking rate
    pic_sink_in_L2  = pic_sink_out_L1 * (h1 / h2)

    # (c) Subsurface remineralization releases bound iron + carbon. This is
    #     the SOLE iron path back to dissolved phase in L2.
    poc_remin = r_remin * POC_2                                       # mmol C/m^3/d
    pic_dissolve = R_PIC_DISSOL * PIC_2                               # separate calcite dissolution rate
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
    dPIC_2 = pic_sink_in_L2 - pic_dissolve - W_SINK_PIC * PIC_2

    # L2 carbonate: respiration restores DIC, PIC dissolution restores ALK.
    # No air-sea flux at depth. (Carbonate-system closure is for consistency;
    # L2 DIC/ALK are not used in the v2.7 loss.)
    dDIC_2 = +poc_remin + pic_dissolve           # respiration + carbonate dissolution
    dALK_2 = +2.0 * pic_dissolve                 # carbonate dissolution stoichiometry

    new_state = torch.stack([
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
    # Non-negativity floor: tracer concentrations are physically >= 0. This is a
    # no-op for well-behaved trajectories (Carroll-range params, short spin-up),
    # so v2.7/v2.8/v3.x recovery and the reduce-to-plain-integrate equivalence are
    # unchanged. It guards the carbonate budget (dDIC_1/dALK_1 have no floor and
    # forward-Euler has no clamp) from running away monotonically negative at the
    # PARAM_BOUNDS extremes the DINN can emit under multi-cycle seasonal spin-up
    # (a latent NaN-at-native-resolution; pre-scale-up audit 2026-06-18). The
    # carbonate solver only guards its own discriminant, not upstream negative
    # DIC/ALK, so the floor must live here.
    return new_state.clamp(min=0.0)


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
    step_fn: Callable[..., torch.Tensor] | None = None,
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
    # ``step_fn`` lets a caller inject a torch.compile'd per-step (the batched/
    # compiled runner path, #115/#119); default is the eager module step.
    _step = step_fn if step_fn is not None else carroll6_5pft_2layer_step
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = _step(
                state, params, dt, T, S, wind, pco2_atm, h1, h2, kz_m2_per_day, r_remin,
            )
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = _step(
            state, params, dt, T, S, wind, pco2_atm, h1, h2, kz_m2_per_day, r_remin,
        )
        if step in snapshot_set:
            snaps.append(state)
    return torch.stack(snaps)


# Mean Gregorian month (365.25 / 12 ≈ 30.44 d). At DT=0.25 d that is ~122
# steps/month, ~1461 steps/yr — the seasonal trajectory length behind the
# seasonal memory estimate (measured fit in scripts/measure_memory_scaling.py +
# docs/findings/memory_scaling.md on the unmerged PR #102 branch).
DAYS_PER_MONTH: float = 365.25 / 12.0


def carroll6_5pft_2layer_integrate_seasonal(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    T_monthly: torch.Tensor,
    S_monthly: torch.Tensor,
    wind_monthly: torch.Tensor,
    *,
    steps_per_month: int | None = None,
    n_spinup_cycles: int = 0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h1: float = H1,
    h2: float = H2,
    kz_m2_per_day: float = KZ_M2_PER_DAY,
    r_remin: float = R_REMIN,
    step_fn: Callable[..., torch.Tensor] | None = None,
) -> torch.Tensor:
    """Integrate a transient annual cycle with month-varying forcing.

    Where :func:`carroll6_5pft_2layer_integrate` runs ONE constant-forcing block
    to quasi-steady-state (the time-mean / climatology fit), this threads 12
    monthly forcing fields through a single continuous forward-Euler trajectory
    and records the state at each month-end. Those 12 model snapshots are the
    seasonal-fit prediction — they carry the bloom *timing* (e.g. coccolithophore
    PIC phenology distinct from diatom POC) that an annual mean averages away, and
    are the basis for the seasonal R_PICPOC degeneracy test.

    The whole trajectory stays on the autograd graph, so the gradient w.r.t.
    ``params`` flows through every step exactly as in the single-block integrator;
    peak memory scales with ``(n_spinup_cycles + 1) * 12 * steps_per_month``
    (measured ~356 B per cell-step, pre-checkpointing; harness on the unmerged
    PR #102 branch, ``scripts/measure_memory_scaling.py``).

    Args:
        state0: initial 15-tracer state, shape ``[15, ...]``.
        params: Carroll-6 parameters, shape ``[6, ...]``.
        dt: time step in days.
        T_monthly, S_monthly, wind_monthly: monthly forcing fields, each with a
            **leading length-12 month axis** (``[12, ...]``, broadcasting over the
            state's spatial shape). Month ``m`` uses ``T_monthly[m]`` etc.
        steps_per_month: forward-Euler steps per month. Defaults to
            ``round(DAYS_PER_MONTH / dt)`` (~122 at dt=0.25).
        n_spinup_cycles: full 12-month cycles to run BEFORE the recorded year, to
            damp the initial-condition transient. ``0`` records the first year.
        pco2_atm, h1, h2, kz_m2_per_day, r_remin: see
            :func:`carroll6_5pft_2layer_step`.

    Returns:
        End-of-month states from the final (recorded) cycle, shape ``[12, 15, ...]``.
        With constant forcing across all months and ``n_spinup_cycles=0``, the last
        snapshot equals ``carroll6_5pft_2layer_integrate`` run for
        ``12 * steps_per_month`` steps (the seasonal loop reduces to the plain one).

    Raises:
        ValueError: if any forcing field's leading axis is not length 12, or
            ``steps_per_month < 1``.
    """
    for name, field in (
        ("T_monthly", T_monthly),
        ("S_monthly", S_monthly),
        ("wind_monthly", wind_monthly),
    ):
        if field.shape[0] != 12:
            raise ValueError(
                f"{name} must have a leading length-12 month axis, "
                f"got shape {tuple(field.shape)}"
            )
    spm = steps_per_month if steps_per_month is not None else round(DAYS_PER_MONTH / dt)
    if spm < 1:
        raise ValueError(f"steps_per_month must be >= 1, got {spm}")

    # ``step_fn`` lets a caller inject a torch.compile'd per-step (the batched/
    # compiled seasonal runner, #115/#119); default is the eager module step.
    _step = step_fn if step_fn is not None else carroll6_5pft_2layer_step
    state = state0
    recorded: list[torch.Tensor] = []
    for cycle in range(n_spinup_cycles + 1):
        is_recorded_cycle = cycle == n_spinup_cycles
        month_ends: list[torch.Tensor] = []
        for month in range(12):
            t_m = T_monthly[month]
            s_m = S_monthly[month]
            w_m = wind_monthly[month]
            for _ in range(spm):
                state = _step(
                    state, params, dt, t_m, s_m, w_m, pco2_atm, h1, h2,
                    kz_m2_per_day, r_remin,
                )
            if is_recorded_cycle:
                month_ends.append(state)
        if is_recorded_cycle:
            recorded = month_ends
    return torch.stack(recorded)
