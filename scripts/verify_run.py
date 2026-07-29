#!/usr/bin/env python3
r"""verify_run.py -- anti-hallucination verifier for DarwinDiff parameter-recovery runs.

This is the trust gate for autonomous experiment loops. It reads the REAL per-seed
JSON artifacts in a run/config directory and emits an HONEST, *recomputed* verdict.

It never trusts a stored number:
  * Every Carroll-6 band is RE-DERIVED from the raw `joint_recovered` vs
    `joint_carroll_published` via the canonical `diagnostics.band_of`, then
    cross-checked against the band the runner stored. Mismatch => DISCREPANCY.
  * The stored `joint_carroll_published` is cross-checked against the canonical
    `carroll6.CARROLL_VALUES`. Wrong reference => DISCREPANCY (guards the
    "graded against the wrong Carroll" failure mode).
  * The stored `n_cal_grade` is cross-checked against the recomputed k-of-6.
  * Seeds present are counted against the expected batch size. Short => INCOMPLETE.
  * A dir with `.log` but no `.json` => CRASHED_NO_JSON (post-train write failed,
    e.g. Windows MAX_PATH); use scripts/recover_failed_config_log.py.
  * A dir with nothing => NO_DATA.

If there is no artifact, there is no result. The verifier reports FAILED/INCOMPLETE
rather than inventing a number. A loop MUST treat any nonzero exit as "no
trustworthy result" -- never record or headline a number this script did not bless.

Usage:
    python scripts/verify_run.py "D:\runs\bcr_<stamp>\<config>"        # one config dir
    python scripts/verify_run.py "D:\runs\bcr_<stamp>"                 # recurse to every config dir
    python scripts/verify_run.py <dir> --expect-seeds 10              # enforce completeness
    python scripts/verify_run.py <dir> --json                         # machine-readable verdict

Exit codes (the loop branches on these):
    0  VERIFIED & COMPLETE -- safe to record the reported numbers verbatim
    2  DISCREPANCY         -- recomputed != stored (data-integrity problem; investigate)
    3  INCOMPLETE          -- fewer seeds than expected (re-run / wait)
    4  CRASHED_NO_JSON     -- training likely ran but JSON write failed (recover from .log)
    5  NO_DATA             -- nothing on disk (the run did not happen)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]

# Canonical Carroll-6 published optimum. MUST stay bit-identical to
# src/darwindiff/carroll6.py::CARROLL_VALUES (verified against the v04 JAMES build).
CARROLL = {
    "alpfe": 0.92831,
    "scav_rat": 10.41124 * 0.005 / 86400.0,  # 6.025e-7 per second
    "Smallgrow": 0.66098,
    "Biggrow": 0.43148,
    "diatomgraz": 0.83003,
    "R_PICPOC": 0.04245,
}
REF_TOL = 1e-3  # max relative drift allowed between stored published value and CARROLL

# Load the canonical band_of WITHOUT importing the torch-heavy package __init__.
_spec = importlib.util.spec_from_file_location(
    "_dd_diag", ROOT / "src" / "darwindiff" / "diagnostics.py"
)
_diag = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _diag  # dataclass in diagnostics.py needs the module registered first
_spec.loader.exec_module(_diag)
band_of = _diag.band_of  # (rel_offset: float) -> "Excellent"|"Cal-grade"|"Loose"|"Drifted"

CAL_PLUS = {"Excellent", "Cal-grade"}


def _rel(recovered: float, reference: float) -> float:
    if reference == 0:
        return float("inf")
    return abs(recovered - reference) / abs(reference)


#: Loss terms whose weight is declared separately from the cell count they actually got.
#: A term can be switched ON in the config and still contribute NOTHING -- if its data is
#: unstaged or has no coverage in any AOI, the runner prints a `[warn]` and skips the term,
#: but the run JSON still records the weight. The artifact then *declares* an anchor that
#: never applied.
#:
#: This is not hypothetical. A 2026-07-29 holdout run declared `DANIELS_RPICPOC_W=1` with the
#: PANGAEA compilation unstaged; every AOI got 0 Daniels cells, so it was silently an
#: anchor-off run -- and it passed this script at exit 0, because nothing compared the weight
#: against the count. R_PICPOC came out at 0.20-0.26x Carroll, which is the anchor-off
#: signature, and would have been read as a flagship result.
#:
#: The check is one-directional on purpose: a *zero* weight with a nonzero cell count is
#: normal (counts are computed whether or not the term is used).
_TERM_CELL_KEYS = {
    "daniels_rpicpoc_w": "n_daniels_cells_per_aoi",
    "alk_abs_w": "n_alk_abs_cells_per_aoi",
    "pic_abs_w": "n_pic_abs_cells_per_aoi",
    "poc_abs_w": "n_poc_abs_cells_per_aoi",
    "ratio_w": "n_ratio_cells_per_aoi",
    "posi_w": "n_posi_cells_per_aoi",
    "posi_darwin_w": "n_posi_dw_cells_per_aoi",
    "f_co2_abs_w": "n_f_co2_abs_cells_per_aoi",
    "geotraces_poc_sub_w": "n_geo_poc_subsurface_cells_per_aoi",
}


def inert_terms(d: dict) -> list[str]:
    """Declared-on loss terms that contributed zero cells in every AOI."""
    out = []
    for w_key, n_key in _TERM_CELL_KEYS.items():
        w = d.get(w_key)
        counts = d.get(n_key)
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w <= 0:
            continue
        if not isinstance(counts, dict) or not counts:
            continue
        if all((c or 0) == 0 for c in counts.values()):
            out.append(
                f"{w_key}={w:g} but {n_key} is zero in every AOI -- the loss term was "
                f"SKIPPED (data unstaged or no coverage). This run is NOT the config it "
                f"declares; treat it as that term switched off."
            )
    return out


def verify_seed(path: Path) -> dict:
    """Recompute one seed's verdict from raw values; flag any stored/recomputed gap."""
    d = json.loads(path.read_text(encoding="utf-8"))
    discrepancies: list[str] = []
    rpicpoc_n_aois = 0
    params = d.get("params")
    if not isinstance(params, dict) or any(p not in params for p in PARAMS):
        return {"file": path.name, "status": "MALFORMED",
                "discrepancies": [f"missing params block or a Carroll-6 key in {path.name}"]}

    bands: dict[str, str] = {}
    per_aoi_calplus: dict[str, int] = {}
    for p in PARAMS:
        pp = params[p]
        rec = pp.get("joint_recovered")
        pub = pp.get("joint_carroll_published")
        if rec is None or pub is None:
            discrepancies.append(f"{p}: missing joint_recovered/joint_carroll_published")
            bands[p] = "Drifted"
            continue
        # 1) recomputed band from raw values
        band = band_of(_rel(rec, pub))
        bands[p] = band
        stored_band = pp.get("joint_band")
        if stored_band is not None and stored_band != band:
            discrepancies.append(
                f"{p}: stored band '{stored_band}' != recomputed '{band}' "
                f"(rel={_rel(rec, pub):.4f})")
        # 2) stored published value must match canonical Carroll
        if _rel(pub, CARROLL[p]) > REF_TOL:
            discrepancies.append(
                f"{p}: stored Carroll ref {pub:.6g} != canonical {CARROLL[p]:.6g} "
                f"(WRONG REFERENCE)")
        # per-AOI bands (for the R_PICPOC straddle guard)
        aoi_map = pp.get("per_aoi_recovered", {}) or {}
        per_aoi_calplus[p] = sum(
            1 for v in aoi_map.values() if band_of(_rel(v, CARROLL[p])) in CAL_PLUS
        )
        if p == "R_PICPOC":
            rpicpoc_n_aois = len(aoi_map)

    discrepancies.extend(inert_terms(d))

    k = sum(1 for p in PARAMS if bands[p] in CAL_PLUS)
    excellents = sum(1 for p in PARAMS if bands[p] == "Excellent")
    stored_k = d.get("n_cal_grade")
    if stored_k is not None and stored_k != k:
        discrepancies.append(f"n_cal_grade stored {stored_k} != recomputed {k}")

    iron_pair = bands["alpfe"] in CAL_PLUS and bands["scav_rat"] in CAL_PLUS
    # R_PICPOC straddle (multi-AOI only): joint says Cal+ but it lands in <2 AOIs
    # individually -- the cell-weighted mean straddles Carroll. Meaningless for 1-AOI.
    straddle = (bands["R_PICPOC"] in CAL_PLUS and rpicpoc_n_aois >= 2
                and per_aoi_calplus.get("R_PICPOC", 0) < 2)

    return {
        "file": path.name,
        "seed": d.get("seed"),
        "status": "OK" if not discrepancies else "DISCREPANCY",
        "k_of_6": k,
        "excellents": excellents,
        "iron_pair": iron_pair,
        "bands": bands,
        "rpicpoc_per_aoi_calplus": per_aoi_calplus.get("R_PICPOC", 0),
        "rpicpoc_straddle": straddle,
        "loss_final": d.get("loss_final"),
        "n_seeds_in_batch": d.get("n_seeds_in_batch"),
        "discrepancies": discrepancies,
    }


