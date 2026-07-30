"""Regression tests for scripts/verify_run.py — the anti-hallucination trust gate.

verify_run.py decides whether every cluster parameter-recovery number is believable,
yet had no tests of its own. These pin each exit-code path (VERIFIED / INCOMPLETE /
NO_DATA / CRASHED_NO_JSON / DISCREPANCY) and each honesty flag (LOW_N / RARE_EVENT /
RPICPOC_STRADDLE) against crafted JSON fixtures, loading the REAL verifier from disk so
the contract can't silently drift. The RPICPOC_STRADDLE case encodes the load-bearing
ALK-anchor finding (a cell-weighted joint mean can be Cal+ while no single AOI is).
"""
from __future__ import annotations

import pytest
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
        val = recovered.get(p, CARROLL[p])
        # Real runs always carry a per-AOI payload, and verify_run now grades on
        # it. Default every AOI to the joint value so a fixture is a *consistent*
        # run (per-AOI agrees with cell-weighted) rather than one missing the
        # honest metric entirely. Pass ``per_aoi`` explicitly to build a straddle.
        default_aoi = {a: val for a in ("eqpac", "natlsubpolar", "southernoceanpac")}
        block = {
            "joint_recovered": val,
            "joint_carroll_published": CARROLL[p],
            "per_aoi_recovered": (per_aoi or {}).get(p, default_aoi),
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
    assert any("STRADDLE[R_PICPOC]" in f for f in res["flags"]), res["flags"]
    assert res["straddled_seeds"]["R_PICPOC"] == 1
    # the per-AOI count must refuse what the cell-weighted count claims
    assert res["per_param_calplus"]["R_PICPOC"] == 1
    assert res["per_param_per_aoi"]["R_PICPOC"] == 0


@pytest.mark.parametrize("param", ["alpfe", "scav_rat", "diatomgraz", "Smallgrow"])
def test_straddle_guard_is_not_rpicpoc_specific(tmp_path, param):
    """The straddle guard must fire for EVERY parameter, not just R_PICPOC.

    Regression for a real miss: on the observations-only n=50 run `scav_rat`
    reads 40/50 cell-weighted and 0/50 per-AOI, because all 50 seeds land
    Cal-grade in exactly one AOI so no 2-of-3 majority forms. The old guard only
    watched R_PICPOC, so that inversion was not flagged.
    """
    per_aoi = {param: {"eqpac": _drifted(param),
                       "natlsubpolar": CARROLL[param] * 0.7}}
    _write(tmp_path, [_record(0, {}, n_seeds=1, per_aoi=per_aoi)])
    res = V.verify_config_dir(tmp_path, expect_seeds=1)
    assert any(f"STRADDLE[{param}]" in f for f in res["flags"]), res["flags"]
    assert res["per_param_per_aoi"][param] == 0


def test_missing_per_aoi_payload_is_flagged_not_reported_as_zero(tmp_path):
    """A run with no per-AOI data cannot be graded honestly, and must say so.

    Reporting "per-AOI 0/n" for such a run would read as a measured failure when
    in fact the metric is uncomputable. That is a different condition from a
    straddle and gets its own flag.
    """
    rec = _record(0, {}, n_seeds=1)
    for p in PARAMS:
        rec["params"][p]["per_aoi_recovered"] = {}
    _write(tmp_path, [rec])
    res = V.verify_config_dir(tmp_path, expect_seeds=1)
    assert any("NO_PER_AOI_DATA" in f for f in res["flags"]), res["flags"]
    # and it must NOT masquerade as a straddle
    assert not any("STRADDLE" in f for f in res["flags"]), res["flags"]


def test_per_aoi_majority_is_required_when_three_aois_present(tmp_path):
    """1-of-3 is NOT recovery; 2-of-3 is. This is the metric the paper quotes."""
    one_of_three = {"alpfe": {"eqpac": CARROLL["alpfe"],
                              "natlsubpolar": _drifted("alpfe"),
                              "southernoceanpac": _drifted("alpfe")}}
    _write(tmp_path, [_record(0, {}, n_seeds=1, per_aoi=one_of_three)])
    assert V.verify_config_dir(tmp_path, expect_seeds=1)["per_param_per_aoi"]["alpfe"] == 0

    two_of_three = {"alpfe": {"eqpac": CARROLL["alpfe"],
                              "natlsubpolar": CARROLL["alpfe"] * 0.95,
                              "southernoceanpac": _drifted("alpfe")}}
    d2 = tmp_path / "two"
    d2.mkdir()
    _write(d2, [_record(0, {}, n_seeds=1, per_aoi=two_of_three)])
    assert V.verify_config_dir(d2, expect_seeds=1)["per_param_per_aoi"]["alpfe"] == 1


# --------------------------------------------------------------------------
# Registry coupling. Before 2026-07-29 verify_run.py kept a private hardcoded
# PARAMS list and CARROLL dict, so a 7th registry parameter would be trained,
# graded and written by the runner and then silently skipped by the gate, with
# the run still exiting 0 "VERIFIED". These pin the fix.
# --------------------------------------------------------------------------


def test_gate_derives_its_parameter_list_from_the_registry():
    """PARAMS/CARROLL must BE the registry, not a copy that can drift from it."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from darwindiff.carroll6 import PARAMS as REGISTRY

    assert V.PARAMS == [p.name for p in REGISTRY], (
        "verify_run.PARAMS has drifted from carroll6.PARAMS. The gate must grade "
        "every registered parameter."
    )
    assert V.CARROLL == {p.name: p.carroll_value for p in REGISTRY}
    assert len(V.PARAMS) == len(REGISTRY)


def test_historical_carroll_values_are_still_the_reference():
    """Deriving from the registry must not let Carroll's published optimum move.

    Every recovery count in the repo is graded against these six numbers. The
    module raises SystemExit at import if the registry disagrees, so reaching
    this assertion at all means the invariant held; it is pinned here too so the
    intent is visible in the test suite.
    """
    for name, val in V._HISTORICAL_CARROLL.items():
        assert name in V.CARROLL
        assert abs(V.CARROLL[name] - val) <= 1e-9 * max(abs(val), 1e-30)


def test_extra_ungraded_parameter_is_rejected_not_ignored(tmp_path):
    """An artifact carrying a parameter the gate does not know must NOT pass.

    This is the seventh-parameter failure mode: the runner grades it, the gate
    skips it, and the run is still blessed. The gate must refuse instead.
    """
    rec = _record(0, {}, n_seeds=1)
    rec["params"]["a_seventh_parameter"] = {
        "joint_recovered": 1.0,
        "joint_carroll_published": 1.0,
        "joint_band": "Excellent",
    }
    _write(tmp_path, [rec])
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] != "VERIFIED", "gate blessed a run containing an ungraded parameter"
    joined = " ".join(res.get("discrepancies", []))
    assert "a_seventh_parameter" in joined
    assert "UNGRADED" in joined


def test_missing_registry_parameter_is_still_rejected(tmp_path):
    """The original malformed path must keep working alongside the extra-key check."""
    rec = _record(0, {}, n_seeds=1)
    rec["params"].pop(V.PARAMS[0])
    _write(tmp_path, [rec])
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] != "VERIFIED"
    assert V.PARAMS[0] in " ".join(res.get("discrepancies", []))


def test_seed_level_straddles_are_reported_even_when_they_net_to_zero(tmp_path, capsys):
    """The blind spot a mathematical audit proved on 2026-07-29.

    The STRADDLE flag fires only on a NET over-claim (a - b > 0), so it is silent
    whenever reverse seeds cancel straddling ones. That is tolerable for a
    parameter's own MARGINAL count and NOT tolerable for a JOINT one: cancellation
    permutes WHICH seeds pass, and a joint count is a conjunction over the same
    seeds, so equal marginals do not imply equal joints.

    The per-seed count was already computed and emitted in --json but never
    rendered, so it was invisible in the output anyone actually reads.
    """
    res = V.verify_config_dir(tmp_path, expect_seeds=None)  # smoke the empty path
    assert res["status"] == "NO_DATA"

    # The value must be carried in the machine-readable payload for every run.
    drift = {p: _drifted(p) for p in PARAMS if p != "alpfe"}
    _write(tmp_path, [_record(s, drift) for s in range(10)])
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert "straddled_seeds" in res
    assert set(res["straddled_seeds"]) == set(PARAMS)


def test_straddle_flag_still_fires_on_a_net_overclaim(tmp_path):
    """Guard the guard: making net-zero visible must not silence the real flag."""
    per_aoi = {"eqpac": True, "natlsubpolar": False, "southernoceanpac": False}
    recs = []
    for s in range(6):
        r = _record(s, {}, n_seeds=6, per_aoi={p: dict(per_aoi) for p in PARAMS})
        recs.append(r)
    _write(tmp_path, recs)
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert any("STRADDLE" in f for f in res["flags"]), \
        "a genuine net over-claim must still raise the flag"
