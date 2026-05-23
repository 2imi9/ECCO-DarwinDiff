#!/usr/bin/env python3
"""Generate the statistical figures (Figs 2, 3, 4, 5) for the DarwinDiff
internal white paper.

Figure 1 (the conceptual pipeline diagram) is generated separately via
Claude Design; the raw SVG is saved as ``fig1_pipeline.svg`` in this
directory. Convert it to PDF for LaTeX inclusion via::

    rsvg-convert -f pdf fig1_pipeline.svg > fig1_pipeline.pdf
    # or:
    inkscape --export-type=pdf fig1_pipeline.svg

This script handles only the data-driven figures, which need to be
rendered from the actual sweep outputs in ``D:\\runs\\bcr_*\\``.

Inputs
------
Option A — aggregated JSON at ``--aggregated`` with the schema::

    {
      "seeds": [
        {
          "config": "<config-name>",
          "seed": <int>,
          "recovered": {"alpfe": float, "scav_rat": float, ...},
          "cal_grade": {"alpfe": bool, "scav_rat": bool, ...}
        },
        ...
      ]
    }

Option B — no aggregated data. The script then produces *illustrative*
figures using the headline numbers from ``STATUS.md`` /
``docs/findings/v3.1_closeout.md``. These are clearly labeled
``[Illustrative]`` in their titles so they cannot be confused with the
real results.

Outputs (in this directory)
---------------------------
    fig2_ceiling.{pdf,png}         — Cal-grade distribution across 857 seeds
    fig3_basinC_scatter.{pdf,png}  — Iron-pair recovery scatter, F2, n=40
    fig4_per_param_box.{pdf,png}   — Per-parameter recovery distributions
    fig5_wave6.{pdf,png}           — Wave 6 composition test

Usage
-----
    python make_figures.py                          # illustrative, all 4
    python make_figures.py --aggregated path/to/aggregated_v3.1.json
    python make_figures.py --figures 2,4            # subset

Requirements
------------
    matplotlib >= 3.7
    numpy

Verified Carroll-6 optima (from docs/ecco_darwin_parameter_inventory.md):
    alpfe = 0.92831
    scav_rat = 10.41124 * 0.005 / 86400 ≈ 6.026e-7 s^-1
    Smallgrow = 0.66098 d^-1
    Biggrow = 0.43148 d^-1
    diatomgraz = 0.83003
    R_PICPOC = 0.04245
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


# Okabe-Ito colorblind-safe palette
PALETTE = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",  # accent red (also used in Fig 1)
    "purple": "#CC79A7",
    "gray": "#999999",
    "light_gray": "#CCCCCC",
}

# Carroll-6 published optima
CARROLL_OPTIMA = {
    "alpfe": 0.92831,
    "scav_rat": 10.41124 * 0.005 / 86400,
    "Smallgrow": 0.66098,
    "Biggrow": 0.43148,
    "diatomgraz": 0.83003,
    "R_PICPOC": 0.04245,
}

PARAM_NAMES = list(CARROLL_OPTIMA.keys())

CAL_GRADE_RANGE = 0.40  # ±40% defines Cal-grade
EXCELLENT_RANGE = 0.10  # ±10% defines Excellent


def set_paper_style() -> None:
    """Set matplotlib rcParams for clean academic-paper output."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def _save_figure(fig, out_dir: Path, basename: str) -> None:
    for ext in ("pdf", "png"):
        path = out_dir / f"{basename}.{ext}"
        fig.savefig(path)
        print(f"  wrote {path}")


