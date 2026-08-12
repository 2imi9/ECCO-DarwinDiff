from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/findings/2026-08-09_seasonal_twin_blocker_minimality_audit.json"
SOURCE = ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
RECEIPT = ROOT / "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_verification.json"
SCRIPT = ROOT / "scripts/analysis/verify_seasonal_twin_blocker_minimality.py"


@pytest.fixture(scope="module")
def verifier():
    spec = importlib.util.spec_from_file_location("blocker_minimality_verifier", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts():
    return tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in (AUDIT, SOURCE, RECEIPT)
    )


def test_canonical_waiver_lattice_verifies(verifier, artifacts) -> None:
    audit, source, receipt = artifacts
    result = verifier.verify(audit, source, receipt)
    assert result["verified"] is True
    assert result["lattice_nodes_checked"] == 8
    assert result["decision"]["minimum_waiver_count"] == 3
    assert result["decision"]["target_rehabilitated"] is False
    assert result["decision"]["b200_authorized"] is False


def test_no_singleton_or_pair_passes(artifacts) -> None:
    audit, _, _ = artifacts
    assert not any(
        node["pass"] for node in audit["lattice"] if node["waiver_count"] < 3
    )
    assert [node["waivers"] for node in audit["lattice"] if node["pass"]] == [
        [
            "drop_large_predator_obligations",
            "waive_eqpac_seasonality",
            "waive_parameter_handle",
        ]
    ]


def test_tampered_minimum_is_rejected(verifier, artifacts) -> None:
    audit, source, receipt = artifacts
    tampered = copy.deepcopy(audit)
    tampered["decision"]["minimum_waiver_count"] = 1
    with pytest.raises(verifier.VerificationError, match="decision differs"):
        verifier.verify(tampered, source, receipt)


def test_tampered_pair_pass_is_rejected(verifier, artifacts) -> None:
    audit, source, receipt = artifacts
    tampered = copy.deepcopy(audit)
    pair = next(node for node in tampered["lattice"] if node["waiver_count"] == 2)
    pair["pass"] = True
    pair["remaining_failures"] = []
    with pytest.raises(verifier.VerificationError, match="lattice differs"):
        verifier.verify(tampered, source, receipt)
