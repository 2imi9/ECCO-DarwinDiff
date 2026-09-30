"""Render a context map of ECCO-Darwin v05 surface chlorophyll with the three study regions.

The field is total surface chlorophyll (the sum of Darwin's five phytoplankton types,
``Chl1``..``Chl5``) averaged over every monthly record of the public v05 1-degree bin-average
product, 1995-2017. It is the model whose parameters this study identifies. The three outlines are
the study's areas of interest, read from ``darwindiff.ecco_darwin_loader`` so they cannot drift
from the code, and drawn over exactly the cells ``subset_aoi`` selects.

Style follows ocean-model papers: a Robinson projection, the model's own land mask in grey with
Natural Earth coastlines on top, region outlines that follow the projection, and a vertical colour
bar with units. A light and a dark variant are written for GitHub's ``<picture>`` switch.

The input is ``v05_ECCO-Darwin_bin_average_1x1_deg.nc`` (1.9 GB) from
https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/ and is looked up where
the flagship runner looks for it, ``$DARWIN_DATA_ROOT/bin_average/``. Needs the ``figures``
dependency group (cartopy); cartopy fetches the Natural Earth coastlines on first use.

    uv run --group figures python scripts/make_chlorophyll_map.py [--bin-average PATH]
"""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patheffects import withStroke

from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
    SOUTHERN_OCEAN_PACIFIC_AOI,
    open_bin_average,
    total_chlorophyll,
)

REPO = Path(__file__).resolve().parents[1]
FILENAME = "v05_ECCO-Darwin_bin_average_1x1_deg.nc"
CENTRAL_LON = -110.0  # puts all three regions near the centre, where Robinson distorts least
PC = ccrs.PlateCarree()

# (AOI, label, label anchor (lon, lat), outline colour). Colours are chosen to stay visible on
# viridis; each outline also carries a thin halo in the background colour.
AOIS = [
    (EQUATORIAL_PACIFIC_AOI, "Equatorial Pacific", (-135.0, 21.0), "#ff3030"),
    (NORTH_ATLANTIC_SUBPOLAR_AOI, "North Atlantic", (-24.0, 72.0), "#ff4fd8"),
    (SOUTHERN_OCEAN_PACIFIC_AOI, "Southern Ocean", (-140.0, -75.0), "#ffb000"),
]

# GitHub's light/dark palettes (Primer), so the figure sits flush on either README theme.
THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", muted="#59636e", land="#bdbdbd", coast="#3d3d3d"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", muted="#9198a1", land="#484f58", coast="#c9d1d9"),
}


def aoi_outline(aoi, n: int = 60):
    """Closed outline of the cells an AOI selects, densely sampled so it curves in Robinson.

    ``subset_aoi`` keeps south-west corner labels lat_min..lat_max and lon_min..lon_max
    inclusive, so the selected cells reach one degree past the nominal north and east bounds.
    """
    w, e = aoi.lon_min, aoi.lon_max + 1.0
    s, n_ = aoi.lat_min, aoi.lat_max + 1.0
    lon = np.concatenate([np.linspace(w, e, n), np.full(n, e), np.linspace(e, w, n), np.full(n, w)])
    lat = np.concatenate(
        [np.full(n, s), np.linspace(s, n_, n), np.full(n, n_), np.linspace(n_, s, n)]
    )
    return lon, lat


def load_field(path: Path):
    """Time-mean total chlorophyll with 1-degree cell EDGES.

    The bin-average's integer lat/lon (-90..89, -180..179) label the south-west CORNER of each
    cell, not its centre (the file's ``area`` variable matches the [lat, lat+1] band on every
    row), so the edges are the labels plus one final edge.
    """
    ds = open_bin_average(path)
    chl = total_chlorophyll(ds).mean("time", skipna=True)
    # Rotate longitudes into the projection's own frame (relative to CENTRAL_LON, -180..180) so
    # no cell straddles the map seam; cartopy otherwise drops seam-crossing cells.
    rel = (chl["lon"].values - CENTRAL_LON + 180.0) % 360.0 - 180.0
    chl = chl.assign_coords(lon=rel).sortby("lon")
    lon_edges = np.append(chl["lon"].values, chl["lon"].values[-1] + 1.0)  # -180..180, rotated
    # An edge at exactly +-180 in the rotated frame is ambiguous (either side of the seam), which
    # makes cartopy treat the whole first column as wrapping; pull the two outer edges inside it.
    lon_edges[0], lon_edges[-1] = -179.9999, 179.9999
    lat_edges = np.append(chl["lat"].values, chl["lat"].values[-1] + 1.0)  # -90..90
    # Land is NaN. Exact zeros are ice-covered ocean (76-87N, 75S) with no modelled
    # chlorophyll; floor them so they draw as the low end of the scale, not as land.
    field = np.ma.masked_invalid(np.clip(chl.values, 1e-6, None))
    first, last = (str(ds.time.values[i])[:7] for i in (0, -1))
    pct = np.nanpercentile(chl.values, [1, 50, 99]).round(3)
    print(f"records {ds.sizes['time']} ({first}..{last}); chl p1/p50/p99 = {pct} mg m^-3")
    return lon_edges, lat_edges, field


