# -*- coding: utf-8 -*-
"""v3.0 multi-AOI parameter-recovery arc analysis.

Aggregates JSON results from PRs #44-#57 (baseline), #58 (per-AOI DINNs +
lambda sweep), and #59 (PIC absolute alone + paired POC+PIC anchors) into
a single per-config summary + per-parameter breakdown + trade-off plot.

Outputs (in `docs/findings/v3.0_arc/`):
    - summary.csv          one row per (config family, weight set)
    - param_bands.csv      per-parameter band hit rates across the arc
    - obs_pic_poc_per_aoi.csv   regional PIC/POC ratios from cached targets
    - r_picpoc_distribution.png   R_PICPOC mean (+ Carroll line) by config
    - per_aoi_r_picpoc.png        eqpac vs natl R_PICPOC scatter
    - tradeoff_iron_vs_rpicpoc.png  alpfe Cal rate vs R_PICPOC Cal rate

Used as the data engine for `notebooks/32_v3_0_param_learner_ceiling.ipynb`.
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path
from collections import defaultdict
import csv

import numpy as np

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

PARAM_ORDER = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
CARROLL = {
    "alpfe": 0.92831, "scav_rat": 6.0250e-7, "Smallgrow": 0.66098,
    "Biggrow": 0.43148, "diatomgraz": 0.83003, "R_PICPOC": 0.04245,
}
BANDS_CAL = ("Cal-grade", "Excellent")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCRIPTS = HERE
OUT_DIR = ROOT / "docs" / "findings" / "v3.0_arc"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v3.0 best-config tag fragments (shared across all sweeps): AOI ID + GEO POC=0.5
# + hd=32 + NAtl_W=2.0, at standard PINN/POC weights.
TAG_BASE = "_surf0.3_sub1.0_pinn3.0_pocsubW3.0_geopocW0.5_aoiid_hd32_w-natlsubpolar2.0"


# ============================================================================
# Config families
# ============================================================================

def baseline_pattern() -> str:
    """PR #57 best config without per-AOI DINN, without abs anchors."""
    return f"run_v3.0_joint_eqpac-natlsubpolar_seed*{TAG_BASE}.json"


def lambda_patterns() -> dict[str, str]:
    """PR #58 per-AOI lambda sweep."""
    return {
        f"peraoi_lam{lam}": f"run_v3.0_joint_eqpac-natlsubpolar_seed*{TAG_BASE}_peraoi_lam{lam}.json"
        for lam in ["0.01", "0.1", "1.0", "10.0"]
    }


def pic_alone_patterns() -> dict[str, str]:
    """PR #59 sweep 1: PIC_ABS_W alone."""
    return {
        f"picabsW{w}": f"run_v3.0_joint_eqpac-natlsubpolar_seed*{TAG_BASE}_picabsW{w}.json"
        for w in ["0.3", "1.0", "3.0", "10.0"]
    }


def paired_heavy_patterns() -> dict[str, str]:
    """PR #59 sweep 2: paired POC+PIC, weights >= 0.3."""
    pairs = [("0.3", "0.3"), ("1.0", "1.0"), ("3.0", "1.0"), ("1.0", "3.0")]
    return {
        f"poc{poc}_pic{pic}": f"run_v3.0_joint_eqpac-natlsubpolar_seed*{TAG_BASE}_picabsW{pic}_pocabsW{poc}.json"
        for (poc, pic) in pairs
    }


def paired_light_patterns() -> dict[str, str]:
    """PR #59 sweep 3 (this session): light paired, weights < 0.3."""
    pairs = [("0.05", "0.3"), ("0.1", "0.5"), ("0.1", "1.0"), ("0.5", "1.0")]
    return {
        f"poc{poc}_pic{pic}": f"run_v3.0_joint_eqpac-natlsubpolar_seed*{TAG_BASE}_picabsW{pic}_pocabsW{poc}.json"
        for (poc, pic) in pairs
    }


# ============================================================================
# Aggregation
# ============================================================================

