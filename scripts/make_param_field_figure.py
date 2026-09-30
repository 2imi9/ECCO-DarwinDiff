"""Six-panel figure: the per-cell recovered field of every Carroll-6 parameter, relative to Carroll.

Each panel maps one parameter over the three study regions as recovered / Carroll's published
value, on a log scale where white is Carroll's value and the +/-40% Cal band is marked on the
colour bar. Each cell shows the MEDIAN over the run's seeds. Style follows ocean-model papers and
``scripts/make_chlorophyll_map.py``: Robinson projection, the model's land mask in grey with
Natural Earth coastlines, outlines that follow the projection, a vertical colour bar with units.

Read this as a picture of the fit, not as a result in its own right:
- The per-cell field is fit-generated. Recovery is graded on per-region collapses (README table,
  STATUS.md), and within-box structure does not follow ocean provinces
  (docs/findings/2026-08-20_the_dispersion_lives_inside_one_province.md).
- Each panel carries the verdict of the identifiability map, because colour alone overstates
  some parameters: ``alpfe`` rails to its upper bound (a direction, not a value), ``R_PICPOC``
  has no calcite data in the Southern Ocean, and ``scav_rat`` / ``diatomgraz`` are identifiable
  in one basin each.
- The growth pair is excluded from the result and drawn without values. The box also uses
  ``Smallgrow`` / ``Biggrow`` as rates where Darwin uses them as times (issue #257), so a
  value map of them would mislead.
- Ocean outside the three regions was not fitted and has its own tone, never the white that
  means "equals Carroll". The parameters exist only where the model was fitted, so the rest of
  the globe is deliberately not coloured.

Input: a run directory written with ``SAVE_PER_CELL_SEEDS>0`` (``RUN_DIR/per_cell/*.npz``), and the
v05 bin-average file for the land mask. Needs the ``figures`` dependency group (cartopy).

    uv run --group figures python scripts/make_param_field_figure.py \
        docs/findings/2026-09-29_flagship_percell_local \
        --source "Flagship configuration re-run locally with per-cell output, seeds 0-9."
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, TwoSlopeNorm
from matplotlib.patches import Polygon
from matplotlib.patheffects import withStroke

from darwindiff.carroll6 import PARAMS
from darwindiff.ecco_darwin_loader import AOI_BY_KEY, open_bin_average

REPO = Path(__file__).resolve().parents[1]
FILENAME = "v05_ECCO-Darwin_bin_average_1x1_deg.nc"
CENTRAL_LON = -110.0  # same centring as scripts/make_chlorophyll_map.py
PC = ccrs.PlateCarree()
ROT = ccrs.PlateCarree(central_longitude=CENTRAL_LON)  # data frame: no cell crosses the seam
LOG2_RANGE = 3.0  # colour scale spans Carroll / 8 .. Carroll x 8
BAND = 0.40  # the Cal band: |recovered / Carroll - 1| <= 0.40

# Panel order and verdicts follow the identifiability map (paper Fig. 2, CLAUDE.md).
PANELS = [
    ("alpfe", "global, direction only: rails to its upper bound"),
    ("R_PICPOC", "recovered where the calcite anchor has data"),
    ("scav_rat", "regional: Southern Ocean"),
    ("diatomgraz", "regional: equatorial Pacific (graded at ≤10%)"),
    ("Smallgrow", "excluded: not identifiable from time-mean data"),
    ("Biggrow", "excluded: unobservable by construction"),
]
EXCLUDED = {"Smallgrow", "Biggrow"}
NOTES = {
    ("R_PICPOC", "southernoceanpac"): "no calcite data",
    # Across seeds the eqpac alpfe collapse splits between the bound and well below it (in the
    # flagship too), so the per-cell median there sits between two groups and matches no seed.
    ("alpfe", "eqpac"): "seeds split: half at the bound",
}

# The unfitted-sea and outline colours must stay off the RdBu_r path, or a fitted cell near
# Carroll reads as "nothing fitted" (sea) or swallows its own outline. Checked in render().
MIN_DELTA_E = 8.0
THEMES = {
    "light": dict(
        bg="#ffffff",
        fg="#1f2328",
        muted="#59636e",
        land="#9c9c95",
        sea="#c9c9c2",
        coast="#3d3d3d",
        hatch="#6e7781",
        outline="#1f2328",
        halo="#ffffff",
    ),
    "dark": dict(
        bg="#0d1117",
        fg="#e6edf3",
        muted="#9198a1",
        land="#484f58",
        sea="#1c2128",
        coast="#c9d1d9",
        hatch="#8b949e",
        outline="#8b949e",
        halo="#0d1117",
    ),
}


def _lab(hex_colours) -> np.ndarray:
    """sRGB hex strings (or RGB rows in 0..1) to CIE L*a*b* (D65)."""
    rgb = np.array(
        [
            [int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)] if isinstance(h, str) else h[:3]
            for h in hex_colours
        ],
        dtype=float,
    )
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    m = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = lin @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], -1)


def min_delta_e(hex_colour: str, cmap) -> float:
    """Smallest CIE76 distance between a colour and any of the colour map's 256 entries."""
    lut = _lab(cmap(np.arange(256)))
    return float(np.min(np.linalg.norm(lut - _lab([hex_colour]), axis=1)))


