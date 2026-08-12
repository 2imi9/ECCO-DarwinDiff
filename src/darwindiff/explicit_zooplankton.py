"""Source-mirrored two-grazer projection for the seasonal self-twin gate.

This module deliberately wraps, rather than changes, the production 15-state
Carroll box.  It replaces only the legacy linear diatom grazing transfer with
the Carroll/Darwin-1 prey-pool and two-predator closure.  The projection has no
DOC state, so all unassimilated prey and predator mortality are routed to POC.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import G0_GRAZE

I_Z_SMALL = 15
I_Z_LARGE = 16
N_TRACERS_EXPLICIT_ZOO = 17

ZOOPLANKTON_STATE_INDICES: tuple[int, ...] = (I_Z_SMALL, I_Z_LARGE)
PLANKTON_STATE_INDICES: tuple[int, ...] = (
    *layer2.PHYTOPLANKTON_STATE_INDICES,
    *ZOOPLANKTON_STATE_INDICES,
)
PLANKTON_NAMES: tuple[str, ...] = (
    *layer2.PHYTOPLANKTON_NAMES,
    "z_small",
    "z_large",
)
STATE_NAMES: tuple[str, ...] = (
    "DFe1",
    "Chl1_diatom",
    "Chl2_lge",
    "Chl3_syn",
    "Chl4_proll",
    "Chl5_prohl",
    "POC1",
    "PIC1",
    "DIC1",
    "ALK1",
    "DFe2",
    "POC2",
    "PIC2",
    "DIC2",
    "ALK2",
    "Z_small",
    "Z_large",
)
CHEMICAL_RESTORING_INDICES: tuple[int, ...] = (
    layer2.I_DFE_1,
    layer2.I_POC_1,
    layer2.I_PIC_1,
    layer2.I_DIC_1,
    layer2.I_ALK_1,
    layer2.I_DFE_2,
    layer2.I_POC_2,
    layer2.I_PIC_2,
    layer2.I_DIC_2,
    layer2.I_ALK_2,
)

# Carroll-2020 Darwin-1 source constants, expressed in the box's carbon units.
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
ZOO_MORTALITY_PER_DAY = 1.0 / 30.0
GRAZING_DENOMINATOR_EPS = 1.0e-20
SOURCE_PHYGRAZ_MIN_C = 1.0e-10 * 120.0
"""Darwin-1's prey floor converted from phosphorus to carbon units."""

ASSIMILATION = (
    (0.2, 0.5),  # diatom: large prey
    (0.2, 0.5),  # other large eukaryote
    (0.5, 0.7),  # Synechococcus: small prey
    (0.5, 0.7),  # Prochlorococcus LL
    (0.5, 0.7),  # Prochlorococcus HL
)


def _require_state(state: torch.Tensor) -> None:
    if state.ndim < 1 or state.shape[0] != N_TRACERS_EXPLICIT_ZOO:
        raise ValueError(
            "explicit-zooplankton state must have leading size "
            f"{N_TRACERS_EXPLICIT_ZOO}, got {tuple(state.shape)}"
        )


