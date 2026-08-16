"""Build the v1 RESULTS MANIFEST: every quoted number resolved to its provenance.

WHY THIS EXISTS. This project's failure mode is not wrong numbers - it is numbers whose provenance
decays. Three instances are already on record:

  * `so_only/` is job 237913, the run that FAILED verify_run with exit 2, while the reportable arm
    is `so_only2/` (job 238079). Both give identical counts, so the mistake is invisible in the
    number itself.
  * 119 of 211 run dirs predate the collapse instrumentation and cannot be pooler-checked at all;
    `pooler_audit.py` prints `<absent>` and exits 2. Absent is UNKNOWN, not equal.
  * The AICR checkout drifted behind main and nothing in the artifact recorded which code ran.

So a version tag alone would freeze the ambiguity rather than remove it. The manifest is the part
that makes `v1.0-evidence` mean something: for each quoted number, WHERE it came from and WHETHER
its gates held.

WHAT IT EMITS, per run directory: the arm name, seed count and range, the recorded code provenance,
whether the collapse keys are present (i.e. whether it is pooler-auditable AT ALL), which loss terms
were declared active with their per-AOI cell counts, and the per-AOI recovered value for each
parameter under all three collapses.

It reads ONLY on-disk artifacts. It runs nothing and re-fits nothing.

Run:
    python scripts/analysis/build_results_manifest.py --runs <dir> [<dir> ...] --out manifest.json
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np

PARAMS = ["alpfe", "scav_rat", "R_PICPOC", "diatomgraz", "Smallgrow", "Biggrow"]
COLLAPSE = {
    "arithmetic": "per_aoi_recovered",
    "geometric": "per_aoi_recovered_geom",
    "median": "per_aoi_recovered_median",
}
# loss terms whose declared weight and realised cell counts decide whether a run
# is "the config it declares" (the inert-term check verify_run enforces)
TERMS = [
    ("daniels_rpicpoc_w", "n_daniels_cells_per_aoi"),
    ("posi_w", "n_posi_cells_per_aoi"),
    ("geotraces_w", "n_geo_surf_cells_per_aoi"),
    ("geotraces_sub_w", "n_geo_sub_cells_per_aoi"),
]


def scan(run_dir: str) -> dict | None:
    files = sorted(glob.glob(str(Path(run_dir) / "*.json")))
    seeds, recs = [], []
    for f in files:
        m = re.search(r"_seed(\d+)_", Path(f).name)
        if not m:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        seeds.append(int(m.group(1)))
        recs.append(d)
    if not recs:
        return None

    first = recs[0]
    prov = first.get("code_provenance") or {}

    # collapse-key presence: the gate that decides whether this run is auditable at all
    p0 = (first.get("params") or {}).get("alpfe") or {}
    has_geom = "per_aoi_recovered_geom" in p0
    has_med = "per_aoi_recovered_median" in p0
    has_logsd = "per_aoi_log_sd" in p0

    terms = {}
    for wkey, ckey in TERMS:
        w = first.get(wkey)
        cells = first.get(ckey)
        if w is None:
            continue
        entry = {"declared_weight": w, "cells_per_aoi": cells}
        if w and cells and isinstance(cells, dict):
            total = sum(v for v in cells.values() if isinstance(v, (int, float)))
            entry["INERT"] = bool(total == 0)
        terms[wkey] = entry

    # per-parameter recovered values under each collapse, medianed over seeds
    params: dict = {}
    for p in PARAMS:
        entry: dict = {}
        for cname, field in COLLAPSE.items():
            per_aoi: dict[str, list[float]] = {}
            for d in recs:
                v = ((d.get("params") or {}).get(p) or {}).get(field)
                if isinstance(v, dict):
                    for aoi, val in v.items():
                        per_aoi.setdefault(aoi, []).append(float(val))
            if per_aoi:
                entry[cname] = {a: float(np.median(v)) for a, v in per_aoi.items()}
        if entry:
            params[p] = entry

    return {
        "run_dir": run_dir,
        "n_seeds": len(seeds),
        "seed_range": [min(seeds), max(seeds)],
        "seeds_contiguous": sorted(seeds) == list(range(min(seeds), min(seeds) + len(seeds))),
        "aois": first.get("aois"),
        "n_epochs": first.get("n_epochs") or first.get("nb23_n_epochs"),
        "lr": first.get("lr"),
        "n_steps": first.get("n_steps"),
        "dinn_hidden_dim": first.get("dinn_hidden_dim"),
        "global_scalar": first.get("global_scalar"),
        "per_aoi_dinn": first.get("per_aoi_dinn"),
        "rpicpoc_anchor_source": first.get("rpicpoc_anchor_source", "<absent: pre-2026-08-12>"),
        "code_provenance": {
            "git_sha": prov.get("git_sha"), "git_dirty": prov.get("git_dirty"),
            "code_digest": prov.get("code_digest"), "config_digest": prov.get("config_digest"),
        },
        "pooler_auditable": bool(has_geom and has_med),
        "collapse_keys": {"geom": has_geom, "median": has_med, "log_sd": has_logsd},
        "declared_terms": terms,
        "params": params,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    manifest, skipped = [], []
    for r in args.runs:
        got = scan(r)
        (manifest.append(got) if got else skipped.append(r))

    print(f"{'run':38s} {'n':>4} {'seeds':>10} {'poolable':>9}  {'anchor':>8}  code")
    print("-" * 100)
    for m in manifest:
        sr = f"{m['seed_range'][0]}-{m['seed_range'][1]}"
        sha = (m["code_provenance"]["git_sha"] or "<absent>")[:9]
        src = m["rpicpoc_anchor_source"]
        src = src if not src.startswith("<absent") else "-"
        label = "/".join(Path(m["run_dir"]).parts[-2:])   # parent/name: so_only/so_only vs so_only2/so_only
        print(f"{label:38s} {m['n_seeds']:>4} {sr:>10} "
              f"{'YES' if m['pooler_auditable'] else 'NO':>9}  {src:>8}  {sha}")

    n_aud = sum(1 for m in manifest if m["pooler_auditable"])
    print(f"\n{len(manifest)} runs; pooler-auditable {n_aud}/{len(manifest)}; "
          f"skipped (no seed JSONs) {len(skipped)}")

    inert = [("/".join(Path(m["run_dir"]).parts[-2:]), k) for m in manifest
             for k, v in m["declared_terms"].items() if v.get("INERT")]
    if inert:
        print("\nDECLARED-BUT-INERT loss terms (verify_run's exit-2 condition):")
        for r, k in inert:
            print(f"  {r}: {k} declared non-zero with ZERO cells in every AOI")

    if args.out:
        Path(args.out).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