def load_fields(run_dir: Path):
    """Median over seeds of recovered / Carroll, on a global 1-degree (lat, lon) grid.

    Grid labels are south-west cell corners (the bin-average convention the runner inherits):
    row = lat + 90, column = lon + 180. Returns (ratio[param, 180, 360], seeds, per-AOI mask).
    """
    files = sorted((run_dir / "per_cell").glob("percell_*_seed*.npz"))
    if not files:
        raise SystemExit(
            f"no per-cell fields under {run_dir / 'per_cell'} (SAVE_PER_CELL_SEEDS=0?)"
        )
    names = [p.name for p in PARAMS]
    carroll = np.array([p.carroll_value for p in PARAMS], dtype=np.float64)
    stacks: dict[str, list[np.ndarray]] = {}
    seeds: set[int] = set()
    masks: dict[str, np.ndarray] = {}
    for f in files:
        aoi, seed = re.fullmatch(r"percell_(.+)_seed(\d+)\.npz", f.name).groups()
        z = np.load(f)
        if list(z["param_names"]) != names:
            raise SystemExit(f"{f.name}: param order {list(z['param_names'])} != registry {names}")
        n_cols = int(z["W"])
        idx = z["ocean_index"]
        rows = np.rint(z["lats"][idx // n_cols] + 90).astype(int)
        cols = np.rint(z["lons"][idx % n_cols] + 180).astype(int)
        grid = np.full((len(names), 180, 360), np.nan)
        grid[:, rows, cols] = z["values"].astype(np.float64) / carroll[:, None]
        stacks.setdefault(aoi, []).append(grid)
        m = np.zeros((180, 360), bool)
        m[rows, cols] = True
        masks[aoi] = m
        seeds.add(int(seed))
    ratio = np.full((len(names), 180, 360), np.nan)
    for aoi, grids in stacks.items():
        # [seed, param, cell] over this region's cells only, then the median over seeds.
        cells = np.stack([g[:, masks[aoi]] for g in grids])
        ratio[:, masks[aoi]] = np.median(cells, axis=0)
    per_aoi_n = {a: len(g) for a, g in stacks.items()}
    if len(set(per_aoi_n.values())) != 1:
        raise SystemExit(f"uneven seed counts per region: {per_aoi_n}")
    return ratio, sorted(seeds), masks


def land_mask(path: Path) -> np.ndarray:
    """True on land, (lat+90, lon+180) indexed, from the bin-average SST NaN pattern."""
    sst = open_bin_average(path)["SST"].isel(time=0)
    return ~np.isfinite(sst.values)


def to_rotated(a: np.ndarray):
    """Reorder a (..., 360) array indexed by lon+180 into the ROT frame; return it with edges."""
    rel = (np.arange(-180.0, 180.0) - CENTRAL_LON + 180.0) % 360.0 - 180.0
    order = np.argsort(rel)
    edges = np.append(rel[order], rel[order][-1] + 1.0)
    return a[..., order], edges


def aoi_outline(aoi, n: int = 60):
    """Closed outline of the cells an AOI selects (SW-corner labels, inclusive: +1 degree N/E)."""
    w, e = aoi.lon_min, aoi.lon_max + 1.0
    s, n_ = aoi.lat_min, aoi.lat_max + 1.0
    lon = np.concatenate([np.linspace(w, e, n), np.full(n, e), np.linspace(e, w, n), np.full(n, w)])
    lat = np.concatenate(
        [np.full(n, s), np.linspace(s, n_, n), np.full(n, n_), np.linspace(n_, s, n)]
    )
    return lon, lat


def render(ratio, seeds, masks, land, theme: str, out: Path, source: str = "") -> None:
    c = THEMES[theme]
    plt.rcParams.update(
        {
            "text.color": c["fg"],
            "axes.labelcolor": c["fg"],
            "hatch.linewidth": 0.9,
            "hatch.color": c["hatch"],
        }
    )
    names = [p.name for p in PARAMS]
    lat_edges = np.arange(-90.0, 91.0)
    cmap = plt.get_cmap("RdBu_r").copy()
    for role in ("sea", "outline"):
        de = min_delta_e(c[role], cmap)
        if de < MIN_DELTA_E:
            raise SystemExit(
                f"{theme} {role} colour {c[role]} is dE {de:.1f} from RdBu_r (< {MIN_DELTA_E})"
            )
    # Box cells the run did not fit (ocean in the SST mask but not in the run's own ocean mask,
    # e.g. five cells at 65N north of Iceland) are drawn as land, so no box interior carries the
    # unfitted-sea tone.
    in_box = np.zeros_like(land)
    fitted = np.zeros_like(land)
    for key, m in masks.items():
        aoi = AOI_BY_KEY[key]
        r0, r1 = int(aoi.lat_min) + 90, int(aoi.lat_max) + 91
        c0, c1 = int(aoi.lon_min) + 180, int(aoi.lon_max) + 181
        in_box[r0:r1, c0:c1] = True
        fitted |= m
    backdrop, lon_edges = to_rotated(np.where(land | (in_box & ~fitted), 1.0, 0.0))  # 1 = land
    back_cmap = ListedColormap([c["sea"], c["land"]])
    norm = TwoSlopeNorm(vmin=-LOG2_RANGE, vcenter=0.0, vmax=LOG2_RANGE)
    halo = [withStroke(linewidth=3.2, foreground=c["halo"])]
    proj = ccrs.Robinson(central_longitude=CENTRAL_LON)

    fig = plt.figure(figsize=(12.0, 10.4), dpi=200, facecolor=c["bg"])
    left, right, top, bottom, hgap, vgap = 0.13, 0.995, 0.955, 0.075, 0.015, 0.075
    pw = (right - left - hgap) / 2
    ph = (top - bottom - 2 * vgap) / 3
    mesh = None
    for i, (name, verdict) in enumerate(PANELS):
        row, col = divmod(i, 2)
        x0 = left + col * (pw + hgap)
        y0 = top - (row + 1) * ph - row * vgap
        ax = fig.add_axes([x0, y0, pw, ph], projection=proj)
        ax.set_global()
        ax.set_facecolor(c["bg"])
        ax.pcolormesh(
            lon_edges,
            lat_edges,
            backdrop,
            cmap=back_cmap,
            vmin=0,
            vmax=1,
            transform=ROT,
            rasterized=True,
        )
        k = names.index(name)
        if name not in EXCLUDED:
            field, _ = to_rotated(np.log2(ratio[k]))
            mesh = ax.pcolormesh(
                lon_edges,
                lat_edges,
                np.ma.masked_invalid(np.clip(field, -LOG2_RANGE, LOG2_RANGE)),
                cmap=cmap,
                norm=norm,
                transform=ROT,
                shading="flat",
                rasterized=True,
            )
        ax.coastlines("110m", linewidth=0.45, color=c["coast"])
        ax.spines["geo"].set_edgecolor(c["fg"])
        ax.spines["geo"].set_linewidth(0.9)
        for key in masks:
            lon, lat = aoi_outline(AOI_BY_KEY[key])
            if name in EXCLUDED:
                ax.add_patch(
                    Polygon(
                        np.column_stack([lon, lat]),
                        closed=True,
                        transform=PC,
                        facecolor="none",
                        edgecolor=c["hatch"],
                        hatch="////",
                        linewidth=0,
                        zorder=4,
                    )
                )
            ax.plot(
                lon,
                lat,
                transform=PC,
                color=c["outline"],
                linewidth=1.2,
                path_effects=halo,
                zorder=5,
            )
            note = NOTES.get((name, key))
            if note:
                aoi = AOI_BY_KEY[key]
                ax.text(
                    (aoi.lon_min + aoi.lon_max + 1) / 2,
                    aoi.lat_min - 7,
                    note,
                    transform=PC,
                    ha="center",
                    va="center",
                    fontsize=10,
                    style="italic",
                    color=c["fg"],
                    path_effects=[withStroke(linewidth=3, foreground=c["bg"])],
                    zorder=6,
                )
        if name in EXCLUDED:
            ax.text(
                -140,
                35,
                "excluded",
                transform=PC,
                ha="center",
                va="center",
                fontsize=16,
                weight="bold",
                color=c["muted"],
                path_effects=[withStroke(linewidth=3, foreground=c["bg"])],
                zorder=6,
            )
        letter = "abcdef"[i]
        ax.set_title(
            f"({letter})  $\\bf{{{name.replace('_', chr(92) + '_')}}}$\n{verdict}",
            fontsize=12,
            loc="left",
            color=c["fg"],
            pad=6,
        )

    cax = fig.add_axes([0.1, 0.2, 0.018, 0.6])
    cb = fig.colorbar(mesh, cax=cax, orientation="vertical", extend="both")
    ticks = np.arange(-LOG2_RANGE, LOG2_RANGE + 1)
    cb.set_ticks(ticks)
    cb.set_ticklabels(
        [
            f"÷{2 ** int(-t)}" if t < 0 else ("Carroll" if t == 0 else f"×{2 ** int(t)}")
            for t in ticks
        ]
    )
    cb.ax.yaxis.set_ticks_position("left")
    cb.ax.yaxis.set_label_position("left")
    cb.ax.tick_params(labelsize=10.5, colors=c["muted"])
    cb.outline.set_edgecolor(c["muted"])
    lo, hi = np.log2(1 - BAND), np.log2(1 + BAND)
    cb.ax.axhline(lo, color="#1f2328", linewidth=1.6)  # on the pale centre in both themes
    cb.ax.axhline(hi, color="#1f2328", linewidth=1.6)
    n_seed = f"{len(seeds)} seed" + ("s" if len(seeds) != 1 else "")
    cb.set_label(
        f"recovered / Carroll, per cell, median of {n_seed}  (lines: ±40% band)",
        fontsize=11.5,
        color=c["fg"],
    )

    footer = (
        "Colour is the fitted per-cell field, not the grade: recovery is graded on each region's "
        "collapsed value. Outside the three regions nothing was fitted. The colour-bar lines mark "
        "the ±40% Cal band; diatomgraz is graded at ≤10%."
    )
    fig.text(
        0.13,
        0.03,
        f"{footer} {source}".strip(),
        ha="left",
        va="top",
        fontsize=10,
        color=c["muted"],
        wrap=True,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=c["bg"], bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--bin-average", type=Path, default=root / "bin_average" / FILENAME)
    ap.add_argument("--out-dir", type=Path, default=REPO / "docs" / "figures")
    ap.add_argument("--stem", default="fig_param_fields")
    ap.add_argument("--source", default="", help="provenance line printed under the figure")
    args = ap.parse_args()

    ratio, seeds, masks = load_fields(args.run_dir)
    land = land_mask(args.bin_average)
    print(f"seeds {seeds}; regions {sorted(masks)}")
    for k, p in enumerate(PARAMS):
        vals = ratio[k][np.isfinite(ratio[k])]
        inside = np.mean(np.abs(vals - 1) <= BAND)
        print(f"  {p.name:<10} median ratio {np.median(vals):.3f}; cells in band {inside:.0%}")
    for theme, suffix in (("light", ""), ("dark", "_dark")):
        out = args.out_dir / f"{args.stem}{suffix}.png"
        render(ratio, seeds, masks, land, theme, out, args.source)
    default_out = args.out_dir.resolve() == (REPO / "docs" / "figures").resolve()
    if default_out and args.stem == "fig_param_fields":
        record_in_manifest("scripts/make_param_field_figure.py")


def record_in_manifest(script: str) -> None:
    """Refresh this generator's entries in docs/figures/generated.sha256 (checked in CI)."""
    path = REPO / "docs" / "figures" / "generated_manifest.py"
    spec = importlib.util.spec_from_file_location("generated_manifest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.update(script)


if __name__ == "__main__":
    main()
