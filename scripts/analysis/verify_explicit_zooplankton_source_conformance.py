#!/usr/bin/env python3
"""Independently verify the explicit-zooplankton source-conformance audit."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
AOI_SHAPES = {
    "eqpac": (21, 51),
    "natlsubpolar": (16, 31),
    "southernoceanpac": (16, 81),
}
OCEAN_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
RESTORING_INDICES = (0, 6, 7, 8, 9, 10, 11, 12, 13, 14)
PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_explicit_zooplankton_source_conformance.md"
)
SOURCE_COMMIT = "75b8e4337c2fa0c0baa9fa9376590503229121af"
CORROBORATION_COMMIT = "488cb795d7b933ea5a79b3bad84a182d7dbbe1ef"
DIRECT_FILES = {
    "options": (
        "v04/llc270_JAMES_paper/code_darwin/DARWIN_OPTIONS.h",
        "75705a67eaff7d77309f88da21d6f6abef07bb31",
    ),
    "init_fixed": (
        "v04/llc270_JAMES_paper/code_darwin/darwin_init_fixed.F",
        "20aa2864b97ddfafbde8245c43cfc34ee84607bf",
    ),
    "generate_phyto": (
        "v04/llc270_JAMES_paper/code_darwin/darwin_generate_phyto.F",
        "2a112873650922030237df5430a7cae0341dcb87",
    ),
    "plankton": (
        "v04/llc270_JAMES_paper/code_darwin/darwin_plankton.F",
        "6af2b5fff7746bcd904a51af9390d92e2e764d30",
    ),
    "readme": (
        "v04/llc270_JAMES_paper/readme/readme_ecco_darwin.txt",
        "84e3a53af19444d81308ffc24c840af56df97fc3",
    ),
    "legacy_generate_zoo": (
        "v02/cs510_Manizza_AO/darwin/darwin_generate_zoo.F",
        "a3c811fa06544331b9b291ae54ae0b5b68eec0e0",
    ),
}
CORROBORATION_FILES = {
    "tempfunc": (
        "monod/monod_tempfunc.F",
        "df89435be92cfa5544d0ba437f6abc44d0d12c18",
    ),
    "generate_zoo": (
        "monod/monod_generate_zoo.F",
        "1bd7f20d8dc3397450c1a6ab7e1ddbad7bb40d1e",
    ),
    "init_fixed": (
        "monod/monod_init_fixed.F",
        "9711fd46b91c00a7b1ab29d08a61d203b59a8729",
    ),
}
DT = 0.25
STEPS_PER_MONTH = 122
SOURCE_PHYGRAZ_MIN_C = 1.2e-8
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
ZOO_MORTALITY_PER_DAY = 1.0 / 30.0
SCALAR_ATOL = 1.0e-12
SOURCE_FLOOR_ATOL = 1.0e-12
SOURCE_FLOOR_RTOL = 1.0e-6
PRIOR_LOG_ATOL = 5.0e-4
PRIOR_ENDPOINT_REL_L2_ATOL = 2.0e-5
CONTINUOUS_EXCLUSION_THRESHOLD = -0.10
RUNTIME_ASSIMILATION = (
    (0.2, 0.5),
    (0.2, 0.5),
    (0.5, 0.7),
    (0.5, 0.7),
    (0.5, 0.7),
)
DECLARED_PROJECTION_DIFFERENCES = [
    "no DOC state; dissolved grazing remainder is routed to POC",
    "surface-only zooplankton in a two-layer box",
    "mean-neutralized approximate phytoplankton temperature multiplier",
    "chemical-state restoring toward frozen references",
    "Euler integration with nonnegative state clamp",
]


class VerificationError(ValueError):
    """Raised when a frozen source-conformance relation does not hold."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha(payload: bytes) -> str:
    canonical = payload.replace(b"\r\n", b"\n")
    header = f"blob {len(canonical)}\0".encode()
    return hashlib.sha1(header + canonical).hexdigest()


