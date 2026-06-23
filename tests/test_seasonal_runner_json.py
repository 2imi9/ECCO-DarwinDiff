"""seed_recovery_json emits the exact schema scripts/verify_run.py blesses (#115).

The seasonal runner's whole point on the cluster is that its per-seed JSON passes the
verified-loop trust gate. Without this the first H200/B200 fit would emit nothing the
loop can read (CRASHED_NO_JSON) and get reaped. These tests pin the contract against the
REAL verifier loaded from disk: a perfect-recovery batch verifies clean at 6/6, an
off-Carroll batch recomputes without DISCREPANCY, and a single-AOI run never trips the
multi-AOI R_PICPOC straddle guard.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from darwindiff.carroll6 import CARROLL_VALUES, PARAM_NAMES
from darwindiff.seasonal import seed_recovery_json

ROOT = Path(__file__).resolve().parents[1]
CARROLL = [float(c) for c in CARROLL_VALUES]


def _load_verify():
    """Load scripts/verify_run.py as a module (it self-loads diagnostics.band_of)."""
    spec = importlib.util.spec_from_file_location("_verify_run", ROOT / "scripts" / "verify_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(tmp_path: Path, records: list[dict]) -> None:
    for r in records:
        (tmp_path / f"run_seasonal_eqpac_seasonal_seed{r['seed']}.json").write_text(
            json.dumps(r, allow_nan=False), encoding="utf-8"
        )


def test_perfect_recovery_verifies_clean(tmp_path: Path) -> None:
    verify = _load_verify()
    records = [
        seed_recovery_json(
            seed=s, recovered=CARROLL, aoi="eqpac", carroll=CARROLL,
            param_names=PARAM_NAMES, n_seeds_in_batch=2, loss_final=1e-4,
        )
        for s in range(2)
    ]
    _write(tmp_path, records)
    res = verify.verify_config_dir(tmp_path, expect_seeds=2)
    assert res["status"] == "VERIFIED", res
    assert res["n"] == 2
    assert res["n_at_6"] == 2  # exact Carroll values -> 6/6 for every seed
    assert not res["discrepancies"]


def test_off_carroll_recomputes_without_discrepancy(tmp_path: Path) -> None:
    verify = _load_verify()
    # 50% off every param -> "Loose" (rel 0.5 > 0.40), so 0/6 Cal-grade. The point is
    # that the runner-stored joint_band / n_cal_grade match what verify RE-derives.
    recovered = [c * 1.5 for c in CARROLL]
    rec = seed_recovery_json(
        seed=0, recovered=recovered, aoi="eqpac", carroll=CARROLL,
        param_names=PARAM_NAMES, n_seeds_in_batch=1, loss_final=0.1,
    )
    _write(tmp_path, [rec])
    res = verify.verify_config_dir(tmp_path, expect_seeds=1)
    assert not res["discrepancies"], res["discrepancies"]
    assert res["k_by_seed"] == [0]


def test_single_aoi_never_straddles(tmp_path: Path) -> None:
    # Even if R_PICPOC lands Cal+, a 1-AOI run has <2 AOIs so the straddle guard must
    # stay silent (the cell-weighted-mean artifact is impossible with one AOI).
    verify = _load_verify()
    rec = seed_recovery_json(
        seed=0, recovered=CARROLL, aoi="eqpac", carroll=CARROLL,
        param_names=PARAM_NAMES, n_seeds_in_batch=1, loss_final=1e-4,
    )
    _write(tmp_path, [rec])
    res = verify.verify_config_dir(tmp_path, expect_seeds=1)
    assert not any("STRADDLE" in f for f in res["flags"]), res["flags"]
