from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.json"
BUNDLE = ROOT / "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.pt.gz"
TARGET_REPORT = (
    ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
TARGET_BUNDLE = (
    ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
)
EXCLUSION_REPORT = (
    ROOT / "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json"
)
EXCLUSION_BUNDLE = (
    ROOT / "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz"
)
SCRIPT = (
    ROOT / "scripts/analysis/verify_explicit_zooplankton_prey_energy_audit.py"
)


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in (BUNDLE, TARGET_BUNDLE, EXCLUSION_BUNDLE)),
    reason="local-only tensor bundles absent; the verification JSONs pin their sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("prey_energy_verifier", SCRIPT)
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
    exclusion_report = json.loads(EXCLUSION_REPORT.read_text(encoding="utf-8"))
    exclusion_bundle = verifier.load_bundle(EXCLUSION_BUNDLE)
    hashes = {
        "source_target_report_sha256": verifier._sha256(TARGET_REPORT),
        "source_target_bundle_sha256": verifier._sha256(TARGET_BUNDLE),
        "source_exclusion_report_sha256": verifier._sha256(EXCLUSION_REPORT),
        "source_exclusion_bundle_sha256": verifier._sha256(EXCLUSION_BUNDLE),
    }
    return (
        report,
        bundle,
        target_report,
        target_bundle,
        exclusion_report,
        exclusion_bundle,
        hashes,
    )


def _verify(verifier, artifacts, **overrides):
    names = (
        "report",
        "bundle",
        "target_report",
        "target_bundle",
        "exclusion_report",
        "exclusion_bundle",
        "hashes",
    )
    inputs = dict(zip(names, artifacts, strict=True))
    inputs.update(overrides)
    return verifier.verify(**inputs)


def test_canonical_prey_energy_audit_verifies(verifier, artifacts) -> None:
    result = _verify(verifier, artifacts)
    assert result["verified"] is True
    assert result["raw_tensor_cells"] == 564_011
    assert result["decision"]["branch"] == "prey-field-energy-deficit"
    assert result["decision"]["target_rehabilitated"] is False
    assert result["decision"]["b200_authorized"] is False


def test_tampered_prey_partition_is_rejected(verifier, artifacts) -> None:
    bundle = copy.deepcopy(artifacts[1])
    bundle["aois"]["eqpac"]["monthly_specific_gain_by_prey"][0, 0, 0, 0, 0] += 1.0
    with pytest.raises(verifier.VerificationError, match="value differs"):
        _verify(verifier, artifacts, bundle=bundle)


def test_tampered_source_hash_is_rejected(verifier, artifacts) -> None:
    hashes = dict(artifacts[-1])
    hashes["source_exclusion_bundle_sha256"] = "0" * 64
    with pytest.raises(verifier.VerificationError, match="source_exclusion_bundle_sha256"):
        _verify(verifier, artifacts, hashes=hashes)


def test_tampered_compute_authorization_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["decision"]["b200_authorized"] = True
    with pytest.raises(verifier.VerificationError, match="B200 authorized"):
        _verify(verifier, artifacts, report=report)
