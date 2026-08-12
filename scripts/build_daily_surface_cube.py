#!/usr/bin/env python3
r"""Build a time-resolved 1-degree cube from staged v05 DAILY surface files.

Turns ~208 GB of native LLC270 daily binaries into a ~15 GB co-registered cube,
which is what actually gets trained on. /scratch is on a 30-day purge, so the raw
tree is disposable and this artifact is not.

WHY THIS EXISTS RATHER THAN llc270_loader.bin_native_tracer_to_1deg
    That function is for MONTHLY 3-D tracers: it takes k=0 of a 50-level file and
    reduces over time with a mean. The daily archive is 2-D surface only, and the
    entire point here is to PRESERVE time -- a time-mean is what makes the growth
    pair unidentifiable in the first place.

WHY bincount RATHER THAN binned_statistic_2d
    `bin_to_1deg_grid` calls scipy's binned_statistic_2d, which recomputes the bin
    assignment on every call. xc/yc are FIXED across all 58,740 files, so the
    assignment is computed once here and reused via np.bincount. Same arithmetic
    (sum per bin / count per bin), roughly two orders of magnitude faster.

GRID CONVENTION
    Integer-degree centres, lat -90..89 and lon -180..179, matching the v05
    bin_average product so the cube stacks directly against its covariates. Note
    the existing "global 1 degree" emulator runs used bounds that produced 171 rows
    at 0.998538 deg spacing and were therefore NOT co-registered with bin_average
    or with any 1 deg satellite regrid; this does not repeat that.

TIME IS DERIVED FROM THE ITERATION NUMBER, NEVER FROM A STORED times_days
    day = iter * delta_t / 86400 with delta_t = 1200 s, which is confirmed by the
    files' own .meta (timeInterval = [1.2000E+03, 8.6400E+04]). The pre-2026-07-19
    cubes assumed 900 s, so their time axis was 0.75x truth, 94% of month-of-year
    bins were wrong, and a "~9-month useful horizon" had to be retracted. The
    regression check at the bottom of this file exists so that cannot recur.

USAGE
    python scripts/build_daily_surface_cube.py \
        --raw /scratch/qi_zim_neu/v05_daily/raw \
        --grid $HOME/emulator_poc/grid \
        --out /scratch/qi_zim_neu/v05_daily/cube \
        --vars surfChl1,surfChl2,surfChl3,surfChl4,surfChl5,SST
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import re
import sys
from pathlib import Path

import numpy as np

# LLC270 compact 2-D layout, from the daily files' own .meta:
#   dimList = [270, 1, 270 / 3510, 1, 3510]  ->  270 * 3510 = 947,700 cells
N_CELLS = 947_700
BYTES_PER_FILE = N_CELLS * 4          # float32, verified against content-length
DELTA_T = 1200.0                      # seconds, from .meta timeInterval
SECONDS_PER_DAY = 86_400.0
MODEL_START = dt.date(1992, 1, 1)     # stated as an assumption; see --model-start

# LAND IS ENCODED AS 0.0, NOT AS missingValue. The .meta advertises
# missingValue = -999, but not one cell in the staged archive carries it:
# measured on surfChl1.0000000144.data, `== -999` is 0 cells while `== 0.0` is
# 401,005 -- which matches Depth == 0 EXACTLY (401,005 land cells of 947,700).
# Filtering on -999 therefore masks nothing, and 401,005 land cells enter as
# "chlorophyll 0.0". That inflated the ocean-bin count to 64,493 of 64,800 (99.5%)
# against a true ~43,900 (67.8%), and would have dragged every spatial mean toward
# zero. Land MUST be masked from the grid's Depth field.
MISSING = -999.0                      # advertised in .meta; absent in practice

_ITER_RE = re.compile(r"\.(\d{10})\.data$")


def read_ocean_mask(grid_dir: Path) -> np.ndarray:
    """Ocean mask from the grid's Depth field. Depth > 0 is ocean.

    This is the ONLY correct land mask for this archive -- see the MISSING note
    above. Verified: Depth == 0 selects exactly the 401,005 cells that carry 0.0
    in the data.
    """
    p = grid_dir / "Depth.data"
    if not p.is_file():
        raise SystemExit(
            f"{p} missing. Depth is required to mask land: the daily files encode "
            "land as 0.0 rather than as missingValue, so without it 401,005 land "
            "cells are averaged in as real zeros.")
    d = np.fromfile(p, dtype=">f4")
    if d.size != N_CELLS:
        raise SystemExit(f"{p.name}: expected {N_CELLS} cells, got {d.size}")
    return d > 0


def read_grid(grid_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load native cell-centre longitude/latitude as flat [N_CELLS] arrays."""
    out = []
    for name in ("XC", "YC"):
        p = grid_dir / f"{name}.data"
        if not p.is_file():
            raise SystemExit(f"grid file missing: {p}")
        a = np.fromfile(p, dtype=">f4")          # MITgcm writes big-endian
        if a.size != N_CELLS:
            raise SystemExit(
                f"{p.name}: expected {N_CELLS} cells, got {a.size}. This is not an "
                "LLC270 compact 2-D grid file.")
        out.append(a.astype(np.float64))
    return out[0], out[1]


