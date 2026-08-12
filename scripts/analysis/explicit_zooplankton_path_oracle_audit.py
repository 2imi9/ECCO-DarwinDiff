#!/usr/bin/env python
"""Solve continuity-constrained frozen-path large-Z survival oracles."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import time
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import torch

from darwindiff.explicit_zooplankton import (
    GRAZE_HALF_SATURATION_C,
    GRAZE_MAX_PER_DAY,
    SOURCE_PHYGRAZ_MIN_C,
    ZOO_MORTALITY_PER_DAY,
)

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
RADII = (0, 1, 2, 4)
PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_continuity_constrained_large_z_path_oracle.md"
)
DEFAULT_DISCRETE_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_discrete_transport_oracle_audit.json"
)
DEFAULT_SUPPORT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
DEFAULT_SUPPORT_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_path_oracle_audit.json"
)

DT = 0.25
STEPS_PER_MONTH = 122
TOTAL_STEPS = 12 * STEPS_PER_MONTH
REPLAY_ATOL = 2.0e-9


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_bundle(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return torch.load(stream, map_location="cpu", weights_only=True)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _step_logs(item: dict) -> torch.Tensor:
    pool = item["weighted_large_prey"].double() + item["weighted_small_prey"].double()
    numerator = (
        item["assimilated_large_numerator"].double()
        + item["assimilated_small_numerator"].double()
    )
    source_pool = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, item["source_prey_floor_c"]),
    )
    responsive_pool = (source_pool - item["source_prey_floor_c"]).clamp(min=0.0)
    gain = (
        GRAZE_MAX_PER_DAY
        * responsive_pool
        / (responsive_pool + GRAZE_HALF_SATURATION_C)
        * numerator
        / source_pool
    )
    factor = 1.0 + DT * (gain - ZOO_MORTALITY_PER_DAY)
    if not bool((factor[item["mask"].unsqueeze(0).expand_as(factor)] > 0.0).all()):
        raise RuntimeError("non-positive wet-cell Euler factor")
    return torch.log(factor)


def _neighbor_table(mask: torch.Tensor, radius: int) -> torch.Tensor:
    coordinates = mask.nonzero()
    count = coordinates.shape[0]
    index_grid = torch.full(mask.shape, count, dtype=torch.long)
    index_grid[mask] = torch.arange(count)
    offsets = [
        (dy, dx)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if abs(dy) + abs(dx) <= radius
    ]
    neighbors = torch.full((count, len(offsets)), count, dtype=torch.long)
    height, width = mask.shape
    for column, (dy, dx) in enumerate(offsets):
        candidate = coordinates + torch.tensor((dy, dx))
        valid = (
            (candidate[:, 0] >= 0)
            & (candidate[:, 0] < height)
            & (candidate[:, 1] >= 0)
            & (candidate[:, 1] < width)
        )
        if bool(valid.any()):
            candidate_valid = candidate[valid]
            neighbors[valid, column] = index_grid[
                candidate_valid[:, 0], candidate_valid[:, 1]
            ]
    return neighbors


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


def _solve_radius(wet_logs: torch.Tensor, mask: torch.Tensor, radius: int) -> dict:
    coordinates = mask.nonzero()
    neighbors = _neighbor_table(mask, radius)
    count = coordinates.shape[0]
    previous = wet_logs[0]
    backpointers = torch.empty(
        (TOTAL_STEPS - 1, count), dtype=torch.int32
    )
    rows = torch.arange(count)
    for step in range(1, TOTAL_STEPS):
        padded = torch.cat((previous, torch.tensor([float("-inf")])))
        candidates = padded[neighbors]
        best, choice = candidates.max(dim=1)
        selected_previous = neighbors[rows, choice]
        if bool((selected_previous == count).any()):
            raise RuntimeError("a wet path state has no wet predecessor")
        backpointers[step - 1] = selected_previous.to(torch.int32)
        previous = wet_logs[step] + best
    score_tensor, endpoint = previous.max(dim=0)
    path = torch.empty(TOTAL_STEPS, dtype=torch.long)
    path[-1] = endpoint
    for step in range(TOTAL_STEPS - 1, 0, -1):
        path[step - 1] = backpointers[step - 1, path[step]].long()
    summary = _path_summary(float(score_tensor), path, coordinates)
    if summary["maximum_realized_manhattan_jump"] > radius:
        raise RuntimeError("reconstructed path violates the radius")
    return summary


def _solve_unrestricted(wet_logs: torch.Tensor, mask: torch.Tensor) -> dict:
    values, path = wet_logs.max(dim=1)
    return _path_summary(float(values.sum()), path, mask.nonzero())


def _summarize(item: dict, prior: dict) -> dict:
    logs = _step_logs(item)
    wet_logs = logs[:, item["mask"]]
    ladder = {str(radius): _solve_radius(wet_logs, item["mask"], radius) for radius in RADII}
    unrestricted = _solve_unrestricted(wet_logs, item["mask"])
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discrete-report", type=Path, default=DEFAULT_DISCRETE_REPORT)
    parser.add_argument("--support-report", type=Path, default=DEFAULT_SUPPORT_REPORT)
    parser.add_argument("--support-bundle", type=Path, default=DEFAULT_SUPPORT_BUNDLE)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    discrete_report = json.loads(args.discrete_report.read_text(encoding="utf-8"))
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = _load_bundle(args.support_bundle)
    hashes = {
        "discrete_report_sha256": _sha256(args.discrete_report),
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
    }
    if support_report["bundle_artifact"]["sha256"] != hashes["support_bundle_sha256"]:
        raise RuntimeError("support report does not bind its bundle")
    if support_report["config"] != support_bundle["config"]:
        raise RuntimeError("support configs differ")
    if discrete_report["config"]["support_report_sha256"] != hashes[
        "support_report_sha256"
    ]:
        raise RuntimeError("discrete report does not bind the support report")
    if discrete_report["config"]["support_bundle_sha256"] != hashes[
        "support_bundle_sha256"
    ]:
        raise RuntimeError("discrete report does not bind the support bundle")
    if support_report["config"]["source_prey_floor_c"] != SOURCE_PHYGRAZ_MIN_C:
        raise RuntimeError("support artifact uses the wrong prey floor")

    config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "total_steps": TOTAL_STEPS,
        "mortality_per_day": ZOO_MORTALITY_PER_DAY,
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "manhattan_radii": list(RADII),
        "longitude_wrap": False,
        "replay_atol": REPLAY_ATOL,
        **hashes,
    }
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "aois": {},
    }
    for aoi in AOIS:
        report["aois"][aoi] = _summarize(
            support_bundle["aois"][aoi], discrete_report["aois"][aoi]
        )

    integrity = all(item["integrity"]["pass"] for item in report["aois"].values())
    natl_radius1_positive = (
        report["aois"]["natlsubpolar"]["radius_ladder"]["1"][
            "annual_log_multiplier"
        ]
        > 0.0
    )
    if integrity and natl_radius1_positive:
        branch = "natl-knife-edge-survives-radius1-continuity"
        primary = "supported"
    elif integrity:
        branch = "natl-knife-edge-requires-discontinuous-relocation"
        primary = "falsified"
    else:
        branch = "unresolved-reproduction-failed"
        primary = "unresolved"
    report["decision"] = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "natl_radius1_positive": natl_radius1_positive,
        "actual_transport_tested": False,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_json(args.report, report)
    print(f"path-oracle audit: branch={branch} elapsed={report['elapsed_seconds']:.2f}s")
    return 0 if integrity else 2


if __name__ == "__main__":
    raise SystemExit(main())
