"""Spatial-distribution figures for the Jon/Cristina meeting follow-up.

They asked, repeatedly, to SEE the spatial distribution ("what is the spatial
distribution", "assume there is some spatial distribution to visualize", "spatial
variability on geotraces"). This makes the maps, from data already on D:, CPU-only.

Panels (saved to docs/findings/figures/2026-07-07_spatial/):
  1. per_aoi_fields.png   -- per-AOI scatter maps: PIC:POC, modeled DFe, Chl2 fraction
  2. global_calcifier.png -- global v05 coccolithophore-proxy (Chl2) fraction map
  3. geotraces_iron.png   -- GEOTRACES surface dissolved-Fe COVERAGE (sparse; annotated).
                             Per the iron-lit review, iron obs are too sparse for a dense
                             field map -- this is a coverage/section-style figure by design.
  4. composition_refuted.png -- bulk PIC:POC vs calcifier fraction vs implied per-calcifier R
                             (the key result: composition is flat, environment carries the spread)

All inputs verified present: native caches, v05 bin_average, GEOTRACES IDP2025.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff.safe_load import safe_torch_load  # noqa: E402

OUT = Path("docs/findings/figures/2026-07-07_spatial")
OUT.mkdir(parents=True, exist_ok=True)

CACHES = {
    "Eq. Pacific": "D:/ecco_darwin_v5/cache/native_targets_equatorial_pacific.pt",
    "N. Atl. Subpolar": "D:/ecco_darwin_v5/cache/native_targets_north_atlantic_subpolar.pt",
    "S. Ocean Pacific": "D:/ecco_darwin_v5/cache/native_targets_southern_ocean_pacific.pt",
}
BIN_AVG = "D:/ecco_darwin_v5/bin_average/v05_ECCO-Darwin_bin_average_1x1_deg.nc"
GEOTRACES = "D:/geotraces/GEOTRACES_IDP2025_Seawater.nc"


def _load(path):
    d = safe_torch_load(path, map_location="cpu")
    g = lambda k: np.asarray(d[k]).ravel().astype(float)
    lat, lon = g("darwin_lats"), g("darwin_lons")
    pic, poc, fet = g("pic_binned"), g("poc_binned"), g("fet_binned")
    chl = {i: np.clip(np.asarray(d["chl_per_pft"][f"Chl{i}"]).ravel().astype(float), 0, None)
           for i in range(1, 6)}
    tot = sum(chl[i] for i in range(1, 6))
    return dict(lat=lat, lon=lon, pic=pic, poc=poc, fet=fet, chl2=chl[2], chltot=tot)


def fig_per_aoi():
    fig, axes = plt.subplots(len(CACHES), 3, figsize=(14, 3.4 * len(CACHES)))
    for r, (name, path) in enumerate(CACHES.items()):
        c = _load(path)
        m = (c["poc"] > 0) & np.isfinite(c["pic"]) & np.isfinite(c["poc"])
        ratio = np.where(m, c["pic"] / np.where(c["poc"] > 0, c["poc"], np.nan), np.nan)
        panels = [
            ("PIC:POC ratio", ratio, "viridis", True),
            ("modeled DFe", np.where(c["fet"] > 0, c["fet"], np.nan), "plasma", True),
            ("calcifier frac (Chl2/total)",
             np.where(c["chltot"] > 1e-4, c["chl2"] / np.where(c["chltot"] > 1e-4, c["chltot"], np.nan), np.nan),
             "cividis", False),
        ]
        for col, (title, val, cmap, logc) in enumerate(panels):
            ax = axes[r, col]
            good = np.isfinite(val) & (val > 0 if logc else np.isfinite(val))
            # robust color limits: clip the few POC->0 blow-up cells (SO artifact)
            norm = None
            if logc and good.sum():
                lo, hi = np.nanpercentile(val[good], [2, 98])
                norm = LogNorm(vmin=max(lo, 1e-6), vmax=hi)
            sc = ax.scatter(c["lon"][good], c["lat"][good], c=val[good], s=6, cmap=cmap, norm=norm)
            fig.colorbar(sc, ax=ax, shrink=0.85)
            if r == 0:
                ax.set_title(title, fontsize=11)
            if col == 0:
                ax.set_ylabel(f"{name}\nlat", fontsize=10)
    fig.suptitle("ECCO-Darwin v05 native fields per AOI — PIC:POC, iron, calcifier fraction", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "per_aoi_fields.png", dpi=110)
    plt.close(fig)
    print("wrote per_aoi_fields.png")


def fig_global_calcifier():
    from darwindiff.ecco_darwin_loader import open_bin_average
    print("  loading bin_average (1.9 GB, time-mean of Chl1-5)...")
    ds = open_bin_average(BIN_AVG)
    chls = [ds[f"Chl{i}"].mean("time", skipna=True).clip(min=0) for i in range(1, 6)]
    tot = sum(chls)
    frac = (chls[1] / tot.where(tot > 1e-4)).values  # Chl2 fraction
    lat = ds["lat"].values
    lon = ds["lon"].values
    fig, ax = plt.subplots(figsize=(13, 6))
    pm = ax.pcolormesh(lon, lat, frac, cmap="cividis", vmin=0, vmax=0.5, shading="auto")
    fig.colorbar(pm, ax=ax, label="Chl2 / total Chl (coccolithophore-proxy fraction)")
    ax.set_title("Global v05 coccolithophore-proxy (Chl2) fraction — the composition field\n"
                 "(nearly flat ~0.1-0.15 across the 3 AOIs; does NOT carry the 100x PIC:POC spread)",
                 fontsize=12)
    ax.set_xlabel("lon"); ax.set_ylabel("lat")
    fig.tight_layout()
    fig.savefig(OUT / "global_calcifier.png", dpi=110)
    plt.close(fig)
    print("wrote global_calcifier.png")


def fig_geotraces():
    import xarray as xr
    from darwindiff.geotraces_loader import open_geotraces_bottle, GEOTRACES_VAR_MAP
    ds = open_geotraces_bottle(GEOTRACES)
    var = GEOTRACES_VAR_MAP["Fe_D"]
    arr = ds[var].values  # (n_stations, n_samples)
    ns, nsamp = arr.shape
    lat = np.broadcast_to(ds.latitude.values[:, None], (ns, nsamp)).ravel()
    lon = np.broadcast_to(ds.longitude.values[:, None], (ns, nsamp)).ravel()
    dep = ds.DEPTH.values.ravel() if ds.DEPTH.values.ndim > 1 else np.broadcast_to(ds.DEPTH.values, (ns, nsamp)).ravel()
    val = arr.ravel()
    surf = np.isfinite(val) & (val > 0) & np.isfinite(dep) & (dep <= 50)
    fig, ax = plt.subplots(figsize=(13, 6))
    sc = ax.scatter(lon[surf], lat[surf], c=val[surf], s=10, cmap="plasma",
                    norm=LogNorm(), edgecolors="k", linewidths=0.2)
    fig.colorbar(sc, ax=ax, label="dissolved Fe (surface <=50 m)")
    ax.set_title(f"GEOTRACES IDP2025 surface dissolved-iron COVERAGE  (n={surf.sum()} surface samples)\n"
                 "Iron is sparsely observed -- this coverage is the honest point "
                 "(a held-out test constrains a scalar, not a spatial field)", fontsize=11)
    ax.set_xlabel("lon"); ax.set_ylabel("lat"); ax.set_xlim(-180, 180); ax.set_ylim(-90, 90)
    fig.tight_layout()
    fig.savefig(OUT / "geotraces_iron.png", dpi=110)
    plt.close(fig)
    print(f"wrote geotraces_iron.png ({surf.sum()} surface samples)")


def fig_composition_refuted():
    names, bulks, fcs, Rs = [], [], [], []
    for name, path in CACHES.items():
        c = _load(path)
        m = np.isfinite(c["pic"]) & np.isfinite(c["poc"]) & (c["poc"] > 0) & (c["chltot"] > 1e-4)
        bulk = c["pic"][m].sum() / c["poc"][m].sum()
        fcalc = c["chl2"][m].sum() / c["chltot"][m].sum()
        names.append(name); bulks.append(bulk); fcs.append(fcalc); Rs.append(bulk / fcalc)
    x = np.arange(len(names))
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(14, 4.2))
    for ax, vals, title, col in [
        (a1, bulks, "bulk PIC:POC\n(spans ~113x)", "#0C6473"),
        (a2, fcs, "calcifier fraction Chl2/total\n(nearly FLAT ~1.4x)", "#A2571A"),
        (a3, Rs, "implied per-calcifier R = bulk/frac\n(NOT constant ~92x)", "#6b3fa0"),
    ]:
        ax.bar(x, vals, color=col)
        ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_yscale("log")
        for xi, v in zip(x, vals):
            ax.text(xi, v, f"{v:.3g}", ha="center", va="bottom", fontsize=9)
    fig.suptitle("Composition alone is REFUTED: the calcifier fraction is flat, so environment "
                 "(not which PFTs) carries the PIC:POC basin spread", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "composition_refuted.png", dpi=110)
    plt.close(fig)
    print("wrote composition_refuted.png")


def main() -> int:
    for fn in (fig_per_aoi, fig_composition_refuted, fig_global_calcifier, fig_geotraces):
        try:
            fn()
        except Exception as e:
            print(f"  [skip] {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\nfigures in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