def darwin1_explicit_grazing_rates(
    state: torch.Tensor,
    params: torch.Tensor,
    source_prey_floor_c: float = 0.0,
) -> dict[str, torch.Tensor]:
    """Return the Carroll/Darwin-1 two-predator carbon fluxes in 1/day.

    The returned ``grazing_by_prey_predator`` has leading dimensions
    ``[five prey, two predators]``. Every other dimension follows the spatial
    dimensions of ``state`` and ``params``.
    """
    _require_state(state)
    if params.ndim < 1 or params.shape[0] != 6:
        raise ValueError("params must have leading size 6")
    if not math.isfinite(source_prey_floor_c) or source_prey_floor_c < 0.0:
        raise ValueError("source_prey_floor_c must be finite and >= 0")

    phyto = state[list(layer2.PHYTOPLANKTON_STATE_INDICES)]
    zoo = state[list(ZOOPLANKTON_STATE_INDICES)]
    diatomgraz = params[layer2.I_DIATOMGRAZ]
    one = torch.ones_like(diatomgraz)

    palat_small = torch.stack(
        (
            0.2 * diatomgraz,
            0.18 * one,
            one,
            one,
            one,
        )
    )
    palat_large = torch.stack(
        (
            diatomgraz,
            0.90 * one,
            0.20 * one,
            0.20 * one,
            0.20 * one,
        )
    )
    palatability = torch.stack((palat_small, palat_large), dim=1)
    weighted_prey = palatability * phyto.unsqueeze(1)
    prey_pool = weighted_prey.sum(dim=0)

    allocation_denominator = prey_pool.clamp(min=GRAZING_DENOMINATOR_EPS)
    if source_prey_floor_c > 0.0:
        source_pool = torch.where(
            prey_pool > 0.0,
            prey_pool,
            torch.full_like(prey_pool, source_prey_floor_c),
        )
        responsive_pool = (source_pool - source_prey_floor_c).clamp(min=0.0)
        specific_ingestion = (
            GRAZE_MAX_PER_DAY
            * responsive_pool
            / (responsive_pool + GRAZE_HALF_SATURATION_C)
        )
        allocation_denominator = source_pool
    else:
        specific_ingestion = (
            GRAZE_MAX_PER_DAY
            * prey_pool
            / (prey_pool + GRAZE_HALF_SATURATION_C)
        )
    ingestion = specific_ingestion * zoo
    grazing = (
        ingestion.unsqueeze(0)
        * weighted_prey
        / allocation_denominator.unsqueeze(0)
    )

    assimilation = torch.tensor(
        ASSIMILATION,
        dtype=state.dtype,
        device=state.device,
    ).reshape(5, 2, *([1] * (state.ndim - 1)))
    assimilated = grazing * assimilation
    unassimilated = grazing - assimilated
    prey_loss = grazing.sum(dim=1)
    zoo_gain = assimilated.sum(dim=0)
    zoo_mortality = ZOO_MORTALITY_PER_DAY * zoo
    prey_allocation = (
        weighted_prey / allocation_denominator.unsqueeze(0)
    )
    zoo_specific_gain_by_prey = (
        specific_ingestion.unsqueeze(0) * prey_allocation * assimilation
    )
    zoo_specific_gain = zoo_specific_gain_by_prey.sum(dim=0)
    zoo_specific_net = zoo_specific_gain - ZOO_MORTALITY_PER_DAY

    return {
        "palatability": palatability,
        "prey_pool": prey_pool,
        "predator_specific_ingestion": specific_ingestion,
        "predator_ingestion": ingestion,
        "grazing_by_prey_predator": grazing,
        "prey_allocation": prey_allocation,
        "prey_loss": prey_loss,
        "zoo_gain": zoo_gain,
        "zoo_specific_gain_by_prey": zoo_specific_gain_by_prey,
        "zoo_specific_gain": zoo_specific_gain,
        "zoo_specific_net": zoo_specific_net,
        "unassimilated_to_poc": unassimilated.sum(dim=(0, 1)),
        "zoo_mortality": zoo_mortality,
        "zoo_net": zoo_gain - zoo_mortality,
    }


def explicit_zooplankton_process_rates(
    state: torch.Tensor,
    params: torch.Tensor,
    t: torch.Tensor | float = 15.0,
    light: torch.Tensor | float = layer2.LIGHT,
    source_prey_floor_c: float = 0.0,
) -> dict[str, torch.Tensor]:
    """Return exact pre-clamp phytoplankton and zooplankton process rates."""
    _require_state(state)
    base = layer2.phytoplankton_process_rates(state[:15], params, t, light)
    grazing = darwin1_explicit_grazing_rates(
        state,
        params,
        source_prey_floor_c,
    )
    mortality = base["linear_mortality"] + base["quadratic_mortality"]
    prey_loss = grazing["prey_loss"]
    return {
        "growth": base["growth"],
        "linear_mortality": base["linear_mortality"],
        "quadratic_mortality": base["quadratic_mortality"],
        "grazing": prey_loss,
        "loss": mortality + prey_loss,
        "net": base["growth"] - mortality - prey_loss,
        "f_fe": base["f_fe"],
        "gamma_t": base["gamma_t"],
        "light": base["light"],
        **grazing,
    }