def build_bin_index(xc: np.ndarray, yc: np.ndarray,
                    lat_min: int, lat_max: int, lon_min: int, lon_max: int):
    """Precompute the flat destination bin for every native cell, once.

    Returns (flat_index, n_lat, n_lon, keep) where `keep` selects cells that fall
    inside the target grid. Cells outside are dropped rather than folded, so a
    wrapped longitude cannot silently contaminate an edge bin.
    """
    n_lat = lat_max - lat_min + 1
    n_lon = lon_max - lon_min + 1
    # integer-degree centres -> edges at centre +/- 0.5
    ilat = np.floor(yc - (lat_min - 0.5)).astype(np.int64)
    ilon = np.floor(xc - (lon_min - 0.5)).astype(np.int64)
    keep = (ilat >= 0) & (ilat < n_lat) & (ilon >= 0) & (ilon < n_lon)
    flat = np.full(xc.shape, -1, dtype=np.int64)
    flat[keep] = ilat[keep] * n_lon + ilon[keep]
    return flat, n_lat, n_lon, keep


def bin_one(values: np.ndarray, flat: np.ndarray, keep: np.ndarray,
            n_bins: int) -> np.ndarray:
    """Mean per bin via bincount. NaN where a bin received no valid cell.

    `keep` must already exclude land (see read_ocean_mask). Negative values are
    RETAINED: they are genuine model output and dropping them would bias the mean
    upward. Their fraction is reported by the caller as a diagnostic.
    """
    good = keep & np.isfinite(values) & (values != MISSING)
    idx = flat[good]
    v = values[good].astype(np.float64)
    s = np.bincount(idx, weights=v, minlength=n_bins)
    c = np.bincount(idx, minlength=n_bins)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return m


