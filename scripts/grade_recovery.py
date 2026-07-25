#!/usr/bin/env python3
r"""grade_recovery.py -- one-pass HONEST recovery grader for DarwinDiff runs.

Collapses the experiment->grade->gate loop into a single versioned, importable
call. It layers the *science* metric (per-AOI >=2-of-3 Cal+ co-recovery, medians,
and the sloppy-iron-ridge witness rho(alpfe,scav_rat)) on top of the *integrity*
gate that ``verify_run.py`` already owns -- and it surfaces BOTH the honest
per-AOI count and ``verify_run``'s joint (cell-weighted) count side by side, so
the well-known straddle inflation (joint credits seeds no single AOI recovers)
is a number you read, not something you must remember to eyeball.

Honest metric (per param, per seed):
    Cal+ in an AOI  <=>  |v - carroll| / |carroll| <= CAL_MAX (default 0.40),
                         where carroll = that param's stored joint_carroll_published.
    per-AOI recovered <=>  Cal+ in >= n_aoi_min AOIs (default 2, i.e. >=2-of-3).
    (Single-AOI runs degenerate to a 1-of-1 test and are labeled n/a-1AOI.)

Gate: ``verify_run.verify_config_dir`` is invoked on the same dir; its exit
severity, RPICPOC_STRADDLE flag and joint per-param Cal+ counts are reported
verbatim. If ``verify_run`` cannot be imported the tool DEGRADES GRACEFULLY --
it still prints the per-AOI grade, marking the gate column "unavailable".

Usage:
    python scripts/grade_recovery.py <dir> [<dir> ...]
        [--expect-seeds 10]
        [--params alpfe,scav_rat,R_PICPOC,diatomgraz]
        [--n-aoi-min 2]
        [--json out.json]

Importable:
    from grade_recovery import grade_dir
    rep = grade_dir(r"D:\runs\bcr_x\geo1_MLD_DANIELS8", expect_seeds=10)
    rep["params"]["R_PICPOC"]["peraoi_calplus"]   # honest per-AOI count
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Canonical Carroll-6 optimum + band thresholds (mirror verify_run / diagnostics).
# Used as a fallback reference only; the per-AOI grade uses each param's stored
# joint_carroll_published (per the tool contract), falling back to these.
# ---------------------------------------------------------------------------
CARROLL = {
    "alpfe": 0.92831,
    "scav_rat": 10.41124 * 0.005 / 86400.0,  # 6.025e-7 per second
    "Smallgrow": 0.66098,
    "Biggrow": 0.43148,
    "diatomgraz": 0.83003,
    "R_PICPOC": 0.04245,
}
ALL_PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]

EXCELLENT_MAX = 0.05
CAL_MAX = 0.40   # Cal-grade+ ceiling == diagnostics.BAND_CAL_GRADE_MAX
LOOSE_MAX = 0.80

# ---------------------------------------------------------------------------
# Optional integrity gate. Degrade gracefully if verify_run is unavailable.
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    import verify_run as _vr  # noqa: E402
    _GATE_OK = True
    _GATE_ERR = None
except Exception as exc:  # pragma: no cover - env dependent
    _vr = None
    _GATE_OK = False
    _GATE_ERR = f"{type(exc).__name__}: {exc}"


def _rel(v: float, ref: float) -> float:
    if ref is None or ref == 0 or v is None:
        return float("inf")
    return abs(v - ref) / abs(ref)


def band_of(rel: float) -> str:
    """Local copy of the canonical banding (kept in sync with diagnostics.band_of)."""
    if rel <= EXCELLENT_MAX:
        return "Excellent"
    if rel <= CAL_MAX:
        return "Cal-grade"
    if rel <= LOOSE_MAX:
        return "Loose"
    return "Drifted"


def _is_calplus(v: float, ref: float, cal_max: float = CAL_MAX) -> bool:
    return _rel(v, ref) <= cal_max


def _pearson(xs, ys) -> float:
    """Manual Pearson r (no scipy). NaN when n<3 or a series is constant."""
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if x.size < 3:
        return float("nan")
    xd = x - x.mean()
    yd = y - y.mean()
    denom = math.sqrt(float((xd * xd).sum()) * float((yd * yd).sum()))
    if denom == 0.0:
        return float("nan")
    return float((xd * yd).sum() / denom)


def _load_seeds(d: str):
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    seeds = []
    for f in files:
        try:
            r = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(r, dict) and isinstance(r.get("params"), dict):
            seeds.append((os.path.basename(f), r))
    return seeds


def grade_dir(d, expect_seeds=None, params=None, n_aoi_min=2, cal_max=CAL_MAX):
    """Grade one config dir. Returns a structured dict (importable API).

    Keys: config, path, n, expected_seeds, aois, params{p:{...}}, iron_pair_peraoi,
    rho_alpfe_scav, rho_note, gate{...}, gate_available, straddle_notes[].
    """
    d = str(d)
    params = list(params) if params else list(ALL_PARAMS)
    seeds = _load_seeds(d)
    n = len(seeds)

    # discover AOI set (union across seeds, per param -- runner is uniform)
    aoi_union = set()
    for _, r in seeds:
        for p in params:
            pv = r["params"].get(p)
            if pv:
                aoi_union |= set((pv.get("per_aoi_recovered") or {}).keys())
    aois = sorted(aoi_union)

    out_params = {}
    joint_vals = {p: [] for p in params}  # per-seed joint_recovered (for medians + rho)
    for p in params:
        peraoi_hits = 0            # seeds where p is Cal+ in >= n_aoi_min AOIs
        aoi_tally = {a: 0 for a in aois}
        per_seed_recovered = []
        n_aois_p = 0
        ref_used = None
        for _, r in seeds:
            pv = r["params"].get(p)
            if not pv:
                continue
            ref = pv.get("joint_carroll_published", CARROLL.get(p))
            ref_used = ref
            jr = pv.get("joint_recovered")
            if jr is not None:
                per_seed_recovered.append(float(jr))
                joint_vals[p].append(float(jr))
            per_aoi = pv.get("per_aoi_recovered") or {}
            n_aois_p = max(n_aois_p, len(per_aoi))
            n_ok = 0
            for a, v in per_aoi.items():
                ok = _is_calplus(v, ref, cal_max)
                if ok:
                    aoi_tally[a] = aoi_tally.get(a, 0) + 1
                    n_ok += 1
            thr = min(n_aoi_min, len(per_aoi)) if per_aoi else n_aoi_min
            if per_aoi and n_ok >= thr:
                peraoi_hits += 1

        single_aoi = n_aois_p <= 1
        med = float(np.median(per_seed_recovered)) if per_seed_recovered else float("nan")
        out_params[p] = {
            "peraoi_calplus": peraoi_hits,
            "peraoi_label": "n/a-1AOI" if single_aoi else f">={min(n_aoi_min, max(n_aois_p,1))}-of-{n_aois_p}",
            "median": med,
            "carroll": ref_used if ref_used is not None else CARROLL.get(p),
            "per_aoi_calplus": aoi_tally,
            "n_aois": n_aois_p,
        }

    # honest iron pair: both alpfe & scav_rat clear the per-AOI bar in the SAME seed
    iron_pair_peraoi = 0
    if "alpfe" in params and "scav_rat" in params:
        for _, r in seeds:
            pv_a = r["params"].get("alpfe")
            pv_s = r["params"].get("scav_rat")
            if not pv_a or not pv_s:
                continue
            ok = True
            for pv, name in ((pv_a, "alpfe"), (pv_s, "scav_rat")):
                ref = pv.get("joint_carroll_published", CARROLL.get(name))
                per_aoi = pv.get("per_aoi_recovered") or {}
                thr = min(n_aoi_min, len(per_aoi)) if per_aoi else n_aoi_min
                n_ok = sum(1 for v in per_aoi.values() if _is_calplus(v, ref, cal_max))
                if not (per_aoi and n_ok >= thr):
                    ok = False
                    break
            if ok:
                iron_pair_peraoi += 1

    # sloppy-ridge witness: Pearson r of per-seed recovered (alpfe, scav_rat)
    rho = float("nan")
    rho_note = None
    if "alpfe" in joint_vals and "scav_rat" in joint_vals:
        a, s = joint_vals["alpfe"], joint_vals["scav_rat"]
        k = min(len(a), len(s))
        if k < 3:
            rho_note = "n<3"
        rho = _pearson(a[:k], s[:k])

    # -------- integrity gate (verify_run) --------
    gate = None
    gate_available = _GATE_OK
    if _GATE_OK:
        try:
            gate = _vr.verify_config_dir(Path(d), expect_seeds)
        except Exception as exc:  # pragma: no cover
            gate_available = False
            gate = {"status": "GATE_ERROR", "error": f"{type(exc).__name__}: {exc}"}

    # straddle notes: honest per-AOI vs verify_run joint per-param Cal+
    straddle_notes = []
    joint_calplus = {}
    if gate and gate.get("per_param_calplus"):
        for p in params:
            jc = gate["per_param_calplus"].get(p)
            joint_calplus[p] = jc
            honest = out_params[p]["peraoi_calplus"]
            if jc is not None and out_params[p]["n_aois"] >= 2 and jc > honest:
                straddle_notes.append(
                    f"{p}: joint(cell-wtd) {jc}/{n} OVERSTATES per-AOI {honest}/{n} "
                    f"(+{jc - honest}); the cell-weighted mean straddles Carroll")

    return {
        "config": os.path.basename(os.path.normpath(d)),
        "path": d,
        "n": n,
        "expected_seeds": expect_seeds if expect_seeds is not None
        else (gate.get("expected_seeds") if gate else None),
        "aois": aois,
        "params": out_params,
        "joint_calplus": joint_calplus,      # from verify_run gate (may be empty)
        "iron_pair_peraoi": iron_pair_peraoi,
        "rho_alpfe_scav": rho,
        "rho_note": rho_note,
        "gate": gate,
        "gate_available": gate_available,
        "gate_status": (gate or {}).get("status") if gate else "unavailable",
        "gate_exit": (_vr.SEVERITY.get((gate or {}).get("status"), 2)
                      if (gate and _GATE_OK) else None),
        "gate_flags": (gate or {}).get("flags", []) if gate else [],
        "rpicpoc_straddle": any("RPICPOC_STRADDLE" in f for f in ((gate or {}).get("flags") or [])),
        "straddle_notes": straddle_notes,
    }


def _fmt_ct(hits, n):
    return f"{hits}/{n}"


def _print_arm(rep, params):
    n = rep["n"]
    gs = rep["gate_status"]
    gx = rep["gate_exit"]
    hdr = f"\n[{rep['config']}]  n={n}/{rep['expected_seeds'] or '?'}"
    if rep["gate_available"] and gs is not None:
        hdr += f"   gate: {gs} (exit {gx})"
    else:
        hdr += "   gate: unavailable"
    print(hdr)
    has_joint = bool(rep["joint_calplus"])
    print(f"  {'param':<11}{'per-AOI>=2/3':>13}{'joint(cw)':>11}{'straddle':>10}"
          f"{'median':>13}{'Carroll':>13}   AOI Cal+ tally")
    for p in params:
        pp = rep["params"][p]
        honest = pp["peraoi_calplus"]
        jc = rep["joint_calplus"].get(p)
        jc_s = _fmt_ct(jc, n) if jc is not None else "  -  "
        strd = ""
        if jc is not None and pp["n_aois"] >= 2 and jc > honest:
            strd = f"+{jc - honest} <<"
        tally = " ".join(f"{a[:4]}:{c}" for a, c in pp["per_aoi_calplus"].items())
        carroll = pp["carroll"]
        cstr = f"{carroll:.4g}" if carroll is not None else "?"
        print(f"  {p:<11}{_fmt_ct(honest, n):>13}{jc_s:>11}{strd:>10}"
              f"{pp['median']:>13.4g}{cstr:>13}   {tally}")
    rho = rep["rho_alpfe_scav"]
    rho_s = f"{rho:+.2f}" if math.isfinite(rho) else f"nan({rep['rho_note']})"
    ridge = ""
    if math.isfinite(rho):
        ridge = "[ridge INTACT: scav_rat unconstrained]" if abs(rho) > 0.7 \
            else "[ridge partially broken]"
    print(f"  iron_pair (per-AOI honest): {rep['iron_pair_peraoi']}/{n}    "
          f"rho(alpfe,scav_rat)={rho_s}  {ridge}")
    if rep["rpicpoc_straddle"]:
        print("  ! RPICPOC_STRADDLE (from verify_run gate)")
    for note in rep["straddle_notes"]:
        print(f"  ! STRADDLE {note}")
    if not has_joint and rep["gate_available"] is False:
        print("  (joint column blank: verify_run gate unavailable -- "
              f"{_GATE_ERR or 'gate error'})")


def _print_matrix(reports, params):
    if len(reports) < 2:
        return
    print("\nMULTI-ARM COMPARISON  (metric: per-AOI >=2/3 Cal+;  (j+N)=joint inflation)")
    colw = 22
    head = f"  {'arm':<{colw}}{'n':>4}  " + "".join(f"{p[:9]:>11}" for p in params)
    head += f"{'iron_pr':>9}{'rho':>7}"
    print(head)
    for rep in reports:
        n = rep["n"]
        row = f"  {rep['config'][:colw]:<{colw}}{n:>4}  "
        for p in params:
            honest = rep["params"][p]["peraoi_calplus"]
            jc = rep["joint_calplus"].get(p)
            cell = f"{honest}/{n}"
            if jc is not None and rep["params"][p]["n_aois"] >= 2 and jc > honest:
                cell += f"(j+{jc - honest})"
            row += f"{cell:>11}"
        rho = rep["rho_alpfe_scav"]
        rho_s = f"{rho:+.2f}" if math.isfinite(rho) else "nan"
        row += f"{rep['iron_pair_peraoi']}/{n:<0}".rjust(9) + f"{rho_s:>7}"
        print(row)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Honest per-AOI recovery grader (+ verify_run gate) for DarwinDiff runs.")
    ap.add_argument("dirs", nargs="+", help="config dir(s) with per-seed *.json")
    ap.add_argument("--expect-seeds", type=int, default=None,
                    help="required seed count per config (forwarded to the gate)")
    ap.add_argument("--params", default=None,
                    help="comma list to grade (default all 6 Carroll params)")
    ap.add_argument("--n-aoi-min", type=int, default=2,
                    help="AOIs a param must be Cal+ in to count as per-AOI recovered")
    ap.add_argument("--cal-max", type=float, default=CAL_MAX,
                    help="Cal-grade+ relative-offset ceiling (default 0.40)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="also write the structured report to this path")
    args = ap.parse_args(argv)

    params = ([p.strip() for p in args.params.split(",") if p.strip()]
              if args.params else list(ALL_PARAMS))
    unknown = [p for p in params if p not in ALL_PARAMS]
    if unknown:
        print(f"ERROR: unknown params {unknown}; valid: {ALL_PARAMS}", file=sys.stderr)
        return 2

    if not _GATE_OK:
        print(f"WARNING: verify_run gate unavailable ({_GATE_ERR}); "
              "printing per-AOI grade only.", file=sys.stderr)

    reports = []
    for d in args.dirs:
        if not Path(d).exists():
            print(f"\n[{d}] SKIP: path does not exist", file=sys.stderr)
            continue
        rep = grade_dir(d, expect_seeds=args.expect_seeds, params=params,
                        n_aoi_min=args.n_aoi_min, cal_max=args.cal_max)
        reports.append(rep)
        _print_arm(rep, params)

    _print_matrix(reports, params)

    if args.json_out:
        payload = {
            "tool": "grade_recovery", "version": "1.0.0",
            "cal_max": args.cal_max, "n_aoi_min": args.n_aoi_min,
            "gate_available": _GATE_OK, "gate_error": _GATE_ERR,
            "params_graded": params,
            "arms": reports,
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=1, default=str),
                                       encoding="utf-8")
        print(f"\nwrote {args.json_out}")

    # exit = worst gate severity (0 when gate clean / unavailable-but-graded)
    if _GATE_OK and reports:
        worst = max((r["gate_exit"] or 0) for r in reports)
    else:
        worst = 0
    return worst


if __name__ == "__main__":
    sys.exit(main())
