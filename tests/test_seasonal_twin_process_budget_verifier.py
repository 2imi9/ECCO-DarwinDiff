from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from scripts.analysis.verify_seasonal_twin_process_budget import (
    TARGET_REPORTS,
    VerificationError,
    load_bundle,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-09_seasonal_twin_phytoplankton_process_budget.json"
BUNDLE = ROOT / "docs/findings/2026-08-09_seasonal_twin_phytoplankton_process_budget.pt.gz"


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not BUNDLE.is_file(),
    reason="local-only tensor bundle absent; the verification JSON pins its sha256",
)


@pytest.fixture(scope="module")
def artifacts() -> tuple[dict, dict, dict[str, dict]]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    bundle = load_bundle(BUNDLE)
    targets = {
        name: json.loads((ROOT / path).read_text(encoding="utf-8"))
        for name, path in TARGET_REPORTS.items()
    }
    return report, bundle, targets


def test_process_budget_verifier_accepts_raw_bundle(artifacts) -> None:
    report, bundle, targets = artifacts
    receipt = verify(report, bundle, targets)
    assert receipt["verified"] is True
    assert receipt["raw_tensor_cells"] == 1_786_512
    assert receipt["decision"]["branch"] == "mixed-or-other"
    assert receipt["decision"]["b200_authorized"] is False


def test_process_budget_verifier_rejects_hidden_phyto_closure(artifacts) -> None:
    report, bundle, targets = artifacts
    corrupted = copy.deepcopy(bundle)
    item = corrupted["constructions"]["chemical-fixed-light"]["aois"]["eqpac"]
    mask = item["mask"]
    item["cycles"][1]["closure_abs"][0][mask] = 1e-3
    with pytest.raises(VerificationError, match="closure"):
        verify(report, corrupted, targets)


def test_process_budget_verifier_rejects_reported_decision_drift(artifacts) -> None:
    report, bundle, targets = artifacts
    corrupted = copy.deepcopy(report)
    corrupted["decision"]["branch"] = "intrinsic-sink-imbalance"
    with pytest.raises(VerificationError, match="decision tree"):
        verify(corrupted, bundle, targets)
