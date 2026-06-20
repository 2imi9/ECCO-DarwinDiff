"""Measure the cell-count inputs to the AICR compute budget on the 5090.

Cheap + stable: loads ONE native LLC270 monthly tracer (a load + mask + count,
no autograd / no training loop), counts ocean cells globally and per AOI, then
prints the memory + B200-count budget from the MEASURED 356 B/(cell-step)
constant. These cell counts were the estimates in
``docs/research_notes/2026-06-19_aicr_memory_budget.md`` (§6).

It deliberately does NOT run the native/global fit itself — that one is slow and
unstable to test on the laptop, so its memory is extrapolated from the measured
constant x the (now measured) cell counts. eqpac is the self-check: it should
reproduce the 9,750 from notebook 14.

Run:  .venv/Scripts/python.exe scripts/measure_compute_budget.py
Env:  DARWIN_DATA_ROOT (default D:\\ecco_darwin_v5)
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np

from darwindiff.llc270_loader import open_llc270_tracer, aoi_mask_from_xc_yc
from darwindiff.ecco_darwin_loader import AOI_BY_KEY

ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
MONTHLY = ROOT / "output" / "monthly"
GRID = ROOT / "grid"

CONST = 356.0          # B per (cell-step), measured eager (pre_scaleup_verification.md:41)
R5090, H200, B200 = 24, 144, 192   # GiB usable per card
AOIS = ["eqpac", "natlsubpolar", "southernoceanpac"]


def pick_var() -> str:
    for v in ("FeT", "NO3", "ALK", "DIC", "POC"):
        if (MONTHLY / v).is_dir():
            return v
    raise FileNotFoundError(f"no known tracer dir under {MONTHLY}")


def count_cells():
    var = pick_var()
    print(f"loading native LLC270 {var} (first month) from {MONTHLY} ...", flush=True)
    ds = open_llc270_tracer(str(MONTHLY), str(GRID), var, iters="first")
    surf = ds[var].isel(time=0, k=0)
    vals = np.asarray(surf.values)
    xc = np.asarray(ds["XC"].values)
    yc = np.asarray(ds["YC"].values)
    ocean = np.isfinite(vals) & (vals != 0.0)
    glob = int(ocean.sum())
    print(f"global native ocean cells (surface, {var}!=0): {glob:,}")
    per = {}
    for k in AOIS:
        a = AOI_BY_KEY[k]
        m = np.asarray(aoi_mask_from_xc_yc(xc, yc, a.lat_min, a.lat_max, a.lon_min, a.lon_max))
        per[k] = int((m & ocean).sum())
        print(f"  {k:18s} native ocean cells: {per[k]:,}")
    tot = sum(per.values())
    print(f"  3-AOI native total: {tot:,}")
    print(f"  [self-check] eqpac should be ~9,750 (notebook 14): "
          f"{'OK' if abs(per['eqpac'] - 9750) < 300 else 'MISMATCH — check ocean mask def'}")
    return glob, per, tot


def gib(cells: int, steps: int, batch: int) -> float:
    return CONST * cells * steps * batch / 2**30


def machine(g: float) -> str:
    if g <= R5090:
        return "5090 (now)"
    if g <= H200:
        return "H200 (free)"
    if g <= B200:
        return "1x B200"
    return f"{math.ceil(g / B200)}x B200"


def budget(cells: int, label: str):
    print(f"\n{label}  ({cells:,} cells)")
    for steps, sname in ((200, "time-mean"), (2000, "seasonal")):
        for b in (1, 10):
            g = gib(cells, steps, b)
            n_b200 = 0 if g <= H200 else math.ceil(g / B200)
            print(f"  {sname:9s} b{b:<2d}  {g:9.1f} GiB  ->  {machine(g):12s}  B200 = {n_b200}")


if __name__ == "__main__":
    glob, per, tot = count_cells()
    print("\n=== BUDGET from measured 356 B/(cell-step) ===")
    print("(<=24 GiB fits the 5090; <=144 the free Explorer H200; B200 count = ceil(GiB/192))")
    budget(per["eqpac"], "1-AOI native (eqpac)")
    budget(tot, "3-AOI native (the near-term ask)")
    budget(glob, "global LLC270 native (surface ocean)")
    print("\nNote: checkpointing (5-15x, unmeasured) divides every GiB above; "
          "LLC90 wet + native wall-clock are the remaining unmeasured inputs.")
