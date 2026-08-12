#!/usr/bin/env python
"""Independently verify continuity-constrained large-Z path oracles."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
AOI_SHAPES = {
    "eqpac": (21, 51),
    "natlsubpolar": (16, 31),
    "southernoceanpac": (16, 81),
}
OCEAN_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
RADII = (0, 1, 2, 4)
PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_continuity_constrained_large_z_path_oracle.md"
)
DT = 0.25
STEPS_PER_MONTH = 122
TOTAL_STEPS = 12 * STEPS_PER_MONTH
SOURCE_PREY_FLOOR_C = 1.2e-8
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
MORTALITY_PER_DAY = 1.0 / 30.0
REPLAY_ATOL = 2.0e-9


class VerificationError(ValueError):
    """Raised when a constrained path relation does not hold."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bundle(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return torch.load(stream, map_location="cpu", weights_only=True)


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key, value in expected.items():
            _compare(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        _require(isinstance(actual, list), f"{path}: expected list")
        _require(len(expected) == len(actual), f"{path}: length differs")
        for index, value in enumerate(expected):
            _compare(value, actual[index], f"{path}[{index}]")
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        tolerance = 2.0e-9 * max(abs(expected), 1.0)
        _require(
            math.isclose(expected, float(actual), abs_tol=tolerance),
            f"{path}: value differs",
        )
    else:
        _require(expected == actual, f"{path}: value differs")


def _step_logs(item: dict) -> torch.Tensor:
    pool = item["weighted_large_prey"].double() + item["weighted_small_prey"].double()
    numerator = (
        item["assimilated_large_numerator"].double()
        + item["assimilated_small_numerator"].double()
    )
    source = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, item["source_prey_floor_c"]),
    )
    responsive = (source - item["source_prey_floor_c"]).clamp(min=0.0)
    gain = (
        GRAZE_MAX_PER_DAY
        * responsive
        / (responsive + GRAZE_HALF_SATURATION_C)
        * numerator
        / source
    )
    factor = 1.0 + DT * (gain - MORTALITY_PER_DAY)
    wet = factor[:, item["mask"]]
    _require(bool((wet > 0.0).all()), "non-positive wet-cell Euler factor")
    return torch.log(factor)


def _neighbors(mask: torch.Tensor, radius: int) -> torch.Tensor:
    coordinates = mask.nonzero()
    count = coordinates.shape[0]
    grid = torch.full(mask.shape, count, dtype=torch.long)
    grid[mask] = torch.arange(count)
    offsets = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if abs(dy) + abs(dx) <= radius
    ]
    table = torch.full((count, len(offsets)), count, dtype=torch.long)
    height, width = mask.shape
    for column, (dy, dx) in enumerate(offsets):
        candidates = coordinates + torch.tensor((dy, dx))
        valid = (
            (candidates[:, 0] >= 0)
            & (candidates[:, 0] < height)
            & (candidates[:, 1] >= 0)
            & (candidates[:, 1] < width)
        )
        candidates = candidates[valid]
        table[valid, column] = grid[candidates[:, 0], candidates[:, 1]]
    return table


def _path_summary(score: float, path: torch.Tensor, coordinates: torch.Tensor) -> dict:
    points = coordinates[path]
    jumps = (points[1:] - points[:-1]).abs().sum(dim=1)
    return {
        "annual_log_multiplier": score,
        "annual_retention": math.exp(score),
        "start_row_col": [int(points[0, 0]), int(points[0, 1])],
        "end_row_col": [int(points[-1, 0]), int(points[-1, 1])],
        "selected_cell_count": int(torch.unique(path).numel()),
        "switch_count": int((path[1:] != path[:-1]).sum()),
        "maximum_realized_manhattan_jump": int(jumps.max()),
    }


def _solve(wet_logs: torch.Tensor, mask: torch.Tensor, radius: int) -> dict:
    coordinates = mask.nonzero()
    table = _neighbors(mask, radius)
    count = coordinates.shape[0]
    previous = wet_logs[0]
    back = torch.empty((TOTAL_STEPS - 1, count), dtype=torch.int32)
    rows = torch.arange(count)
    for step in range(1, TOTAL_STEPS):
        padded = torch.cat((previous, torch.tensor([float("-inf")])))
        candidates = padded[table]
        best, choice = candidates.max(dim=1)
        predecessor = table[rows, choice]
        _require(bool((predecessor != count).all()), "wet state has no predecessor")
        back[step - 1] = predecessor.to(torch.int32)
        previous = wet_logs[step] + best
    score, endpoint = previous.max(dim=0)
    path = torch.empty(TOTAL_STEPS, dtype=torch.long)
    path[-1] = endpoint
    for step in range(TOTAL_STEPS - 1, 0, -1):
        path[step - 1] = back[step - 1, path[step]].long()
    summary = _path_summary(float(score), path, coordinates)
    _require(
        summary["maximum_realized_manhattan_jump"] <= radius,
        "reconstructed path violates radius",
    )
    return summary


def _unrestricted(wet_logs: torch.Tensor, mask: torch.Tensor) -> dict:
    values, path = wet_logs.max(dim=1)
    return _path_summary(float(values.sum()), path, mask.nonzero())


