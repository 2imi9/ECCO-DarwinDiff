"""Publication figures for the Track-2 identifiability-limits map.

  fig1_map      — the headline 3-closure identifiability map (clean card table)
  fig2_calcite  — (a) within-region Omega support vs the identifiability threshold;
                  (b) the Simpson artifact (within-basin slopes +, pooled -)
  fig3_e2       — the make-or-break out-of-sample transport E2 (learned vs null, K_num)

Colorblind-safe categorical palette (Wong 2011): eqpac=orange, natl=blue, SO=teal;
null/reference=grey. Layout is placed to avoid text collisions (dataviz step 7).
CPU. Writes PNGs to docs/findings/figures/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

mpl.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 220, "font.size": 10,
    "font.family": "DejaVu Sans",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 11, "axes.titleweight": "bold",
    "axes.labelsize": 10, "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.color": "#E6E6E6", "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})
OUT = Path("docs/findings/figures"); OUT.mkdir(parents=True, exist_ok=True)
INK, MUTED = "#1A1A1A", "#666666"
C = {"eqpac": "#E69F00", "natl": "#0072B2", "so": "#009E73", "null": "#9A9A9A",
     "bad": "#C44601", "line": "#333333"}
THRESH = 0.30
LBL = {"eqpac": "Eq. Pacific", "natl": "N. Atl. subpolar", "so": "Southern Ocean"}


def _marsh_pairs():
    from darwindiff import marsh_loader
    from darwindiff.ecco_darwin_loader import (
        EQUATORIAL_PACIFIC_AOI, NORTH_ATLANTIC_SUBPOLAR_AOI, SOUTHERN_OCEAN_PACIFIC_AOI)
    from darwindiff.held_out_obs import aoi_env_field
    aois = {"eqpac": EQUATORIAL_PACIFIC_AOI, "natl": NORTH_ATLANTIC_SUBPOLAR_AOI,
            "so": SOUTHERN_OCEAN_PACIFIC_AOI}
    out = {}
    for k, aoi in aois.items():
        env = aoi_env_field(aoi)
        om = np.asarray(env["omega_c"].numpy()); fin = np.asarray(env["finite"].numpy(), bool)
        vals, dmask, _ = marsh_loader.build_aoi_climatology(aoi)
        vals = np.asarray(vals, float); dmask = np.asarray(dmask, bool)
        cov = dmask & fin & np.isfinite(vals) & (vals > 0) & np.isfinite(om) & (om > 0)
        out[k] = (om[cov], vals[cov])
    return out


# --------------------------------------------------------------------------- #
def fig1_map():
    """Formal scientific table (booktabs rules, no color fills)."""
    fig = plt.figure(figsize=(11, 3.7)); ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    L, R = 0.02, 0.985  # rule extent
    XC, XP, XO, XV, XW = 0.02, 0.135, 0.30, 0.50, 0.635  # column anchors
    cols = [(XC, "Closure"), (XP, "Parameter"), (XO, "Observable"),
            (XV, "Verdict"), (XW, "Reason")]
    rows = [
        ("Iron", "scav_rat", "dissolved Fe conc. (GEOTRACES)", "observability wall",
         "concentration is a low-information projection of the rate"),
        ("Calcite", "R_PICPOC (Ω-mod.)", "PIC:POC ratio (Daniels / Marsh)", "support-limited",
         "within-region Ω range ≤ 0.16 dex; transport E2 fails"),
        ("Growth", "Smallgrow, Biggrow", "primary production (¹⁴C / NPP)", "unobservable",
         "total NPP gives only the biomass-weighted mean rate"),
    ]
    # caption (formal "Table N." style, left-aligned, above the rule)
    ax.text(L, 0.95, "Table 1.", fontsize=11, weight="bold", color=INK, va="top")
    ax.text(L + 0.075, 0.95,
            "Which ECCO-Darwin biogeochemical closures real observations can constrain — none, "
            "for three distinct reasons.", fontsize=10, color=INK, va="top")
    y_toprule, y_header, y_midrule = 0.79, 0.72, 0.665
    y_rows = [0.55, 0.40, 0.25]
    y_botrule = 0.18
    # rules (booktabs: heavier top/bottom, lighter mid; no vertical rules, no fills)
    ax.plot([L, R], [y_toprule, y_toprule], color=INK, lw=1.4)
    ax.plot([L, R], [y_midrule, y_midrule], color=INK, lw=0.8)
    ax.plot([L, R], [y_botrule, y_botrule], color=INK, lw=1.4)
    for x, h in cols:
        ax.text(x, y_header, h, fontsize=9.5, weight="bold", color=INK, va="center")
    for (name, param, obs, verdict, reason), y in zip(rows, y_rows):
        ax.text(XC, y, name, fontsize=10, color=INK, va="center")
        ax.text(XP, y, param, fontsize=8.5, color=INK, va="center", family="monospace")
        ax.text(XO, y, obs, fontsize=9, color=INK, va="center")
        ax.text(XV, y, verdict, fontsize=9.5, color=INK, va="center", style="italic")
        ax.text(XW, y, reason, fontsize=8.7, color=INK, va="center")
    ax.text(L, 0.10, "Notes: the scalar R_PICPOC is itself recoverable — only its Ω-modulation is "
            "untestable. The method is not the limit; the observing system is.", fontsize=8,
            style="italic", color=MUTED, va="top")
    ax.text(L, 0.035, "Needed to break each limit: wider within-region Ω; a pure scavenged-Fe "
            "observable; per-PFT production.", fontsize=8, style="italic", color=MUTED, va="top")
    fig.savefig(OUT / "fig1_identifiability_map.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def fig2_calcite(pairs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    order = ["eqpac", "natl", "so"]
    spans = {k: float(np.log10(pairs[k][0].max()) - np.log10(pairs[k][0].min())) for k in order}
    pooled = float(np.log10(max(pairs[k][0].max() for k in order))
                   - np.log10(min(pairs[k][0].min() for k in order)))

    # (a) support bars
    ax1.grid(axis="y", visible=False)
    rows = order + ["pooled"]
    vals = [spans[k] for k in order] + [pooled]
    cols = [C[k] for k in order] + [C["null"]]
    ys = np.arange(len(rows))[::-1]
    ax1.barh(ys, vals, color=cols, height=0.62, zorder=3)
    for y, v in zip(ys, vals):
        ax1.text(v + 0.008, y, f"{v:.2f}", va="center", ha="left", fontsize=9.5, color=INK)
    ax1.axvline(THRESH, ls=(0, (4, 3)), color=C["bad"], lw=1.8, zorder=6)
    ax1.text(THRESH + 0.016, 2.35, "identifiability\nthreshold\n(0.30 dex)",
             color=C["bad"], fontsize=8.5, ha="left", va="center", weight="bold", zorder=7)
    ax1.set_yticks(ys)
    ax1.set_yticklabels([f"{LBL[k]}  (n={pairs[k][0].size})" for k in order]
                        + ["pooled (between-biome)"], fontsize=9.5)
    ax1.set_xlim(0, 0.52); ax1.set_ylim(-0.6, len(rows) + 0.4)
    ax1.set_xlabel("within-region Ω support  (log₁₀ range, dex)")
    ax1.set_title("(a)  Ω barely varies within any region", loc="left")

    # (b) Simpson scatter
    ax2.grid(True)
    for k in order:
        om, ra = pairs[k]
        x, y = np.log10(om), np.log10(ra)
        ax2.scatter(x, y, s=26, color=C[k], alpha=0.75, edgecolor="white", linewidth=0.4,
                    label=f"{LBL[k]}", zorder=3)
        b, a = np.polyfit(x, y, 1)
        xs = np.array([x.min(), x.max()])
        ax2.plot(xs, a + b * xs, color=C[k], lw=2.4, zorder=4)
    allx = np.concatenate([np.log10(pairs[k][0]) for k in order])
    ally = np.concatenate([np.log10(pairs[k][1]) for k in order])
    bp, ap = np.polyfit(allx, ally, 1)
    xs = np.array([allx.min(), allx.max()])
    ax2.plot(xs, ap + bp * xs, color=INK, lw=2.6, ls=(0, (5, 3)),
             label=f"pooled slope {bp:+.1f}", zorder=5)
    ax2.set_xlabel("log₁₀ Ω_calcite"); ax2.set_ylabel("log₁₀ PIC:POC rain ratio")
    ax2.set_title("(b)  each basin's slope +, pooled − (Simpson)", loc="left")
    ax2.legend(fontsize=8.5, loc="upper left", framealpha=0.95, edgecolor="#DDDDDD")
    fig.suptitle("Calcite — the Ω-dependence of the rain ratio is untestable, not disproven",
                 fontsize=12.5, weight="bold")
    fig.savefig(OUT / "fig2_calcite_support.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def fig3_e2():
    default = {"learned": -1.53, "null": 0.50, "kh": [-2.03, -0.67, -0.67]}
    reg = {"learned": -0.05, "null": 0.50, "kh": [-0.55, -0.55, -0.55]}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)

    # (a) learned vs null
    ax1.grid(axis="x", visible=False)
    x = np.arange(2); w = 0.34
    ax1.bar(x - w / 2, [default["learned"], reg["learned"]], w, label="learned closure",
            color=C["bad"], zorder=3)
    ax1.bar(x + w / 2, [default["null"], reg["null"]], w, label="constant null",
            color=C["null"], zorder=3)
    ax1.axhline(0, color=INK, lw=1.0)
    ax1.set_xticks(x); ax1.set_xticklabels(["default\n(hidden 16)", "regularized\n(hidden 4, wd 0.01)"],
                                           fontsize=9.5)
    ax1.set_ylabel("held-out anomaly R²"); ax1.set_ylim(-1.85, 0.85)
    ax1.set_title("(a)  learned never beats the constant null", loc="left")
    ax1.legend(fontsize=9, loc="center", bbox_to_anchor=(0.5, 0.60),
               framealpha=0.95, edgecolor="#DDDDDD")
    for xi, v in zip(x - w / 2, [default["learned"], reg["learned"]]):
        ax1.text(xi, v - 0.09 if v < -0.2 else v + 0.05, f"{v:+.2f}",
                 ha="center", va="top" if v < -0.2 else "bottom", fontsize=9, color=C["bad"], weight="bold")
    for xi, v in zip(x + w / 2, [default["null"], reg["null"]]):
        ax1.text(xi, v + 0.05, f"{v:+.2f}", ha="center", fontsize=9, color=MUTED, weight="bold")
    ax1.text(0.5, -1.72, "regularization removes the overfit,\nbut there is no signal to beat null",
             ha="center", fontsize=8.6, color=MUTED, style="italic")

    # (b) K_num ladder
    kh = np.array([50, 200, 800])
    ax2.plot(kh, default["kh"], "o-", color=C["bad"], lw=2.2, ms=8, label="default", zorder=4)
    ax2.plot(kh, reg["kh"], "s-", color=C["null"], lw=2.2, ms=8, label="regularized", zorder=4)
    ax2.axhline(0, color=INK, lw=1.0, ls=(0, (2, 2)))
    ax2.set_xscale("log"); ax2.set_xticks(kh); ax2.set_xticklabels(kh, fontsize=9.5)
    ax2.set_xlabel("horizontal diffusivity  kh  (K_num control)")
    ax2.set_ylabel("Δ (learned − null) R²"); ax2.set_ylim(-2.25, 0.55)
    ax2.set_title("(b)  K_num non-discriminating — no real signal", loc="left")
    ax2.legend(fontsize=9, loc="center right", framealpha=0.95, edgecolor="#DDDDDD")
    ax2.text(kh.mean(), 0.32, "a PASS needs Δ > 0, largest at physical kh, shrinking as kh grows",
             ha="center", fontsize=8.2, color=MUTED, style="italic")
    fig.suptitle("The make-or-break out-of-sample transport E2 (calcite) — a decisive negative",
                 fontsize=12.5, weight="bold")
    fig.savefig(OUT / "fig3_e2_result.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def main():
    print("recomputing calcite pairs...")
    pairs = _marsh_pairs()
    for k, (om, ra) in pairs.items():
        print(f"  {k}: n={om.size} Omega[{om.min():.2f},{om.max():.2f}]")
    fig1_map(); print("wrote fig1")
    fig2_calcite(pairs); print("wrote fig2")
    fig3_e2(); print("wrote fig3")
    print(f"figures in {OUT}")


if __name__ == "__main__":
    main()
