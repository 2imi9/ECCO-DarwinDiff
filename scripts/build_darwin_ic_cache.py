"""Build a cached Darwin v5 initial-condition NPZ for the v2.7 box model.

Reads the pickup_ptracers.0000000001 file (LLC270 native, 31 records of
float64 big-endian, 50 levels x 3510 x 270 each) and extracts the 5
inorganic tracers the box-model state needs: DIC, FeT, POC, PIC, ALK.

For each tracer:
  - Compute depth-weighted mean over L1 (levels 0-4, 0-50 m)
  - Compute depth-weighted mean over L2 (levels 5-28, 50-1056 m)
  - Mask to Equatorial Pacific AOI (-5 to 15 N, -160 to -110 E)
  - Bin native cells to 1 deg via the existing scipy bin_to_1deg_grid

The phyto biomass IC for the box model's 5 PFTs is left to literature
defaults (handled in the runner) because: (a) the Darwin 7-PFT -> box 5-PFT
mapping requires data.traits to disambiguate which c-tracer maps to which
group, and (b) phyto biomass equilibrates fast under the integrator so
the IC matters much less than the inorganic anchors.

Result: scripts/darwin_ic_cache.npz with 10 fields (5 tracers x 2 layers),
each shape (n_lat=21, n_lon=51) for the Equatorial Pacific AOI.

Run once; ~30 sec wall clock for 5 tracers x 11 GB pickup.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    MID_ATLANTIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
    NORTH_PACIFIC_AOI,
)
from darwindiff.llc270_loader import bin_to_1deg_grid

_AOI_MAP = {
    "eqpac": EQUATORIAL_PACIFIC_AOI,
    "natlsubpolar": NORTH_ATLANTIC_SUBPOLAR_AOI,
    "midatl": MID_ATLANTIC_AOI,
    "npac": NORTH_PACIFIC_AOI,
}

# --- Paths --------------------------------------------------------------------

DARWIN_ROOT = Path(r"D:\ecco_darwin_v5")
PICKUP_PATH = DARWIN_ROOT / "input" / "darwin_initial_conditions" / "pickup_ptracers.0000000001.data"
GRID_DIR = DARWIN_ROOT / "grid"
import os as _os
_CACHE_NAME = _os.environ.get("CACHE_NAME", "darwin_ic_cache.npz")
CACHE_PATH = _HERE / _CACHE_NAME

# --- Pickup file layout (from .meta) ------------------------------------------

NX, NY, NZ = 270, 3510, 50
N_RECORDS = 31
DTYPE = np.dtype(">f8")  # MITgcm pickup: float64 big-endian
BYTES_PER_RECORD = NX * NY * NZ * DTYPE.itemsize  # 378_840_000

# --- Tracer indices (0-indexed, from v05 data.ptracers fldList) ---------------
# pTr01..pTr31 -> DIC, NO3, NO2, NH4, PO4, FeT, SiO2, DOC, DON, DOP, DOFe,
#                 POC, PON, POP, POFe, POSi, PIC, ALK, O2, c01..c07, Chl01..Chl05.
INORGANIC_TRACERS = {
    "DIC": 0,    # pTr01
    "FeT": 5,    # pTr06
    "POC": 11,   # pTr12
    "PIC": 16,   # pTr17
    "ALK": 17,   # pTr18
}

# --- Depth windows for box-model 2-layer split --------------------------------

L1_LEVELS = slice(0, int(_os.environ.get("L1_STOP", "5")))
# Env-var override for the L2 window (defaults to 50-1056 m via levels 5..28).
# Narrow upper-twilight window for scav_rat sensitivity: L2_START=5, L2_STOP=17 (50-207 m).
L2_LEVELS = slice(int(_os.environ.get("L2_START", "5")), int(_os.environ.get("L2_STOP", "29")))


def read_grid_field(name: str, dtype: str = ">f4") -> np.ndarray:
    """Read a 2-D native LLC270 grid field (XC/YC) from {GRID_DIR}/{name}.data."""
    path = GRID_DIR / f"{name}.data"
    arr = np.fromfile(path, dtype=np.dtype(dtype))
    return arr.reshape(NY, NX)


def read_drf() -> np.ndarray:
    """Read the 50-level vertical layer thicknesses (m)."""
    drf = np.fromfile(GRID_DIR / "DRF.data", dtype=">f4")
    if drf.shape != (NZ,):
        raise ValueError(f"DRF unexpected shape {drf.shape}, expected ({NZ},)")
    return drf.astype(np.float64)


def read_tracer_record(mm: np.memmap, record_idx: int) -> np.ndarray:
    """Read one tracer record from the pickup memmap. Returns (NZ, NY, NX) float64."""
    if record_idx < 0 or record_idx >= N_RECORDS:
        raise IndexError(f"record_idx {record_idx} out of range [0, {N_RECORDS})")
    start = record_idx * NZ * NY * NX
    stop = start + NZ * NY * NX
    block = mm[start:stop].reshape(NZ, NY, NX)
    # The memmap is read-only; cast to native float64 once for arithmetic.
    return block.astype(np.float64, copy=False)


def depth_weighted_mean(volume: np.ndarray, drf: np.ndarray, levels: slice) -> np.ndarray:
    """Depth-weighted vertical mean over `levels`.

    `volume` is (NZ, NY, NX) with MITgcm land-fill 0.0 on dry cells.
    We treat 0.0 as missing for the weighting (land + bottom topography),
    so the mean is over the wet column only at each (y, x).
    """
    sub = volume[levels]              # (n_lev, NY, NX)
    wts_1d = drf[levels]              # (n_lev,)
    wts = wts_1d[:, None, None]       # broadcast to (n_lev, 1, 1)
    wet = (sub != 0.0).astype(np.float64)
    num = (sub * wet * wts).sum(axis=0)
    den = (wet * wts).sum(axis=0).clip(min=1e-30)
    out = num / den
    # Cells that were dry across the whole window get 0 (will be masked downstream
    # by AOI + non-zero filter).
    return out


def main():
    aoi_key = _os.environ.get("DARWIN_AOI", "eqpac")
    if aoi_key not in _AOI_MAP:
        raise ValueError(f"DARWIN_AOI={aoi_key!r} not in {sorted(_AOI_MAP)}")
    aoi = _AOI_MAP[aoi_key]
    print(f"=== Build Darwin v5 IC cache ===")
    print(f"  Pickup : {PICKUP_PATH}")
    print(f"  Grid   : {GRID_DIR}")
    print(f"  AOI    : {aoi.name} ({aoi.lat_min}..{aoi.lat_max} N, "
          f"{aoi.lon_min}..{aoi.lon_max} E)")
    print(f"  Output : {CACHE_PATH}")

    if not PICKUP_PATH.is_file():
        raise FileNotFoundError(f"pickup not found: {PICKUP_PATH}")
    pickup_size = PICKUP_PATH.stat().st_size
    expected_size = N_RECORDS * BYTES_PER_RECORD
    if pickup_size != expected_size:
        raise ValueError(
            f"pickup size mismatch: got {pickup_size}, expected {expected_size} "
            f"({N_RECORDS} records x {BYTES_PER_RECORD} bytes/record)"
        )

    print(f"  Pickup size  : {pickup_size / 1024**3:.2f} GB ({N_RECORDS} records)")

    print("\nLoading grid (XC, YC, DRF)...")
    xc = read_grid_field("XC", dtype=">f4")  # (NY, NX) deg lon
    yc = read_grid_field("YC", dtype=">f4")  # (NY, NX) deg lat
    drf = read_drf()                          # (NZ,) m
    print(f"  XC dtype={xc.dtype} shape={xc.shape}  range [{xc.min():.1f}, {xc.max():.1f}]")
    print(f"  YC dtype={yc.dtype} shape={yc.shape}  range [{yc.min():.1f}, {yc.max():.1f}]")
    print(f"  L1 window (0-50 m): levels {L1_LEVELS.start}..{L1_LEVELS.stop - 1}, sum_dz = {drf[L1_LEVELS].sum():.1f} m")
    print(f"  L2 window (50-1056 m): levels {L2_LEVELS.start}..{L2_LEVELS.stop - 1}, sum_dz = {drf[L2_LEVELS].sum():.1f} m")

    aoi_mask_native = (
        (yc >= aoi.lat_min) & (yc <= aoi.lat_max)
        & (xc >= aoi.lon_min) & (xc <= aoi.lon_max)
    )
    n_aoi = int(aoi_mask_native.sum())
    print(f"  AOI native cells: {n_aoi}")

    print(f"\nOpening pickup as memmap ({pickup_size / 1024**3:.2f} GB)...")
    mm = np.memmap(PICKUP_PATH, dtype=DTYPE, mode="r")

    fields = {}
    overall_start = time.time()
    for tracer_name, rec_idx in INORGANIC_TRACERS.items():
        t0 = time.time()
        print(f"\n[{tracer_name}] reading record {rec_idx} (offset {rec_idx * BYTES_PER_RECORD / 1024**3:.2f} GB)...")
        vol = read_tracer_record(mm, rec_idx)
        print(f"  vol stats : min={vol.min():.3g} max={vol.max():.3g} mean(nonzero)={vol[vol != 0].mean():.3g}")

        for layer_name, levels in (("L1", L1_LEVELS), ("L2", L2_LEVELS)):
            depth_mean = depth_weighted_mean(vol, drf, levels)
            aoi_good = aoi_mask_native & np.isfinite(depth_mean) & (depth_mean != 0)
            n_good = int(aoi_good.sum())
            binned = bin_to_1deg_grid(
                xc[aoi_good], yc[aoi_good], depth_mean[aoi_good],
                aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max,
            )
            key = f"{tracer_name}_{layer_name}"
            fields[key] = binned
            nan_frac = float(np.isnan(binned).mean())
            print(f"  {layer_name}: native_cells={n_good}  binned shape={binned.shape}  "
                  f"mean={np.nanmean(binned):.4g}  nan_frac={nan_frac:.2%}")
        print(f"  elapsed: {time.time() - t0:.1f}s")

    print(f"\nTotal extraction time: {time.time() - overall_start:.1f}s")

    print(f"\nSaving cache to {CACHE_PATH}")
    np.savez_compressed(
        CACHE_PATH,
        lat_min=np.float64(aoi.lat_min),
        lat_max=np.float64(aoi.lat_max),
        lon_min=np.float64(aoi.lon_min),
        lon_max=np.float64(aoi.lon_max),
        timestep=np.int64(78912),
        l1_levels_start=np.int32(L1_LEVELS.start),
        l1_levels_stop=np.int32(L1_LEVELS.stop),
        l2_levels_start=np.int32(L2_LEVELS.start),
        l2_levels_stop=np.int32(L2_LEVELS.stop),
        **{k: v.astype(np.float64) for k, v in fields.items()},
    )
    print(f"  saved {len(fields)} fields ({CACHE_PATH.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
