"""Pure metrics for the preregistered seasonally forced self-twin target gate."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import torch

from darwindiff.carroll6_5pft_2layer import (
    H1,
    H2,
    I_ALK_1,
    I_DFE_1,
    I_DFE_2,
    I_DIATOM,
    I_DIC_1,
    I_LGE,
    I_PIC_1,
    I_POC_1,
    I_PROHL,
    I_PROLL,
    I_SYN,
    KZ_M2_PER_DAY,
    PCO2_ATM_DEFAULT,
    PHYTOPLANKTON_STATE_INDICES,
    R_REMIN,
    carroll6_5pft_2layer_step,
    phytoplankton_process_rates,
)

STABILITY_FIELDS: tuple[tuple[str, int], ...] = (
    ("DFe1", I_DFE_1),
    ("DFe2", I_DFE_2),
    ("Chl1_diatom", I_DIATOM),
    ("Chl2_lge", I_LGE),
    ("Chl3_syn", I_SYN),
    ("Chl4_proll", I_PROLL),
    ("Chl5_prohl", I_PROHL),
    ("POC1", I_POC_1),
    ("PIC1", I_PIC_1),
    ("DIC1", I_DIC_1),
    ("ALK1", I_ALK_1),
)

DFE2_MIN_REL_SD: dict[str, float] = {
    "eqpac": 0.0423,
    "natlsubpolar": 0.0662,
    "southernoceanpac": 0.1195,
}

CHEMICAL_RESTORING_INDICES: tuple[int, ...] = (
    I_DFE_1,
    I_POC_1,
    I_PIC_1,
    I_DIC_1,
    I_ALK_1,
    I_DFE_2,
    11,  # POC2
    12,  # PIC2
    13,  # DIC2
    14,  # ALK2
)
PHYTOPLANKTON_INDICES: tuple[int, ...] = (I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL)
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
)

GREGORIAN_MONTH_LENGTHS: tuple[int, ...] = (
    31,
    28,
    31,
    30,
    31,
    30,
    31,
    31,
    30,
    31,
    30,
    31,
)
MONTH_MIDPOINT_DAY_OF_YEAR: tuple[float, ...] = tuple(
    sum(GREGORIAN_MONTH_LENGTHS[:month])
    + (GREGORIAN_MONTH_LENGTHS[month] + 1.0) / 2.0
    for month in range(12)
)
ASTRONOMICAL_OBLIQUITY_DEGREES = 23.439
ASTRONOMICAL_YEAR_DAYS = 365.25
ASTRONOMICAL_DECLINATION_PHASE_DAY = 80.0
ASTRONOMICAL_RECONSTRUCTION_ATOL = 5e-7


def astronomical_monthly_light(latitude_degrees: torch.Tensor) -> torch.Tensor:
    """Return parameter-free monthly daily-mean TOA light normalized per cell.

    The calculation follows the frozen ``hy_szn_light`` preregistration. It is
    evaluated in float64 for stable polar geometry, then cast back to the input
    floating dtype and normalized once more so float32 outputs retain mean one.
    """
    latitude = torch.as_tensor(latitude_degrees)
    if not latitude.is_floating_point():
        latitude = latitude.to(torch.float32)
    if not bool(torch.isfinite(latitude).all()):
        raise ValueError("latitude_degrees must be finite")
    if bool((latitude.abs() > 90.0).any()):
        raise ValueError("latitude_degrees must lie in [-90, 90]")

    work = latitude.to(torch.float64)
    phi = work * (math.pi / 180.0)
    days = torch.tensor(
        MONTH_MIDPOINT_DAY_OF_YEAR,
        dtype=torch.float64,
        device=latitude.device,
    ).reshape(12, *([1] * latitude.ndim))
    obliquity = math.radians(ASTRONOMICAL_OBLIQUITY_DEGREES)
    declination = torch.asin(
        math.sin(obliquity)
        * torch.sin(
            2.0
            * math.pi
            * (days - ASTRONOMICAL_DECLINATION_PHASE_DAY)
            / ASTRONOMICAL_YEAR_DAYS
        )
    )
    hour_angle = torch.acos(
        (-torch.tan(phi).unsqueeze(0) * torch.tan(declination)).clamp(-1.0, 1.0)
    )
    q = (
        hour_angle * torch.sin(phi).unsqueeze(0) * torch.sin(declination)
        + torch.cos(phi).unsqueeze(0)
        * torch.cos(declination)
        * torch.sin(hour_angle)
    ).clamp(min=0.0)
    annual_mean = q.mean(dim=0, keepdim=True)
    if not bool((annual_mean > 0.0).all()):
        raise ValueError("astronomical light has a non-positive annual mean")
    light = (q / annual_mean).to(latitude.dtype)
    return light / light.mean(dim=0, keepdim=True)


def evaluate_light_integrity(
    light_monthly: torch.Tensor,
    mask: torch.Tensor,
    *,
    mean_tolerance: float = 1e-6,
) -> dict:
    """Evaluate the frozen light-field integrity gates over ocean cells."""
    if light_monthly.shape[0] != 12 or light_monthly.shape[1:] != mask.shape:
        raise ValueError("light_monthly must have shape [12, *mask.shape]")
    if mask.dtype != torch.bool:
        raise TypeError("mask must be a boolean tensor")
    values = light_monthly[:, mask]
    finite = bool(torch.isfinite(values).all())
    nonnegative = finite and bool((values >= 0.0).all())
    per_cell_means = values.mean(dim=0)
    max_mean_error = float((per_cell_means - 1.0).abs().max().detach().cpu())
    mean_one = finite and math.isfinite(max_mean_error) and max_mean_error <= mean_tolerance
    failures: list[str] = []
    if not finite:
        failures.append("non_finite")
    if not nonnegative:
        failures.append("negative")
    if not mean_one:
        failures.append("per_cell_mean")
    return {
        "pass": not failures,
        "failure_reasons": failures,
        "finite": finite,
        "nonnegative": nonnegative,
        "per_cell_mean_one": mean_one,
        "per_cell_mean_tolerance": mean_tolerance,
        "max_abs_per_cell_mean_error": max_mean_error,
        "minimum": float(values.min().detach().cpu()),
        "maximum": float(values.max().detach().cpu()),
    }


def integrate_seasonal_restored_summary(
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
    n_spinup_cycles: int = 0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    step_fn: Callable[..., torch.Tensor] | None = None,
    light_monthly: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
    """Integrate a seasonal cycle with a fixed parameter-independent restoring closure.

    Budget tensors contain time-integrated absolute applied closure increments,
    endogenous model increments, and pre-step inventory. They retain spatial
    dimensions so the target gate can aggregate over its exact ocean mask.
    ``light_monthly=None`` preserves the legacy constant-light step call.
    """
    if restoring_reference.shape != state0.shape:
        raise ValueError(
            "restoring_reference must match state0 shape, got "
            f"{tuple(restoring_reference.shape)} != {tuple(state0.shape)}"
        )
    if restoring_timescale_days <= 0 or not math.isfinite(restoring_timescale_days):
        raise ValueError("restoring_timescale_days must be finite and > 0")
    if steps_per_month < 1:
        raise ValueError("steps_per_month must be >= 1")
    for name, forcing in (
        ("T_monthly", t_monthly),
        ("S_monthly", s_monthly),
        ("wind_monthly", wind_monthly),
    ):
        if forcing.shape[0] != 12:
            raise ValueError(f"{name} must have a leading length-12 month axis")
    if light_monthly is not None and light_monthly.shape[0] != 12:
        raise ValueError("light_monthly must have a leading length-12 month axis")
    indices = tuple(int(index) for index in restoring_indices)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("restoring_indices must be non-empty and unique")
    if min(indices) < 0 or max(indices) >= state0.shape[0]:
        raise ValueError("restoring_indices contains an out-of-range state index")

    selector = torch.zeros_like(state0)
    spatial_selector: torch.Tensor | float = 1.0
    if restoring_spatial_mask is not None:
        if restoring_spatial_mask.dtype != torch.bool:
            raise TypeError("restoring_spatial_mask must be boolean")
        try:
            spatial_selector = restoring_spatial_mask.to(state0.dtype).expand(state0.shape[1:])
        except RuntimeError as exc:
            raise ValueError(
                "restoring_spatial_mask is not broadcastable to state spatial shape"
            ) from exc
    selector[list(indices)] = spatial_selector

    _step = step_fn if step_fn is not None else carroll6_5pft_2layer_step
    state = state0
    recorded: list[torch.Tensor] = []
    state_sum: torch.Tensor | None = None
    closure_abs = torch.zeros_like(state0)
    model_abs = torch.zeros_like(state0)
    inventory_abs = torch.zeros_like(state0)
    for cycle in range(n_spinup_cycles + 1):
        recorded_cycle = cycle == n_spinup_cycles
        month_ends: list[torch.Tensor] = []
        for month in range(12):
            for _ in range(steps_per_month):
                step_args = (
                    state,
                    params,
                    dt,
                    t_monthly[month],
                    s_monthly[month],
                    wind_monthly[month],
                    pco2_atm,
                    H1,
                    H2,
                    KZ_M2_PER_DAY,
                    R_REMIN,
                )
                if light_monthly is None:
                    model_next = _step(*step_args)
                else:
                    model_next = _step(*step_args, light_monthly[month])
                requested = (
                    dt * (restoring_reference - state) / restoring_timescale_days * selector
                )
                next_state = (model_next + requested).clamp(min=0.0)
                if recorded_cycle:
                    applied = next_state - model_next
                    closure_abs = closure_abs + applied.abs()
                    model_abs = model_abs + (model_next - state).abs()
                    inventory_abs = inventory_abs + state.abs()
                    state_sum = next_state if state_sum is None else state_sum + next_state
                state = next_state
            if recorded_cycle:
                month_ends.append(state)
        if recorded_cycle:
            recorded = month_ends

    if state_sum is None:  # pragma: no cover - validated positive cycle length
        raise RuntimeError("recorded restoring cycle contained no states")
    return (
        torch.stack(recorded),
        state_sum / float(12 * steps_per_month),
        {
            "closure_abs": closure_abs,
            "model_abs": model_abs,
            "inventory_abs": inventory_abs,
        },
    )


@torch.no_grad()
def integrate_seasonal_restored_process_budgets(
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
    n_cycles: int = 8,
    budget_cycles: Sequence[int] = (1, 2, 7, 8),
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    step_fn: Callable[..., torch.Tensor] | None = None,
    light_monthly: torch.Tensor | None = None,
) -> tuple[torch.Tensor, dict[int, dict[str, torch.Tensor | int]]]:
    """Integrate frozen seasonal targets and retain exact per-cell PFT budgets."""
    if restoring_reference.shape != state0.shape:
        raise ValueError("restoring_reference must match state0 shape")
    if restoring_timescale_days <= 0 or not math.isfinite(restoring_timescale_days):
        raise ValueError("restoring_timescale_days must be finite and > 0")
    if steps_per_month < 1:
        raise ValueError("steps_per_month must be >= 1")
    if n_cycles < 1:
        raise ValueError("n_cycles must be >= 1")
    selected_cycles = tuple(int(cycle) for cycle in budget_cycles)
    if not selected_cycles or len(set(selected_cycles)) != len(selected_cycles):
        raise ValueError("budget_cycles must be non-empty and unique")
    if min(selected_cycles) < 1 or max(selected_cycles) > n_cycles:
        raise ValueError("budget_cycles must lie within 1..n_cycles")
    for name, forcing in (
        ("T_monthly", t_monthly),
        ("S_monthly", s_monthly),
        ("wind_monthly", wind_monthly),
    ):
        if forcing.shape[0] != 12:
            raise ValueError(f"{name} must have a leading length-12 month axis")
    if light_monthly is not None and light_monthly.shape[0] != 12:
        raise ValueError("light_monthly must have a leading length-12 month axis")

    indices = tuple(int(index) for index in restoring_indices)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("restoring_indices must be non-empty and unique")
    if min(indices) < 0 or max(indices) >= state0.shape[0]:
        raise ValueError("restoring_indices contains an out-of-range state index")

    selector = torch.zeros_like(state0)
    spatial_selector: torch.Tensor | float = 1.0
    if restoring_spatial_mask is not None:
        if restoring_spatial_mask.dtype != torch.bool:
            raise TypeError("restoring_spatial_mask must be boolean")
        try:
            spatial_selector = restoring_spatial_mask.to(state0.dtype).expand(
                state0.shape[1:]
            )
        except RuntimeError as exc:
            raise ValueError(
                "restoring_spatial_mask is not broadcastable to state spatial shape"
            ) from exc
    selector[list(indices)] = spatial_selector

    _step = step_fn if step_fn is not None else carroll6_5pft_2layer_step
    phyto_indices = list(PHYTOPLANKTON_STATE_INDICES)
    selected = set(selected_cycles)
    state = state0
    output: dict[int, dict[str, torch.Tensor | int]] = {}
    steps_in_cycle = 12 * steps_per_month

    for cycle in range(1, n_cycles + 1):
        record = cycle in selected
        budget: dict[str, torch.Tensor | int] = {}
        if record:
            phyto = state[phyto_indices]
            spatial = state[I_DFE_1]
            budget = {
                "growth": torch.zeros_like(phyto),
                "linear_mortality": torch.zeros_like(phyto),
                "quadratic_mortality": torch.zeros_like(phyto),
                "grazing": torch.zeros_like(phyto),
                "actual_increment": torch.zeros_like(phyto),
                "clamp_correction": torch.zeros_like(phyto),
                "raw_negative_events": torch.zeros_like(phyto, dtype=torch.int64),
                "post_step_zero_events": torch.zeros_like(phyto, dtype=torch.int64),
                "closure_abs": torch.zeros_like(phyto),
                "f_fe_sum": torch.zeros_like(spatial),
                "light_sum": torch.zeros_like(spatial),
                "gamma_t_sum": torch.zeros_like(spatial),
                "state_sum": torch.zeros_like(state),
                "initial_phyto": phyto.clone(),
                "step_count": steps_in_cycle,
            }
            month_ends: list[torch.Tensor] = []

        for month in range(12):
            for _ in range(steps_per_month):
                step_args = (
                    state,
                    params,
                    dt,
                    t_monthly[month],
                    s_monthly[month],
                    wind_monthly[month],
                    pco2_atm,
                    H1,
                    H2,
                    KZ_M2_PER_DAY,
                    R_REMIN,
                )
                if light_monthly is None:
                    rates = phytoplankton_process_rates(
                        state, params, t_monthly[month]
                    )
                    model_next = _step(*step_args)
                else:
                    rates = phytoplankton_process_rates(
                        state, params, t_monthly[month], light_monthly[month]
                    )
                    model_next = _step(*step_args, light_monthly[month])

                requested = (
                    dt * (restoring_reference - state) / restoring_timescale_days * selector
                )
                next_state = (model_next + requested).clamp(min=0.0)
                if record:
                    current_phyto = state[phyto_indices]
                    next_phyto = next_state[phyto_indices]
                    net_increment = dt * rates["net"]
                    actual_increment = next_phyto - current_phyto
                    raw_next = current_phyto + net_increment
                    for key in (
                        "growth",
                        "linear_mortality",
                        "quadratic_mortality",
                        "grazing",
                    ):
                        budget[key] += dt * rates[key]
                    budget["actual_increment"] += actual_increment
                    budget["clamp_correction"] += raw_next.clamp(min=0.0) - raw_next
                    budget["raw_negative_events"] += (raw_next < 0).to(torch.int64)
                    budget["post_step_zero_events"] += (next_phyto == 0).to(torch.int64)
                    budget["closure_abs"] += (
                        next_state[phyto_indices] - model_next[phyto_indices]
                    ).abs()
                    budget["f_fe_sum"] += rates["f_fe"]
                    budget["light_sum"] += rates["light"]
                    budget["gamma_t_sum"] += rates["gamma_t"]
                    budget["state_sum"] += next_state
                state = next_state
            if record:
                month_ends.append(state.clone())

        if record:
            budget["net"] = (
                budget["growth"]
                - budget["linear_mortality"]
                - budget["quadratic_mortality"]
                - budget["grazing"]
            )
            budget["final_phyto"] = state[phyto_indices].clone()
            budget["all_step_mean"] = budget.pop("state_sum") / float(steps_in_cycle)
            budget["month_ends"] = torch.stack(month_ends)
            budget["f_fe_mean"] = budget.pop("f_fe_sum") / float(steps_in_cycle)
            budget["light_mean"] = budget.pop("light_sum") / float(steps_in_cycle)
            budget["gamma_t_mean"] = budget.pop("gamma_t_sum") / float(steps_in_cycle)
            output[cycle] = budget

    return state, output


def evaluate_restoring_budget(
    budget: dict[str, torch.Tensor],
    mask: torch.Tensor,
    *,
    restoring_indices: Sequence[int] = CHEMICAL_RESTORING_INDICES,
    share_max: float = 0.50,
    turnover_max: float = 1.0,
) -> dict:
    """Evaluate gross closure dominance and exact no-phytoplankton-restoring gates."""
    required = {"closure_abs", "model_abs", "inventory_abs"}
    if set(budget) != required:
        raise KeyError(f"restoring budget keys must be {sorted(required)}")
    closure_abs = budget["closure_abs"]
    model_abs = budget["model_abs"]
    inventory_abs = budget["inventory_abs"]
    if closure_abs.shape != model_abs.shape or closure_abs.shape != inventory_abs.shape:
        raise ValueError("restoring budget tensors must have identical shapes")

    restored = set(int(index) for index in restoring_indices)
    per_tracer: dict[str, dict[str, float | bool]] = {}
    failures: list[str] = []
    for index, name in enumerate(STATE_NAMES):
        closure = float(closure_abs[index][mask].sum())
        model = float(model_abs[index][mask].sum())
        inventory = float(inventory_abs[index][mask].sum())
        share = closure / max(closure + model, 1e-30)
        turnover = closure / max(inventory, 1e-30)
        is_restored = index in restored
        share_pass = (not is_restored) or share <= share_max
        turnover_pass = (not is_restored) or turnover <= turnover_max
        zero_when_unrestored = is_restored or closure == 0.0
        if not share_pass:
            failures.append(f"{name}:closure_share")
        if not turnover_pass:
            failures.append(f"{name}:closure_turnover")
        if not zero_when_unrestored:
            failures.append(f"{name}:unexpected_closure")
        per_tracer[name] = {
            "restored": is_restored,
            "closure_abs": closure,
            "model_abs": model,
            "inventory_abs": inventory,
            "closure_share": share,
            "closure_turnover": turnover,
            "share_pass": share_pass,
            "turnover_pass": turnover_pass,
            "zero_when_unrestored": zero_when_unrestored,
        }

    phytoplankton_zero = all(
        float(closure_abs[index][mask].sum()) == 0.0 for index in PHYTOPLANKTON_INDICES
    )
    return {
        "pass": not failures,
        "failure_reasons": failures,
        "closure_share_threshold": share_max,
        "closure_turnover_threshold": turnover_max,
        "phytoplankton_closure_exactly_zero": phytoplankton_zero,
        "per_tracer": per_tracer,
    }


def masked_relative_l2(
    current: torch.Tensor,
    previous: torch.Tensor,
    mask: torch.Tensor,
) -> float:
    """Return ||current-previous||_2 / ||previous||_2 over ``mask``."""
    curr = current[mask]
    prev = previous[mask]
    denominator = torch.linalg.vector_norm(prev).clamp(min=1e-30)
    return float((torch.linalg.vector_norm(curr - prev) / denominator).detach().cpu())


def relative_spatial_sd(field: torch.Tensor, mask: torch.Tensor) -> float:
    """Sample spatial SD divided by absolute spatial mean over ``mask``."""
    values = field[mask]
    if values.numel() < 2:
        return float("nan")
    rel_sd = values.std() / values.mean().abs().clamp(min=1e-30)
    return float(rel_sd.detach().cpu())


def summarize_target_state(state: torch.Tensor, mask: torch.Tensor) -> dict[str, dict[str, float]]:
    """Summarize every raw state field used by the target-quality gate."""
    out: dict[str, dict[str, float]] = {}
    for name, index in STABILITY_FIELDS:
        values = state[index][mask]
        out[name] = {
            "mean": float(values.mean().detach().cpu()),
            "min": float(values.min().detach().cpu()),
            "max": float(values.max().detach().cpu()),
            "relative_spatial_sd": relative_spatial_sd(state[index], mask),
        }
    return out


def evaluate_target_cycle(
    previous_mean: torch.Tensor,
    current_mean: torch.Tensor,
    mask: torch.Tensor,
    aoi_key: str,
    *,
    field_rel_l2_max: float = 0.01,
    dfe2_rel_sd_change_max: float = 0.05,
    chl1_rel_sd_min: float = 0.1,
    chl1_rel_sd_max: float = 1.0,
) -> dict:
    """Evaluate one all-step cycle mean against the frozen Stage-0 gates."""
    if aoi_key not in DFE2_MIN_REL_SD:
        raise KeyError(f"no preregistered DFe2 contrast threshold for AOI {aoi_key!r}")
    if mask.dtype is not torch.bool:
        raise TypeError("mask must be a boolean tensor")
    if int(mask.sum()) < 2:
        raise ValueError("target gate needs at least two masked cells")

    field_changes = {
        name: masked_relative_l2(current_mean[index], previous_mean[index], mask)
        for name, index in STABILITY_FIELDS
    }
    previous_dfe2_rel_sd = relative_spatial_sd(previous_mean[I_DFE_2], mask)
    current_dfe2_rel_sd = relative_spatial_sd(current_mean[I_DFE_2], mask)
    dfe2_rel_sd_change = abs(current_dfe2_rel_sd - previous_dfe2_rel_sd) / max(
        abs(previous_dfe2_rel_sd), 1e-30
    )
    chl1_rel_sd = relative_spatial_sd(current_mean[I_DIATOM], mask)

    finite_values = [
        *field_changes.values(),
        previous_dfe2_rel_sd,
        current_dfe2_rel_sd,
        dfe2_rel_sd_change,
        chl1_rel_sd,
    ]
    finite = all(math.isfinite(v) for v in finite_values)
    fields_stable = finite and all(v <= field_rel_l2_max for v in field_changes.values())
    dfe2_stable = finite and dfe2_rel_sd_change <= dfe2_rel_sd_change_max
    dfe2_contrast = finite and current_dfe2_rel_sd >= DFE2_MIN_REL_SD[aoi_key]
    chl1_sane = finite and chl1_rel_sd_min <= chl1_rel_sd <= chl1_rel_sd_max

    failures: list[str] = []
    if not finite:
        failures.append("non_finite_metric")
    if not fields_stable:
        failures.append("cycle_field_stability")
    if not dfe2_stable:
        failures.append("dfe2_contrast_stability")
    if not dfe2_contrast:
        failures.append("dfe2_contrast_retention")
    if not chl1_sane:
        failures.append("chl1_sanity")

    return {
        "pass": not failures,
        "failure_reasons": failures,
        "field_relative_l2": field_changes,
        "max_field_relative_l2": max(field_changes.values()),
        "field_relative_l2_threshold": field_rel_l2_max,
        "previous_dfe2_relative_spatial_sd": previous_dfe2_rel_sd,
        "dfe2_relative_spatial_sd": current_dfe2_rel_sd,
        "dfe2_relative_spatial_sd_change": dfe2_rel_sd_change,
        "dfe2_relative_spatial_sd_change_threshold": dfe2_rel_sd_change_max,
        "dfe2_min_relative_spatial_sd": DFE2_MIN_REL_SD[aoi_key],
        "chl1_relative_spatial_sd": chl1_rel_sd,
        "chl1_relative_spatial_sd_interval": [chl1_rel_sd_min, chl1_rel_sd_max],
        "checks": {
            "finite": finite,
            "cycle_fields_stable": fields_stable,
            "dfe2_contrast_stable": dfe2_stable,
            "dfe2_contrast_retained": dfe2_contrast,
            "chl1_sane": chl1_sane,
        },
    }