# ----------------------------------------------------------------------------
# Figure 2 — Cal-grade distribution across 857 seeds (the 5/6 ceiling)
# ----------------------------------------------------------------------------
def fig2_ceiling(out_dir: Path, data: dict | None = None) -> None:
    if data is None:
        # Illustrative bucket counts; total = 857
        counts = [50, 150, 250, 250, 155, 2, 0]
        illustrative = True
    else:
        per_seed_count = [sum(s["cal_grade"].values()) for s in data["seeds"]]
        counts = [per_seed_count.count(k) for k in range(7)]
        illustrative = False

    total = sum(counts)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(7)
    colors = [PALETTE["gray"]] * 7
    colors[5] = PALETTE["vermillion"]
    colors[6] = "#FFFFFF"

    bars = ax.bar(x, counts, color=colors, edgecolor="#000000", linewidth=0.8)
    bars[6].set_edgecolor(PALETTE["vermillion"])
    bars[6].set_linewidth(2.0)

    if counts[5] > 0:
        ax.annotate(
            f"{counts[5]} seeds ({counts[5]/total*100:.2f}%)",
            xy=(5, counts[5]),
            xytext=(5, counts[5] + max(counts) * 0.06),
            ha="center", fontsize=10, color=PALETTE["vermillion"],
        )
    ax.annotate(
        f"0/{total} — structural ceiling",
        xy=(6, 0),
        xytext=(6, max(counts) * 0.5),
        ha="center", fontsize=10, color=PALETTE["vermillion"],
        arrowprops=dict(arrowstyle="->", color=PALETTE["vermillion"], lw=1.2),
    )

    ax.set_xlabel("Carroll-N parameters recovered at Cal-grade (per seed)")
    ax.set_ylabel(f"Number of seeds out of {total}")
    title = f"v3.1 sweep: Cal-grade distribution ({total} seeds, 86 configurations)"
    if illustrative:
        title += "  [Illustrative]"
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_ylim(0, max(counts) * 1.25)

    fig.tight_layout()
    _save_figure(fig, out_dir, "fig2_ceiling")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Figure 3 — Basin C iron-pair recovery scatter, F2 config, n=40
# ----------------------------------------------------------------------------
def fig3_basinC_scatter(out_dir: Path, data: dict | None = None) -> None:
    if data is None:
        rng = np.random.default_rng(42)
        n_clustered = 38
        alpfe_cluster = rng.normal(0.93, 0.08, n_clustered).clip(0.05, 1.0)
        scav_cluster_log = rng.normal(np.log10(6.026e-7), 0.18, n_clustered)
        scav_cluster = 10 ** scav_cluster_log
        alpfe_out = np.array([0.32, 0.55])
        scav_out = np.array([5e-8, 1.5e-6])
        alpfe = np.concatenate([alpfe_cluster, alpfe_out])
        scav = np.concatenate([scav_cluster, scav_out])
        illustrative = True
    else:
        # The F2 / Basin C iron-pair n=40 spans four 10-seed batches across
        # the v3.1 sweep, in dirs whose canonical config names are:
        #   sweep_d4_F2_chl1W_20260519_1934   (seeds 0-9)
        #   arc6_basinC_seeds10-19            (seeds 10-19)
        #   w2f_basinC_seeds20-29             (seeds 20-29)
        #   e_basinC_seeds30-39               (seeds 30-39)
        # Match either by 'basinC' substring or the seed-0-9 F2 batch dir name.
        f2_batch_markers = ("basinc",
                            "sweep_d4_f2",
                            "f2_chl1w",
                            "f2_seeds")
        F2_seeds = [s for s in data["seeds"]
                    if any(m in s["config"].lower() for m in f2_batch_markers)]
        alpfe = np.array([s["recovered"]["alpfe"] for s in F2_seeds])
        scav = np.array([s["recovered"]["scav_rat"] for s in F2_seeds])
        # Iron-pair Cal-grade count uses the aggregator's per-param flags,
        # which already apply the project ±40% definition consistently.
        n_iron_pair_cal = sum(
            1 for s in F2_seeds
            if s["cal_grade"]["alpfe"] and s["cal_grade"]["scav_rat"]
        )
        n_total_F2 = len(F2_seeds)
        illustrative = False

    carroll_alpfe = CARROLL_OPTIMA["alpfe"]
    carroll_scav = CARROLL_OPTIMA["scav_rat"]

    fig, ax = plt.subplots(figsize=(6, 5))

    # Cal-grade region (light blue)
    cal_x = carroll_alpfe * (1 - CAL_GRADE_RANGE)
    cal_w = carroll_alpfe * 2 * CAL_GRADE_RANGE
    cal_y = carroll_scav * (1 - CAL_GRADE_RANGE)
    cal_h = carroll_scav * 2 * CAL_GRADE_RANGE
    ax.add_patch(Rectangle((cal_x, cal_y), cal_w, cal_h,
                           facecolor=PALETTE["sky_blue"], alpha=0.2,
                           edgecolor=PALETTE["sky_blue"], linewidth=0.5,
                           label="Cal-grade (±40%)"))

    # Excellent region (light yellow)
    exc_x = carroll_alpfe * (1 - EXCELLENT_RANGE)
    exc_w = carroll_alpfe * 2 * EXCELLENT_RANGE
    exc_y = carroll_scav * (1 - EXCELLENT_RANGE)
    exc_h = carroll_scav * 2 * EXCELLENT_RANGE
    ax.add_patch(Rectangle((exc_x, exc_y), exc_w, exc_h,
                           facecolor=PALETTE["yellow"], alpha=0.4,
                           edgecolor="#998800", linewidth=0.5,
                           label="Excellent (±10%)"))

    ax.scatter(alpfe, scav, s=30, c=PALETTE["black"], alpha=0.75,
               edgecolors="white", linewidths=0.5,
               label=f"Seed recoveries (n={len(alpfe)})")

    ax.scatter([carroll_alpfe], [carroll_scav], s=300, marker="*",
               c=PALETTE["vermillion"], edgecolors="white", linewidths=1.5,
               label="Carroll 2020 optimum", zorder=10)

    ax.set_xscale("linear")
    ax.set_yscale("log")
    ax.set_xlim(0.05, 1.0)
    ax.set_ylim(3e-8, 3e-6)
    ax.set_xlabel(r"recovered $\alpha_{fe}$ (iron dust solubility)")
    ax.set_ylabel(r"recovered $r_{scav}$ (iron scavenging rate, s$^{-1}$)")
    title = "Basin C iron-pair recovery, F2 configuration"
    if illustrative:
        title += "  [Illustrative]"
    ax.set_title(title)
    ax.legend(loc="upper left", framealpha=0.95)

    if not illustrative:
        pct = (n_iron_pair_cal / n_total_F2 * 100) if n_total_F2 > 0 else 0
        annotation = (f"F2 / Basin C config, n={n_total_F2}\n"
                      f"{n_iron_pair_cal}/{n_total_F2} ({pct:.0f}%) "
                      "iron-pair Cal-grade\n"
                      "across four 10-seed batches")
    else:
        annotation = ("F2 / Basin C config, n=40\n"
                      "38/40 (95%) iron-pair Cal-grade\n"
                      "across four 10-seed batches")
    ax.text(0.97, 0.03, annotation,
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=9,
            bbox=dict(facecolor="white", edgecolor=PALETTE["light_gray"],
                      alpha=0.95))

    fig.tight_layout()
    _save_figure(fig, out_dir, "fig3_basinC_scatter")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Figure 4 — Per-parameter recovery distributions across 857 seeds