def load_bundle(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return torch.load(stream, map_location="cpu", weights_only=True)


def _source_record(path: str, expected_blob: str, payload: bytes) -> dict:
    actual_blob = _git_blob_sha(payload)
    return {
        "path": path,
        "bytes": len(payload),
        "expected_git_blob": expected_blob,
        "actual_git_blob": actual_blob,
        "sha256": _sha256_bytes(payload),
        "working_tree_crlf": b"\r\n" in payload,
        "pass": actual_blob == expected_blob,
    }


def _active_assignment_rhs(text: str, name: str) -> tuple[str, int]:
    pattern = re.compile(rf"^\s+{re.escape(name)}\s*=\s*(.+)$", re.IGNORECASE)
    matches = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = pattern.match(line)
        if match:
            matches.append((match.group(1).split("!")[0].strip(), line_number))
    if not matches:
        raise VerificationError(f"active assignment not found: {name}")
    return matches[-1]


def _eval_fortran_day_expression(rhs: str) -> float:
    expression = re.sub(
        r"(?i)(\d+(?:\.\d*)?|\.\d+)\s*_d\s*([+-]?\d+)",
        r"\1e\2",
        rhs,
    )
    expression = re.sub(r"(?i)\bpday\b", "1.0", expression)
    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd | ast.USub):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
        raise VerificationError(f"unsupported Fortran expression: {rhs}")

    return evaluate(tree)


def _normalize_fortran(text: str) -> str:
    active = []
    for line in text.splitlines():
        if line and line[0] in {"c", "C", "*", "!"}:
            continue
        active.append(line)
    return re.sub(r"[\s&]+", "", "".join(active)).lower()


def _anchor_checks(text: str, anchors: dict[str, str]) -> dict[str, bool]:
    normalized = _normalize_fortran(text)
    return {
        name: re.sub(r"\s+", "", token).lower() in normalized
        for name, token in anchors.items()
    }


