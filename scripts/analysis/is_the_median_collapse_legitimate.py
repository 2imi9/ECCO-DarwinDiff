"""Is a per-AOI MEDIAN collapse legitimate for a sparsely-anchored parameter, or an artifact?

THE GATE. The Marsh Southern Ocean anchor (12 of 1296 cells, 0.9%) gave R_PICPOC 43/50 under the
median collapse, 6/50 geometric, 0/50 arithmetic (job 354596). Until we know whether 43/50 is a
measurement or a collapse artifact, that number cannot be quoted. `pooler_audit.py` exists because
the arithmetic collapse was caught manufacturing scav_rat recovery; the same scepticism has to be
applied to the median before it is used in our favour.

THE MECHANISM AT ISSUE. With a sparse anchor, the per-cell recovered field splits into two
populations: ~12 ANCHORED cells pulled toward the observation, and ~1284 UNANCHORED cells that stay
wherever the network's prior/initialisation puts them. A median over such a field reports the
MAJORITY population. So the question is sharp and decidable:

    does the median track the ANCHORED cells (a real local measurement),
    or does it track the UNANCHORED majority (an artifact that would move with the prior)?

If the median reports the unanchored majority, then 43/50 says nothing about calcite - it says the
untrained prior happens to sit inside the +/-40% band. That is exactly the diatomgraz trap
(prior midpoint at rel 0.3675, inside the band, so an untrained net scores 50/50).

THE DECISIVE CHECK, and it needs no new run. The untrained null arm IS the unanchored population:
it is the same architecture at initialisation with no training at all. So:

  * if the anchored arm's median is close to the NULL's median -> the median is reporting the
    prior, and 43/50 is an artifact of where the prior sits;
  * if the anchored arm's median has MOVED away from the null and toward the observed value
    (Marsh SO geomean 0.0489, Carroll 0.04245) -> the median is tracking real information.

Also reports the arithmetic and geometric centres for the same arms, so the three collapses can be
compared on identical fits.

Run: python scripts/analysis/is_the_median_collapse_legitimate.py --run <dir> --null <dir> [...]
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np

CARROLL_RPICPOC = 0.04245
MARSH_SO_GEOMEAN = 0.0489   # measured by the runner: 12 cells, 42 samples
BAND = 0.40


def collect(run_dir: str, param: str = "R_PICPOC") -> dict[str, np.ndarray]:
    """Per-seed recovered value under each available collapse."""
    fields = {
        "arithmetic": "per_aoi_recovered",
        "geometric": "per_aoi_recovered_geom",
        "median": "per_aoi_recovered_median",
    }
    out: dict[str, list[float]] = {k: [] for k in fields}
    for f in sorted(glob.glob(str(Path(run_dir) / "*.json"))):
        if not re.search(r"_seed(\d+)_", Path(f).name):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        e = (d.get("params") or {}).get(param) or {}
        for k, fld in fields.items():
            v = e.get(fld)
            if isinstance(v, dict):          # per-AOI dict; single-AOI runs have one entry
                v = list(v.values())[0] if v else None
            if v is not None:
                out[k].append(float(v))
    return {k: np.array(v) for k, v in out.items() if v}


def summarize(name: str, vals: np.ndarray) -> dict:
    med = float(np.median(vals))
    rel = abs(med - CARROLL_RPICPOC) / CARROLL_RPICPOC
    return {
        "arm": name, "n": int(vals.size), "median": med,
        "median_over_carroll": med / CARROLL_RPICPOC,
        "rel_offset": rel, "in_band": bool(rel <= BAND),
        "iqr": [float(np.percentile(vals, 25)), float(np.percentile(vals, 75))],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="anchored (trained) arm")
    ap.add_argument("--control", default=None, help="unanchored trained arm")
    ap.add_argument("--null", required=True, help="untrained null = the unanchored population")
    ap.add_argument("--param", default="R_PICPOC")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    arms = {"anchored": args.run, "null(untrained)": args.null}
    if args.control:
        arms["unanchored(trained)"] = args.control

    print(f"Parameter: {args.param}   Carroll = {CARROLL_RPICPOC}")
    print(f"Observed Marsh SO geomean = {MARSH_SO_GEOMEAN} "
          f"({MARSH_SO_GEOMEAN/CARROLL_RPICPOC:.3f}x Carroll)\n")

    report = {}
    for label, d in arms.items():
        got = collect(d, args.param)
        if not got:
            print(f"[skip] {label}: no {args.param} values in {d}")
            continue
        print(f"=== {label} ===")
        report[label] = {}
        for collapse, vals in got.items():
            s = summarize(label, vals)
            report[label][collapse] = s
            print(f"  {collapse:12s} n={s['n']:3d}  median={s['median']:.5f} "
                  f"({s['median_over_carroll']:6.3f}x Carroll)  rel={s['rel_offset']:.3f}  "
                  f"{'IN band' if s['in_band'] else 'out of band'}")
        print()

    # THE DECISIVE COMPARISON
    a = report.get("anchored", {})
    n = report.get("null(untrained)", {})
    if a and n:
        print("DECISIVE: does the anchored median MOVE away from the untrained prior?\n")
        for collapse in a:
            if collapse not in n:
                continue
            am, nm = a[collapse]["median"], n[collapse]["median"]
            if nm == 0:
                continue
            move = abs(np.log(am / nm)) if (am > 0 and nm > 0) else float("nan")
            toward = "TOWARD Carroll" if abs(am - CARROLL_RPICPOC) < abs(nm - CARROLL_RPICPOC) \
                else "AWAY from Carroll"
            verdict = ("REAL INFORMATION" if move > 0.10 and toward.startswith("TOWARD")
                       else "REPORTS THE PRIOR - artifact risk")
            print(f"  {collapse:12s} anchored {am:.5f} vs untrained {nm:.5f}   "
                  f"|dln|={move:.3f}   {toward}   -> {verdict}")

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
