from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/findings/"
    "2026-08-10_explicit_zooplankton_source_conformance_postcorrection.json"
)
BUNDLE = ROOT / (
    "docs/findings/"
    "2026-08-10_explicit_zooplankton_source_conformance_postcorrection.pt.gz"
)
TARGET_REPORT = ROOT / (
    "docs/findings/"
    "2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected.json"
)
TARGET_BUNDLE = ROOT / (
    "docs/findings/"
    "2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected.pt.gz"
)
ENERGY_REPORT = ROOT / (
    "docs/findings/"
    "2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.json"
)
ENERGY_BUNDLE = ROOT / (
    "docs/findings/"
    "2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.pt.gz"
)
SCRIPT = ROOT / (
    "scripts/analysis/verify_explicit_zooplankton_source_conformance.py"
)


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in (BUNDLE, TARGET_BUNDLE, ENERGY_BUNDLE)),
    reason="local-only tensor bundles absent; the verification JSONs pin their sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("source_conformance_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(verifier):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    bundle = verifier.load_bundle(BUNDLE)
    target_report = json.loads(TARGET_REPORT.read_text(encoding="utf-8"))
    target_bundle = verifier.load_bundle(TARGET_BUNDLE)
    energy_report = json.loads(ENERGY_REPORT.read_text(encoding="utf-8"))
    energy_bundle = verifier.load_bundle(ENERGY_BUNDLE)
    hashes = {
        "audit_bundle_sha256": verifier._sha256(BUNDLE),
        "source_target_report_sha256": verifier._sha256(TARGET_REPORT),
        "source_target_bundle_sha256": verifier._sha256(TARGET_BUNDLE),
        "source_energy_report_sha256": verifier._sha256(ENERGY_REPORT),
        "source_energy_bundle_sha256": verifier._sha256(ENERGY_BUNDLE),
    }
    return (
        report,
        bundle,
        target_report,
        target_bundle,
        energy_report,
        energy_bundle,
        hashes,
    )


def _verify(verifier, artifacts, **overrides):
    names = (
        "report",
        "bundle",
        "target_report",
        "target_bundle",
        "energy_report",
        "energy_bundle",
        "hashes",
    )
    inputs = dict(zip(names, artifacts, strict=True))
    inputs.update(overrides)
    return verifier.verify(**inputs)


def test_canonical_source_conformance_artifact_verifies(verifier, artifacts) -> None:
    result = _verify(verifier, artifacts)
    assert result["verified"] is True
    assert result["source_file_count"] == 9
    assert result["raw_tensor_cells"] == 323_519
    assert result["decision"]["branch"] == "source-conformant-bounded-projection"
    assert result["decision"]["b200_authorized"] is False


def test_tampered_source_bytes_are_rejected(verifier, artifacts) -> None:
    bundle = copy.deepcopy(artifacts[1])
    bundle["source_bytes"]["direct"]["options"] += b"\n"

    with pytest.raises(verifier.VerificationError, match="source_files"):
        _verify(verifier, artifacts, bundle=bundle)


def test_tampered_tolerance_tensor_is_rejected(verifier, artifacts) -> None:
    bundle = copy.deepcopy(artifacts[1])
    bundle["aois"]["eqpac"]["maximum_source_floor_tolerance_ratio"][0, 0, 0] = 2.0

    with pytest.raises(verifier.VerificationError, match="summary"):
        _verify(verifier, artifacts, bundle=bundle)


def test_tampered_b200_authorization_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["decision"]["b200_authorized"] = True

    with pytest.raises(verifier.VerificationError, match="report decision differs"):
        _verify(verifier, artifacts, report=report)


def test_tampered_source_artifact_hash_is_rejected(verifier, artifacts) -> None:
    hashes = dict(artifacts[-1])
    hashes["source_energy_bundle_sha256"] = "0" * 64

    with pytest.raises(
        verifier.VerificationError,
        match=r"config\.source_energy_bundle_sha256",
    ):
        _verify(verifier, artifacts, hashes=hashes)
