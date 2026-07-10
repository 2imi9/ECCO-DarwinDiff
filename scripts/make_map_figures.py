"""Publication figures for the Track-2 identifiability-limits map.

Three figures, from the committed findings + a quick recompute of the raw calcite pairs:
  fig1_map           — the headline 3-closure identifiability map (schematic)
  fig2_calcite       — (a) within-region Omega support vs the identifiability threshold;
                       (b) the Simpson artifact: within-basin slopes positive, pooled negative
  fig3_e2            — the make-or-break out-of-sample transport E2 (learned vs null, K_num)

Colorblind-safe palette (Wong): eqpac=orange, natl=blue, SO=teal; null/reference=grey.
CPU. Writes PNGs to docs/findings/figures/.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

mpl.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 11, "axes.titleweight": "bold", "figure.facecolor": "white",
})
OUT = Path("docs/findings/figures"); OUT.mkdir(parents=True, exist_ok=True)
C = {"eqpac": "#E69F00", "natl": "#0072B2", "so": "#009E73",
     "null": "#999999", "bad": "#D55E00", "ok": "#009E73", "grey": "#555555"}
THRESH = 0.30


# --------------------------------------------------------------------------- #
def _marsh_pairs():
    """Recompute (Omega, ratio) per basin from the Marsh climatology + cache Omega."""
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
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    # column x-anchors (data coords): closure | observable | verdict box | why
    XC, XO, XVB, XV, XW = 0.01, 0.14, 0.40, 0.505, 0.62
    VBW = 0.21  # verdict box width
    rows = [
        ("Iron", "scav_rat  (scav. rate)", "dissolved Fe conc.\n(GEOTRACES)",
         "observability wall", "concentration is a low-info projection of the rate;\na particulate observable does not rescue it"),
        ("Calcite", "Ω-modulation\nof R_PICPOC", "PIC:POC prod. ratio\n(Daniels / Marsh)",
         "support-limited", "within-region Ω range ≤0.16 dex everywhere;\nconfirmed on in-situ Ω, driver-general, E2 fails"),
        ("Growth", "Smallgrow,\nBiggrow", "primary production\n(14C / satellite NPP)",
         "unobservable", "total NPP gives only the biomass-weighted mean\n→ the {small, large} rate pair stays degenerate"),
    ]
    ax.set_title("Which ECCO-Darwin BGC closures can real observations constrain? — none, for three distinct reasons",
                 loc="left", pad=14)
    for x, h in [(XC, "closure"), (XO, "observable"), (XVB, "verdict"), (XW, "why")]:
        ax.text(x, 0.9, h, fontsize=9, weight="bold", color="black")
    ys = [0.66, 0.40, 0.14]
    for (name, param, obs, verdict, why), y in zip(rows, ys):
        ax.text(XC, y + 0.03, name, fontsize=11, weight="bold", va="center")
        ax.text(XC, y - 0.05, param, fontsize=7.5, color=C["grey"], va="center")
        ax.text(XO, y, obs, fontsize=8.5, va="center")
        ax.add_patch(mpl.patches.FancyBboxPatch(
            (XVB, y - 0.045), VBW, 0.09, boxstyle="round,pad=0.004",
            facecolor=C["bad"], alpha=0.9, edgecolor="none"))
        ax.text(XVB + VBW / 2, y, verdict, fontsize=8.5, color="white", weight="bold",
                ha="center", va="center")
        ax.text(XW, y, why, fontsize=7.8, color=C["grey"], va="center")
    ax.text(XC, -0.03, "The method is ready; the observing system is the binding constraint. "
            "The map tells the community what to measure: wider within-region Ω, pure scavenged Fe, per-PFT production.",
            fontsize=7.8, style="italic", color=C["grey"])
    fig.savefig(OUT / "fig1_identifiability_map.png", bbox_inches="tight")
    plt.close(fig)


def fig2_calcite(pairs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2))
    # (a) within-region Omega support vs threshold
    order = ["eqpac", "natl", "so"]
    labels = {"eqpac": "Eq. Pacific", "natl": "N. Atl. subpolar", "so": "Southern Ocean"}
    spans = {k: (np.log10(pairs[k][0].max()) - np.log10(pairs[k][0].min())) for k in order}
    pooled_span = (np.log10(max(pairs[k][0].max() for k in order))
                   - np.log10(min(pairs[k][0].min() for k in order)))
    ys = np.arange(len(order))
    ax1.barh(ys, [spans[k] for k in order], color=[C[k] for k in order], height=0.55)
    ax1.barh([len(order)], [pooled_span], color=C["grey"], height=0.55)
    ax1.axvline(THRESH, ls="--", color=C["bad"], lw=1.5)
    ax1.text(THRESH + 0.005, -0.6, "identifiability\nthreshold (0.30 dex)", color=C["bad"], fontsize=8, va="top")
    ax1.set_yticks(list(ys) + [len(order)])
    ax1.set_yticklabels([f"{labels[k]}\n(n={pairs[k][0].size})" for k in order]
                        + [f"pooled\n(between-biome)"])
    ax1.set_xlabel("within-region Ω support (log₁₀ range, dex)")
    ax1.set_title("(a) Ω barely varies within any region")
    for i, k in enumerate(order):
        ax1.text(spans[k] + 0.004, i, f"{spans[k]:.2f}", va="center", fontsize=8)
    ax1.text(pooled_span + 0.004, len(order), f"{pooled_span:.2f}", va="center", fontsize=8)
    ax1.set_xlim(0, 0.45)

    # (b) Simpson: log ratio vs log Omega per basin
    for k in order:
        om, ra = pairs[k]
        ax2.scatter(np.log10(om), np.log10(ra), s=18, color=C[k], alpha=0.7, label=labels[k])
        if om.size >= 3:
            b, a = np.polyfit(np.log10(om), np.log10(ra), 1)
            xs = np.array([np.log10(om.min()), np.log10(om.max())])
            ax2.plot(xs, a + b * xs, color=C[k], lw=2)
    # pooled slope
    allom = np.concatenate([np.log10(pairs[k][0]) for k in order])
    allra = np.concatenate([np.log10(pairs[k][1]) for k in order])
    bp, ap = np.polyfit(allom, allra, 1)
    xs = np.array([allom.min(), allom.max()])
    ax2.plot(xs, ap + bp * xs, color="black", lw=2.5, ls="--", label=f"pooled slope {bp:+.1f}")
    ax2.set_xlabel("log₁₀ Ω_calcite"); ax2.set_ylabel("log₁₀ PIC:POC rain ratio")
    ax2.set_title("(b) within-basin slopes +, pooled − (Simpson)")
    ax2.legend(fontsize=7.5, loc="best", framealpha=0.9)
    fig.suptitle("Calcite: the Ω-dependence of the rain ratio is untestable, not disproven", weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT / "fig2_calcite_support.png", bbox_inches="tight")
    plt.close(fig)


def fig3_e2():
    # from docs/findings/2026-07-10_e2_powered_result.md
    default = {"learned": -1.53, "null": 0.50, "kh": [(-2.03), (-0.67), (-0.67)]}
    reg = {"learned": -0.05, "null": 0.50, "kh": [(-0.55), (-0.55), (-0.55)]}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.0))
    # (a) learned vs null R2 for the two closures
    x = np.arange(2); w = 0.36
    ax1.bar(x - w / 2, [default["learned"], reg["learned"]], w, label="learned closure", color=C["bad"])
    ax1.bar(x + w / 2, [default["null"], reg["null"]], w, label="constant null", color=C["null"])
    ax1.axhline(0, color="black", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(["default\n(hidden 16)", "regularized\n(hidden 4, wd 0.01)"])
    ax1.set_ylabel("held-out anomaly R²")
    ax1.set_title("(a) learned never beats the constant null")
    ax1.legend(fontsize=8, loc="lower right")
    for xi, v in zip(x - w / 2, [default["learned"], reg["learned"]]):
        ax1.text(xi, v - 0.12, f"{v:+.2f}", ha="center", fontsize=8, color=C["bad"])
    for xi, v in zip(x + w / 2, [default["null"], reg["null"]]):
        ax1.text(xi, v + 0.03, f"{v:+.2f}", ha="center", fontsize=8, color=C["grey"])
    ax1.annotate("regularization removes\nthe overfit — but still\nno signal to beat null",
                 xy=(1 - w / 2, reg["learned"]), xytext=(0.35, -0.9), fontsize=7.5,
                 arrowprops=dict(arrowstyle="->", color=C["grey"]), color=C["grey"])
    # (b) K_num control ladder
    kh = [50, 200, 800]
    ax2.plot(kh, default["kh"], "o-", color=C["bad"], label="default")
    ax2.plot(kh, reg["kh"], "s-", color=C["null"], label="regularized")
    ax2.axhline(0, color="black", lw=0.8, ls=":")
    ax2.set_xscale("log"); ax2.set_xticks(kh); ax2.set_xticklabels(kh)
    ax2.set_xlabel("horizontal diffusivity kh (K_num control)")
    ax2.set_ylabel("delta (learned − null) R²")
    ax2.set_title("(b) K_num non-discriminating (no real signal)")
    ax2.legend(fontsize=8)
    ax2.text(0.5, 0.05, "a PASS needs delta > 0 and largest at physical kh, shrinking as kh grows",
             transform=ax2.transAxes, fontsize=7, color=C["grey"], ha="center")
    fig.suptitle("The make-or-break out-of-sample transport E2 (calcite) — a decisive negative", weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT / "fig3_e2_result.png", bbox_inches="tight")
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
