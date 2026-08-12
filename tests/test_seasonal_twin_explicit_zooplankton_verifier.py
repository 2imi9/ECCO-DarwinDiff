from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
BUNDLE = ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
SCRIPT = ROOT / "scripts/analysis/verify_seasonal_twin_explicit_zooplankton_gate.py"


# Raw tensor bundles are local-only (untracked; see .gitignore). The tracked
# verification JSON pins each bundle's sha256, so a machine that has the bundle
# re-verifies against the identical bytes; a fresh checkout skips instead of failing.
pytestmark = pytest.mark.skipif(
    not BUNDLE.is_file(),
    reason="local-only tensor bundle absent; the verification JSON pins its sha256",
)


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("explicit_zoo_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(verifier):
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    bundle = verifier.load_bundle(BUNDLE)
    return report, bundle


def test_canonical_explicit_zoo_artifact_verifies(verifier, artifacts) -> None:
    report, bundle = artifacts
    result = verifier.verify(report, bundle)
    assert result["verified"] is True
    assert result["raw_tensor_cells"] == 4_681_005
    assert result["maximum_source_partition_residual"] < 2e-15
    assert result["decision"]["branch"] == "stage0-failed-stop"
    assert result["decision"]["b200_authorized"] is False


def test_tampered_b200_authorization_is_rejected(verifier, artifacts) -> None:
    report, bundle = artifacts
    tampered = copy.deepcopy(report)
    tampered["decision"]["b200_authorized"] = True
    with pytest.raises(verifier.VerificationError, match="B200 authorized"):
        verifier.verify(tampered, bundle)
