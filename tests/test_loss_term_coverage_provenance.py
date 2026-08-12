"""External loss terms must distinguish source failure from geographic zero coverage."""

from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_v3.0_joint_multi_aoi.py"

pytestmark = pytest.mark.skipif(not _RUNNER.is_file(), reason=f"{_RUNNER} not present")


@pytest.fixture(scope="module")
def src() -> str:
    return _RUNNER.read_text(encoding="utf-8")


def test_artifact_records_external_source_and_coverage_status(src: str) -> None:
    assert '"loss_term_provenance"' in src
    assert '"source_status": "loaded" if DANIELS_RPICPOC_W > 0 else "off"' in src
    assert '"source_status": "loaded" if POSI_W > 0 else "off"' in src
    assert '"coverage_status_per_aoi"' in src


def test_active_daniels_load_failure_aborts_instead_of_skipping(src: str) -> None:
    assert "refusing an anchor-off run" in src
    assert "Daniels load failed" not in src


def test_active_posi_with_missing_variables_aborts_instead_of_skipping(src: str) -> None:
    assert "refusing a POSi-off run" in src
    assert "neither bSi_LPT_CONC nor bSi_SPT_CONC present in GEOTRACES; skipping" not in src


def test_native_path_cannot_claim_an_unloaded_daniels_source(src: str) -> None:
    native_guard = src.split("def _load_aoi_bundle_native", 1)[1].split(
        "def load_aoi_bundle", 1
    )[0]
    assert '"DANIELS_RPICPOC_W": DANIELS_RPICPOC_W' in native_guard
