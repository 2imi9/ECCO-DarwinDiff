#!/usr/bin/env python3
"""Audit the explicit-grazer projection against its Carroll-2020 source lineage."""

from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import torch
from seasonal_twin_target_gate import (
    DEFAULT_AOIS,
    DT,
    _device,
    _load_aoi,
    _parse_aois,
    _synchronize,
)

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES, PARAMS
from darwindiff.ecco_darwin_loader import open_bin_average
from darwindiff.explicit_zooplankton import (
    ASSIMILATION,
    CHEMICAL_RESTORING_INDICES,
    GRAZE_HALF_SATURATION_C,
    GRAZE_MAX_PER_DAY,
    I_Z_LARGE,
    I_Z_SMALL,
    SOURCE_PHYGRAZ_MIN_C,
    ZOO_MORTALITY_PER_DAY,
    darwin1_explicit_grazing_rates,
    explicit_zooplankton_step,
)
from darwindiff.seasonal_twin import astronomical_monthly_light

PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_explicit_zooplankton_source_conformance.md"
)
SOURCE_COMMIT = "75b8e4337c2fa0c0baa9fa9376590503229121af"
CORROBORATION_COMMIT = "488cb795d7b933ea5a79b3bad84a182d7dbbe1ef"
RAW_CORROBORATION_ROOT = (
    "https://raw.githubusercontent.com/SunderlandLab/MITgcm_PCB_pkg/"
    f"{CORROBORATION_COMMIT}/"
)

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

SOURCE_TARGET_REPORT = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
SOURCE_TARGET_BUNDLE = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
)
SOURCE_ENERGY_REPORT = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.json"
)
SOURCE_ENERGY_BUNDLE = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_source_conformance.json"
)
DEFAULT_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_source_conformance.pt.gz"
)

STEPS_PER_MONTH = 122
RESTORING_TAU_DAYS = 365.25
CENTRAL_SCENARIO = "ic_0p10"
SCALAR_ATOL = 1.0e-12
SOURCE_FLOOR_ATOL = 1.0e-12
SOURCE_FLOOR_RTOL = 1.0e-6
PRIOR_LOG_ATOL = 5.0e-4
PRIOR_ENDPOINT_REL_L2_ATOL = 2.0e-5
CONTINUOUS_EXCLUSION_THRESHOLD = -0.10


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


def _atomic_gzip_torch_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as stream:
        torch.save(payload, stream)
    temporary.replace(path)


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "DarwinDiff-source-conformance"})
    with urlopen(request, timeout=60) as response:
        return response.read()


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
        raise ValueError(f"active assignment not found: {name}")
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
        raise ValueError(f"unsupported Fortran expression: {rhs}")

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
        raise ValueError("TEMP_VERSION 2 section not found")
    return match.group(1)