def explicit_zooplankton_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    t: torch.Tensor | float = 15.0,
    s: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = layer2.PCO2_ATM_DEFAULT,
    h1: float = layer2.H1,
    h2: float = layer2.H2,
    kz_m2_per_day: float = layer2.KZ_M2_PER_DAY,
    r_remin: float = layer2.R_REMIN,
    light: torch.Tensor | float = layer2.LIGHT,
    source_prey_floor_c: float = 0.0,
) -> torch.Tensor:
    """Advance the 17-state box by one source-mirrored explicit-grazer step."""
    _require_state(state)
    if layer2.USE_COCCOLITH_ONLY_CALCITE or layer2.USE_ENV_RAIN_RATIO:
        raise RuntimeError(
            "the explicit-grazer Stage-0 projection requires the legacy total-loss "
            "calcite source and bare R_PICPOC"
        )

    base_state = state[:15]
    base_next = layer2.carroll6_5pft_2layer_step(
        base_state,
        params,
        dt,
        t,
        s,
        wind,
        pco2_atm,
        h1,
        h2,
        kz_m2_per_day,
        r_remin,
        light,
    )
    rates = darwin1_explicit_grazing_rates(
        state,
        params,
        source_prey_floor_c,
    )

    old_linear_grazing = (
        params[layer2.I_DIATOMGRAZ]
        * G0_GRAZE
        * state[layer2.I_DIATOM]
    )
    old_by_pft = torch.stack(
        (
            old_linear_grazing,
            torch.zeros_like(old_linear_grazing),
            torch.zeros_like(old_linear_grazing),
            torch.zeros_like(old_linear_grazing),
            torch.zeros_like(old_linear_grazing),
        )
    )
    prey_loss = rates["prey_loss"]
    phyto_correction = dt * (old_by_pft - prey_loss)

    explicit_grazing_total = prey_loss.sum(dim=0)
    zoo_mortality_total = rates["zoo_mortality"].sum(dim=0)
    poc_correction = dt * (
        -old_linear_grazing
        + rates["unassimilated_to_poc"]
        + zoo_mortality_total
    )

    # Keep the existing total-loss calcite projection so grazing is the only
    # mechanism changed in this bounded test.
    calcite_rate_correction = params[layer2.I_R_PICPOC] * (
        explicit_grazing_total - old_linear_grazing
    )

    corrected_base = torch.stack(
        (
            base_next[layer2.I_DFE_1],
            base_next[layer2.I_DIATOM] + phyto_correction[0],
            base_next[layer2.I_LGE] + phyto_correction[1],
            base_next[layer2.I_SYN] + phyto_correction[2],
            base_next[layer2.I_PROLL] + phyto_correction[3],
            base_next[layer2.I_PROHL] + phyto_correction[4],
            base_next[layer2.I_POC_1] + poc_correction,
            base_next[layer2.I_PIC_1] + dt * calcite_rate_correction,
            base_next[layer2.I_DIC_1] - dt * calcite_rate_correction,
            base_next[layer2.I_ALK_1] - 2.0 * dt * calcite_rate_correction,
            base_next[layer2.I_DFE_2],
            base_next[layer2.I_POC_2],
            base_next[layer2.I_PIC_2],
            base_next[layer2.I_DIC_2],
            base_next[layer2.I_ALK_2],
        )
    )
    zoo = state[list(ZOOPLANKTON_STATE_INDICES)]
    next_zoo = zoo + dt * rates["zoo_net"]
    return torch.cat((corrected_base, next_zoo), dim=0).clamp(min=0.0)


def initialize_zooplankton(
    base_state: torch.Tensor,
    fraction_per_predator: float,
) -> torch.Tensor:
    """Append two predator states, each a fixed fraction of initial total prey."""
    if base_state.ndim < 1 or base_state.shape[0] != 15:
        raise ValueError("base_state must have leading size 15")
    if not math.isfinite(fraction_per_predator) or fraction_per_predator <= 0.0:
        raise ValueError("fraction_per_predator must be finite and > 0")
    total_phyto = base_state[list(layer2.PHYTOPLANKTON_STATE_INDICES)].sum(dim=0)
    zoo = fraction_per_predator * total_phyto
    return torch.cat((base_state, torch.stack((zoo, zoo))), dim=0)