def _summarize(item: dict, prior: dict) -> dict:
    wet_logs = _step_logs(item)[:, item["mask"]]
    ladder = {str(radius): _solve(wet_logs, item["mask"], radius) for radius in RADII}
    unrestricted = _unrestricted(wet_logs, item["mask"])
    fixed_error = abs(
        ladder["0"]["annual_log_multiplier"]
        - prior["fixed_cell"]["annual_log_multiplier"]
    )
    unrestricted_error = abs(
        unrestricted["annual_log_multiplier"]
        - prior["stepwise_teleport"]["annual_log_multiplier"]
    )
    scores = [ladder[str(radius)]["annual_log_multiplier"] for radius in RADII]
    scores.append(unrestricted["annual_log_multiplier"])
    monotone = all(left <= right + REPLAY_ATOL for left, right in pairwise(scores))
    return {
        "integrity": {
            "pass": fixed_error <= REPLAY_ATOL
            and unrestricted_error <= REPLAY_ATOL
            and monotone,
            "fixed_cell_replay_abs_error": fixed_error,
            "unrestricted_replay_abs_error": unrestricted_error,
            "replay_atol": REPLAY_ATOL,
            "score_ladder_nondecreasing": monotone,
        },
        "radius_ladder": ladder,
        "unrestricted": unrestricted,
    }


def verify(
    report: dict,
    discrete_report: dict,
    support_report: dict,
    support_bundle: dict,
    hashes: dict[str, str],
) -> dict:
    _require(report["schema_version"] == 1, "report schema version")
    _require(report["status"] == "MEASURED_NOT_INDEPENDENTLY_VERIFIED", "report status")
    _require(report["preregistration"] == PREREGISTRATION, "report preregistration")
    _require(
        support_report["bundle_artifact"]["sha256"] == hashes["support_bundle_sha256"],
        "support bundle SHA-256 differs",
    )
    _require(support_report["config"] == support_bundle["config"], "support configs differ")
    _require(
        discrete_report["config"]["support_report_sha256"]
        == hashes["support_report_sha256"],
        "discrete-to-support report lineage differs",
    )
    _require(
        discrete_report["config"]["support_bundle_sha256"]
        == hashes["support_bundle_sha256"],
        "discrete-to-support bundle lineage differs",
    )
    expected_config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "total_steps": TOTAL_STEPS,
        "mortality_per_day": MORTALITY_PER_DAY,
        "source_prey_floor_c": SOURCE_PREY_FLOOR_C,
        "manhattan_radii": list(RADII),
        "longitude_wrap": False,
        "replay_atol": REPLAY_ATOL,
        **hashes,
    }
    _require(report["config"] == expected_config, "frozen config differs")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")

    summaries = {}
    raw_support_tensor_cells = 0
    for aoi in AOIS:
        item = support_bundle["aois"][aoi]
        mask = item["mask"]
        _require(
            mask.dtype == torch.bool and tuple(mask.shape) == AOI_SHAPES[aoi],
            f"{aoi}: mask differs",
        )
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: wet-cell count differs")
        _require(item["source_prey_floor_c"] == SOURCE_PREY_FLOOR_C, f"{aoi}: prey floor")
        for name in (
            "weighted_large_prey",
            "weighted_small_prey",
            "assimilated_large_numerator",
            "assimilated_small_numerator",
        ):
            tensor = item[name]
            _require(
                tensor.dtype == torch.float32
                and tuple(tensor.shape) == (TOTAL_STEPS, *AOI_SHAPES[aoi]),
                f"{aoi}.{name}: shape or dtype differs",
            )
            raw_support_tensor_cells += tensor.numel()
        _require(
            torch.allclose(
                item["assimilated_large_numerator"],
                0.5 * item["weighted_large_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: large-prey assimilation relation differs",
        )
        _require(
            torch.allclose(
                item["assimilated_small_numerator"],
                0.7 * item["weighted_small_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: small-prey assimilation relation differs",
        )
        summary = _summarize(item, discrete_report["aois"][aoi])
        _compare(summary, report["aois"][aoi], f"report.{aoi}")
        summaries[aoi] = summary

    integrity = all(item["integrity"]["pass"] for item in summaries.values())
    natl_positive = (
        summaries["natlsubpolar"]["radius_ladder"]["1"]["annual_log_multiplier"]
        > 0.0
    )
    if integrity and natl_positive:
        branch = "natl-knife-edge-survives-radius1-continuity"
        primary = "supported"
    elif integrity:
        branch = "natl-knife-edge-requires-discontinuous-relocation"
        primary = "falsified"
    else:
        branch = "unresolved-reproduction-failed"
        primary = "unresolved"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "natl_radius1_positive": natl_positive,
        "actual_transport_tested": False,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(report["decision"]["actual_transport_tested"] is False, "transport tested")
    _require(report["decision"]["target_rehabilitated"] is False, "target rehabilitated")
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_support_tensor_cells": raw_support_tensor_cells,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--discrete-report", type=Path, required=True)
    parser.add_argument("--support-report", type=Path, required=True)
    parser.add_argument("--support-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    discrete_report = json.loads(args.discrete_report.read_text(encoding="utf-8"))
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = load_bundle(args.support_bundle)
    hashes = {
        "discrete_report_sha256": _sha256(args.discrete_report),
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
    }
    try:
        result = verify(
            report, discrete_report, support_report, support_bundle, hashes
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"PATH-ORACLE VERIFICATION FAILED: {exc}")
        return 2
    result.update(
        {
            "report": args.report.as_posix(),
            "report_sha256": _sha256(args.report),
            **hashes,
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED explicit-zoo path oracle: "
        f"decision={result['decision']['branch']} "
        f"raw_support_tensor_cells={result['raw_support_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
