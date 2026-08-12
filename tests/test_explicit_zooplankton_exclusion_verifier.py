from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json"
BUNDLE = ROOT / "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz"
SCRIPT = ROOT / "scripts/analysis/verify_explicit_zooplankton_exclusion_audit.py"


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not BUNDLE.is_file(),
    reason="local-only tensor bundle absent; the verification JSON pins its sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("exclusion_audit_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(verifier):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    bundle = verifier.load_bundle(BUNDLE)
    return report, bundle


def test_canonical_exclusion_audit_verifies(verifier, artifacts) -> None:
    report, bundle = artifacts
    result = verifier.verify(report, bundle)
    assert result["verified"] is True
    assert result["raw_tensor_cells"] == 220_451
    assert result["decision"]["branch"] == "endogenous-large-predator-exclusion"
    assert result["decision"]["target_rehabilitated"] is False
    assert result["decision"]["b200_authorized"] is False


def test_tampered_target_rehabilitation_is_rejected(verifier, artifacts) -> None:
    report, bundle = artifacts
    tampered = copy.deepcopy(report)
    tampered["decision"]["target_rehabilitated"] = True
    with pytest.raises(verifier.VerificationError, match="target rehabilitated"):
        verifier.verify(tampered, bundle)


def test_tampered_large_predator_classification_is_rejected(verifier, artifacts) -> None:
    report, bundle = artifacts
    tampered = copy.deepcopy(report)
    tampered["aois"]["eqpac"]["summary"]["predators"]["z_large"][
        "classification"
    ] = "mixed-or-near-neutral"
    with pytest.raises(verifier.VerificationError, match="value differs"):
        verifier.verify(tampered, bundle)
