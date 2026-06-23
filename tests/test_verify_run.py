"""Regression tests for scripts/verify_run.py — the anti-hallucination trust gate.

verify_run.py decides whether every cluster parameter-recovery number is believable,
yet had no tests of its own. These pin each exit-code path (VERIFIED / INCOMPLETE /
NO_DATA / CRASHED_NO_JSON / DISCREPANCY) and each honesty flag (LOW_N / RARE_EVENT /
RPICPOC_STRADDLE) against crafted JSON fixtures, loading the REAL verifier from disk so
the contract can't silently drift. The RPICPOC_STRADDLE case encodes the load-bearing
ALK-anchor finding (a cell-weighted joint mean can be Cal+ while no single AOI is).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_verify():
    spec = importlib.util.spec_from_file_location("_verify_run", ROOT / "scripts" / "verify_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load_verify()
PARAMS = V.PARAMS
CARROLL = V.CARROLL


def _drifted(p: str) -> float:
    """A value well outside Cal-grade for param ``p`` (rel offset 1.0 -> Drifted)."""
    return CARROLL[p] * 2.0


def _record(seed, recovered, *, n_seeds=10, per_aoi=None, bands=None, n_cal=None):
    """One per-seed JSON dict in the verify_run schema.

    ``recovered`` maps param->value (omitted params default to exact Carroll =
    Excellent); ``per_aoi`` maps param->{aoi: value}; ``bands`` stores a (possibly
    wrong) ``joint_band`` to probe the stored-vs-recomputed cross-check.
    """
    params = {}
    for p in PARAMS:
        block = {
            "joint_recovered": recovered.get(p, CARROLL[p]),
            "joint_carroll_published": CARROLL[p],
            "per_aoi_recovered": (per_aoi or {}).get(p, {}),
        }
        if bands and p in bands:
            block["joint_band"] = bands[p]
        params[p] = block
    rec = {"seed": seed, "n_seeds_in_batch": n_seeds, "params": params}
    if n_cal is not None:
        rec["n_cal_grade"] = n_cal
    return rec


def _write(d: Path, records):
    for r in records:
        (d / f"seed{r['seed']}.json").write_text(json.dumps(r, allow_nan=False), encoding="utf-8")


def test_verified_exit0_clean(tmp_path):
    # 10 seeds, only the iron pair Cal+ (k=2) -> VERIFIED, no flags.
    drift = {p: _drifted(p) for p in PARAMS if p not in ("alpfe", "scav_rat")}
    _write(tmp_path, [_record(s, drift) for s in range(10)])
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "VERIFIED"
    assert V.SEVERITY[res["status"]] == 0
    assert res["n"] == 10
    assert res["flags"] == []
    assert res["iron_pair_joint"] == 10


def test_incomplete_short_seeds(tmp_path):
    _write(tmp_path, [_record(s, {}, n_seeds=10) for s in range(3)])
    res = V.verify_config_dir(tmp_path, expect_seeds=10)
    assert res["status"] == "INCOMPLETE"
    assert V.SEVERITY[res["status"]] == 3


def test_no_data_empty_dir(tmp_path):
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "NO_DATA"
    assert V.SEVERITY[res["status"]] == 5


def test_crashed_no_json(tmp_path):
    (tmp_path / "train.log").write_text("trained ok\n", encoding="utf-8")
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "CRASHED_NO_JSON"
    assert V.SEVERITY[res["status"]] == 4


def test_discrepancy_wrong_stored_band(tmp_path):
    # store joint_band="Excellent" for a param that is actually Drifted -> DISCREPANCY
    rec = _record(0, {"diatomgraz": _drifted("diatomgraz")}, bands={"diatomgraz": "Excellent"})
    _write(tmp_path, [rec])
    res = V.verify_config_dir(tmp_path, expect_seeds=1)
    assert res["status"] == "DISCREPANCY"
    assert V.SEVERITY[res["status"]] == 2


def test_discrepancy_wrong_reference(tmp_path):
    # stored Carroll reference drifted from canonical -> guards "graded vs wrong Carroll"
    rec = _record(0, {})
    rec["params"]["alpfe"]["joint_carroll_published"] = CARROLL["alpfe"] * 1.5
    _write(tmp_path, [rec])
    res = V.verify_config_dir(tmp_path, expect_seeds=1)
    assert res["status"] == "DISCREPANCY"


def test_low_n_flag(tmp_path):
    drift = {p: _drifted(p) for p in PARAMS if p != "alpfe"}
    _write(tmp_path, [_record(s, drift) for s in range(2)])
    res = V.verify_config_dir(tmp_path, expect_seeds=2)
    assert res["status"] == "VERIFIED"
    assert any("LOW_N" in f for f in res["flags"])


def test_rare_event_flag(tmp_path):
    # every seed at 6/6 -> RARE_EVENT (a seed >=5/6)
    _write(tmp_path, [_record(s, {}) for s in range(10)])
    res = V.verify_config_dir(tmp_path, expect_seeds=10)
    assert any("RARE_EVENT" in f for f in res["flags"])
    assert res["n_at_6"] == 10


def test_rpicpoc_straddle_flag(tmp_path):
    # R_PICPOC Cal+ jointly but in 0 of 2 AOIs individually -> straddle (ALK-anchor lesson)
    per_aoi = {"R_PICPOC": {"eqpac": _drifted("R_PICPOC"),
                            "natlsubpolar": CARROLL["R_PICPOC"] * 0.3}}
    _write(tmp_path, [_record(0, {}, n_seeds=1, per_aoi=per_aoi)])
    res = V.verify_config_dir(tmp_path, expect_seeds=1)
    assert any("RPICPOC_STRADDLE" in f for f in res["flags"]), res["flags"]