def load_runs(pattern: str) -> list[dict]:
    files = sorted(glob.glob(str(SCRIPTS / pattern)))
    runs = []
    for f in files:
        try:
            runs.append(json.load(open(f, encoding="utf-8")))
        except Exception as e:
            print(f"  [warn] failed to read {f}: {e}")
    return runs


def per_config_stats(runs: list[dict]) -> dict:
    if not runs:
        return {"n": 0}
    n = len(runs)
    cal = [r["n_cal_grade"] for r in runs]
    exc = [r["n_excellent"] for r in runs]
    band_hits_cal = {p: 0 for p in PARAM_ORDER}
    band_hits_exc = {p: 0 for p in PARAM_ORDER}
    means = {p: [] for p in PARAM_ORDER}
    offs = {p: [] for p in PARAM_ORDER}
    per_aoi = {p: {"eqpac": [], "natlsubpolar": []} for p in PARAM_ORDER}
    for r in runs:
        for p in PARAM_ORDER:
            info = r["params"][p]
            if info["joint_band"] in BANDS_CAL:
                band_hits_cal[p] += 1
            if info["joint_band"] == "Excellent":
                band_hits_exc[p] += 1
            means[p].append(info["joint_recovered"])
            offs[p].append(info["joint_abs_rel_offset"])
            pao = info.get("per_aoi_recovered") or {}
            for k in ("eqpac", "natlsubpolar"):
                if k in pao:
                    per_aoi[p][k].append(pao[k])
    return {
        "n": n,
        "n_at_6": sum(1 for c in cal if c >= 6),
        "n_at_5": sum(1 for c in cal if c >= 5),
        "n_at_4": sum(1 for c in cal if c >= 4),
        "mean_cal": float(np.mean(cal)),
        "total_exc": int(sum(exc)),
        "band_hits_cal": band_hits_cal,
        "band_hits_exc": band_hits_exc,
        "param_means": {p: float(np.mean(means[p])) for p in PARAM_ORDER},
        "param_offs": {p: float(np.mean(offs[p])) for p in PARAM_ORDER},
        "per_aoi_means": {
            p: {k: (float(np.mean(per_aoi[p][k])) if per_aoi[p][k] else None)
                for k in ("eqpac", "natlsubpolar")}
            for p in PARAM_ORDER
        },
    }


