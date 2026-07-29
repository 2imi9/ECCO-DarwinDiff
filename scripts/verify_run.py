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
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------
# The gate reads the parameter layout from the REGISTRY, not from a private copy.
#
# Until 2026-07-29 this file kept its own hardcoded PARAMS list and CARROLL dict.
# That made the gate blind in a specific and dangerous way: a seventh registry
# parameter would be trained, bounded, collapsed per AOI, graded by the runner and
# written to JSON, and this script would never look at it. The run would still exit
# 0 "VERIFIED", so a parameter no observation constrained could be reported as a
# recovery with the project's own trust gate blessing it.
#
# carroll6 is imported for its registry only. It pulls torch (~2 s), which is
# acceptable for a gate that already parses every seed JSON in a run directory.
# --------------------------------------------------------------------------
sys.path.insert(0, str(ROOT / "src"))
try:
    from darwindiff.carroll6 import PARAMS as _REGISTRY
except Exception as _exc:  # pragma: no cover - environment failure, not logic
    raise SystemExit(
        f"verify_run: cannot import the Carroll-N registry from {ROOT / 'src'}: {_exc}\n"
        "The gate derives its parameter list and reference values from "
        "src/darwindiff/carroll6.py::PARAMS and refuses to fall back to a stale "
        "hardcoded copy, because a silent fallback is exactly the failure mode this "
        "gate exists to prevent."
    ) from _exc

PARAMS = [p.name for p in _REGISTRY]
CARROLL = {p.name: p.carroll_value for p in _REGISTRY}

# Anti-drift invariant. These six values were this file's hardcoded reference from
# its creation until 2026-07-29, independently transcribed from the v04 JAMES build.
# Deriving from the registry buys extensibility; keeping them here as an assertion
# preserves what the hardcoding actually guaranteed, which is that Carroll's
# published optimum for the original six can never move without someone noticing.
# A registry typo now fails loudly here instead of silently re-grading history.
_HISTORICAL_CARROLL = {
    "alpfe": 0.92831,
    "scav_rat": 10.41124 * 0.005 / 86400.0,  # 6.025e-7 per second
    "Smallgrow": 0.66098,
    "Biggrow": 0.43148,
    "diatomgraz": 0.83003,
    "R_PICPOC": 0.04245,
}
for _name, _val in _HISTORICAL_CARROLL.items():
    if _name not in CARROLL:
        raise SystemExit(
            f"verify_run: registry no longer defines '{_name}'. Removing an original "
            "Carroll-6 parameter invalidates every published recovery count that "
            "included it; update _HISTORICAL_CARROLL deliberately if that is intended."
        )
    if abs(CARROLL[_name] - _val) > 1e-9 * max(abs(_val), 1e-30):
        raise SystemExit(
            f"verify_run: registry Carroll value for '{_name}' is {CARROLL[_name]!r} but "
            f"the historical published optimum is {_val!r}. Every recovery count in the "
            "repo is graded against the historical value; refusing to grade against a "
            "changed reference."
        )

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


