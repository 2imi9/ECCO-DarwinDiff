from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from scripts.analysis.verify_seasonal_twin_diatom_invasion import (
    VerificationError,
    load_bundle,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-09_seasonal_twin_diatom_invasion.json"
BUNDLE = ROOT / "docs/findings/2026-08-09_seasonal_twin_diatom_invasion.pt.gz"


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not BUNDLE.is_file(),
    reason="local-only tensor bundle absent; the verification JSON pins its sha256",
)


@pytest.fixture(scope="module")
def artifacts() -> tuple[dict, dict]:
    return json.loads(REPORT.read_text(encoding="utf-8")), load_bundle(BUNDLE)


def test_diatom_invasion_verifier_accepts_monthly_tensors(artifacts) -> None:
    report, bundle = artifacts
    receipt = verify(report, bundle)
    assert receipt["verified"] is True
    assert receipt["raw_tensor_cells"] == 549_696
    assert receipt["decision"]["branch"] == "spatial-or-mixed-viability"
    assert receipt["decision"]["b200_authorized"] is False


def test_diatom_invasion_verifier_rejects_nonpositive_euler_factor(artifacts) -> None:
    report, bundle = artifacts
    corrupted = copy.deepcopy(bundle)
    record = corrupted["constructions"]["chemical-fixed-light"]["aois"]["eqpac"]
    record["cycles"][7]["monthly_min_euler_factor"][0, 0, 0] = 0.0
    with pytest.raises(VerificationError, match="Euler factor"):
        verify(report, corrupted)


def test_diatom_invasion_verifier_rejects_decision_drift(artifacts) -> None:
    report, bundle = artifacts
    corrupted = copy.deepcopy(report)
    corrupted["decision"]["branch"] = "structural-diatom-free-attractor"
    with pytest.raises(VerificationError, match="decision tree"):
        verify(corrupted, bundle)