def main():
    families = {
        "baseline_pr57": {"baseline": baseline_pattern()},
        "lambda_sweep_pr58": lambda_patterns(),
        "pic_alone_pr59": pic_alone_patterns(),
        "paired_heavy_pr59": paired_heavy_patterns(),
        "paired_light_pr59": paired_light_patterns(),
    }

    summary_rows = []
    param_rows = []

    print(f"{'family':<22} {'cfg':<22} {'n':<3} {'6+':<3} {'5+':<3} {'4+':<3} {'mean_cal':<9} {'tot_exc':<8} {'R_PICPOC(off)':<16} {'alpfe Cal':<10}")
    for fam, cfgs in families.items():
        for cfg, pat in cfgs.items():
            runs = load_runs(pat)
            s = per_config_stats(runs)
            if s["n"] == 0:
                print(f"{fam:<22} {cfg:<22} (no runs)")
                continue
            rp = s["param_means"]["R_PICPOC"]
            rp_off = s["param_offs"]["R_PICPOC"]
            alpfe_cal = s["band_hits_cal"]["alpfe"]
            print(f"{fam:<22} {cfg:<22} {s['n']:<3} {s['n_at_6']:<3} {s['n_at_5']:<3} {s['n_at_4']:<3} "
                  f"{s['mean_cal']:<9.2f} {s['total_exc']:<8} {rp:.4f} ({rp_off:.2f}){'':<5} {alpfe_cal}/{s['n']}")
            summary_rows.append({
                "family": fam, "config": cfg, "n": s["n"],
                "n_at_6": s["n_at_6"], "n_at_5": s["n_at_5"], "n_at_4": s["n_at_4"],
                "mean_cal": round(s["mean_cal"], 3),
                "total_exc": s["total_exc"],
                "R_PICPOC_mean": s["param_means"]["R_PICPOC"],
                "R_PICPOC_off": s["param_offs"]["R_PICPOC"],
                "R_PICPOC_eqpac": s["per_aoi_means"]["R_PICPOC"].get("eqpac"),
                "R_PICPOC_natlsubpolar": s["per_aoi_means"]["R_PICPOC"].get("natlsubpolar"),
                "alpfe_cal_rate": s["band_hits_cal"]["alpfe"] / s["n"],
                "scav_rat_cal_rate": s["band_hits_cal"]["scav_rat"] / s["n"],
                "R_PICPOC_cal_rate": s["band_hits_cal"]["R_PICPOC"] / s["n"],
            })
            for p in PARAM_ORDER:
                param_rows.append({
                    "family": fam, "config": cfg, "n": s["n"], "param": p,
                    "joint_mean": s["param_means"][p],
                    "joint_off": s["param_offs"][p],
                    "carroll": CARROLL[p],
                    "cal_hits": s["band_hits_cal"][p],
                    "exc_hits": s["band_hits_exc"][p],
                    "eqpac_mean": s["per_aoi_means"][p].get("eqpac"),
                    "natlsubpolar_mean": s["per_aoi_means"][p].get("natlsubpolar"),
                })

    # CSV outputs
    summary_path = OUT_DIR / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        w.writeheader(); w.writerows(summary_rows)
    print(f"\nWrote {summary_path}")

    param_path = OUT_DIR / "param_bands.csv"
    with param_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(param_rows[0].keys()))
        w.writeheader(); w.writerows(param_rows)
    print(f"Wrote {param_path}")

    # Observed PIC/POC per AOI from cached targets
    from darwindiff.safe_load import safe_torch_load
    ratios = {}
    for name in ["equatorial_pacific", "north_atlantic_subpolar"]:
        cache_path = Path(r"D:\ecco_darwin_v5") / "cache" / f"eqpac_targets_{name}.pt"
        if cache_path.is_file():
            cache = safe_torch_load(cache_path, map_location="cpu")
            pic = cache["pic_binned"]; poc = cache["poc_binned"]
            ok = np.isfinite(pic) & np.isfinite(poc) & (pic > 0) & (poc > 0)
            ratios[name] = {
                "n_cells_ok": int(ok.sum()),
                "PIC_mean": float(pic[ok].mean()),
                "POC_mean": float(poc[ok].mean()),
                "ratio_of_means": float(pic[ok].mean() / poc[ok].mean()),
                "mean_of_ratios": float((pic[ok] / poc[ok]).mean()),
            }
    obs_path = OUT_DIR / "obs_pic_poc_per_aoi.csv"
    if ratios:
        with obs_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["aoi"] + list(next(iter(ratios.values())).keys()))
            w.writeheader()
            for aoi, vals in ratios.items():
                w.writerow({"aoi": aoi, **vals})
        print(f"Wrote {obs_path}")

    # Plots
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[warn] matplotlib unavailable; skipping plots")
        return

    # Plot 1: R_PICPOC joint mean by config, with Carroll reference
    fig, ax = plt.subplots(figsize=(11, 4.5))
    xs = list(range(len(summary_rows)))
    rps = [r["R_PICPOC_mean"] for r in summary_rows]
    labels = [f"{r['family'].split('_pr')[0]}\n{r['config']}" for r in summary_rows]
    colors = []
    for r in summary_rows:
        if r["family"] == "baseline_pr57": colors.append("#999")
        elif r["family"] == "lambda_sweep_pr58": colors.append("#4682b4")
        elif r["family"] == "pic_alone_pr59": colors.append("#d62728")
        elif r["family"] == "paired_heavy_pr59": colors.append("#2ca02c")
        else: colors.append("#9467bd")
    ax.bar(xs, rps, color=colors)
    ax.axhline(CARROLL["R_PICPOC"], color="k", ls="--", lw=1, label=f"Carroll = {CARROLL['R_PICPOC']:.4f}")
    ax.axhline(0.5 * CARROLL["R_PICPOC"], color="k", ls=":", lw=0.7, alpha=0.5, label=f"Cal-grade (~0.50 off) at {0.5*CARROLL['R_PICPOC']:.4f}")
    ax.set_xticks(xs); ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("R_PICPOC joint mean")
    ax.set_title("R_PICPOC recovered across the v3.0 arc")
    ax.legend(loc="upper left", fontsize=8)
    plt.tight_layout()
    plot1 = OUT_DIR / "r_picpoc_distribution.png"
    plt.savefig(plot1, dpi=140); plt.close()
    print(f"Wrote {plot1}")

    # Plot 2: per-AOI R_PICPOC scatter (eqpac vs natl)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    for r in summary_rows:
        eq = r["R_PICPOC_eqpac"]; na = r["R_PICPOC_natlsubpolar"]
        if eq is None or na is None: continue
        c = ({"baseline_pr57": "#999", "lambda_sweep_pr58": "#4682b4",
              "pic_alone_pr59": "#d62728", "paired_heavy_pr59": "#2ca02c",
              "paired_light_pr59": "#9467bd"})[r["family"]]
        ax.scatter(eq, na, s=80, c=c, alpha=0.8, edgecolor="k", linewidth=0.5)
    ax.axhline(CARROLL["R_PICPOC"], color="k", ls="--", lw=1, alpha=0.6)
    ax.axvline(CARROLL["R_PICPOC"], color="k", ls="--", lw=1, alpha=0.6)
    # observed PIC/POC ratios
    if "equatorial_pacific" in ratios:
        ax.axvline(ratios["equatorial_pacific"]["ratio_of_means"], color="#4682b4", ls=":", lw=1,
                   label=f"obs eqpac PIC/POC = {ratios['equatorial_pacific']['ratio_of_means']:.3f}")
    if "north_atlantic_subpolar" in ratios:
        ax.axhline(ratios["north_atlantic_subpolar"]["ratio_of_means"], color="#d62728", ls=":", lw=1,
                   label=f"obs natl PIC/POC = {ratios['north_atlantic_subpolar']['ratio_of_means']:.3f}")
    ax.set_xlabel("R_PICPOC eqpac")
    ax.set_ylabel("R_PICPOC natlsubpolar")
    ax.set_title("Per-AOI R_PICPOC across the v3.0 arc")
    ax.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plot2 = OUT_DIR / "per_aoi_r_picpoc.png"
    plt.savefig(plot2, dpi=140); plt.close()
    print(f"Wrote {plot2}")

    # Plot 3: trade-off scatter — alpfe Cal rate vs R_PICPOC Cal rate
    fig, ax = plt.subplots(figsize=(7, 6))
    for r in summary_rows:
        c = ({"baseline_pr57": "#999", "lambda_sweep_pr58": "#4682b4",
              "pic_alone_pr59": "#d62728", "paired_heavy_pr59": "#2ca02c",
              "paired_light_pr59": "#9467bd"})[r["family"]]
        ax.scatter(r["alpfe_cal_rate"], r["R_PICPOC_cal_rate"], s=100, c=c, alpha=0.85,
                   edgecolor="k", linewidth=0.5,
                   label=r["family"] if r["config"] in ("baseline", "peraoi_lam0.1",
                                                         "picabsW1.0", "poc1.0_pic1.0",
                                                         "poc0.1_pic0.5") else None)
    ax.set_xlim(-0.05, 1.05); ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("alpfe Cal-grade rate (fraction of seeds)")
    ax.set_ylabel("R_PICPOC Cal-grade rate (fraction of seeds)")
    ax.set_title("The trade-off: anchoring R_PICPOC costs the iron pair")
    ax.legend(loc="upper right", fontsize=8)
    # diagonal "win-win" line
    ax.plot([0, 1], [0, 1], "k:", alpha=0.3, lw=1)
    plt.tight_layout()
    plot3 = OUT_DIR / "tradeoff_iron_vs_rpicpoc.png"
    plt.savefig(plot3, dpi=140); plt.close()
    print(f"Wrote {plot3}")


if __name__ == "__main__":
    main()