# ----------------------------------------------------------------------------
def fig4_per_param_box(out_dir: Path, data: dict | None = None) -> None:
    if data is None:
        rng = np.random.default_rng(7)
        n = 857
        recovered_ratio = {
            "alpfe": rng.normal(1.0, 0.18, n).clip(0.3, 2.0),
            "scav_rat": rng.lognormal(0.0, 0.25, n).clip(0.2, 5.0),
            "Smallgrow": rng.lognormal(0.25, 0.55, n).clip(0.12, 8.0),
            "Biggrow": rng.lognormal(0.1, 0.55, n).clip(0.12, 8.0),
            "diatomgraz": rng.lognormal(0.0, 0.55, n).clip(0.12, 8.0),
            "R_PICPOC": rng.lognormal(0.4, 0.7, n).clip(0.12, 8.0),
        }
        illustrative = True
    else:
        recovered_ratio: dict[str, list[float]] = {p: [] for p in PARAM_NAMES}
        for s in data["seeds"]:
            for p in PARAM_NAMES:
                if p in s.get("recovered", {}):
                    recovered_ratio[p].append(
                        s["recovered"][p] / CARROLL_OPTIMA[p]
                    )
        recovered_ratio = {p: np.array(v) for p, v in recovered_ratio.items()}
        illustrative = False

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.axhspan(1 - CAL_GRADE_RANGE, 1 + CAL_GRADE_RANGE,
               color=PALETTE["sky_blue"], alpha=0.15, zorder=0)
    ax.axhspan(1 - EXCELLENT_RANGE, 1 + EXCELLENT_RANGE,
               color=PALETTE["yellow"], alpha=0.25, zorder=0)
    ax.axhline(1.0, color="#444444", linewidth=1.0, zorder=1)

    data_arrays = [recovered_ratio[p] for p in PARAM_NAMES]
    positions = np.arange(1, 7)
    ax.boxplot(
        data_arrays, positions=positions, widths=0.5,
        patch_artist=True,
        boxprops=dict(facecolor="#888888", alpha=0.4, edgecolor="#000000"),
        medianprops=dict(color="#000000", linewidth=1.5),
        whiskerprops=dict(color="#000000"),
        capprops=dict(color="#000000"),
        flierprops=dict(marker="o", markersize=3, markerfacecolor="none",
                        markeredgecolor="#666666", alpha=0.5),
    )

    # band labels at right edge
    ax.text(6.4, 1 + CAL_GRADE_RANGE * 0.7, "Cal-grade band (±40%)",
            color=PALETTE["sky_blue"], fontsize=9, va="center")
    ax.text(6.4, 1 + EXCELLENT_RANGE * 0.7, "Excellent band (±10%)",
            color="#998800", fontsize=9, va="center")

    ax.set_xticks(positions)
    ax.set_xticklabels(PARAM_NAMES, family="monospace", fontsize=10)
    ax.set_yscale("log")
    ax.set_ylim(0.1, 10.0)
    ax.set_ylabel("Recovered value / Carroll 2020 optimum (log scale)")
    title = "Carroll-N recovery distributions across 857 seeds"
    if illustrative:
        title += "  [Illustrative]"
    ax.set_title(title)
    ax.set_xlim(0.3, 8.0)

    fig.tight_layout()
    _save_figure(fig, out_dir, "fig4_per_param_box")
    plt.close(fig)