def _binom_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Used for the chance-baseline effect size."""
    if n <= 0:
        return float("nan")
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _rel(recovered: float, reference: float) -> float:
    if reference == 0:
        return float("inf")
    return abs(recovered - reference) / abs(reference)


def verify_seed(path: Path) -> dict:
    """Recompute one seed's verdict from raw values; flag any stored/recomputed gap."""
    d = json.loads(path.read_text(encoding="utf-8"))
    discrepancies: list[str] = []
    rpicpoc_n_aois = 0
    params = d.get("params")
    if not isinstance(params, dict):
        return {"file": path.name, "status": "MALFORMED",
                "discrepancies": [f"missing or non-dict params block in {path.name}"]}
    missing = [p for p in PARAMS if p not in params]
    # An EXTRA key means the run was produced by a LARGER registry than this gate
    # knows about. Previously the gate ignored extras, so those parameters were
    # trained and graded by the runner and then silently skipped here while the
    # run still exited 0 "VERIFIED". Refusing is the point: an ungraded parameter
    # must never be blessed by the trust gate.
    extra = [k for k in params if k not in PARAMS]
    if missing or extra:
        msg = []
        if missing:
            msg.append(f"missing registry parameter(s) {missing}")
        if extra:
            msg.append(
                f"UNGRADED parameter(s) {extra} present in the artifact but absent from the "
                f"registry this gate loaded ({len(PARAMS)} params). The run and the gate "
                f"disagree about the parameter set; re-run the gate against the matching "
                f"src/darwindiff/carroll6.py rather than trusting a partial grade"
            )
        return {"file": path.name, "status": "MALFORMED",
                "discrepancies": [f"{path.name}: " + "; ".join(msg)]}

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

    k = sum(1 for p in PARAMS if bands[p] in CAL_PLUS)
    excellents = sum(1 for p in PARAMS if bands[p] == "Excellent")
    stored_k = d.get("n_cal_grade")
    if stored_k is not None and stored_k != k:
        discrepancies.append(f"n_cal_grade stored {stored_k} != recomputed {k}")

    iron_pair = bands["alpfe"] in CAL_PLUS and bands["scav_rat"] in CAL_PLUS

    # ---- per-AOI recovery: THE metric. `bands` above is cell-weighted and is
    # not a recovery statement (CLAUDE.md: "grade on the per-AOI >=2-of-3 metric,
    # never the cell-weighted one"). A cell-weighted mean can sit inside the band
    # while every individual AOI sits outside it on alternating sides -- a
    # STRADDLE. Measured 2026-07-29 on the observations-only n=50 run: scav_rat
    # reads 40/50 cell-weighted and 0/50 per-AOI, because all 50 seeds land
    # Cal-grade in exactly one AOI (always southernoceanpac) so no 2-of-3
    # majority ever forms. That is the opposite conclusion, not a rounding
    # difference.
    per_aoi_recovered: dict[str, bool] = {}
    per_aoi_n: dict[str, int] = {}
    straddles: list[str] = []
    for p in PARAMS:
        n_aois = len((params[p].get("per_aoi_recovered", {}) or {}))
        per_aoi_n[p] = n_aois
        if n_aois >= 2:
            ok = per_aoi_calplus.get(p, 0) >= 2
        elif n_aois == 1:
            ok = per_aoi_calplus.get(p, 0) >= 1
        else:
            ok = False
        per_aoi_recovered[p] = ok
        # straddle: cell-weighted claims recovery, per-AOI refuses it
        if n_aois >= 2 and bands[p] in CAL_PLUS and not ok:
            straddles.append(p)

    k_per_aoi = sum(1 for p in PARAMS if per_aoi_recovered[p])

    return {
        "file": path.name,
        "seed": d.get("seed"),
        "status": "OK" if not discrepancies else "DISCREPANCY",
        # k_of_6 is CELL-WEIGHTED and is retained only so historical tooling keeps
        # parsing. Do not headline it. k_of_6_per_aoi is the honest count.
        "k_of_6": k,
        "k_of_6_per_aoi": k_per_aoi,
        "per_aoi_recovered": per_aoi_recovered,
        "per_aoi_n": per_aoi_n,
        "straddles": straddles,
        "excellents": excellents,
        "iron_pair": iron_pair,
        "bands": bands,
        "rpicpoc_per_aoi_calplus": per_aoi_calplus.get("R_PICPOC", 0),
        "rpicpoc_straddle": "R_PICPOC" in straddles,
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
    # per_param is CELL-WEIGHTED. Kept for historical tooling only.
    per_param = {p: sum(1 for s in good if s["bands"][p] in CAL_PLUS) for p in PARAMS}
    # per_param_per_aoi is THE metric: per-AOI >=2-of-3 co-recovery.
    per_param_per_aoi = {
        p: sum(1 for s in good if s.get("per_aoi_recovered", {}).get(p)) for p in PARAMS
    }
    straddled = {
        p: sum(1 for s in good if p in s.get("straddles", [])) for p in PARAMS
    }

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
    # STRADDLE guard, generalised from R_PICPOC-only to every parameter
    # (2026-07-29). A cell-weighted count that exceeds its per-AOI count is not
    # a weaker version of the same result, it can be the OPPOSITE result: on the
    # observations-only n=50 run scav_rat reads 40/50 cell-weighted and 0/50
    # per-AOI.
    # Fire only in the OVER-CLAIMING direction: the aggregate cell-weighted count
    # exceeds the per-AOI count, so quoting cell-weighted would report a stronger
    # result than the honest metric supports. Per-seed disagreements that net to
    # an equal or lower cell-weighted total are not a reporting hazard for that
    # parameter's own MARGINAL count, and flagging them would train readers to
    # ignore the flag.
    #
    # BUT the net-only rule has a proven blind spot (mathematical audit, 2026-07-29).
    # Writing a = seeds that straddle and b = seeds that reverse, the flag fires only
    # when a - b > 0, so whenever a <= b it is silent even though a seeds genuinely
    # straddle. A real archived example: D:/runs/cocc_c scav_rat has a = b = 2, so
    # both rows print 7/10, no flag is raised, and the run exits 0 VERIFIED.
    #
    # That is tolerable for a marginal count and NOT tolerable for a JOINT one.
    # Cancellation permutes WHICH seeds pass, and a joint count (the trio) is a
    # CONJUNCTION over the same seeds, so equal marginals do not imply equal joints:
    # a constructed 10-seed case gives identical per-parameter marginals with a trio
    # of 9/10 cell-weighted against 8/10 per-AOI. The seed-level count is therefore
    # printed unconditionally below as information rather than as a flag, which keeps
    # the flag channel sharp while removing the blind spot.
    # A run carrying no per_aoi_recovered payload cannot be graded on the honest
    # metric at all. That is a DIFFERENT condition from a straddle and must not be
    # reported as "per-AOI 0/n", which would read as a measured failure.
    has_aoi = {p: any((s.get("per_aoi_n") or {}).get(p, 0) for s in good) for p in PARAMS}

    for p in PARAMS:
        if not has_aoi[p]:
            continue
        overclaim = per_param[p] - per_param_per_aoi[p]
        if overclaim > 0:
            sev = ("INVERTS IT (per-AOI says zero)" if per_param_per_aoi[p] == 0
                   else "OVERSTATES it")
            flags.append(
                f"STRADDLE[{p}]: cell-weighted {per_param[p]}/{n} vs per-AOI "
                f"{per_param_per_aoi[p]}/{n} -- cell-weighted {sev}, +{overclaim} seeds "
                f"({straddled[p]}/{n} straddle individually). QUOTE THE PER-AOI NUMBER.")

    missing_aoi = [p for p in PARAMS if not has_aoi[p]]
    if missing_aoi and n:
        flags.append(
            f"NO_PER_AOI_DATA for {', '.join(missing_aoi)}: this run carries no "
            f"per_aoi_recovered payload, so the honest per-AOI >=2-of-3 metric cannot "
            f"be computed. Only the cell-weighted count exists, and it must not be "
            f"quoted as recovery.")

    return {
        "config": cdir.name, "path": str(cdir), "status": status,
        "n": n, "expected_seeds": expected,
        "mean_cal": round(mean_cal, 3),
        "n_at_6": sum(1 for kk in ks if kk == 6),
        "n_at_5": sum(1 for kk in ks if kk == 5),
        "n_at_4plus": sum(1 for kk in ks if kk >= 4),
        "iron_pair_joint": sum(1 for s in good if s["iron_pair"]),
        "total_excellents": sum(s["excellents"] for s in good),
        "per_param_calplus": per_param,                 # cell-weighted, do not headline
        "per_param_per_aoi": per_param_per_aoi,         # THE metric
        "straddled_seeds": straddled,
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
    ap.add_argument("--baseline", default=None,
                    help="directory of an UNTRAINED prior-control run (NB23_LR=0, "
                         "NB23_N_EPOCHS=1) with a MATCHING architecture. Recovery counts "
                         "are not interpretable without one.")
    ap.add_argument("--require-baseline", action="store_true",
                    help="exit 6 (NO_BASELINE) if --baseline is absent. Use in loops and CI "
                         "so an uninterpretable count cannot be recorded as a result.")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"NO_DATA: path does not exist: {root}")
        return 5

    results = [verify_config_dir(c, args.expect_seeds) for c in config_dirs(root)]
    worst = max(SEVERITY.get(r["status"], 2) for r in results)

    # ---- chance-baseline gate -------------------------------------------------
    # A recovery count on its own is not a result. How much of a parameter's PRIOR
    # already satisfies "within +/-40 % of Carroll" depends entirely on its bounds.
    # Measured 2026-07-29, n=50 untrained: diatomgraz scores 0.640 and alpfe 0.200
    # with NO TRAINING AT ALL. A 35/50 diatomgraz count beats an architecture-matched
    # untrained network by one seed (P=0.447). Baselines are also architecture
    # dependent: adding the MLD input channel alone moved alpfe's untrained rate
    # from 10/50 to 16/50.
    baseline_info = None
    if args.baseline:
        bdir = Path(args.baseline)
        if not bdir.exists():
            print(f"NO_DATA: --baseline path does not exist: {bdir}")
            return 5
        bres = [verify_config_dir(c, None) for c in config_dirs(bdir)]
        bn = sum(r.get("n", 0) for r in bres)
        bcounts = {p: sum(r["per_param_per_aoi"].get(p, 0) for r in bres) for p in PARAMS}
        baseline_info = {"dir": str(bdir), "n": bn, "counts": bcounts}
    elif args.require_baseline:
        print("\nX NO_BASELINE: --require-baseline was set but no --baseline was given.")
        print("  A recovery count without an architecture-matched untrained control is")
        print("  not interpretable. Produce one with NB23_LR=0 NB23_N_EPOCHS=1 and the")
        print("  SAME input channels, then pass it with --baseline.")
        return 6

    if args.json:
        print(json.dumps({"exit": worst, "configs": results}, indent=1))
        return worst

    for r in results:
        print(f"\n[{r['status']}] {r['config']}  ({r.get('n', 0)}/{r.get('expected_seeds', '?')} seeds)")
        if r["status"] in ("NO_DATA", "CRASHED_NO_JSON"):
            print(f"   {r.get('note', '')}")
            continue
        # PER-AOI FIRST. This is the number that may be quoted.
        print("   per-AOI >=2-of-3 (THE metric): "
              + ", ".join(f"{p} {r['per_param_per_aoi'][p]}/{r['n']}" for p in PARAMS))
        # Cell-weighted second, explicitly marked. Printed only so a straddle is
        # visible by comparison, never as a result in its own right.
        cw = ", ".join(f"{p} {r['per_param_calplus'][p]}/{r['n']}" for p in PARAMS)
        print(f"   cell-weighted [DO NOT QUOTE]:  {cw}")
        # Seed-level straddle counts, printed UNCONDITIONALLY as information.
        # The STRADDLE flag above fires only on a NET over-claim, so it is silent
        # whenever reverse seeds cancel straddling ones. That is fine for a marginal
        # count and unsafe for a JOINT one, because a joint count is a conjunction
        # over the same seeds and cancellation permutes which seeds pass. This value
        # was already computed and emitted in --json but never rendered.
        _str = r.get("straddled_seeds") or {}
        if any(_str.get(p) for p in PARAMS):
            body = ", ".join(f"{p} {_str[p]}/{r['n']}" for p in PARAMS if _str.get(p))
            print(f"   seeds straddling individually:  {body}")
            print("     (a seed whose cell-weighted verdict disagrees with its per-AOI "
                  "verdict. Nonzero here means JOINT counts are not protected even when "
                  "the marginal counts above agree.)")
        print(f"   mean_cal={r['mean_cal']}  iron_pair_joint={r['iron_pair_joint']}/{r['n']}  "
              f"excellents={r['total_excellents']}   (all cell-weighted)")
        print(f"   k by seed: {r['k_by_seed']}")
        for f in r["flags"]:
            print(f"   ! {f}")
        for dsc in r["discrepancies"]:
            print(f"   X DISCREPANCY: {dsc}")
        for m in r["malformed"]:
            print(f"   X MALFORMED: {m}")

        # effect size against the measured untrained control, or a loud warning
        if baseline_info and baseline_info["n"]:
            bn = baseline_info["n"]
            print(f"   vs untrained baseline ({Path(baseline_info['dir']).name}, n={bn}):")
            for p in PARAMS:
                k, nn = r["per_param_per_aoi"][p], r["n"]
                bk = baseline_info["counts"][p]
                # rule of three: 0 events in N gives a 95% upper bound of 3/N.
                # Testing against a literal 0.000 makes any nonzero count look
                # infinitely significant.
                chance = (3.0 / bn) if bk == 0 else (bk / bn)
                pv = _binom_ge(k, nn, chance)
                verdict = ("decisive" if pv < 1e-4 else "strong" if pv < 0.01
                           else "marginal" if pv < 0.05 else "NOT ABOVE CHANCE")
                print(f"      {p:<11} {k}/{nn} vs chance {chance:.3f}  P={pv:.3g}  {verdict}")
        else:
            print("   ! NO_BASELINE: counts above have no untrained control, so they are")
            print("     NOT interpretable as recovery. Untrained networks score some")
            print("     parameters highly by construction (diatomgraz 0.640 measured).")
            print("     Pass --baseline <untrained run dir>.")

    tag = {0: "VERIFIED & COMPLETE", 2: "DISCREPANCY", 3: "INCOMPLETE",
           4: "CRASHED_NO_JSON", 5: "NO_DATA", 6: "NO_BASELINE"}[worst]
    print(f"\n==> exit {worst} ({tag})")
    return worst


if __name__ == "__main__":
    sys.exit(main())
