"""Add primprod_binned (Darwin PP, time-mean, 1deg) to the 3 AOI target caches.

PRIMPROD_W needs a primProd target, but the cluster v05 staging lacks the primProd
monthly field. Local has it, so bin it here (reusing the runner's exact call) and add
the field to each target cache; ship the caches to the cluster. Other cache fields are
untouched (only primprod_binned is added). Idempotent.

Run:  uv run python scripts/build_primprod_cache.py
"""

from __future__ import annotations

import os
from pathlib import Path

import torch

from darwindiff.ecco_darwin_loader import AOI_BY_KEY
from darwindiff.llc270_loader import bin_native_tracer_to_1deg

ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
MONTHLY = ROOT / "output" / "monthly"
GRID = ROOT / "grid"
CACHE = ROOT / "cache"
KEYS = ["eqpac", "natlsubpolar", "southernoceanpac"]


def main() -> int:
    for k in KEYS:
        aoi = AOI_BY_KEY[k]
        cp = CACHE / f"eqpac_targets_{aoi.name.replace(' ', '_').lower()}.pt"
        c = torch.load(cp, weights_only=False)
        if "primprod_binned" in c:
            print(f"{k}: already has primprod_binned {c['primprod_binned'].shape}")
            continue
        c["primprod_binned"] = bin_native_tracer_to_1deg(
            monthly_root=MONTHLY, grid_dir=GRID, variable="primProd",
            lat_min=aoi.lat_min, lat_max=aoi.lat_max,
            lon_min=aoi.lon_min, lon_max=aoi.lon_max, iters="all",
        )
        torch.save(c, cp)
        import numpy as np
        pp = c["primprod_binned"]
        print(f"{k}: added primprod_binned shape={pp.shape} "
              f"mean(finite)={float(np.nanmean(pp)):.4g} -> saved {cp.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