# ----------------------------------------------------------------------------
# Figure 5 — Wave 6 composition test
# ----------------------------------------------------------------------------
def fig5_wave6(out_dir: Path) -> None:
    """Values verified in v3.1_closeout.md Wave 6 section."""
    configs = ["w2e_peraoi_lam0.1\n(parent 1)",
               "c_chl40_posi15\n(parent 2)",
               "w6_combo\n(composed)"]
    mean_cal = [2.40, 2.70, 2.00]
    colors = [PALETTE["gray"], PALETTE["gray"], PALETTE["vermillion"]]

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(configs))
    bars = ax.bar(x, mean_cal, color=colors, edgecolor="#000000", linewidth=0.8)

    for bar, val in zip(bars, mean_cal):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.05,
                f"{val:.2f}", ha="center", fontsize=10)

    ax.axhline(2.00, color=PALETTE["vermillion"],
               linewidth=0.8, linestyle="--", alpha=0.5)
    ax.annotate("regresses below either parent",
                xy=(2, 2.00), xytext=(0.5, 3.4),
                ha="center", fontsize=9, color=PALETTE["vermillion"],
                arrowprops=dict(arrowstyle="->",
                                color=PALETTE["vermillion"], lw=1.0))

    ax.set_xticks(x)
    ax.set_xticklabels(configs, fontsize=9, family="monospace")
    ax.set_ylim(0, 4)
    ax.set_ylabel("Mean Cal-grade count (out of 6)")
    ax.set_title("Wave 6 composition test: combining the two 5/6 lever families")

    fig.tight_layout()
    _save_figure(fig, out_dir, "fig5_wave6")
    plt.close(fig)


# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--aggregated", type=Path, default=None,
        help="Path to aggregated sweep JSON (schema in module docstring). "
             "If omitted, illustrative figures are produced.",
    )
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent,
        help="Output directory for figures (default: this script's directory).",
    )
    parser.add_argument(
        "--figures", default="2,3,4,5",
        help="Comma-separated figure numbers to generate (default: 2,3,4,5).",
    )
    args = parser.parse_args()

    figs = set(map(int, args.figures.split(",")))
    args.out.mkdir(parents=True, exist_ok=True)
    set_paper_style()

    data: dict[str, Any] | None = None
    if args.aggregated and args.aggregated.exists():
        with open(args.aggregated) as f:
            data = json.load(f)
        print(f"Loaded aggregated data: {len(data['seeds'])} seeds")
    else:
        print("No aggregated data provided; producing ILLUSTRATIVE figures.")
        print("Re-run with --aggregated path/to/aggregated_v3.1.json for real data.")

    if 2 in figs:
        print("Generating fig2_ceiling ...")
        fig2_ceiling(args.out, data)
    if 3 in figs:
        print("Generating fig3_basinC_scatter ...")
        fig3_basinC_scatter(args.out, data)
    if 4 in figs:
        print("Generating fig4_per_param_box ...")
        fig4_per_param_box(args.out, data)
    if 5 in figs:
        print("Generating fig5_wave6 ...")
        fig5_wave6(args.out)

    print("Done.")


if __name__ == "__main__":
    main()
