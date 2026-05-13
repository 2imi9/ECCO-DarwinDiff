"""Aggregate v2.7 multilayer experiment JSONs into a seed-averaged summary.

Reads all ``run_v2.7_multilayer_result_*.json`` files in ``scripts/`` and
prints per-parameter recovery statistics across seeds at each (surf_w,
sub_w) configuration.

Run:
    python scripts/analyze_v2.7_results.py [--config surf=0.3,sub=0.3]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent

PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
CARROLL = {
    "alpfe": 0.928309977054596,
    "scav_rat": 6.025023253641848e-07,
    "Smallgrow": 0.6609799861907959,
    "Biggrow": 0.4314799904823303,
    "diatomgraz": 0.8300300240516663,
    "R_PICPOC": 0.04244999960064888,
}


def band_of(rel_offset: float) -> str:
    if rel_offset <= 0.05:
        return "Excellent"
    if rel_offset <= 0.40:
        return "Cal-grade"
    if rel_offset <= 0.80:
        return "Loose"
    return "Drifted"


def load_results() -> list[dict]:
    out = []
    for f in sorted(SCRIPTS.glob("run_v2.7_multilayer_result_*.json")):
        try:
            with f.open("r", encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception as e:
            print(f"  [warn] skip {f.name}: {e}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="filter to a single config, e.g. 'surf=0.3,sub=0.3'",
    )
    args = parser.parse_args()

    results = load_results()
    print(f"Loaded {len(results)} v2.7 result JSONs from {SCRIPTS}")

    config_filter = None
    if args.config:
        config_filter = dict(
            kv.split("=") for kv in args.config.split(",")
        )
        config_filter = {k: float(v) for k, v in config_filter.items()}
        print(f"Filtering to config: {config_filter}")

    # Group by (surf_w, sub_w, pinn_w)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in results:
        key = (r["geotraces_w"], r["geotraces_sub_w"], r["pinn_w"])
        if config_filter is not None:
            if (config_filter.get("surf") not in (None, r["geotraces_w"])
                    or config_filter.get("sub") not in (None, r["geotraces_sub_w"])):
                continue
        groups[key].append(r)

    for (surf_w, sub_w, pinn_w), runs in sorted(groups.items()):
        print(
            f"\n=== Config: surface_w={surf_w}, subsurface_w={sub_w}, pinn_w={pinn_w} | "
            f"n_seeds={len(runs)} ==="
        )
        seeds = sorted(r["seed"] for r in runs)
        print(f"Seeds: {seeds}")
        print(f"{'Param':<12s} {'mean':>12s} {'std':>12s} {'rel_off':>10s} "
              f"{'band':<12s} {'Cal/Exc rate':>14s}")
        for name in PARAM_NAMES:
            recovered = np.array([r["params"][name]["recovered"] for r in runs])
            mean = recovered.mean()
            std = recovered.std()
            carroll = CARROLL[name]
            rel_mean = abs(mean - carroll) / abs(carroll)
            n_cal = sum(1 for r in runs if r["params"][name]["band"] in ("Excellent", "Cal-grade"))
            n_exc = sum(1 for r in runs if r["params"][name]["band"] == "Excellent")
            print(
                f"{name:<12s} {mean:>12.4e} {std:>12.4e} {rel_mean:>10.4f} "
                f"{band_of(rel_mean):<12s} {f'{n_cal}/{len(runs)} ({n_exc} Exc)':>14s}"
            )

        # Overall verdict distribution
        verdict_counts = defaultdict(int)
        for r in runs:
            n_cal = r.get("n_cal_grade", 0)
            verdict_counts[n_cal] += 1
        print(f"\nCal-grade count distribution (out of 6):")
        for k in sorted(verdict_counts, reverse=True):
            print(f"  {k}/6: {verdict_counts[k]} seeds")


if __name__ == "__main__":
    main()
