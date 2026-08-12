from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-10_explicit_zooplankton_path_oracle_audit.json"
DISCRETE_REPORT = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_discrete_transport_oracle_audit.json"
)
SUPPORT_REPORT = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
SUPPORT_BUNDLE = ROOT / (
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)
SCRIPT = ROOT / "scripts/analysis/verify_explicit_zooplankton_path_oracle_audit.py"


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not SUPPORT_BUNDLE.is_file(),
    reason="local-only tensor bundle absent; the verification JSON pins its sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("path_oracle_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(verifier):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    discrete_report = json.loads(DISCRETE_REPORT.read_text(encoding="utf-8"))
    support_report = json.loads(SUPPORT_REPORT.read_text(encoding="utf-8"))
    support_bundle = verifier.load_bundle(SUPPORT_BUNDLE)
    hashes = {
        "discrete_report_sha256": verifier._sha256(DISCRETE_REPORT),
        "support_report_sha256": verifier._sha256(SUPPORT_REPORT),
        "support_bundle_sha256": verifier._sha256(SUPPORT_BUNDLE),
    }
    return report, discrete_report, support_report, support_bundle, hashes


def _verify(verifier, artifacts, **overrides):
    names = (
        "report",
        "discrete_report",
        "support_report",
        "support_bundle",
        "hashes",
    )
    inputs = dict(zip(names, artifacts, strict=True))
    inputs.update(overrides)
    return verifier.verify(**inputs)


def test_canonical_path_oracle_verifies(verifier, artifacts) -> None:
    result = _verify(verifier, artifacts)
    assert result["verified"] is True
    assert result["raw_support_tensor_cells"] == 16_765_728
    assert result["decision"]["branch"] == (
        "natl-knife-edge-requires-discontinuous-relocation"
    )
    assert result["decision"]["natl_radius1_positive"] is False
    natl = artifacts[0]["aois"]["natlsubpolar"]["radius_ladder"]
    assert natl["1"]["annual_log_multiplier"] == pytest.approx(-0.025718255968627687)
    assert natl["4"]["annual_log_multiplier"] == pytest.approx(-0.004977078763334924)
    assert result["decision"]["actual_transport_tested"] is False
    assert result["decision"]["target_rehabilitated"] is False
    assert result["decision"]["b200_authorized"] is False


def test_tampered_radius_score_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["aois"]["natlsubpolar"]["radius_ladder"]["1"][
        "annual_log_multiplier"
    ] += 0.1
    with pytest.raises(verifier.VerificationError, match="value differs"):
        _verify(verifier, artifacts, report=report)


def test_tampered_path_constraint_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["aois"]["natlsubpolar"]["radius_ladder"]["1"][
        "maximum_realized_manhattan_jump"
    ] = 2
    with pytest.raises(verifier.VerificationError, match="value differs"):
        _verify(verifier, artifacts, report=report)


def test_tampered_support_is_rejected(verifier, artifacts) -> None:
    bundle = copy.deepcopy(artifacts[3])
    item = bundle["aois"]["natlsubpolar"]
    row, column = item["mask"].nonzero()[0]
    item["weighted_large_prey"][0, row, column] += 1.0
    with pytest.raises(verifier.VerificationError):
        _verify(verifier, artifacts, support_bundle=bundle)


def test_tampered_compute_decision_is_rejected(verifier, artifacts) -> None:
    report = copy.deepcopy(artifacts[0])
    report["decision"]["b200_authorized"] = True
    with pytest.raises(verifier.VerificationError, match="report decision differs"):
        _verify(verifier, artifacts, report=report)
