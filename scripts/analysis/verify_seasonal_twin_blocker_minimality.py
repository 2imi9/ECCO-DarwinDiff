#!/usr/bin/env python3
"""Independently verify the seasonal-target blocker waiver lattice."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
WAIVERS = (
    "drop_large_predator_obligations",
    "waive_eqpac_seasonality",
    "waive_parameter_handle",
)


class VerificationError(ValueError):
    """Raised when the audit does not follow the frozen lattice."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=2e-12 * max(abs(left), 1.0))


def _source_criteria(source: dict) -> dict:
    aois = {}
    for aoi in AOIS:
        gates = source["aois"][aoi]["gates"]
        stability = gates["stability"]
        community = gates["viability"]
        robustness = gates["initial_condition_robustness"]
        stability_values = [
            value
            for name, value in stability["per_field_relative_l2"].items()
            if name != "Z_large"
        ]
        plankton = community["per_plankton"]
        retained = {name: item for name, item in plankton.items() if name != "z_large"}
        total = sum(item["cycle12_inventory"] for item in retained.values())
        maximum_dominance = max(
            item["cycle12_inventory"] / total for item in retained.values()
        )
        flank_maxima = []
        for flank in robustness["per_flank"].values():
            flank_maxima.append(
                max(
                    value
                    for name, value in flank["per_plankton_relative_l2"].items()
                    if name != "z_large"
                )
            )
        always = {
            "light": gates["light"]["pass"],
            "numerical": gates["numerical"]["pass"],
            "chemical_closure": gates["closure"]["pass"],
            "dfe_structure": gates["dfe"]["pass"],
            "diatom_retention": plankton["diatom"]["pass"],
            "monthly_diatom_positive": community["monthly_diatom_positive"],
            "non_large_community_retention": all(
                item["pass"] for item in retained.values()
            ),
            "non_large_community_dominance": maximum_dominance <= 0.95,
        }
        aois[aoi] = {
            "always_required": always,
            "stability": {
                "original_pass": stability["pass"],
                "without_z_large_maximum_relative_l2": max(stability_values),
                "without_z_large_pass": max(stability_values)
                <= stability["threshold"],
                "threshold": stability["threshold"],
            },
            "community_viability": {
                "original_pass": all(item["pass"] for item in plankton.values())
                and community["dominance_pass"],
                "without_z_large_pass": all(item["pass"] for item in retained.values())
                and maximum_dominance <= 0.95,
                "without_z_large_maximum_dominance": maximum_dominance,
                "dominance_threshold": 0.95,
            },
            "seasonality": {
                "pass": community["seasonality_pass"],
                "monthly_diatom_cv": community["monthly_diatom_cv"],
                "threshold": community["monthly_diatom_cv_threshold"],
            },
            "initial_condition_robustness": {
                "original_pass": robustness["pass"],
                "without_z_large_pass": max(flank_maxima) <= robustness["threshold"],
                "without_z_large_maximum_relative_l2": max(flank_maxima),
                "threshold": robustness["threshold"],
            },
        }
    sensitivity = source["sensitivity_gate"]
    return {
        "aois": aois,
        "parameter_handle": {
            "pass": sensitivity["pass"],
            "qualifying_aois": sensitivity["qualifying_aois"],
            "minimum_qualifying_aois": sensitivity["minimum_qualifying_aois"],
            "sign_agreement": sensitivity["sign_agreement"],
            "absolute_log_response_by_aoi": {
                aoi: sensitivity["per_aoi"][aoi]["absolute_log_response"]
                for aoi in AOIS
            },
            "threshold": sensitivity["per_aoi"][AOIS[0]]["threshold"],
        },
    }


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key, value in expected.items():
            _compare(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        _require(_close(expected, float(actual)), f"{path}: value differs")
    else:
        _require(expected == actual, f"{path}: value differs")


def _remaining(criteria: dict, subset: tuple[str, ...]) -> list[str]:
    selected = set(subset)
    failures = []
    drop_large = "drop_large_predator_obligations" in selected
    for aoi in AOIS:
        item = criteria["aois"][aoi]
        failures.extend(
            f"{aoi}.{name}"
            for name, passes in item["always_required"].items()
            if not passes
        )
        key = "without_z_large_pass" if drop_large else "original_pass"
        for family in (
            "stability",
            "community_viability",
            "initial_condition_robustness",
        ):
            if not item[family][key]:
                failures.append(f"{aoi}.{family}")
        if not item["seasonality"]["pass"] and not (
            aoi == "eqpac" and "waive_eqpac_seasonality" in selected
        ):
            failures.append(f"{aoi}.seasonality")
    if not criteria["parameter_handle"]["pass"] and "waive_parameter_handle" not in selected:
        failures.append("global.parameter_handle")
    return failures


def verify(audit: dict, source: dict, receipt: dict) -> dict:
    _require(audit["schema_version"] == 1, "audit schema differs")
    _require(receipt["verified"] is True, "source receipt is not verified")
    _require(receipt["decision"] == source["decision"], "source receipt decision differs")
    _require(source["decision"]["branch"] == "stage0-failed-stop", "source branch differs")
    criteria = _source_criteria(source)
    _compare(criteria, audit["criteria"], "audit.criteria")

    expected_lattice = []
    for size in range(4):
        for subset in itertools.combinations(WAIVERS, size):
            failures = _remaining(criteria, subset)
            expected_lattice.append(
                {
                    "waivers": list(subset),
                    "waiver_count": size,
                    "pass": not failures,
                    "remaining_failures": failures,
                }
            )
    _require(expected_lattice == audit["lattice"], "waiver lattice differs")
    passing = [item for item in expected_lattice if item["pass"]]
    minimum = min((item["waiver_count"] for item in passing), default=None)
    decision = {
        "branch": (
            "three-logically-separable-blocker-groups"
            if minimum == 3
            else "two-blocker-groups"
            if minimum == 2
            else "one-blocker-group"
            if minimum == 1
            else "additional-unmodeled-blocker"
        ),
        "minimum_waiver_count": minimum,
        "minimal_passing_sets": [
            item["waivers"] for item in passing if item["waiver_count"] == minimum
        ],
        "all_three_posthoc_waivers_pass": any(
            item["waiver_count"] == 3 for item in passing
        ),
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    _require(decision == audit["decision"], "audit decision differs")
    return {
        "verified": True,
        "schema_version": 1,
        "lattice_nodes_checked": len(expected_lattice),
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--verification", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    source = json.loads(args.source.read_text(encoding="utf-8"))
    receipt = json.loads(args.verification.read_text(encoding="utf-8"))
    try:
        _require(
            audit["source"]["target_report_sha256"] == _sha256(args.source),
            "source report SHA-256 differs",
        )
        _require(
            audit["source"]["verification_receipt_sha256"]
            == _sha256(args.verification),
            "source verification SHA-256 differs",
        )
        _require(
            receipt["report_sha256"] == _sha256(args.source),
            "verification receipt does not bind source report",
        )
        result = verify(audit, source, receipt)
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"BLOCKER MINIMALITY VERIFICATION FAILED: {exc}")
        return 2
    result.update(
        {
            "audit": args.audit.as_posix(),
            "audit_sha256": _sha256(args.audit),
            "source_report_sha256": _sha256(args.source),
            "source_verification_sha256": _sha256(args.verification),
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED blocker minimality: "
        f"nodes={result['lattice_nodes_checked']} "
        f"minimum_waivers={result['decision']['minimum_waiver_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