def _temperature_v2_section(text: str) -> str:
    match = re.search(
        r"#elif\s+TEMP_VERSION\s*==\s*2(.*?)#else",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise VerificationError("TEMP_VERSION 2 section not found")
    return match.group(1)


def _source_evidence(source_bytes: dict[str, dict[str, bytes]]) -> dict:
    try:
        direct = {
            name: payload.decode("utf-8")
            for name, payload in source_bytes["direct"].items()
        }
        corroboration = {
            name: payload.decode("utf-8")
            for name, payload in source_bytes["corroboration"].items()
        }
    except UnicodeDecodeError as exc:
        raise VerificationError("source bytes are not UTF-8") from exc

    options = direct["options"]
    compile_flags = {
        "old_graze_undefined": bool(
            re.search(r"(?mi)^#undef\s+OLD_GRAZE\s*$", options)
        ),
        "notemp_undefined": bool(re.search(r"(?mi)^#undef\s+NOTEMP\s*$", options)),
        "temp_version_2": bool(
            re.search(r"(?mi)^#define\s+TEMP_VERSION\s+2\s*$", options)
        ),
        "nine_species_setup": bool(
            re.search(r"(?mi)^#define\s+NINE_SPECIES_SETUP\s*$", options)
        ),
    }

    init = direct["init_fixed"]
    names = (
        "kgrazesat",
        "phygrazmin",
        "GrazeFast",
        "GrazeEfflow",
        "GrazeEffmod",
        "GrazeEffhi",
        "palathi",
        "palatlo",
        "diatomgraz",
        "coccograz",
        "olargegraz",
        "ZoomortSmall",
        "ZoomortBig",
        "val_R_PC",
    )
    parsed = {}
    assignment_lines = {}
    for name in names:
        rhs, line = _active_assignment_rhs(init, name)
        parsed[name] = _eval_fortran_day_expression(rhs)
        assignment_lines[name] = line

    expected = {
        "kgrazesat": 0.085,
        "phygrazmin": 1.0e-10,
        "GrazeFast": GRAZE_MAX_PER_DAY,
        "GrazeEfflow": 0.2,
        "GrazeEffmod": 0.5,
        "GrazeEffhi": 0.7,
        "palathi": 1.0,
        "palatlo": 0.2,
        "diatomgraz": 0.83003,
        "coccograz": 0.85,
        "olargegraz": 0.90,
        "ZoomortSmall": ZOO_MORTALITY_PER_DAY,
        "ZoomortBig": ZOO_MORTALITY_PER_DAY,
        "val_R_PC": 120.0,
    }
    scalar_errors = {
        name: abs(parsed[name] - value) for name, value in expected.items()
    }
    carbon_half_saturation = parsed["kgrazesat"] * parsed["val_R_PC"]
    carbon_prey_floor = parsed["phygrazmin"] * parsed["val_R_PC"]
    runtime_scalar_errors = {
        "graze_max_per_day": abs(parsed["GrazeFast"] - GRAZE_MAX_PER_DAY),
        "half_saturation_c": abs(
            carbon_half_saturation - GRAZE_HALF_SATURATION_C
        ),
        "zoo_mortality_per_day": max(
            abs(parsed["ZoomortSmall"] - ZOO_MORTALITY_PER_DAY),
            abs(parsed["ZoomortBig"] - ZOO_MORTALITY_PER_DAY),
        ),
        "source_prey_floor_c": abs(
            carbon_prey_floor - SOURCE_PHYGRAZ_MIN_C
        ),
    }

    expected_palatability = torch.tensor(
        (
            (0.2 * parsed["diatomgraz"], parsed["diatomgraz"]),
            (
                parsed["palatlo"] * parsed["olargegraz"],
                parsed["palathi"] * parsed["olargegraz"],
            ),
            (parsed["palathi"], parsed["palatlo"]),
            (parsed["palathi"], parsed["palatlo"]),
            (parsed["palathi"], parsed["palatlo"]),
        ),
        dtype=torch.float64,
    )
    runtime_palatability = torch.tensor(
        (
            (0.2 * 0.83003, 0.83003),
            (0.2 * 0.90, 0.90),
            (1.0, 0.2),
            (1.0, 0.2),
            (1.0, 0.2),
        ),
        dtype=torch.float64,
    )
    expected_assimilation = torch.tensor(
        (
            (parsed["GrazeEfflow"], parsed["GrazeEffmod"]),
            (parsed["GrazeEfflow"], parsed["GrazeEffmod"]),
            (parsed["GrazeEffmod"], parsed["GrazeEffhi"]),
            (parsed["GrazeEffmod"], parsed["GrazeEffhi"]),
            (parsed["GrazeEffmod"], parsed["GrazeEffhi"]),
        ),
        dtype=torch.float64,
    )
    runtime_assimilation = torch.tensor(RUNTIME_ASSIMILATION, dtype=torch.float64)
    matrix_errors = {
        "palatability_max_abs": float(
            (runtime_palatability - expected_palatability).abs().max()
        ),
        "assimilation_max_abs": float(
            (runtime_assimilation - expected_assimilation).abs().max()
        ),
    }

    plankton_anchors = _anchor_checks(
        direct["plankton"],
        {
            "shared_prey_pool": (
                "allphyto(nz)=allphyto(nz)+palat(np,nz)*phyto(np)"
            ),
            "source_prey_floor": "tmpz=max(0._d0,(allphyto(nz)-phygrazmin))",
            "prey_allocation": "(palat(np,nz)*phyto(np)/allphyto(nz))",
            "holling_response": "(tmpz/(tmpz+kgrazesat))",
            "predator_biomass": "grazphy(np,nz)*zooP(nz)",
            "assimilation": "asseff(np,nz)*grazphy(np,nz)*zooP(nz)",
        },
    )
    phyto_anchors = _anchor_checks(
        direct["generate_phyto"],
        {
            "large_first_two": "if(np.lt.3.or.np.eq.6.or.np.eq.9)then",
            "diatom_first": "if(np.eq.1)then\ndiacoc(np)=1.0_d0",
            "shared_carbon_ratio": "R_PC(np)=val_R_PC",
        },
    )
    zoo_rule_anchors = _anchor_checks(
        corroboration["generate_zoo"],
        {
            "same_size_palatability": "palat(np,nz)=palathi",
            "same_size_assimilation": "asseff(np,nz)=GrazeEffmod",
            "cross_size_palatability": "palat(np,nz)=palatlo",
            "small_prey_cross_assimilation": "asseff(np,nz)=GrazeEffhi",
            "large_prey_cross_assimilation": "asseff(np,nz)=GrazeEfflow",
            "diatom_scaling": "palat(np,nz)=palat(np,nz)*diatomgraz",
            "other_large_scaling": "palat(np,nz)=palat(np,nz)*olargegraz",
        },
    )

    temp_v2 = _temperature_v2_section(corroboration["tempfunc"])
    temp_identity = {
        "zoo_grazing_identity": bool(
            re.search(r"(?mi)^\s+zooTempFunction\(nz\)\s*=\s*1\.", temp_v2)
        ),
        "zoo_linear_mortality_identity": bool(
            re.search(r"(?mi)^\s+mortZTempFunction\s*=\s*1\.0", temp_v2)
        ),
        "zoo_quadratic_mortality_identity": bool(
            re.search(r"(?mi)^\s+mortZ2TempFunction\s*=\s*1\.0", temp_v2)
        ),
        "arrhenius_grazing_is_commented": bool(
            re.search(r"(?mi)^c\s+.*zooTempFunction\(nz\)\s*=", temp_v2)
        ),
    }
    corr_init = corroboration["init_fixed"]
    small2_rhs, small2_line = _active_assignment_rhs(corr_init, "ZoomortSmall2")
    big2_rhs, big2_line = _active_assignment_rhs(corr_init, "ZoomortBig2")
    quadratic_mortality = {
        "ZoomortSmall2": _eval_fortran_day_expression(small2_rhs),
        "ZoomortBig2": _eval_fortran_day_expression(big2_rhs),
        "assignment_lines": {
            "ZoomortSmall2": small2_line,
            "ZoomortBig2": big2_line,
        },
    }
    lineage = {
        "base_package_checkout_2018_03_22": "03/22/18" in direct["readme"],
        "base_package_path_declared": (
            "MITgcm_contrib/darwin/pkg/darwin" in direct["readme"]
        ),
    }
    direct_pass = (
        all(compile_flags.values())
        and all(error <= SCALAR_ATOL for error in scalar_errors.values())
        and all(error <= SCALAR_ATOL for error in runtime_scalar_errors.values())
        and all(error <= SCALAR_ATOL for error in matrix_errors.values())
        and all(plankton_anchors.values())
        and all(phyto_anchors.values())
        and all(lineage.values())
    )
    corroboration_pass = (
        all(zoo_rule_anchors.values())
        and all(temp_identity.values())
        and abs(quadratic_mortality["ZoomortSmall2"]) <= SCALAR_ATOL
        and abs(quadratic_mortality["ZoomortBig2"]) <= SCALAR_ATOL
    )
    return {
        "direct_evidence_class": "official-config-at-frozen-git-blobs",
        "corroboration_evidence_class": "same-era-corroboration",
        "compile_flags": compile_flags,
        "parsed_constants": parsed,
        "assignment_lines": assignment_lines,
        "scalar_errors": scalar_errors,
        "carbon_half_saturation": carbon_half_saturation,
        "carbon_prey_floor": carbon_prey_floor,
        "runtime_scalar_errors": runtime_scalar_errors,
        "expected_palatability_at_truth": expected_palatability.tolist(),
        "runtime_palatability_at_truth": runtime_palatability.tolist(),
        "expected_assimilation": expected_assimilation.tolist(),
        "runtime_assimilation": runtime_assimilation.tolist(),
        "matrix_errors": matrix_errors,
        "plankton_algebra_anchors": plankton_anchors,
        "phyto_identity_anchors": phyto_anchors,
        "zooplankton_generation_anchors": zoo_rule_anchors,
        "temperature_identity": temp_identity,
        "quadratic_mortality": quadratic_mortality,
        "lineage": lineage,
        "direct_pass": direct_pass,
        "corroboration_pass": corroboration_pass,
    }


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
        tolerance = 2.0e-10 * max(abs(expected), 1.0)
        _require(
            math.isclose(expected, float(actual), abs_tol=tolerance),
            f"{path}: value differs",
        )
    else:
        _require(expected == actual, f"{path}: value differs")


def _relative_l2(
    actual: torch.Tensor,
    expected: torch.Tensor,
    mask: torch.Tensor,
) -> float:
    numerator = torch.linalg.vector_norm((actual - expected)[:, mask].double())
    denominator = torch.linalg.vector_norm(expected[:, mask].double()).clamp(
        min=1.0e-300
    )
    return float(numerator / denominator)


def _summarize_trajectory(tensors: dict, prior: dict) -> dict:
    mask = tensors["mask"]
    current_log = tensors["current_monthly_log_multiplier"]
    source_total = tensors["source_monthly_total_specific_gain"]
    source_log = tensors["source_monthly_log_multiplier"]
    mortality_integral = (
        12 * STEPS_PER_MONTH * DT * ZOO_MORTALITY_PER_DAY
    )
    source_annual_gain = source_total.sum(dim=0).double()
    source_margin = source_annual_gain - mortality_integral
    source_exact_log = source_log.sum(dim=0).double()
    source_endpoint_log = torch.log(
        tensors["source_floor_end_zoo"].double()
        / tensors["start_zoo"].double()
    )
    maximum_tolerance_ratio = tensors["maximum_source_floor_tolerance_ratio"]
    floor_allclose = maximum_tolerance_ratio <= 1.0
    prior_log_difference = (
        current_log.double() - prior["monthly_log_multiplier"].double()
    ).abs()
    current_endpoint_rel_l2 = _relative_l2(
        tensors["current_end_zoo"], prior["end_zoo"], mask
    )
    source_endpoint_rel_l2 = _relative_l2(
        tensors["source_floor_end_zoo"], tensors["current_end_zoo"], mask
    )
    current_log_endpoint_error = (
        current_log.sum(dim=0).double()
        - torch.log(
            tensors["current_end_zoo"].double()
            / tensors["start_zoo"].double()
        )
    ).abs()
    source_log_endpoint_error = (source_exact_log - source_endpoint_log).abs()
    large_margin = source_margin[1][mask]
    large_log = source_exact_log[1][mask]
    classification = (
        "continuous-energetic-deficit"
        if float(large_margin.max()) < CONTINUOUS_EXCLUSION_THRESHOLD
        else "not-continuously-excluded"
    )
    finite = all(
        bool(torch.isfinite(value).all())
        for key, value in tensors.items()
        if key != "mask"
    )
    integrity = (
        finite
        and bool(floor_allclose[:, mask].all())
        and float(prior_log_difference[:, :, mask].max()) <= PRIOR_LOG_ATOL
        and current_endpoint_rel_l2 <= PRIOR_ENDPOINT_REL_L2_ATOL
        and float(current_log_endpoint_error[:, mask].max()) <= PRIOR_LOG_ATOL
        and float(source_log_endpoint_error[:, mask].max()) <= PRIOR_LOG_ATOL
        and classification == "continuous-energetic-deficit"
    )
    return {
        "pass": integrity,
        "finite": finite,
        "source_floor_allclose": bool(floor_allclose[:, mask].all()),
        "source_floor_atol": SOURCE_FLOOR_ATOL,
        "source_floor_rtol": SOURCE_FLOOR_RTOL,
        "minimum_prey_pool_by_predator": [
            float(tensors["minimum_prey_pool"][index][mask].min())
            for index in range(2)
        ],
        "maximum_abs_specific_ingestion_difference": float(
            tensors["maximum_abs_specific_ingestion_difference"][:, mask].max()
        ),
        "maximum_relative_specific_ingestion_difference": float(
            tensors["maximum_relative_specific_ingestion_difference"][:, mask].max()
        ),
        "maximum_source_floor_tolerance_ratio": float(
            maximum_tolerance_ratio[:, mask].max()
        ),
        "maximum_prior_monthly_log_difference": float(
            prior_log_difference[:, :, mask].max()
        ),
        "current_endpoint_relative_l2_vs_energy_audit": current_endpoint_rel_l2,
        "source_floor_endpoint_relative_l2_vs_projection": source_endpoint_rel_l2,
        "maximum_current_log_endpoint_error": float(
            current_log_endpoint_error[:, mask].max()
        ),
        "maximum_source_floor_log_endpoint_error": float(
            source_log_endpoint_error[:, mask].max()
        ),
        "mortality_integral": mortality_integral,
        "source_floor_large_predator_annual_gain_max": float(
            source_annual_gain[1][mask].max()
        ),
        "source_floor_large_predator_continuous_margin_max": float(
            large_margin.max()
        ),
        "source_floor_large_predator_exact_log_max": float(large_log.max()),
        "large_predator_classification": classification,
    }


def verify(
    report: dict,
    bundle: dict,
    *,
    target_report: dict,
    target_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
    hashes: dict[str, str],
) -> dict:
    """Rebuild source evidence, trajectories, lineage, and the decision."""
    _require(report["schema_version"] == 1, "report schema differs")
    _require(bundle["schema_version"] == 1, "bundle schema differs")
    _require(report["status"] == "MEASURED_NOT_INDEPENDENTLY_VERIFIED", "status")
    _require(report["config"] == bundle["config"], "report/bundle config differs")
    _require(report["preregistration"] == PREREGISTRATION, "report prereg differs")
    _require(bundle["preregistration"] == PREREGISTRATION, "bundle prereg differs")
    _require(
        report["bundle_artifact"]["sha256"] == hashes["audit_bundle_sha256"],
        "audit bundle SHA-256 differs",
    )

    config = bundle["config"]
    expected_scalars = {
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "audit_cycle": 13,
        "aois": list(AOIS),
        "scenario": "ic_0p10",
        "chemical_restoring_tau_days": 365.25,
        "restoring_indices": list(RESTORING_INDICES),
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "source_floor_atol": SOURCE_FLOOR_ATOL,
        "source_floor_rtol": SOURCE_FLOOR_RTOL,
        "prior_monthly_log_atol": PRIOR_LOG_ATOL,
        "prior_endpoint_relative_l2_atol": PRIOR_ENDPOINT_REL_L2_ATOL,
        "continuous_exclusion_threshold": CONTINUOUS_EXCLUSION_THRESHOLD,
        "source_commit": SOURCE_COMMIT,
        "corroboration_commit": CORROBORATION_COMMIT,
    }
    for key, value in expected_scalars.items():
        _require(config[key] == value, f"config.{key} differs")
    current_floor = float(config.get("current_source_prey_floor_c", 0.0))
    _require(
        current_floor in (0.0, SOURCE_PHYGRAZ_MIN_C),
        "current source prey floor is unregistered",
    )
    for key in (
        "source_target_report_sha256",
        "source_target_bundle_sha256",
        "source_energy_report_sha256",
        "source_energy_bundle_sha256",
    ):
        _require(config[key] == hashes[key], f"config.{key} differs")

    _require(target_report["config"] == target_bundle["config"], "target config")
    _require(energy_report["config"] == energy_bundle["config"], "energy config")
    _require(
        target_report["bundle_artifact"]["sha256"]
        == hashes["source_target_bundle_sha256"],
        "target report does not bind target bundle",
    )
    _require(
        energy_report["bundle_artifact"]["sha256"]
        == hashes["source_energy_bundle_sha256"],
        "energy report does not bind energy bundle",
    )
    _require(
        energy_bundle["config"]["source_target_report_sha256"]
        == hashes["source_target_report_sha256"],
        "energy artifact does not bind target report",
    )
    _require(
        energy_bundle["config"]["source_target_bundle_sha256"]
        == hashes["source_target_bundle_sha256"],
        "energy artifact does not bind target bundle",
    )
    _require(
        float(target_bundle["config"].get("source_prey_floor_c", 0.0))
        == current_floor,
        "target prey floor differs",
    )
    _require(
        float(energy_bundle["config"].get("source_prey_floor_c", 0.0))
        == current_floor,
        "energy prey floor differs",
    )

    source_bytes = bundle["source_bytes"]
    _require(set(source_bytes) == {"direct", "corroboration"}, "source classes")
    expected_source_files = {"direct": {}, "corroboration": {}}
    for evidence_class, inventory in (
        ("direct", DIRECT_FILES),
        ("corroboration", CORROBORATION_FILES),
    ):
        _require(
            set(source_bytes[evidence_class]) == set(inventory),
            f"{evidence_class} source inventory differs",
        )
        for name, (path, expected_blob) in inventory.items():
            payload = source_bytes[evidence_class][name]
            _require(isinstance(payload, bytes), f"{evidence_class}.{name}: not bytes")
            expected_source_files[evidence_class][name] = _source_record(
                path, expected_blob, payload
            )
    source_identity_pass = all(
        item["pass"]
        for evidence_class in expected_source_files.values()
        for item in evidence_class.values()
    )
    expected_source_files["identity_pass"] = source_identity_pass
    _compare(expected_source_files, report["source_files"], "report.source_files")

    evidence = _source_evidence(source_bytes)
    _compare(evidence, report["source_evidence"], "report.source_evidence")

    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")
    _require(set(bundle["aois"]) == set(AOIS), "bundle AOIs differ")
    expected_tensor_keys = {
        "mask",
        "start_zoo",
        "current_end_zoo",
        "source_floor_end_zoo",
        "current_monthly_total_specific_gain",
        "current_monthly_log_multiplier",
        "source_monthly_total_specific_gain",
        "source_monthly_log_multiplier",
        "minimum_prey_pool",
        "maximum_abs_specific_ingestion_difference",
        "maximum_relative_specific_ingestion_difference",
        "maximum_projected_specific_ingestion",
        "maximum_source_floor_tolerance_ratio",
    }
    summaries = {}
    raw_tensor_cells = 0
    for aoi in AOIS:
        item = bundle["aois"][aoi]
        _require(set(item) == expected_tensor_keys, f"{aoi}: tensor keys differ")
        shape = AOI_SHAPES[aoi]
        mask = item["mask"]
        _require(mask.dtype == torch.bool, f"{aoi}: mask dtype")
        _require(tuple(mask.shape) == shape, f"{aoi}: mask shape")
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: ocean cells")
        for key in (
            "start_zoo",
            "current_end_zoo",
            "source_floor_end_zoo",
            "minimum_prey_pool",
            "maximum_abs_specific_ingestion_difference",
            "maximum_relative_specific_ingestion_difference",
            "maximum_projected_specific_ingestion",
            "maximum_source_floor_tolerance_ratio",
        ):
            _require(item[key].shape == (2, *shape), f"{aoi}.{key}: shape")
        for key in (
            "current_monthly_total_specific_gain",
            "current_monthly_log_multiplier",
            "source_monthly_total_specific_gain",
            "source_monthly_log_multiplier",
        ):
            _require(item[key].shape == (12, 2, *shape), f"{aoi}.{key}: shape")

        target_item = target_bundle["aois"][aoi]
        prior = energy_bundle["aois"][aoi]
        _require(torch.equal(mask, target_item["mask"]), f"{aoi}: target mask")
        _require(torch.equal(mask, prior["mask"]), f"{aoi}: energy mask")
        target_start = target_item["scenarios"]["ic_0p10"][
            "cycle12_endpoint"
        ][[15, 16]]
        _require(torch.equal(item["start_zoo"], target_start), f"{aoi}: target start")
        _require(torch.equal(item["start_zoo"], prior["start_zoo"]), f"{aoi}: energy start")

        difference = item["maximum_abs_specific_ingestion_difference"]
        projected = item["maximum_projected_specific_ingestion"]
        ratio = item["maximum_source_floor_tolerance_ratio"]
        _require(bool((difference >= 0.0).all()), f"{aoi}: negative difference")
        _require(bool((projected >= 0.0).all()), f"{aoi}: negative rate")
        _require(bool((ratio >= 0.0).all()), f"{aoi}: negative tolerance ratio")
        ratio_lower_bound = difference / (
            SOURCE_FLOOR_ATOL + SOURCE_FLOOR_RTOL * projected
        )
        _require(
            bool((ratio + 2.0e-6 >= ratio_lower_bound).all()),
            f"{aoi}: tolerance ratio understates rate discrepancy",
        )
        if current_floor == SOURCE_PHYGRAZ_MIN_C:
            for current_key, source_key in (
                ("current_end_zoo", "source_floor_end_zoo"),
                (
                    "current_monthly_total_specific_gain",
                    "source_monthly_total_specific_gain",
                ),
                ("current_monthly_log_multiplier", "source_monthly_log_multiplier"),
            ):
                _require(
                    torch.equal(item[current_key], item[source_key]),
                    f"{aoi}: corrected current/source paths differ",
                )

        summary = _summarize_trajectory(item, prior)
        _compare(summary, report["aois"][aoi]["summary"], f"report.{aoi}.summary")
        summaries[aoi] = summary
        raw_tensor_cells += sum(value.numel() for value in item.values())

    trajectory_pass = all(summary["pass"] for summary in summaries.values())
    direct_pass = source_identity_pass and evidence["direct_pass"]
    corroboration_pass = source_identity_pass and evidence["corroboration_pass"]
    if direct_pass and corroboration_pass and trajectory_pass:
        branch = "source-conformant-bounded-projection"
    elif direct_pass and not corroboration_pass and trajectory_pass:
        branch = "source-provenance-incomplete"
    elif not direct_pass or not trajectory_pass:
        branch = "source-mismatch-rerun-required"
    else:
        branch = "audit-invalid"
    decision = {
        "branch": branch,
        "source_identity_pass": source_identity_pass,
        "direct_evidence_pass": direct_pass,
        "corroboration_pass": corroboration_pass,
        "trajectory_pass": trajectory_pass,
        "b200_authorized": False,
        "target_rehabilitated": False,
        "declared_projection_differences": DECLARED_PROJECTION_DIFFERENCES,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(decision == bundle["decision"], "bundle decision differs")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "source_file_count": len(DIRECT_FILES) + len(CORROBORATION_FILES),
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source-target-report", type=Path, required=True)
    parser.add_argument("--source-target-bundle", type=Path, required=True)
    parser.add_argument("--source-energy-report", type=Path, required=True)
    parser.add_argument("--source-energy-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = load_bundle(args.source_target_bundle)
    energy_report = json.loads(args.source_energy_report.read_text(encoding="utf-8"))
    energy_bundle = load_bundle(args.source_energy_bundle)
    hashes = {
        "audit_bundle_sha256": _sha256(args.bundle),
        "source_target_report_sha256": _sha256(args.source_target_report),
        "source_target_bundle_sha256": _sha256(args.source_target_bundle),
        "source_energy_report_sha256": _sha256(args.source_energy_report),
        "source_energy_bundle_sha256": _sha256(args.source_energy_bundle),
    }
    try:
        result = verify(
            report,
            bundle,
            target_report=target_report,
            target_bundle=target_bundle,
            energy_report=energy_report,
            energy_bundle=energy_bundle,
            hashes=hashes,
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"SOURCE-CONFORMANCE VERIFICATION FAILED: {exc}")
        return 2

    result.update(
        {
            "report": args.report.as_posix(),
            "report_sha256": _sha256(args.report),
            "bundle": args.bundle.as_posix(),
            "bundle_sha256": _sha256(args.bundle),
            **{key: value for key, value in hashes.items() if key != "audit_bundle_sha256"},
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED explicit-zoo source conformance: "
        f"decision={result['decision']['branch']} "
        f"source_files={result['source_file_count']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
