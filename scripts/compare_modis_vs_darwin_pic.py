"""Compare MODIS-Aqua observed PIC against Darwin v05 model PIC, per AOI.

The PR #63 paired-anchor sweep used Darwin v05's internal PIC field for the
`PIC_ABS_W` loss. That's fundamentally circular: Darwin v05 was calibrated
by Carroll's Green's functions optimizing the same Carroll-6 parameter
vector we're trying to recover. Anchoring DarwinDiff against Darwin v05 PIC
just re-discovers Darwin v05's biases.

MODIS-Aqua L3m PIC v2022.0 is an independent satellite observation. This
script quantifies the gap to set up a clean Phase 2.A integration:

    * Per-cell MODIS-Aqua PIC (2017-2019 mean) vs Darwin v05 PIC (whatever
      time period the bin_average covers, typically 1992-2017 mean).
    * Per-AOI summary statistics (mean, median, distribution).
    * The natlsubpolar/eqpac PIC ratio comparison (the 2-basin diagnosis
      hinged on this).

Usage::

    python scripts/compare_modis_vs_darwin_pic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make src/ importable without `pip install -e .`.
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import numpy as np
import torch

from darwindiff.ecco_darwin_loader import (
    AOI_BY_KEY,
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
)
from darwindiff.modis_pic_loader import (
    MOL_PER_M3_TO_MMOL_C_PER_M3,
    build_aoi_climatology,
)
from darwindiff.safe_load import safe_torch_load

MODIS_DIR = r"D:\modis_aqua_pic"
# Darwin v05 PIC comes from the LLC270 monthly cache the v3.0 runner already
# built; we read the pickled bundle directly to avoid re-binning from native
# LLC grid.
DARWIN_CACHE = {
    "eqpac": r"D:\ecco_darwin_v5\cache\eqpac_targets_equatorial_pacific.pt",
    "natlsubpolar": r"D:\ecco_darwin_v5\cache\eqpac_targets_north_atlantic_subpolar.pt",
}


def summarize(arr: np.ndarray, mask: np.ndarray, label: str) -> dict:
    v = arr[mask]
    if v.size == 0:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": int(v.size),
        "min": float(v.min()),
        "p05": float(np.percentile(v, 5)),
        "p25": float(np.percentile(v, 25)),
        "median": float(np.median(v)),
        "mean": float(v.mean()),
        "p75": float(np.percentile(v, 75)),
        "p95": float(np.percentile(v, 95)),
        "max": float(v.max()),
        "std": float(v.std()),
    }


def fmt(d: dict, unit: str) -> str:
    if d["n"] == 0:
        return f"{d['label']}: NO CELLS"
    return (
        f"{d['label']:30s}  n={d['n']:>5d}  "
        f"mean={d['mean']:.3e}  median={d['median']:.3e}  "
        f"p5={d['p05']:.3e}  p95={d['p95']:.3e}  ({unit})"
    )


def main() -> None:
    print("=" * 92)
    print("MODIS-Aqua observed PIC vs Darwin v05 model PIC")
    print("=" * 92)

    aois = {
        "eqpac": EQUATORIAL_PACIFIC_AOI,
        "natlsubpolar": NORTH_ATLANTIC_SUBPOLAR_AOI,
    }

    rows: dict[str, dict] = {}
    for key, aoi in aois.items():
        print(f"\n--- AOI: {key} ({aoi.lat_min}..{aoi.lat_max} N, {aoi.lon_min}..{aoi.lon_max} E) ---")

        # Darwin v05 PIC: the v3.0 runner already binned LLC270 PIC to 1° and
        # cached it. Load that bundle and grab the time-mean `pic_binned` field.
        cached = safe_torch_load(DARWIN_CACHE[key], map_location="cpu")
        darwin_pic_mean = np.asarray(cached["pic_binned"])  # (lat, lon)
        darwin_mask = np.isfinite(darwin_pic_mean) & (darwin_pic_mean > 0)
        darwin_summary = summarize(darwin_pic_mean, darwin_mask, f"Darwin v05 PIC ({key})")
        print(fmt(darwin_summary, "mmol C/m^3"))

        # MODIS-Aqua PIC 2017-2019 climatology, same AOI.
        modis_pic_mol_per_m3, modis_mask = build_aoi_climatology(MODIS_DIR, aoi)
        # Convert mol/m^3 -> mmol C/m^3 to align with Darwin's internal convention.
        modis_pic_mmol_c = modis_pic_mol_per_m3 * MOL_PER_M3_TO_MMOL_C_PER_M3
        modis_summary = summarize(modis_pic_mmol_c, modis_mask, f"MODIS-Aqua PIC 2017-2019 ({key})")
        print(fmt(modis_summary, "mmol C/m^3"))

        # Cell-by-cell ratio MODIS / Darwin where both are finite + positive.
        common_mask = darwin_mask & modis_mask
        if common_mask.any() and darwin_pic_mean.shape == modis_pic_mmol_c.shape:
            ratio = modis_pic_mmol_c[common_mask] / np.maximum(
                darwin_pic_mean[common_mask], 1e-12
            )
            print(
                f"\n  MODIS / Darwin per-cell ratio: n={ratio.size}, "
                f"mean={ratio.mean():.3f}, median={np.median(ratio):.3f}, "
                f"p5={np.percentile(ratio, 5):.3f}, p95={np.percentile(ratio, 95):.3f}"
            )
        elif darwin_pic_mean.shape != modis_pic_mmol_c.shape:
            print(
                f"\n  Grid shape mismatch (Darwin {darwin_pic_mean.shape} vs MODIS "
                f"{modis_pic_mmol_c.shape}); per-cell ratio skipped."
            )

        rows[key] = {"darwin": darwin_summary, "modis": modis_summary}

    # Cross-AOI ratios: the 2-basin diagnosis number.
    print("\n" + "=" * 92)
    print("Spatial PIC ratio (natlsubpolar / eqpac) — the 2-basin diagnostic")
    print("=" * 92)
    for src in ("darwin", "modis"):
        eq = rows["eqpac"][src]["mean"]
        nl = rows["natlsubpolar"][src]["mean"]
        ratio = nl / eq if eq > 0 else float("inf")
        print(f"  {src.upper():10s}: natlsubpolar={nl:.4e}, eqpac={eq:.4e}, ratio={ratio:.2f}x")

    print("\nWhy this matters:")
    print("  * PR #63 paired-anchor sweep used Darwin v05 PIC -> R_PICPOC unlock at 5/5 Cal")
    print("    but cost alpfe + diatomgraz. The cost is consistent with Darwin v05's PIC")
    print("    field over-emphasizing the natlsubpolar gradient that the model also has")
    print("    to fit elsewhere.")
    print("  * MODIS-Aqua PIC is an independent observation. If the observed spatial")
    print("    ratio is meaningfully different from Darwin v05's internal ratio, then")
    print("    anchoring DarwinDiff to MODIS instead of v05 should reduce the cost on")
    print("    alpfe + diatomgraz (it's a less aggressive PIC gradient to fit).")
    print("  * If the ratios are similar, MODIS PIC won't dissolve the mutex on its")
    print("    own; we'd need additional independent channels (e.g., PACE v3.2 PIC")
    print("    when shipped, or in-situ coccolithophore counts).")


if __name__ == "__main__":
    main()