def verify_config_dir(cdir: Path, expect_seeds: int | None) -> dict:
    jsons = sorted(cdir.glob("*.json"))
    if not jsons:
        has_log = bool(list(cdir.glob("*.log")) or list(cdir.parent.glob("*.log")))
        return {"config": cdir.name, "path": str(cdir),
                "status": "CRASHED_NO_JSON" if has_log else "NO_DATA",
                "n": 0,
                "note": ("training may have run but JSON write failed -- recover with "
                         "scripts/recover_failed_config_log.py")
                if has_log else "no JSON and no .log -- run did not happen"}

    seeds = [verify_seed(p) for p in jsons]
    discrepancies = [f"{s['file']}: {msg}" for s in seeds for msg in s.get("discrepancies", [])]
    malformed = [s["file"] for s in seeds if s["status"] == "MALFORMED"]
    good = [s for s in seeds if s["status"] != "MALFORMED" and "k_of_6" in s]

    n = len(good)
    expected = expect_seeds
    if expected is None:
        batch = {s.get("n_seeds_in_batch") for s in good if s.get("n_seeds_in_batch")}
        expected = max(batch) if batch else n
    incomplete = n < expected

    ks = [s["k_of_6"] for s in good]
    mean_cal = sum(ks) / n if n else 0.0
    per_param = {p: sum(1 for s in good if s["bands"][p] in CAL_PLUS) for p in PARAMS}

    status = "VERIFIED"
    if discrepancies or malformed:
        status = "DISCREPANCY"
    elif incomplete:
        status = "INCOMPLETE"

    # honesty flags -- surfaced so a loop cannot silently over-claim
    flags = []
    if n < 10:
        flags.append(f"LOW_N (n={n}): do not headline; report seed variance, n>=10 for any claim")
    if any(kk >= 5 for kk in ks):
        flags.append("RARE_EVENT (a seed >=5/6): verify reproducibility at n>=10 before claiming; "
                     "check per-AOI, not just joint cell-weighted")
    if any(s["rpicpoc_straddle"] for s in good):
        flags.append("RPICPOC_STRADDLE: R_PICPOC Cal+ jointly but in <2 AOIs individually -- "
                     "report per-AOI (cell-weighted mean can straddle Carroll; see ALK-anchor finding)")

    return {
        "config": cdir.name, "path": str(cdir), "status": status,
        "n": n, "expected_seeds": expected,
        "mean_cal": round(mean_cal, 3),
        "n_at_6": sum(1 for kk in ks if kk == 6),
        "n_at_5": sum(1 for kk in ks if kk == 5),
        "n_at_4plus": sum(1 for kk in ks if kk >= 4),
        "iron_pair_joint": sum(1 for s in good if s["iron_pair"]),
        "total_excellents": sum(s["excellents"] for s in good),
        "per_param_calplus": per_param,
        "k_by_seed": ks,
        "flags": flags,
        "discrepancies": discrepancies,
        "malformed": malformed,
    }