def render(lon_edges, lat_edges, field, theme: str, out: Path) -> None:
    c = THEMES[theme]
    plt.rcParams.update({"text.color": c["fg"], "axes.labelcolor": c["fg"], "font.size": 11})
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(c["land"])

    fig = plt.figure(figsize=(8.6, 4.6), dpi=200, facecolor=c["bg"])
    ax = fig.add_axes(
        [0.14, 0.04, 0.84, 0.84], projection=ccrs.Robinson(central_longitude=CENTRAL_LON)
    )
    ax.set_global()
    ax.set_facecolor(c["bg"])
    mesh = ax.pcolormesh(
        lon_edges,
        lat_edges,
        field,
        cmap=cmap,
        norm=LogNorm(vmin=0.02, vmax=1.0),
        transform=ccrs.PlateCarree(central_longitude=CENTRAL_LON),
        shading="flat",
        rasterized=True,
    )
    ax.coastlines("110m", linewidth=0.6, color=c["coast"])
    ax.spines["geo"].set_edgecolor(c["fg"])
    ax.spines["geo"].set_linewidth(1.0)

    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.3,
        color=c["muted"],
        alpha=0.35,
        x_inline=False,
        y_inline=False,
    )
    gl.top_labels = gl.right_labels = False
    gl.xlocator = plt.FixedLocator([-180, -120, -60, 0, 60, 120])
    gl.ylocator = plt.FixedLocator([-80, -40, 0, 40, 80])
    gl.xlabel_style = gl.ylabel_style = {"size": 9, "color": c["muted"]}

    halo = [withStroke(linewidth=4.2, foreground=c["bg"])]
    for aoi, label, (lx, ly), color in AOIS:
        lon, lat = aoi_outline(aoi)
        ax.plot(lon, lat, transform=PC, color=color, linewidth=2.2, path_effects=halo, zorder=5)
        ax.text(
            lx,
            ly,
            label,
            transform=PC,
            ha="center",
            va="center",
            fontsize=10.5,
            weight="bold",
            color=color,
            path_effects=[withStroke(linewidth=3, foreground=c["bg"])],
            zorder=6,
        )

    ax.set_title(
        "ECCO-Darwin v05 surface chlorophyll, 1995–2017 mean",
        fontsize=13.5,
        weight="bold",
        pad=10,
        color=c["fg"],
    )
    cax = fig.add_axes([0.05, 0.14, 0.022, 0.64])
    cb = fig.colorbar(mesh, cax=cax, orientation="vertical", extend="both")
    cticks = [0.02, 0.05, 0.1, 0.2, 0.5, 1]
    cb.set_ticks(cticks)
    cb.set_ticklabels([f"{t:g}" for t in cticks])
    cb.ax.yaxis.set_ticks_position("left")
    cb.ax.yaxis.set_label_position("left")
    cb.set_label("Chlorophyll (mg Chl m$^{-3}$, log scale)", fontsize=11, color=c["fg"])
    cb.ax.tick_params(labelsize=9.5, colors=c["muted"])
    cb.outline.set_edgecolor(c["muted"])

    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight", pad_inches=0.1, facecolor=c["bg"])
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bin-average", type=Path, default=root / "bin_average" / FILENAME)
    ap.add_argument("--out-dir", type=Path, default=REPO / "docs" / "figures")
    args = ap.parse_args()

    lon_edges, lat_edges, field = load_field(args.bin_average)
    render(lon_edges, lat_edges, field, "light", args.out_dir / "v05_surface_chlorophyll.png")
    render(lon_edges, lat_edges, field, "dark", args.out_dir / "v05_surface_chlorophyll_dark.png")
    if args.out_dir.resolve() == (REPO / "docs" / "figures").resolve():
        record_in_manifest("scripts/make_chlorophyll_map.py")


def record_in_manifest(script: str) -> None:
    """Refresh this generator's entries in docs/figures/generated.sha256 (checked in CI)."""
    path = REPO / "docs" / "figures" / "generated_manifest.py"
    spec = importlib.util.spec_from_file_location("generated_manifest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.update(script)


if __name__ == "__main__":
    main()
