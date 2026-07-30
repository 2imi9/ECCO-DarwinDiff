#!/usr/bin/env python3
"""Cross-validate every independent implementation of the per-AOI majority rule.

The risk being tested: eight files implement this rule independently, and on
2026-07-30 TWO of them were provably wrong (hardcoded >=2, so single-AOI runs
graded 0/n). If any disagree on a run we actually cite, a published number is wrong.

Compares, per parameter, the per-AOI majority count from:
  A  scripts/verify_run.py              (the trust gate)
  B  scripts/grade_recovery.py          (the canonical-numbers source of truth)
  C  scripts/analysis/grade_all_params.py
  D  scripts/analysis/grade_joint_percell.py   (trio only)
  E  an INDEPENDENT reimplementation written here from the documented rule

E exists so agreement among A-D cannot come from a shared bug.
"""
from __future__ import annotations

import glob
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "src" / "darwindiff").is_dir():
    if ROOT.parent == ROOT:
        raise SystemExit("cannot locate repo root")
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

from darwindiff.carroll6 import PARAMS  # noqa: E402
from darwindiff.diagnostics import band_of  # noqa: E402

CAL = {"Excellent", "Cal-grade"}
NAMES = [p.name for p in PARAMS]
TRIO = ["alpfe", "scav_rat", "R_PICPOC"]


def _load(rel):
    spec = importlib.util.spec_from_file_location(f"_x_{Path(rel).stem}", ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def independent_counts(run_dir):
    """E: written from the documented rule, sharing no code with A-D.

    Rule (CLAUDE.md + verify_run:263-270): a parameter counts for a seed when it is
    Cal-grade-or-better in >=2 of 3 AOIs, or >=1 of 1 for a single-AOI run.
    """
    counts = {n: 0 for n in NAMES}
    trio = 0
    files = sorted(glob.glob(os.path.join(run_dir, "*.json")))
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        params = d.get("params") or {}
        ok = {}
        for n in NAMES:
            pp = params.get(n)
            if not isinstance(pp, dict):
                ok[n] = False
                continue
            pub = pp.get("joint_carroll_published")
            legs = pp.get("per_aoi_recovered") or {}
            if pub in (None, 0) or not legs:
                ok[n] = False
                continue
            good = sum(1 for v in legs.values() if band_of(abs(v - pub) / abs(pub)) in CAL)
            ok[n] = good >= (2 if len(legs) >= 2 else 1)
            if ok[n]:
                counts[n] += 1
        if all(ok.get(t) for t in TRIO):
            trio += 1
    return counts, trio, len(files)


def verify_run_counts(run_dir):
    V = _load("scripts/verify_run.py")
    r = V.verify_config_dir(Path(run_dir), expect_seeds=None)
    return r.get("per_param_per_aoi", {}), r.get("status"), r.get("n", 0)


def grade_all_params_counts(run_dir):
    G = _load("scripts/analysis/grade_all_params.py")
    counts, n, _ = G.per_aoi_2of3(run_dir)
    return {k: counts.get(k, 0) for k in NAMES}, n


def grade_recovery_counts(run_dir):
    """B is CLI-only; parse its table."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/grade_recovery.py"), run_dir,
         "--params", ",".join(NAMES)],
        capture_output=True, text=True,
    )
    if r.returncode not in (0, 1, 2, 3):
        return None, r.stderr[-300:]
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in NAMES:
            for tok in parts[1:]:
                if "/" in tok:
                    try:
                        out[parts[0]] = int(tok.split("/")[0])
                    except ValueError:
                        pass
                    break
    return out, None


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit("usage: grader_crosscheck.py <run_dir> [run_dir ...]")
    any_mismatch = False
    for d in dirs:
        print("=" * 92)
        print(f"RUN: {d}")
        e_counts, e_trio, n = independent_counts(d)
        if n == 0:
            print("  NO DATA")
            continue
        a_counts, a_status, a_n = verify_run_counts(d)
        c_counts, c_n = grade_all_params_counts(d)
        b_counts, b_err = grade_recovery_counts(d)
        print(f"  n seeds: independent={n} verify_run={a_n} grade_all_params={c_n}  "
              f"verify_run status={a_status}")
        if b_err:
            print(f"  [warn] grade_recovery not comparable: {b_err}")
        hdr = f"  {'param':<12}{'INDEP(E)':>10}{'verify(A)':>11}{'gradeall(C)':>13}"
        if b_counts:
            hdr += f"{'graderec(B)':>13}"
        print(hdr)
        for name in NAMES:
            e = e_counts[name]
            a = a_counts.get(name)
            c = c_counts.get(name)
            row = f"  {name:<12}{e:>10}{a if a is not None else '-':>11}{c if c is not None else '-':>13}"
            vals = [v for v in (e, a, c) if v is not None]
            if b_counts and name in b_counts:
                row += f"{b_counts[name]:>13}"
                vals.append(b_counts[name])
            bad = len(set(vals)) > 1
            if bad:
                any_mismatch = True
                row += "   <<< MISMATCH"
            print(row)
        print(f"  trio (independent): {e_trio}/{n}")
    print("=" * 92)
    print("VERDICT: " + ("MISMATCH FOUND -- a published number may be wrong"
                         if any_mismatch else
                         "all implementations agree on every parameter of every run checked"))
    return 1 if any_mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