def integrate_explicit_zooplankton_restored_cycle(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    t_monthly: torch.Tensor,
    s_monthly: torch.Tensor,
    wind_monthly: torch.Tensor,
    restoring_reference: torch.Tensor,
    *,
    restoring_indices: Sequence[int] = CHEMICAL_RESTORING_INDICES,
    restoring_timescale_days: float = 365.25,
    restoring_spatial_mask: torch.Tensor | None = None,
    steps_per_month: int = 122,
    pco2_atm: torch.Tensor | float = layer2.PCO2_ATM_DEFAULT,
    step_fn: Callable[..., torch.Tensor] | None = None,
    light_monthly: torch.Tensor | None = None,
    source_prey_floor_c: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor | int]]:
    """Integrate one seasonal cycle and retain independent gate tensors."""
    _require_state(state0)
    if restoring_reference.shape != state0.shape:
        raise ValueError("restoring_reference must match state0")
    if restoring_timescale_days <= 0 or not math.isfinite(restoring_timescale_days):
        raise ValueError("restoring_timescale_days must be finite and > 0")
    if steps_per_month < 1:
        raise ValueError("steps_per_month must be >= 1")
    if not math.isfinite(source_prey_floor_c) or source_prey_floor_c < 0.0:
        raise ValueError("source_prey_floor_c must be finite and >= 0")
    for name, forcing in (
        ("t_monthly", t_monthly),
        ("s_monthly", s_monthly),
        ("wind_monthly", wind_monthly),
    ):
        if forcing.shape[0] != 12:
            raise ValueError(f"{name} must have a leading length-12 month axis")
    if light_monthly is not None and light_monthly.shape[0] != 12:
        raise ValueError("light_monthly must have a leading length-12 month axis")

    selector = torch.zeros_like(state0)
    spatial_selector: torch.Tensor | float = 1.0
    if restoring_spatial_mask is not None:
        if restoring_spatial_mask.dtype != torch.bool:
            raise TypeError("restoring_spatial_mask must be boolean")
        spatial_selector = restoring_spatial_mask.to(state0.dtype)
    indices = tuple(int(index) for index in restoring_indices)
    if not indices or len(indices) != len(set(indices)):
        raise ValueError("restoring_indices must be non-empty and unique")
    if min(indices) < 0 or max(indices) >= N_TRACERS_EXPLICIT_ZOO:
        raise ValueError("restoring_indices contains an out-of-range index")
    selector[list(indices)] = spatial_selector

    _step = step_fn if step_fn is not None else explicit_zooplankton_step
    state = state0
    state_sum = torch.zeros_like(state0)
    closure_abs = torch.zeros_like(state0)
    model_abs = torch.zeros_like(state0)
    inventory_abs = torch.zeros_like(state0)
    clamp_correction = torch.zeros_like(
        state0[list(PLANKTON_STATE_INDICES)]
    )
    gross_biology = torch.zeros_like(clamp_correction)
    raw_negative_events = torch.zeros_like(clamp_correction, dtype=torch.int64)
    month_ends: list[torch.Tensor] = []

    for month in range(12):
        light = layer2.LIGHT if light_monthly is None else light_monthly[month]
        for _ in range(steps_per_month):
            rates = explicit_zooplankton_process_rates(
                state,
                params,
                t_monthly[month],
                light,
                source_prey_floor_c,
            )
            step_args = (
                state,
                params,
                dt,
                t_monthly[month],
                s_monthly[month],
                wind_monthly[month],
                pco2_atm,
                layer2.H1,
                layer2.H2,
                layer2.KZ_M2_PER_DAY,
                layer2.R_REMIN,
                light,
            )
            if source_prey_floor_c > 0.0:
                model_next = _step(*step_args, source_prey_floor_c)
            else:
                model_next = _step(*step_args)
            requested = (
                dt
                * (restoring_reference - state)
                / restoring_timescale_days
                * selector
            )
            next_state = (model_next + requested).clamp(min=0.0)

            phyto = state[list(layer2.PHYTOPLANKTON_STATE_INDICES)]
            zoo = state[list(ZOOPLANKTON_STATE_INDICES)]
            raw_phyto = phyto + dt * rates["net"]
            raw_zoo = zoo + dt * rates["zoo_net"]
            raw_plankton = torch.cat((raw_phyto, raw_zoo), dim=0)
            clamp_correction += raw_plankton.clamp(min=0.0) - raw_plankton
            raw_negative_events += (raw_plankton < 0.0).to(torch.int64)
            gross_biology[:5] += dt * (
                rates["growth"]
                + rates["linear_mortality"]
                + rates["quadratic_mortality"]
                + rates["grazing"]
            )
            gross_biology[5:] += dt * (
                rates["zoo_gain"] + rates["zoo_mortality"]
            )

            closure_abs += (next_state - model_next).abs()
            model_abs += (model_next - state).abs()
            inventory_abs += state.abs()
            state_sum += next_state
            state = next_state
        month_ends.append(state.clone())

    step_count = 12 * steps_per_month
    return (
        torch.stack(month_ends),
        state_sum / float(step_count),
        {
            "closure_abs": closure_abs,
            "model_abs": model_abs,
            "inventory_abs": inventory_abs,
            "plankton_clamp_correction": clamp_correction,
            "plankton_gross_biology": gross_biology,
            "plankton_raw_negative_events": raw_negative_events,
            "step_count": step_count,
        },
    )
