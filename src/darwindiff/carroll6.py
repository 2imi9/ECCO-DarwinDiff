"""Carroll-2020 6-parameter box model: 0-D Fe-phyto-POC-PIC reaction network.

Surface mixed-layer scalar BGC with five prognostic tracers and external dust + light
forcing. Exposes the exact six parameters Carroll et al. 2020 (JAMES) tuned via Green's
functions for ECCO-Darwin (Darwin 1 source build at MITgcm-contrib/ecco_darwin/v04/
llc270_JAMES_paper):

    1. alpfe       — scalar on the already-soluble Fe deposition flux (≈1, –); NOT a solubility
    2. scav_rat    — iron scavenging rate (s⁻¹)
    3. Smallgrow   — small phytoplankton growth rate (d⁻¹)
    4. Biggrow     — large phytoplankton growth rate (d⁻¹)
    5. diatomgraz  — diatom palatability (–)
    6. R_PICPOC    — PIC/POC ratio (–)

These six are declared once in the ``PARAMS`` registry below — the single source
of truth from which ``PARAM_NAMES``, ``CARROLL_VALUES``, ``PARAM_BOUNDS``,
``PARAM_INDEX`` and the ``P`` named-index namespace are derived. Adding or
dropping a parameter is a one-entry edit to that tuple; see CONTRIBUTING.md.

Equations (5-tracer baseline, ``carroll6_step`` / ``carroll6_integrate``):
    dDFe/dt   = alpfe*Φ_dust - scav_rat*DFe*POC - Q_Fe*(μ_s P_s + μ_l P_l)*f_Fe(DFe)
    dPs/dt    = μ_s f_Fe Ps - m_lin Ps - m_quad Ps²
    dPl/dt    = μ_l f_Fe Pl - m_lin Pl - m_quad Pl² - g_diatom G0 Pl
    dPOC/dt   = M_tot - w_sink POC
    dPIC/dt   = R_PICPOC M_tot - w_sink PIC

with f_Fe(DFe) = DFe / (DFe + K_Fe) and M_tot the sum of all phyto loss fluxes.

Carbonate extension (7-tracer, ``carroll6_carbonate_step`` /
``carroll6_carbonate_integrate``): adds DIC + ALK with couplings

    dDIC/dt   = -μ_s f_Fe Ps - μ_l f_Fe Pl                  # phyto C fixation
                - R_PICPOC * M_tot                            # CaCO3 formation (calcification)
                - F_CO2 / H_mld                               # air-sea flux (F > 0 = outgassing)
    dALK/dt   = -2 * R_PICPOC * M_tot                         # CaCO3 takes 2 ALK eq per mole

F_CO2 is computed each step from (DIC, ALK, T, S) via the Follows-2006 carbonate solver
(``darwindiff.carbonate.solve_carbonate``) and the Wanninkhof-2014 gas-transfer law
(``darwindiff.carbonate.co2_flux``). Total carbon in the box decays only through air-sea
flux + particulate sinking export — verified by ``test_carroll6_carbonate.py``.

Background defaults (M_LIN, M_QUAD, G0_GRAZE, W_SINK, K_FE, PHI_DUST, Q_FE, LIGHT, H_MLD)
are fixed at literature-plausible values and not learned — they correspond to the ~94%
of Darwin parameters Carroll left at expert defaults.

Used by notebooks 05–19 (5-tracer); nb20 onwards uses the 7-tracer extension. Darwin 3
namelist mapping for these names is documented in the project memory at
reference_darwin3.md.
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from dataclasses import dataclass, replace
from types import SimpleNamespace

import torch

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate
from darwindiff.integrators import integrate as _integrate

# Background (non-learned) parameters — the ~94% of Darwin knobs Carroll left at defaults.
M_LIN: float = 0.05         # 1/d, linear phyto mortality
M_QUAD: float = 0.50        # 1/d / (mmol C/m^3), quadratic phyto mortality
G0_GRAZE: float = 0.30      # 1/d, baseline grazing rate (multiplied by diatomgraz)
W_SINK: float = 0.10        # 1/d, particulate sinking rate
K_FE: float = 5.0e-5        # mmol Fe/m^3, iron half-saturation for phyto growth
PHI_DUST: float = 5.0e-5    # mmol Fe/m^3/d, dissolved-iron source from dust
Q_FE: float = 1.0e-5        # mol Fe / mol C, phyto Fe quota
LIGHT: float = 1.0          # surface light, dimensionless
H_MLD: float = 50.0         # m, surface mixed-layer depth for the carbonate extension's
                            # air-sea flux conversion. ~50 m is a reasonable Eq Pacific
                            # climatology; override per-cell once Darwin's MLD field is
                            # in the loader (see Day 3 of the v2.0 closeout).


@dataclass(frozen=True)
class Param:
    """One learnable Carroll-N parameter — a single declarative registry entry.

    Attributes:
        name: identifier used everywhere a parameter is referenced by name —
            the ``P`` index namespace (``P.<name>``), the ``I_<NAME>`` aliases in
            :mod:`darwindiff.carroll6_5pft`, and the gating policies in
            :mod:`darwindiff.gating`. Must be a valid Python identifier.
        bounds: ``(lo, hi)`` physical range for :func:`bounded_params`' sigmoid map.
        carroll_value: Carroll-2020 published Green's-functions optimum.
        units: physical units (documentation only).
        description: one-line physical meaning (documentation only).
        learned: whether the parameter is fit by gradient descent. All six are
            currently learned; the flag lets a future fixed/derived parameter
            live in the registry without being optimised.
        model_value: the value ECCO-Darwin v05 **actually integrates**, when it
            differs from ``carroll_value`` (the *published* Green's-functions
            optimum). ``None`` means they agree. This is not pedantry: for
            ``R_PICPOC`` the published optimum is 0.04245 but v05 loads
            0.0418860 from ``data.traits``, a 1.35 % difference, because
            ``DARWIN_READ_TRAITS`` overwrites the ``val_R_PICPOC`` generation
            scalar at startup. Recovery is graded against ``carroll_value`` by
            default, so this field records the discrepancy rather than hiding
            it. See ``docs/findings/2026-07-28_session_evidence_log.md`` §A6.
        scale: ``"linear"`` (default) or ``"log"`` — the geometry the sigmoid
            map should use across ``bounds``. Parameters spanning decades want
            ``"log"``: a linear map over a 100x range spends ~91 % of the
            sigmoid on the top decade, so the optimiser has almost no
            resolution at small values and the implied prior is badly skewed
            (``scav_rat``: only 7.5 % of prior mass below Carroll, median
            2.52x Carroll). This field is METADATA ONLY — it does not change
            behaviour unless a caller passes the derived mask to
            :func:`bounded_params` via ``log_mask``, which keeps every existing
            run bit-identical by default.
    """

    name: str
    bounds: tuple[float, float]
    carroll_value: float
    units: str
    description: str
    learned: bool = True
    scale: str = "linear"
    model_value: float | None = None


# ============================ Carroll-N parameter registry ====================
# THE SINGLE SOURCE OF TRUTH for the learnable-parameter layout. Add or drop a
# parameter by editing exactly this tuple: PARAM_NAMES, CARROLL_VALUES,
# PARAM_BOUNDS, PARAM_INDEX and the P.<name> index namespace below are all
# DERIVED from it, so they never drift out of sync. See CONTRIBUTING.md →
# "Adding or removing a Carroll-N parameter".
#
# Carroll-2020 optima (JAMES paper Table 1) verified directly against the
# v04/llc270_JAMES_paper source build; see docs/ecco_darwin_parameter_inventory.md.
#
# ORDER IS LOAD-BEARING. Existing runs, IC caches and recovered-value JSONs index
# parameters positionally (params[0]..params[5]); appending a new entry is safe,
# but reordering or inserting changes the on-disk layout and breaks bitwise
# reproduction of every prior result.
PARAMS: tuple[Param, ...] = (
    Param(
        name="alpfe",
        bounds=(0.05, 1.0),
        carroll_value=0.92831,
        units="-",
        # NOT a physical solubility despite Darwin's legacy label. Darwin forces iron with the
        # ALREADY-SOLUBLE Mahowald-2009 product (llc270_Mahowald_2009_soluble_iron_dust.bin), and
        # Darwin3's own docs say alpfe should be "set to 1 if the deposition rate in ironfile is
        # already of soluble iron" -> it is a near-unity dimensionless correction on an already-
        # soluble flux (Carroll GF optimum 0.928), not the ~1-2% fractional solubility of dust iron.
        # See docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md.
        description="scalar on already-soluble Fe deposition (~1)",
    ),
    Param(
        name="scav_rat",
        # per-second, following the Carroll source convention; a 100x window
        # around Carroll's 6e-7 (= 10.41124 * 0.005 / 86400).
        bounds=(3e-8, 3e-6),
        carroll_value=10.41124 * 0.005 / 86400.0,
        units="s^-1",
        description="iron scavenging rate",
        # A rate spanning two decades. Declared log; inert until a caller opts
        # in via bounded_params(log_mask=...). See Param.scale.
        scale="log",
    ),
    Param(
        name="Smallgrow",
        bounds=(0.10, 2.0),
        carroll_value=0.66098,
        units="d^-1",
        description="small phytoplankton growth rate",
    ),
    Param(
        name="Biggrow",
        bounds=(0.10, 2.0),
        carroll_value=0.43148,
        units="d^-1",
        description="large phytoplankton growth rate",
    ),
    Param(
        name="diatomgraz",
        bounds=(0.05, 1.0),
        carroll_value=0.83003,
        units="-",
        description="diatom palatability",
    ),
    Param(
        name="R_PICPOC",
        # Bound raised from 0.20 (session 2026-05-18 diagnostic). Empirical Darwin
        # v05 PIC/POC ratio: eqpac median 0.031, natl median 0.722 (23x AOI
        # variance). The original 0.20 bound capped 3.6x below natl's true ratio.
        # Diagnostic: does the learner push above 0.20 when allowed? If not, the
        # binding constraint is the inter-AOI tension, not the bound.
        bounds=(0.005, 1.5),
        carroll_value=0.04245,
        units="-",
        description="PIC/POC rain ratio",
        # v05 loads 0.0418860 for plankton types 2 and 3 from data.traits, which
        # DARWIN_READ_TRAITS writes over the val_R_PICPOC=0.04245 generation
        # scalar in data.darwin. Verified first-hand against the pinned darwin3
        # source (24885b71): darwin_init_fixed.F generates at line 357 and reads
        # traits at line 382. The 1.35 % gap is far inside the 5 % Excellent
        # band so it changes no verdict, but the published target and the
        # model's running value are not the same number.
        model_value=0.041886,
    ),
)


# ---- Experiment lever: alpfe's UPPER bound ------------------------------------
# `alpfe` rails at its 1.0 bound. Carroll is 0.92831, so the ~8% we have been quoting as an
# accuracy is the BOUND-TO-CARROLL DISTANCE, not a measurement: most seeds land within one
# percent of the bound, and a band sweep is a step function (0/50 at 0.06, 49/50 at 0.08).
# The signal is real and strong (98/100 vs an untrained 0/100 at band 0.10); the PRECISION is
# what is unmeasured.
#
# DD_ALPFE_HI widens the upper bound for ONE arm so bound geometry can be told apart from real
# precision. Reading: the fit runs on to ~1.4 => there is no upper-side information and the
# quoted precision is entirely geometry; it stops near 0.93 => the precision is real.
#
# Unset (the default) reproduces the registry exactly, so every existing run stays
# bit-identical. This is the only sanctioned way to move a bound -- editing PARAMS in place
# would silently change the meaning of every artifact already on disk.
_ALPFE_HI_ENV = os.environ.get("DD_ALPFE_HI", "").strip()
if _ALPFE_HI_ENV:
    _alpfe_hi = float(_ALPFE_HI_ENV)
    _alpfe_lo = next(p for p in PARAMS if p.name == "alpfe").bounds[0]
    if _alpfe_hi <= _alpfe_lo:
        raise ValueError(
            f"DD_ALPFE_HI={_alpfe_hi} must exceed alpfe's lower bound {_alpfe_lo}"
        )
    PARAMS = tuple(
        replace(p, bounds=(_alpfe_lo, _alpfe_hi)) if p.name == "alpfe" else p
        for p in PARAMS
    )

# ---- Derived layout — regenerated from PARAMS; do not edit by hand. -----------
# CARROLL_VALUES / PARAM_BOUNDS reproduce the exact float32 values of the
# pre-registry hardcoded tensors (locked by tests/test_param_registry.py).
PARAM_NAMES: list[str] = [p.name for p in PARAMS]
CARROLL_VALUES: torch.Tensor = torch.tensor([p.carroll_value for p in PARAMS])
PARAM_BOUNDS: torch.Tensor = torch.tensor([list(p.bounds) for p in PARAMS])
PARAM_INDEX: dict[str, int] = {p.name: i for i, p in enumerate(PARAMS)}

# Number of registered parameters. Read this instead of hardcoding 6 so that
# appending a registry entry widens the network head automatically (the per-cell
# DINN head is a 1x1 conv, so the parameter axis is the only thing that changes).
N_PARAMS: int = len(PARAMS)

# Boolean mask of parameters DECLARED log-scale (Param.scale == "log"). Inert by
# construction: nothing consumes it unless a caller passes it to
# bounded_params(log_mask=...), which is how existing runs stay bit-identical.
PARAM_LOG_MASK: torch.Tensor = torch.tensor(
    [p.scale == "log" for p in PARAMS], dtype=torch.bool
)


def prior_midpoint_offset(p: Param) -> float:
    """Relative offset of a parameter's sigmoid MIDPOINT from its Carroll value.

    An untrained network's outputs sit near zero, so ``bounded_params`` maps them
    near the middle of ``bounds``. If that midpoint already falls inside the
    Cal-grade band (``rel <= 0.40``), the parameter scores as "recovered" from a
    network that has learned nothing, and its recovery count measures the choice
    of bounds rather than any observational constraint.

    This is not hypothetical. Measured on 50 untrained networks through the real
    pipeline (2026-07-29): ``diatomgraz`` recovers **32/50** and ``alpfe``
    **10/50** with no training at all. ``diatomgraz``'s midpoint offset is 0.367,
    inside the 0.40 band, which is exactly why.

    Returns:
        ``abs(midpoint - carroll_value) / abs(carroll_value)``. Compare against
        ``diagnostics.BAND_CAL_GRADE_MAX``; larger is safer.
    """
    lo, hi = p.bounds
    mid = math.sqrt(lo * hi) if p.scale == "log" else lo + (hi - lo) * 0.5
    return abs(mid - p.carroll_value) / abs(p.carroll_value)


def log_mask_from_names(names: str | None) -> torch.Tensor | None:
    """Build a ``bounded_params`` log-mask from a comma-separated name list.

    Lets an experiment opt specific parameters into log-space bounding from a
    config/env string (e.g. ``"scav_rat"``) without editing the registry, so an
    A/B against the linear-map baseline is a one-variable change.

    Args:
        names: comma-separated registry names, or None/empty for "no log
            scaling" (returns None, i.e. exactly the historical behaviour).

    Returns:
        A ``[n_params]`` bool tensor, or None when ``names`` is empty.

    Raises:
        KeyError: if a name is not in the registry — fail loudly rather than
            silently applying the mask to nothing.
    """
    if not names or not names.strip():
        return None
    mask = torch.zeros(len(PARAMS), dtype=torch.bool)
    for raw in names.split(","):
        key = raw.strip()
        if not key:
            continue
        if key not in PARAM_INDEX:
            raise KeyError(
                f"unknown parameter {key!r}; registry has {sorted(PARAM_INDEX)}"
            )
        mask[PARAM_INDEX[key]] = True
    return mask

# Named positional indices, so call sites read ``params[P.alpfe]`` instead of the
# position-counted ``params[0]``. Attributes are the registry names, e.g.
# ``P.alpfe``, ``P.Smallgrow``, ``P.R_PICPOC``.
P = SimpleNamespace(**PARAM_INDEX)


def carroll6_tendency(
    state: torch.Tensor,
    params: torch.Tensor,
) -> torch.Tensor:
    """Raw d(state)/dt for the 5-tracer Carroll-6 box (no timestep applied).

    This is the integrator-agnostic core: the rate equations of Eq. (20)-(25) in
    the module docstring, returned as a tendency so any stepper in
    :mod:`darwindiff.integrators` (forward-Euler or RK4) can advance it.

    Args:
        state: shape [5], [DFe, Ps, Pl, POC, PIC] in mmol/m^3 (Fe in mmol Fe/m^3).
        params: shape [6], [alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC].
            scav_rat is per-second following the Carroll source convention; converted
            to per-day here.

    Returns:
        d(state)/dt, shape [5], in per-day units.
    """
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    alpfe = params[P.alpfe]
    scav_rat = params[P.scav_rat]
    mu_s = params[P.Smallgrow]
    mu_l = params[P.Biggrow]
    g_diatom = params[P.diatomgraz]
    R_PICPOC = params[P.R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0

    f_fe = DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * LIGHT * Ps
    growth_l = mu_l * f_fe * LIGHT * Pl
    fe_uptake = Q_FE * (growth_s + growth_l)
    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l

    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
    dPs = growth_s - mort_s
    dPl = growth_l - mort_l - graze_l
    dPOC = mort_total - W_SINK * POC
    dPIC = R_PICPOC * mort_total - W_SINK * PIC

    return torch.stack([dDFe, dPs, dPl, dPOC, dPIC])


def carroll6_ude_tendency(
    state: torch.Tensor,
    params: torch.Tensor,
    *,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
) -> torch.Tensor:
    """Carroll-6 tendency with optional *learned closures* — the UDE hook (Track 2).

    Identical rate equations to :func:`carroll6_tendency`, except two genuinely
    uncertain terms may be replaced by a trained neural network, turning the box
    into a Universal Differential Equation. With both closures ``None`` the output
    is byte-identical to :func:`carroll6_tendency`, so this is a strict superset
    and safe to route existing code through. The two hooks cover the two candidate
    first closures, so the choice can be settled with Jon without changing this API.

    Args:
        state, params: as in :func:`carroll6_tendency`.
        ffe_closure: ``f(DFe) -> f_Fe`` (expected in ``[0, 1]``) replacing the
            mechanistic Michaelis-Menten iron limitation ``DFe / (DFe + K_Fe)`` —
            the closure the Phase-0 feasibility probe learned to ~5%.
        calcite_closure: ``f(state, mort_total) -> PIC production rate`` replacing
            the single-scalar law ``R_PICPOC * mort_total`` that Paper #1 could not
            resolve spatially (the natural calcification-closure target).

    Returns:
        d(state)/dt, shape [5], per-day units.
    """
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    alpfe = params[P.alpfe]
    scav_rat = params[P.scav_rat]
    mu_s = params[P.Smallgrow]
    mu_l = params[P.Biggrow]
    g_diatom = params[P.diatomgraz]
    R_PICPOC = params[P.R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0

    f_fe = ffe_closure(DFe) if ffe_closure is not None else DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * LIGHT * Ps
    growth_l = mu_l * f_fe * LIGHT * Pl
    fe_uptake = Q_FE * (growth_s + growth_l)
    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l

    pic_prod = (
        calcite_closure(state, mort_total)
        if calcite_closure is not None
        else R_PICPOC * mort_total
    )

    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
    dPs = growth_s - mort_s
    dPl = growth_l - mort_l - graze_l
    dPOC = mort_total - W_SINK * POC
    dPIC = pic_prod - W_SINK * PIC

    return torch.stack([dDFe, dPs, dPl, dPOC, dPIC])


def carroll6_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
) -> torch.Tensor:
    """One forward-Euler step of the 5-tracer Carroll-6 box model.

    Thin wrapper over :func:`carroll6_tendency` (``state + dt * tendency``);
    numerically identical to the previous inline form. For long rollouts prefer
    ``carroll6_integrate(..., method="rk4")``.

    Args:
        state: shape [5], [DFe, Ps, Pl, POC, PIC] in mmol/m^3 (Fe in mmol Fe/m^3).
        params: shape [6], [alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC].
        dt: time step in days.

    Returns:
        next state, shape [5].
    """
    return state + dt * carroll6_tendency(state, params)


def carroll6_integrate(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int] | None = None,
    method: str = "euler",
    checkpoint_segment: int | None = None,
) -> torch.Tensor:
    """Integrate the 5-tracer box with autograd through every step.

    Delegates to :func:`darwindiff.integrators.integrate` over
    :func:`carroll6_tendency`. ``method="euler"`` (the default) is byte-identical
    to the historical forward-Euler loop the paper's fits use; ``method="rk4"``
    switches to the fourth-order stepper for long, drift-sensitive rollouts.

    Args:
        state0: initial state, shape [5].
        params: Carroll-6 parameters, shape [6].
        dt: time step in days.
        n_steps: number of steps.
        snapshot_indices: 1-indexed steps at which to save state. If None, returns
            only the final state. If provided, returns shape [len(snapshot_indices), 5].
        method: ``"euler"`` (default) or ``"rk4"``.
        checkpoint_segment: gradient-checkpoint block size for long rollouts;
            honored only when ``snapshot_indices`` is None (see the integrator).

    Returns:
        Final state shape [5] when snapshot_indices is None, else stacked snapshots.
    """
    def tend(s: torch.Tensor) -> torch.Tensor:
        return carroll6_tendency(s, params)

    return _integrate(
        tend, state0, dt, n_steps,
        method=method,
        snapshot_indices=snapshot_indices,
        checkpoint_segment=checkpoint_segment,
    )


def carroll6_carbonate_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h_mld: float = H_MLD,
) -> torch.Tensor:
    """One forward-Euler step of the 7-tracer Carroll-6 + carbonate box model.

    Extends ``carroll6_step`` with explicit DIC + ALK prognostic variables and an
    air-sea CO₂ flux computed each step via the Follows-2006 carbonate solver.
    See module docstring for the equations and the conservation derivation.

    Args:
        state: shape [7], [DFe, Ps, Pl, POC, PIC, DIC, ALK]. Iron in mmol Fe/m³;
            phyto, POC, PIC in mmol C/m³; DIC in mmol C/m³; ALK in mmol Eq/m³.
        params: shape [6], identical to ``carroll6_step``
            ([alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]).
        dt: time step in days.
        T, S, wind, pco2_atm: forcing fields. Scalars or tensors broadcastable
            with ``state`` (e.g. shape-(H, W) for per-cell fits). Defaults are
            Eq Pacific climatology: 15 °C, 35 PSU, 7 m/s wind, 405 µatm atm pCO₂.
        h_mld: mixed-layer depth in m for the air-sea-flux → tracer-rate
            conversion. Defaults to module-level ``H_MLD``.

    Returns:
        Next state, shape [7].
    """
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    DIC, ALK = state[5], state[6]
    alpfe = params[P.alpfe]
    scav_rat = params[P.scav_rat]
    mu_s = params[P.Smallgrow]
    mu_l = params[P.Biggrow]
    g_diatom = params[P.diatomgraz]
    R_PICPOC = params[P.R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0

    # --- 5-tracer base, identical to carroll6_step -------------------------------
    f_fe = DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * LIGHT * Ps
    growth_l = mu_l * f_fe * LIGHT * Pl
    fe_uptake = Q_FE * (growth_s + growth_l)
    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l

    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
    dPs = growth_s - mort_s
    dPl = growth_l - mort_l - graze_l
    dPOC = mort_total - W_SINK * POC
    dPIC = R_PICPOC * mort_total - W_SINK * PIC

    # --- Carbonate extension -----------------------------------------------------
    # Solve for pCO2 from current DIC + ALK + T + S, then compute air-sea flux.
    # F is in mmol C / m^2 / s (positive = ocean → atm); convert to a tracer
    # rate by dividing by mixed-layer depth and multiplying by 86400 to get
    # mmol C / m^3 / d, matching the units of the biological tendencies above.
    carb = solve_carbonate(DIC, ALK, T, S)
    F_co2 = co2_flux(carb["pCO2"], pco2_atm, wind, T, S)  # mmol C / m^2 / s
    F_per_m3_per_day = F_co2 * 86400.0 / h_mld

    dDIC = (
        -growth_s - growth_l                  # phyto C fixation
        - R_PICPOC * mort_total               # CaCO3 formation (each PIC drains 1 DIC)
        - F_per_m3_per_day                    # air-sea export (positive F = DIC loss)
    )
    dALK = -2.0 * R_PICPOC * mort_total       # CaCO3 takes 2 ALK eq per mole

    return torch.stack([
        DFe + dt * dDFe,
        Ps + dt * dPs,
        Pl + dt * dPl,
        POC + dt * dPOC,
        PIC + dt * dPIC,
        DIC + dt * dDIC,
        ALK + dt * dALK,
    ])


def carroll6_carbonate_integrate(
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
) -> torch.Tensor:
    """Forward-Euler integration of the 7-tracer carroll6 + carbonate box model.

    Mirrors ``carroll6_integrate`` (autograd-clean through every step) with the
    extra forcing arguments routed to ``carroll6_carbonate_step``.

    Args:
        state0: initial 7-tracer state, shape [7].
        params: Carroll-6 parameters, shape [6].
        dt: time step in days.
        n_steps: number of forward-Euler steps.
        snapshot_indices: 1-indexed steps at which to save state. If None,
            returns only the final state; otherwise returns shape
            [len(snapshot_indices), 7].
        T, S, wind, pco2_atm, h_mld: forcing — see ``carroll6_carbonate_step``.

    Returns:
        Final state shape [7] when snapshot_indices is None, else stacked snapshots.
    """
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = carroll6_carbonate_step(
                state, params, dt, T, S, wind, pco2_atm, h_mld,
            )
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = carroll6_carbonate_step(
            state, params, dt, T, S, wind, pco2_atm, h_mld,
        )
        if step in snapshot_set:
            snaps.append(state)
    return torch.stack(snaps)


def bounded_params(
    theta: torch.Tensor,
    bounds: torch.Tensor,
    param_axis: int = 0,
    log_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """Map unconstrained theta to physical Carroll-6 ranges via sigmoid.

    The parameter axis of ``theta`` (the dim with size ``n_params`` matching
    ``bounds.shape[0]``) is identified by ``param_axis``. The default is the
    leading dim, which matches the notebook 05 / 07 usage. For trailing-axis
    conventions (notebook 06 style batched MLP output, or batched CNN output),
    pass ``param_axis`` explicitly.

    Examples:
        - ``theta`` shape ``[6]`` (any ``param_axis``): scalar fit, notebook 05.
        - ``theta`` shape ``[6, H, W]`` with ``param_axis=0``: per-cell fit,
          notebook 07.
        - ``theta`` shape ``[B, 6]`` with ``param_axis=-1``: batched MLP
          output, e.g. multiple regimes evaluated in one call.
        - ``theta`` shape ``[B, 6, H, W]`` with ``param_axis=1``: batched CNN
          output (PyTorch convention with batch + channel + spatial).

    Args:
        theta: unconstrained learnable values.
        bounds: per-parameter ``[lo, hi]`` ranges, shape ``[n_params, 2]``.
        param_axis: index (positive or negative) of the parameter axis in
            ``theta``. Defaults to ``0`` (leading).
        log_mask: optional ``[n_params]`` bool tensor. Where True, the sigmoid
            interpolates GEOMETRICALLY between ``lo`` and ``hi`` instead of
            linearly, i.e. ``exp(ln lo + (ln hi - ln lo) * sigmoid(theta))``.
            Use for parameters spanning decades — a linear map over
            ``scav_rat``'s 100x range puts ~91 % of the sigmoid in the top
            decade, leaving the optimiser almost no resolution below Carroll.
            **Default None reproduces the historical linear map exactly**, so
            enabling this is always an explicit, one-variable change.

    Returns:
        physical-range parameters, same shape as ``theta``.

    Raises:
        ValueError: if ``theta.shape[param_axis] != bounds.shape[0]``, if
            ``log_mask`` has the wrong length, or if a log-masked parameter has
            a non-positive lower bound (``ln lo`` undefined).
    """
    n_params = bounds.shape[0]
    if theta.shape[param_axis] != n_params:
        raise ValueError(
            f"theta.shape[{param_axis}] = {theta.shape[param_axis]} does not "
            f"match bounds.shape[0] = {n_params}"
        )
    # Move the parameter axis to position 0 so the reshape + broadcast pattern
    # works uniformly regardless of where the caller put it.
    theta_p = theta.movedim(param_axis, 0)
    extra_dims = theta_p.ndim - 1
    lo = bounds[:, 0].reshape(n_params, *([1] * extra_dims))
    hi = bounds[:, 1].reshape(n_params, *([1] * extra_dims))
    frac = torch.sigmoid(theta_p)
    result = lo + (hi - lo) * frac
    if log_mask is not None:
        if log_mask.shape[0] != n_params:
            raise ValueError(
                f"log_mask has length {log_mask.shape[0]}, expected {n_params}"
            )
        if bool((bounds[:, 0][log_mask] <= 0).any()):
            bad = [i for i in range(n_params) if log_mask[i] and bounds[i, 0] <= 0]
            raise ValueError(
                f"log-scaled parameters need a positive lower bound; "
                f"offending indices {bad}"
            )
        mask = log_mask.reshape(n_params, *([1] * extra_dims)).to(theta_p.device)
        geo = torch.exp(torch.log(lo) + (torch.log(hi) - torch.log(lo)) * frac)
        result = torch.where(mask, geo, result)
    return result.movedim(0, param_axis)