SEVERITY = {"VERIFIED": 0, "INCOMPLETE": 3, "CRASHED_NO_JSON": 4, "NO_DATA": 5, "DISCREPANCY": 2}


def config_dirs(root: Path) -> list[Path]:
    if list(root.glob("*.json")):
        return [root]
    out: list[Path] = []
    for j in sorted(root.rglob("*.json")):
        if j.parent not in out:
            out.append(j.parent)
    return out or [root]


def main() -> int:
    ap = argparse.ArgumentParser(description="Recompute & verify DarwinDiff run artifacts.")
    ap.add_argument("path", help=r"a config dir, or a bcr_<stamp> dir to recurse")
    ap.add_argument("--expect-seeds", type=int, default=None,
                    help="required seed count per config (else inferred from n_seeds_in_batch)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"NO_DATA: path does not exist: {root}")
        return 5

    results = [verify_config_dir(c, args.expect_seeds) for c in config_dirs(root)]
    worst = max(SEVERITY.get(r["status"], 2) for r in results)

    if args.json:
        print(json.dumps({"exit": worst, "configs": results}, indent=1))
        return worst

    for r in results:
        print(f"\n[{r['status']}] {r['config']}  ({r.get('n', 0)}/{r.get('expected_seeds', '?')} seeds)")
        if r["status"] in ("NO_DATA", "CRASHED_NO_JSON"):
            print(f"   {r.get('note', '')}")
            continue
        print(f"   mean_cal={r['mean_cal']}  6/6={r['n_at_6']}  5/6={r['n_at_5']}  "
              f">=4/6={r['n_at_4plus']}  iron_pair_joint={r['iron_pair_joint']}/{r['n']}  "
              f"excellents={r['total_excellents']}")
        print("   per-param Cal+: " + ", ".join(f"{p} {r['per_param_calplus'][p]}/{r['n']}" for p in PARAMS))
        print(f"   k by seed: {r['k_by_seed']}")
        for f in r["flags"]:
            print(f"   ! {f}")
        for dsc in r["discrepancies"]:
            print(f"   X DISCREPANCY: {dsc}")
        for m in r["malformed"]:
            print(f"   X MALFORMED: {m}")

    tag = {0: "VERIFIED & COMPLETE", 2: "DISCREPANCY", 3: "INCOMPLETE",
           4: "CRASHED_NO_JSON", 5: "NO_DATA"}[worst]
    print(f"\n==> exit {worst} ({tag})")
    return worst


if __name__ == "__main__":
    sys.exit(main())
