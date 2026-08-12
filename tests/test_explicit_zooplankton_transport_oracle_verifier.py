from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_transport_oracle_audit.json"
)
SUPPORT_REPORT = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
SUPPORT_BUNDLE = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)
ENERGY_REPORT = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_"
    "source_floor_corrected.json"
)
ENERGY_BUNDLE = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_"
    "source_floor_corrected.pt.gz"
)
SCRIPT = ROOT / (
    "scripts/analysis/verify_explicit_zooplankton_transport_oracle_audit.py"
)


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in (SUPPORT_BUNDLE, ENERGY_BUNDLE)),
    reason="local-only tensor bundles absent; the verification JSONs pin their sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("transport_oracle_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(verifier):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    support_report = json.loads(SUPPORT_REPORT.read_text(encoding="utf-8"))
    support_bundle = verifier.load_bundle(SUPPORT_BUNDLE)
    energy_report = json.loads(ENERGY_REPORT.read_text(encoding="utf-8"))
    energy_bundle = verifier.load_bundle(ENERGY_BUNDLE)
    hashes = {
        "support_report_sha256": verifier._sha256(SUPPORT_REPORT),
        "support_bundle_sha256": verifier._sha256(SUPPORT_BUNDLE),
        "energy_report_sha256": verifier._sha256(ENERGY_REPORT),
        "energy_bundle_sha256": verifier._sha256(ENERGY_BUNDLE),
    }
    return report, support_report, support_bundle, energy_report, energy_bundle, hashes


def _verify(verifier, artifacts, **overrides):
    names = (
        "report",
        "support_report",
        "support_bundle",
        "energy_report",
        "energy_bundle",
        "hashes",
    )
    inputs = dict(zip(names, artifacts, strict=True))
    inputs.update(overrides)
    return verifier.verify(**inputs)


def test_canonical_transport_oracle_verifies(verifier, artifacts) -> None:
    result = _verify(verifier, artifacts)
    assert result["verified"] is True
    assert result["raw_support_tensor_cells"] == 16_765_728
    assert result["decision"]["branch"] == (
        "frozen-path-relocation-ruled-out-in-one-or-more-aois"
    )
    assert result["decision"]["stepwise_oracle_clears_mortality_by_aoi"] == {
        "eqpac": False,
        "natlsubpolar": True,
        "southernoceanpac": False,
    }
    assert result["decision"]["actual_transport_tested"] is False
    assert result["decision"]["target_rehabilitated"] is False
    assert result["decision"]["b200_authorized"] is False


def test_tampered_oracle_gain_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["aois"]["eqpac"]["stepwise_teleport"]["gain_integral"] += 0.1
    with pytest.raises(verifier.VerificationError, match="value differs"):
        _verify(verifier, artifacts, report=report)


def test_tampered_support_is_rejected(verifier, artifacts) -> None:
    bundle = copy.deepcopy(artifacts[2])
    bundle["aois"]["eqpac"]["weighted_large_prey"][0, 0, 0] += 1.0
    with pytest.raises(verifier.VerificationError):
        _verify(verifier, artifacts, support_bundle=bundle)


def test_tampered_energy_hash_is_rejected(verifier, artifacts) -> None:
    hashes = dict(artifacts[-1])
    hashes["energy_bundle_sha256"] = "0" * 64
    with pytest.raises(verifier.VerificationError, match="energy bundle SHA-256"):
        _verify(verifier, artifacts, hashes=hashes)


def test_tampered_compute_authorization_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["decision"]["b200_authorized"] = True
    with pytest.raises(verifier.VerificationError, match="report decision differs"):
        _verify(verifier, artifacts, report=report)