def _source_evidence(source_bytes: dict[str, dict[str, bytes]]) -> dict:
    direct = {name: payload.decode("utf-8") for name, payload in source_bytes["direct"].items()}
    corroboration = {
        name: payload.decode("utf-8")
        for name, payload in source_bytes["corroboration"].items()
    }

    options = direct["options"]
    compile_flags = {
        "old_graze_undefined": bool(re.search(r"(?mi)^#undef\s+OLD_GRAZE\s*$", options)),
        "notemp_undefined": bool(re.search(r"(?mi)^#undef\s+NOTEMP\s*$", options)),
        "temp_version_2": bool(re.search(r"(?mi)^#define\s+TEMP_VERSION\s+2\s*$", options)),
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
        "GrazeFast": 0.625,
        "GrazeEfflow": 0.2,
        "GrazeEffmod": 0.5,
        "GrazeEffhi": 0.7,
        "palathi": 1.0,
        "palatlo": 0.2,
        "diatomgraz": 0.83003,
        "coccograz": 0.85,
        "olargegraz": 0.90,
        "ZoomortSmall": 1.0 / 30.0,
        "ZoomortBig": 1.0 / 30.0,
        "val_R_PC": 120.0,
    }
    scalar_errors = {name: abs(parsed[name] - value) for name, value in expected.items()}
    carbon_half_saturation = parsed["kgrazesat"] * parsed["val_R_PC"]
    carbon_prey_floor = parsed["phygrazmin"] * parsed["val_R_PC"]
    runtime_scalar_errors = {
        "graze_max_per_day": abs(parsed["GrazeFast"] - GRAZE_MAX_PER_DAY),
        "half_saturation_c": abs(carbon_half_saturation - GRAZE_HALF_SATURATION_C),
        "zoo_mortality_per_day": max(
            abs(parsed["ZoomortSmall"] - ZOO_MORTALITY_PER_DAY),
            abs(parsed["ZoomortBig"] - ZOO_MORTALITY_PER_DAY),
        ),
        "source_prey_floor_c": abs(carbon_prey_floor - SOURCE_PHYGRAZ_MIN_C),
    }

    truth = torch.tensor([parameter.carroll_value for parameter in PARAMS], dtype=torch.float64)
    synthetic_state = torch.ones(17, dtype=torch.float64)
    runtime_rates = darwin1_explicit_grazing_rates(synthetic_state, truth)
    runtime_palatability = runtime_rates["palatability"]
    expected_palatability = torch.tensor(
        (
            (0.2 * parsed["diatomgraz"], parsed["diatomgraz"]),
            (parsed["palatlo"] * parsed["olargegraz"], parsed["palathi"] * parsed["olargegraz"]),
            (parsed["palathi"], parsed["palatlo"]),
            (parsed["palathi"], parsed["palatlo"]),
            (parsed["palathi"], parsed["palatlo"]),
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
    runtime_assimilation = torch.tensor(ASSIMILATION, dtype=torch.float64)
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
            "shared_prey_pool": "allphyto(nz)=allphyto(nz)+palat(np,nz)*phyto(np)",
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
        "assignment_lines": {"ZoomortSmall2": small2_line, "ZoomortBig2": big2_line},
    }

    readme = direct["readme"]
    lineage = {
        "base_package_checkout_2018_03_22": "03/22/18" in readme,
        "base_package_path_declared": "MITgcm_contrib/darwin/pkg/darwin" in readme,
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


def _relative_l2(actual: torch.Tensor, expected: torch.Tensor, mask: torch.Tensor) -> float:
    numerator = torch.linalg.vector_norm((actual - expected)[:, mask].double())
    denominator = torch.linalg.vector_norm(expected[:, mask].double()).clamp(min=1.0e-300)
    return float(numerator / denominator)


def _summarize_trajectory(
    tensors: dict[str, torch.Tensor],
    prior: dict[str, torch.Tensor],
) -> dict:
    mask = tensors["mask"]
    current_log = tensors["current_monthly_log_multiplier"]
    source_total = tensors["source_monthly_total_specific_gain"]
    source_log = tensors["source_monthly_log_multiplier"]
    mortality_integral = 12 * STEPS_PER_MONTH * DT * ZOO_MORTALITY_PER_DAY
    source_annual_gain = source_total.sum(dim=0).double()
    source_margin = source_annual_gain - mortality_integral
    source_exact_log = source_log.sum(dim=0).double()
    source_endpoint_log = torch.log(
        tensors["source_floor_end_zoo"].double()
        / tensors["start_zoo"].double()
    )
    maximum_tolerance_ratio = tensors["maximum_source_floor_tolerance_ratio"]
    floor_allclose = maximum_tolerance_ratio <= 1.0
    prior_log_difference = (current_log.double() - prior["monthly_log_multiplier"].double()).abs()
    current_endpoint_rel_l2 = _relative_l2(
        tensors["current_end_zoo"], prior["end_zoo"], mask
    )
    source_endpoint_rel_l2 = _relative_l2(
        tensors["source_floor_end_zoo"], tensors["current_end_zoo"], mask
    )
    current_log_endpoint_error = (
        current_log.sum(dim=0).double()
        - torch.log(tensors["current_end_zoo"].double() / tensors["start_zoo"].double())
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
            float(tensors["minimum_prey_pool"][index][mask].min()) for index in range(2)
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
        "source_floor_large_predator_continuous_margin_max": float(large_margin.max()),
        "source_floor_large_predator_exact_log_max": float(large_log.max()),
        "large_predator_classification": classification,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[2]
    default_data_root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    default_source_root = Path(
        os.environ.get("ECCO_DARWIN_SOURCE_ROOT", repo_root.parent / "ecco_darwin")
    )
    parser.add_argument(
        "--bin-average",
        type=Path,
        default=default_data_root / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc",
    )
    parser.add_argument("--source-root", type=Path, default=default_source_root)
    parser.add_argument("--aois", type=_parse_aois, default=DEFAULT_AOIS)
    parser.add_argument("--device", type=_device, default=torch.device("cuda"))
    parser.add_argument("--source-target-report", type=Path, default=SOURCE_TARGET_REPORT)
    parser.add_argument("--source-target-bundle", type=Path, default=SOURCE_TARGET_BUNDLE)
    parser.add_argument("--source-energy-report", type=Path, default=SOURCE_ENERGY_REPORT)
    parser.add_argument("--source-energy-bundle", type=Path, default=SOURCE_ENERGY_BUNDLE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args(argv)

    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = _load_bundle(args.source_target_bundle)
    energy_report = json.loads(args.source_energy_report.read_text(encoding="utf-8"))
    energy_bundle = _load_bundle(args.source_energy_bundle)
    target_report_hash = _sha256(args.source_target_report)
    target_bundle_hash = _sha256(args.source_target_bundle)
    energy_report_hash = _sha256(args.source_energy_report)
    energy_bundle_hash = _sha256(args.source_energy_bundle)
    if target_report["bundle_artifact"]["sha256"] != target_bundle_hash:
        raise RuntimeError("target report does not bind its bundle")
    if target_report["config"] != target_bundle["config"]:
        raise RuntimeError("target report/bundle configs differ")
    if energy_report["bundle_artifact"]["sha256"] != energy_bundle_hash:
        raise RuntimeError("energy report does not bind its bundle")
    if energy_report["config"] != energy_bundle["config"]:
        raise RuntimeError("energy report/bundle configs differ")
    if energy_bundle["config"]["source_target_report_sha256"] != target_report_hash:
        raise RuntimeError("energy artifact does not bind the target report")
    if energy_bundle["config"]["source_target_bundle_sha256"] != target_bundle_hash:
        raise RuntimeError("energy artifact does not bind the target bundle")
    current_source_prey_floor_c = float(
        target_bundle["config"].get("source_prey_floor_c", 0.0)
    )
    if current_source_prey_floor_c not in (0.0, SOURCE_PHYGRAZ_MIN_C):
        raise RuntimeError("target uses an unregistered source prey floor")
    if (
        float(energy_bundle["config"].get("source_prey_floor_c", 0.0))
        != current_source_prey_floor_c
    ):
        raise RuntimeError("energy artifact prey floor differs from target")

    source_bytes: dict[str, dict[str, bytes]] = {"direct": {}, "corroboration": {}}
    direct_records = {}
    for name, (relative_path, expected_blob) in DIRECT_FILES.items():
        payload = (args.source_root / relative_path).read_bytes()
        source_bytes["direct"][name] = payload
        direct_records[name] = _source_record(relative_path, expected_blob, payload)
    corroboration_records = {}
    for name, (relative_path, expected_blob) in CORROBORATION_FILES.items():
        payload = _fetch(RAW_CORROBORATION_ROOT + relative_path)
        source_bytes["corroboration"][name] = payload
        corroboration_records[name] = _source_record(relative_path, expected_blob, payload)
    source_identity_pass = all(
        item["pass"] for item in (*direct_records.values(), *corroboration_records.values())
    )
    evidence = _source_evidence(source_bytes)

    device = args.device
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by the full-resolution audit")
    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    layer2.USE_COCCOLITH_ONLY_CALCITE = False
    layer2.USE_ENV_RAIN_RATIO = False

    config = {
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "audit_cycle": 13,
        "aois": list(args.aois),
        "scenario": CENTRAL_SCENARIO,
        "chemical_restoring_tau_days": RESTORING_TAU_DAYS,
        "restoring_indices": list(CHEMICAL_RESTORING_INDICES),
        "current_source_prey_floor_c": current_source_prey_floor_c,
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "source_floor_atol": SOURCE_FLOOR_ATOL,
        "source_floor_rtol": SOURCE_FLOOR_RTOL,
        "prior_monthly_log_atol": PRIOR_LOG_ATOL,
        "prior_endpoint_relative_l2_atol": PRIOR_ENDPOINT_REL_L2_ATOL,
        "continuous_exclusion_threshold": CONTINUOUS_EXCLUSION_THRESHOLD,
        "source_commit": SOURCE_COMMIT,
        "corroboration_commit": CORROBORATION_COMMIT,
        "source_target_report_sha256": target_report_hash,
        "source_target_bundle_sha256": target_bundle_hash,
        "source_energy_report_sha256": energy_report_hash,
        "source_energy_bundle_sha256": energy_bundle_hash,
    }
    runtime = {"device": str(device)}
    if device.type == "cuda":
        runtime["device_name"] = torch.cuda.get_device_name(device)
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": PREREGISTRATION,
        "config": config,
        "runtime": runtime,
        "source_files": {
            "direct": direct_records,
            "corroboration": corroboration_records,
            "identity_pass": source_identity_pass,
        },
        "source_evidence": evidence,
        "aois": {},
        "decision": {"b200_authorized": False},
    }
    bundle = {
        "schema_version": 1,
        "preregistration": PREREGISTRATION,
        "config": config,
        "source_bytes": source_bytes,
        "aois": {},
    }

    started = time.perf_counter()
    dataset = open_bin_average(args.bin_average)
    try:
        for aoi in args.aois:
            aoi_started = time.perf_counter()
            _, forcing, mask, _ = _load_aoi(dataset, aoi, device)
            target_item = target_bundle["aois"][aoi]
            prior = energy_bundle["aois"][aoi]
            if not torch.equal(mask.cpu(), target_item["mask"]):
                raise RuntimeError(f"{aoi}: target and live masks differ")
            if not torch.equal(mask.cpu(), prior["mask"]):
                raise RuntimeError(f"{aoi}: energy and live masks differ")
            scenario = target_item["scenarios"][CENTRAL_SCENARIO]
            current_state = scenario["cycle12_endpoint"].to(device)
            source_state = current_state.clone()
            restoring_reference = scenario["initial_state"].to(device)
            start_zoo = current_state[[I_Z_SMALL, I_Z_LARGE]].clone()
            light = astronomical_monthly_light(forcing["latitude_degrees"])
            height, width = mask.shape
            params = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
            params = params.expand(6, height, width).contiguous()
            selector = torch.zeros_like(current_state)
            selector[list(CHEMICAL_RESTORING_INDICES)] = mask.to(current_state.dtype)
            minimum_prey_pool = torch.full((2, height, width), float("inf"), device=device)
            maximum_abs_difference = torch.zeros((2, height, width), device=device)
            maximum_relative_difference = torch.zeros((2, height, width), device=device)
            maximum_projected_ingestion = torch.zeros((2, height, width), device=device)
            maximum_tolerance_ratio = torch.zeros((2, height, width), device=device)
            current_monthly_total = []
            current_monthly_log = []
            source_monthly_total = []
            source_monthly_log = []

            with torch.no_grad():
                for month in range(12):
                    current_total_sum = torch.zeros(
                        (2, height, width), dtype=torch.float64, device=device
                    )
                    current_log_sum = torch.zeros_like(current_total_sum)
                    source_total_sum = torch.zeros_like(current_total_sum)
                    source_log_sum = torch.zeros_like(current_total_sum)
                    for _ in range(STEPS_PER_MONTH):
                        current_rates = darwin1_explicit_grazing_rates(
                            current_state,
                            params,
                            source_prey_floor_c=current_source_prey_floor_c,
                        )
                        same_state_source_rates = darwin1_explicit_grazing_rates(
                            current_state,
                            params,
                            source_prey_floor_c=SOURCE_PHYGRAZ_MIN_C,
                        )
                        source_rates = darwin1_explicit_grazing_rates(
                            source_state,
                            params,
                            source_prey_floor_c=SOURCE_PHYGRAZ_MIN_C,
                        )
                        projected_ingestion = current_rates["predator_specific_ingestion"]
                        source_ingestion = same_state_source_rates[
                            "predator_specific_ingestion"
                        ]
                        difference = (projected_ingestion - source_ingestion).abs()
                        relative = difference / projected_ingestion.abs().clamp(min=1.0e-300)
                        minimum_prey_pool = torch.minimum(
                            minimum_prey_pool,
                            current_rates["prey_pool"],
                        )
                        maximum_abs_difference = torch.maximum(
                            maximum_abs_difference, difference
                        )
                        maximum_relative_difference = torch.maximum(
                            maximum_relative_difference, relative
                        )
                        maximum_projected_ingestion = torch.maximum(
                            maximum_projected_ingestion,
                            projected_ingestion.abs(),
                        )
                        tolerance_ratio = difference / (
                            SOURCE_FLOOR_ATOL
                            + SOURCE_FLOOR_RTOL * projected_ingestion.abs()
                        )
                        maximum_tolerance_ratio = torch.maximum(
                            maximum_tolerance_ratio,
                            tolerance_ratio,
                        )
                        current_total_sum += DT * current_rates[
                            "zoo_specific_gain"
                        ].double()
                        current_log_sum += torch.log(
                            (1.0 + DT * current_rates["zoo_specific_net"]).double()
                        )
                        source_total_sum += DT * source_rates[
                            "zoo_specific_gain"
                        ].double()
                        source_log_sum += torch.log(
                            (1.0 + DT * source_rates["zoo_specific_net"]).double()
                        )

                        current_next = explicit_zooplankton_step(
                            current_state,
                            params,
                            DT,
                            forcing["T_monthly"][month],
                            forcing["S_monthly"][month],
                            forcing["wind_monthly"][month],
                            forcing["pco2_atm"],
                            layer2.H1,
                            layer2.H2,
                            layer2.KZ_M2_PER_DAY,
                            layer2.R_REMIN,
                            light[month],
                            current_source_prey_floor_c,
                        )
                        source_next = explicit_zooplankton_step(
                            source_state,
                            params,
                            DT,
                            forcing["T_monthly"][month],
                            forcing["S_monthly"][month],
                            forcing["wind_monthly"][month],
                            forcing["pco2_atm"],
                            layer2.H1,
                            layer2.H2,
                            layer2.KZ_M2_PER_DAY,
                            layer2.R_REMIN,
                            light[month],
                            SOURCE_PHYGRAZ_MIN_C,
                        )
                        current_requested = (
                            DT
                            * (restoring_reference - current_state)
                            / RESTORING_TAU_DAYS
                            * selector
                        )
                        source_requested = (
                            DT
                            * (restoring_reference - source_state)
                            / RESTORING_TAU_DAYS
                            * selector
                        )
                        current_state = (current_next + current_requested).clamp(min=0.0)
                        source_state = (source_next + source_requested).clamp(min=0.0)
                    current_monthly_total.append(current_total_sum)
                    current_monthly_log.append(current_log_sum)
                    source_monthly_total.append(source_total_sum)
                    source_monthly_log.append(source_log_sum)
            _synchronize(device)
            tensors = {
                "mask": mask.cpu(),
                "start_zoo": start_zoo.cpu(),
                "current_end_zoo": current_state[[I_Z_SMALL, I_Z_LARGE]].cpu(),
                "source_floor_end_zoo": source_state[[I_Z_SMALL, I_Z_LARGE]].cpu(),
                "current_monthly_total_specific_gain": torch.stack(
                    current_monthly_total
                ).cpu(),
                "current_monthly_log_multiplier": torch.stack(current_monthly_log).cpu(),
                "source_monthly_total_specific_gain": torch.stack(source_monthly_total).cpu(),
                "source_monthly_log_multiplier": torch.stack(source_monthly_log).cpu(),
                "minimum_prey_pool": minimum_prey_pool.cpu(),
                "maximum_abs_specific_ingestion_difference": maximum_abs_difference.cpu(),
                "maximum_relative_specific_ingestion_difference": (
                    maximum_relative_difference.cpu()
                ),
                "maximum_projected_specific_ingestion": maximum_projected_ingestion.cpu(),
                "maximum_source_floor_tolerance_ratio": maximum_tolerance_ratio.cpu(),
            }
            summary = _summarize_trajectory(tensors, prior)
            report["aois"][aoi] = {
                "summary": summary,
                "elapsed_seconds": time.perf_counter() - aoi_started,
            }
            bundle["aois"][aoi] = tensors
            print(
                f"{aoi}: {summary['large_predator_classification']} "
                f"pool_min={min(summary['minimum_prey_pool_by_predator']):.3e} "
                f"rel_max={summary['maximum_relative_specific_ingestion_difference']:.3e} "
                f"margin_max={summary['source_floor_large_predator_continuous_margin_max']:.3f}"
            )
    finally:
        dataset.close()

    trajectory_pass = all(item["summary"]["pass"] for item in report["aois"].values())
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
        "declared_projection_differences": [
            "no DOC state; dissolved grazing remainder is routed to POC",
            "surface-only zooplankton in a two-layer box",
            "mean-neutralized approximate phytoplankton temperature multiplier",
            "chemical-state restoring toward frozen references",
            "Euler integration with nonnegative state clamp",
        ],
    }
    report["decision"] = decision
    bundle["decision"] = decision
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_gzip_torch_save(args.bundle, bundle)
    report["bundle_artifact"] = {
        "path": args.bundle.as_posix(),
        "bytes": args.bundle.stat().st_size,
        "sha256": _sha256(args.bundle),
    }
    _atomic_json(args.report, report)
    print(f"decision={branch} report={args.report} bundle={args.bundle}")
    return 0 if branch in {
        "source-conformant-bounded-projection",
        "source-provenance-incomplete",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
