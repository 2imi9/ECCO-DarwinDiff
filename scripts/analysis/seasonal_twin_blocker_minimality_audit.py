#!/usr/bin/env python3
"""Enumerate the preregistered waiver lattice for the failed seasonal target."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
WAIVERS = (
    "drop_large_predator_obligations",
    "waive_eqpac_seasonality",
    "waive_parameter_handle",
)
PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_seasonal_twin_blocker_minimality_audit.md"
)
DEFAULT_SOURCE = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
DEFAULT_RECEIPT = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_verification.json"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-09_seasonal_twin_blocker_minimality_audit.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_aoi(source: dict, aoi: str) -> dict:
    gates = source["aois"][aoi]["gates"]
    stability = gates["stability"]
    viability = gates["viability"]
    robustness = gates["initial_condition_robustness"]

    non_large_stability = {
        name: value
        for name, value in stability["per_field_relative_l2"].items()
        if name != "Z_large"
    }
    non_large_flanks = {}
    for flank, item in robustness["per_flank"].items():
        values = {
            name: value
            for name, value in item["per_plankton_relative_l2"].items()
            if name != "z_large"
        }
        non_large_flanks[flank] = {
            "maximum_relative_l2": max(values.values()),
            "pass": max(values.values()) <= robustness["threshold"],
        }

    plankton = viability["per_plankton"]
    non_large = {name: item for name, item in plankton.items() if name != "z_large"}
    non_large_total = sum(item["cycle12_inventory"] for item in non_large.values())
    non_large_dominance = {
        name: item["cycle12_inventory"] / non_large_total
        for name, item in non_large.items()
    }
    always = {
        "light": gates["light"]["pass"],
        "numerical": gates["numerical"]["pass"],
        "chemical_closure": gates["closure"]["pass"],
        "dfe_structure": gates["dfe"]["pass"],
        "diatom_retention": plankton["diatom"]["pass"],
        "monthly_diatom_positive": viability["monthly_diatom_positive"],
        "non_large_community_retention": all(item["pass"] for item in non_large.values()),
        "non_large_community_dominance": max(non_large_dominance.values()) <= 0.95,
    }
    return {
        "always_required": always,
        "stability": {
            "original_pass": stability["pass"],
            "without_z_large_maximum_relative_l2": max(non_large_stability.values()),
            "without_z_large_pass": max(non_large_stability.values())
            <= stability["threshold"],
            "threshold": stability["threshold"],
        },
        "community_viability": {
            "original_pass": all(item["pass"] for item in plankton.values())
            and viability["dominance_pass"],
            "without_z_large_pass": all(item["pass"] for item in non_large.values())
            and max(non_large_dominance.values()) <= 0.95,
            "without_z_large_maximum_dominance": max(non_large_dominance.values()),
            "dominance_threshold": 0.95,
        },
        "seasonality": {
            "pass": viability["seasonality_pass"],
            "monthly_diatom_cv": viability["monthly_diatom_cv"],
            "threshold": viability["monthly_diatom_cv_threshold"],
        },
        "initial_condition_robustness": {
            "original_pass": robustness["pass"],
            "without_z_large_pass": all(
                item["pass"] for item in non_large_flanks.values()
            ),
            "without_z_large_maximum_relative_l2": max(
                item["maximum_relative_l2"] for item in non_large_flanks.values()
            ),
            "threshold": robustness["threshold"],
        },
    }


def _evaluate(criteria: dict, waiver_set: set[str]) -> list[str]:
    failures = []
    drop_large = "drop_large_predator_obligations" in waiver_set
    for aoi in AOIS:
        item = criteria["aois"][aoi]
        for name, passes in item["always_required"].items():
            if not passes:
                failures.append(f"{aoi}.{name}")
        for family in (
            "stability",
            "community_viability",
            "initial_condition_robustness",
        ):
            key = "without_z_large_pass" if drop_large else "original_pass"
            if not item[family][key]:
                failures.append(f"{aoi}.{family}")
        seasonality_waived = (
            aoi == "eqpac" and "waive_eqpac_seasonality" in waiver_set
        )
        if not item["seasonality"]["pass"] and not seasonality_waived:
            failures.append(f"{aoi}.seasonality")
    if (
        not criteria["parameter_handle"]["pass"]
        and "waive_parameter_handle" not in waiver_set
    ):
        failures.append("global.parameter_handle")
    return failures


def audit(source: dict) -> dict:
    criteria = {
        "aois": {aoi: _atomic_aoi(source, aoi) for aoi in AOIS},
        "parameter_handle": {
            "pass": source["sensitivity_gate"]["pass"],
            "qualifying_aois": source["sensitivity_gate"]["qualifying_aois"],
            "minimum_qualifying_aois": source["sensitivity_gate"][
                "minimum_qualifying_aois"
            ],
            "sign_agreement": source["sensitivity_gate"]["sign_agreement"],
            "absolute_log_response_by_aoi": {
                aoi: source["sensitivity_gate"]["per_aoi"][aoi][
                    "absolute_log_response"
                ]
                for aoi in AOIS
            },
            "threshold": source["sensitivity_gate"]["per_aoi"][AOIS[0]][
                "threshold"
            ],
        },
    }
    lattice = []
    for size in range(len(WAIVERS) + 1):
        for subset in itertools.combinations(WAIVERS, size):
            failures = _evaluate(criteria, set(subset))
            lattice.append(
                {
                    "waivers": list(subset),
                    "waiver_count": size,
                    "pass": not failures,
                    "remaining_failures": failures,
                }
            )
    passing = [item for item in lattice if item["pass"]]
    minimum = min((item["waiver_count"] for item in passing), default=None)
    minimal_sets = [
        item["waivers"] for item in passing if item["waiver_count"] == minimum
    ]
    if minimum == 1:
        branch = "one-blocker-group"
    elif minimum == 2:
        branch = "two-blocker-groups"
    elif minimum == 3:
        branch = "three-logically-separable-blocker-groups"
    else:
        branch = "additional-unmodeled-blocker"
    return {
        "criteria": criteria,
        "lattice": lattice,
        "decision": {
            "branch": branch,
            "minimum_waiver_count": minimum,
            "minimal_passing_sets": minimal_sets,
            "all_three_posthoc_waivers_pass": bool(
                passing and any(item["waiver_count"] == 3 for item in passing)
            ),
            "target_rehabilitated": False,
            "b200_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--verification", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    source = json.loads(args.source.read_text(encoding="utf-8"))
    receipt = json.loads(args.verification.read_text(encoding="utf-8"))
    source_hash = _sha256(args.source)
    if not receipt["verified"] or receipt["report_sha256"] != source_hash:
        raise RuntimeError("source report is not bound to its passing verification receipt")
    if source["decision"]["branch"] != "stage0-failed-stop":
        raise RuntimeError("source is not the registered Stage-0 stopping artifact")

    result = audit(source)
    output = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": PREREGISTRATION,
        "source": {
            "target_report": args.source.as_posix(),
            "target_report_sha256": source_hash,
            "verification_receipt": args.verification.as_posix(),
            "verification_receipt_sha256": _sha256(args.verification),
        },
        **result,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"decision={output['decision']['branch']} "
        f"minimum_waivers={output['decision']['minimum_waiver_count']} "
        f"report={args.report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