def iters_for(raw: Path, var: str) -> list[int]:
    its = []
    for f in glob.glob(str(raw / f"{var}.*.data")):
        m = _ITER_RE.search(os.path.basename(f))
        if m:
            its.append(int(m.group(1)))
    return sorted(its)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--grid", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--vars", required=True, help="comma-separated variable prefixes")
    ap.add_argument("--lat-min", type=int, default=-90)
    ap.add_argument("--lat-max", type=int, default=89)
    ap.add_argument("--lon-min", type=int, default=-180)
    ap.add_argument("--lon-max", type=int, default=179)
    ap.add_argument("--model-start", default="1992-01-01",
                    help="assumed model start; only affects the human-readable dates, "
                         "never the iteration-derived day index")
    ap.add_argument("--limit", type=int, default=0, help="first N iters only (smoke test)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    start = dt.date.fromisoformat(args.model_start)
    xc, yc = read_grid(args.grid)
    ocean = read_ocean_mask(args.grid)
    flat, n_lat, n_lon, inside = build_bin_index(
        xc, yc, args.lat_min, args.lat_max, args.lon_min, args.lon_max)
    keep = inside & ocean          # land excluded HERE, not by missingValue
    n_bins = n_lat * n_lon
    print(f"grid: {n_lat} x {n_lon} = {n_bins} bins", flush=True)
    print(f"native cells: {int(inside.sum())} inside grid, {int(ocean.sum())} ocean, "
          f"{int(keep.sum())} used ({N_CELLS - int(ocean.sum())} land excluded)",
          flush=True)

    for var in args.vars.split(","):
        var = var.strip()
        if not var:
            continue
        its = iters_for(args.raw, var)
        if args.limit:
            its = its[: args.limit]
        if not its:
            print(f"{var}: NO FILES, skipped", flush=True)
            continue
        # Time from the ITERATION NUMBER. Never from a stored times_days.
        days = np.array([i * DELTA_T / SECONDS_PER_DAY for i in its], dtype=np.float64)
        cube = np.full((len(its), n_lat, n_lon), np.nan, dtype=np.float32)
        # Per-timestep negative fraction, recorded rather than silently handled.
        # MEASURED on surfChl1 across the full record: 6.9-12.5% of ocean cells are
        # negative at EVERY sampled date, so this is not spin-up. Magnitude does
        # collapse after ~1000 days (min -2.985 at day 2 vs -0.013 at day 4932)
        # against a positive mean of 0.03-0.17, i.e. numerical undershoot in a
        # positive-definite tracer. This matters because log-space was a
        # load-bearing emulator fix and cannot be applied to a negative value, so
        # any consumer MUST decide how to clip -- and monthly averaging previously
        # hid the problem entirely.
        neg_frac = np.zeros(len(its), dtype=np.float32)
        neg_min = np.zeros(len(its), dtype=np.float32)
        for k, it in enumerate(its):
            p = args.raw / f"{var}.{it:010d}.data"
            sz = p.stat().st_size
            if sz != BYTES_PER_FILE:
                raise SystemExit(
                    f"{p.name}: {sz} bytes, expected {BYTES_PER_FILE}. Truncated "
                    "download -- refusing to build a cube from partial data.")
            a = np.fromfile(p, dtype=">f4").astype(np.float64)
            if k == 0:
                oc = a[keep]
                neg = int((oc < 0).sum())
                print(f"  {var}: first step diagnostic -- {neg}/{oc.size} ocean cells "
                      f"negative ({100.0*neg/max(oc.size,1):.1f}%), "
                      f"range [{oc.min():.4g}, {oc.max():.4g}]", flush=True)
            _oc = a[keep]
            neg_frac[k] = float((_oc < 0).sum()) / max(_oc.size, 1)
            neg_min[k] = float(_oc.min())
            cube[k] = bin_one(a, flat, keep, n_bins).reshape(n_lat, n_lon)
            if (k + 1) % 500 == 0:
                print(f"  {var}: {k+1}/{len(its)}", flush=True)
        dates = np.array([str(start + dt.timedelta(days=float(d))) for d in days])
        f = args.out / f"{var}_daily_1deg.npz"
        np.savez_compressed(
            f, data=cube, iters=np.asarray(its, dtype=np.int64), days=days, dates=dates,
            lat=np.arange(args.lat_min, args.lat_max + 1, dtype=np.float32),
            lon=np.arange(args.lon_min, args.lon_max + 1, dtype=np.float32),
            delta_t=np.float64(DELTA_T), model_start=str(start), variable=var,
            neg_frac_native=neg_frac, neg_min_native=neg_min,
            n_ocean_native=np.int64(int(keep.sum())),
        )
        ocean = int(np.isfinite(cube[0]).sum())
        print(f"{var}: {len(its)} steps, days {days[0]:.0f}..{days[-1]:.0f} "
              f"({dates[0]}..{dates[-1]}), {ocean} ocean bins, "
              f"{f.stat().st_size/1e9:.2f} GB -> {f.name}", flush=True)
        print(f"  {var}: negative-cell fraction median {np.median(neg_frac):.3f}, "
              f"max {neg_frac.max():.3f}; most-negative value {neg_min.min():.4g}",
              flush=True)

    # --- calendar regression check -------------------------------------------
    # delta_t MUST be 1200 s. At the retracted 900 s the day index is 0.75x truth,
    # which put 94% of month-of-year bins in the wrong month.
    assert DELTA_T == 1200.0, "delta_t must be 1200 s (see module docstring)"
    one_day_iters = int(round(SECONDS_PER_DAY / DELTA_T))
    assert one_day_iters == 72, f"one day must be 72 iters, got {one_day_iters}"
    print("calendar check OK: delta_t=1200 s, 72 iters/day")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
