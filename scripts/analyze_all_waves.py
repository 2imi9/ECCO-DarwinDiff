"""Unified post-sweep analysis across all overnight Basin C waves.

Aggregates configs from:
  D:\\runs\\bcr_<stamp>\\         (V1 + V2 — recovered Arc 6, Arc 7 #1-#2 + V2 arcs)
  D:\\runs\\bcr_w2_<stamp>\\      (Wave 2 — orthogonal-lever sensitivity)
  D:\\runs\\bcr_w3_<stamp>\\      (Wave 3 — 2D grids + n=40 robustness)

Extracts per-config lever values from JSON content (robust to naming
variations across waves). Produces:
  - Cross-wave ranked table (markdown)
  - Per-arc lever-response figures (PNG)
  - Basin C robustness summary (n combined across waves)
  - Mutex-binarity verdict
  - 6/6 surface (if any)

Output: docs/findings/modis_arc/all_waves_<now>/
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS_ROOT = Path(r"D:\runs")

CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']


def latest_wave_dirs() -> dict[str, Path]:
    """Return {'wave1': path, 'wave2': path, 'wave3': path}, missing waves
    map to None."""
    out: dict[str, Path] = {}
    for prefix, key in [("bcr_w3_", "wave3"),
                         ("bcr_w2_", "wave2"),
                         ("bcr_", "wave1")]:
        # The non-w_ variants of "bcr_" must NOT match bcr_w2_ or bcr_w3_
        candidates = []
        for p in RUNS_ROOT.glob(f"{prefix}*"):
            if not p.is_dir():
                continue
            name = p.name
            if prefix == "bcr_" and (name.startswith("bcr_w2_") or name.startswith("bcr_w3_")):
                continue
            candidates.append(p)
        candidates.sort(key=lambda p: p.name, reverse=True)
        out[key] = candidates[0] if candidates else None
    return out


def aggregate_config(config_dir: Path) -> dict | None:
    files = sorted(glob.glob(str(config_dir / "*.json")))
    if not files:
        return None
    runs = []
    for f in files:
        try:
            runs.append(json.load(open(f)))
        except Exception:
            continue
    if not runs:
        return None

    cal_counts = [r["n_cal_grade"] for r in runs]
    exc_counts = [r["n_excellent"] for r in runs]

    iron_pair_hits = 0
    for r in runs:
        a = r.get("params", {}).get("alpfe", {}).get("joint_band", "")
        s = r.get("params", {}).get("scav_rat", {}).get("joint_band", "")
        if a in ("Cal-grade", "Excellent") and s in ("Cal-grade", "Excellent"):
            iron_pair_hits += 1

    per_param_cal = {}
    for p in CARROLL_PARAMS:
        per_param_cal[p] = sum(
            1 for r in runs
            if r.get("params", {}).get(p, {}).get("joint_band", "")
               in ("Cal-grade", "Excellent")
        )

    # Levers (robust extraction from JSON content)
    levers = {}
    for k in ['pic_abs_w', 'poc_abs_w', 'posi_w', 'f_co2_abs_w',
              'chl1_w_extra', 'fet_w', 'pinn_w', 'geotraces_w',
              'geotraces_sub_w', 'poc_sub_w', 'geotraces_poc_sub_w',
              'consistency_lambda', 'dinn_hidden_dim', 'n_epochs',
              'use_mehrbach_k1k2', 'modis_pic_abs_w']:
        # Lever values are constant across the seed batch
        val = runs[0].get(k)
        if val is not None:
            levers[k] = val
    aoi_w = runs[0].get('aoi_weights')
    if aoi_w:
        levers['aoi_weights'] = aoi_w

    return {
        "n_seeds": len(runs),
        "n_at_6": sum(1 for c in cal_counts if c >= 6),
        "n_at_5": sum(1 for c in cal_counts if c >= 5),
        "n_at_4": sum(1 for c in cal_counts if c >= 4),
        "n_at_3": sum(1 for c in cal_counts if c >= 3),
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "total_excellents": sum(exc_counts),
        "iron_pair_joint": iron_pair_hits,
        "per_param_cal": per_param_cal,
        "levers": levers,
        "cal_counts": cal_counts,
        "seeds": [r.get("seed") for r in runs],
    }


def classify_arc(config_name: str, levers: dict) -> str:
    """Bucket each config into a lever-response arc for plotting."""
    name = config_name.lower()
    if name.startswith(("arc6", "a6_", "w2f_", "w3e_", "e_basinC", "e_basinc")):
        return "basinC_baseline"
    if name.startswith(("arc7", "a7_")) or ("pic_abs_w" in levers and
                                              levers.get("pic_abs_w", 0) > 0
                                              and levers.get("poc_abs_w", 0) > 0):
        return "arc7_paired"
    if name.startswith(("arc1", "a1_")) or ("pic_abs_w" in levers and
                                              levers.get("pic_abs_w", 0) > 0
                                              and not levers.get("poc_abs_w", 0)):
        return "arc1_pic_alone"
    if name.startswith(("arc2", "a2_")) or ("poc_abs_w" in levers and
                                              levers.get("poc_abs_w", 0) > 0
                                              and not levers.get("pic_abs_w", 0)):
        return "arc2_poc_alone"
    if name.startswith(("arc3", "a3_chl")) or "chl1_w_extra" in levers and \
       levers.get("chl1_w_extra", 0) not in (0, 3.0):
        return "arc3_chl1_response"
    if name.startswith(("arc5", "a5_ep")):
        return "arc5_longer_epochs"
    if name.startswith(("a4_so", "arc4")):
        return "arc4_so_weight"
    if name.startswith(("a8_", "arc8")):
        return "arc8_architecture"
    if name.startswith(("a9_", "arc9")):
        return "arc9_carbonate"
    if name.startswith(("w2a_", "w2b_", "w2c_", "w2d_", "w2e_", "w2f_")):
        return f"wave2_{name[:3]}"
    if name.startswith(("a_posi", "b_natl", "c_chl", "d_pdep", "e_basin")):
        return f"wave3_{name[:6]}"
    return "other"


def plot_lever_response(configs: list[tuple[float, dict]],
                         lever_name: str, out_path: Path, title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    cs = sorted(configs, key=lambda c: c[0])
    xs = [c[0] for c in cs]
    iron = [c[1]["iron_pair_joint"] / max(c[1]["n_seeds"], 1) for c in cs]
    rpicpoc = [c[1]["per_param_cal"]["R_PICPOC"] / max(c[1]["n_seeds"], 1) for c in cs]
    diatomgraz = [c[1]["per_param_cal"]["diatomgraz"] / max(c[1]["n_seeds"], 1) for c in cs]
    mean_cal = [c[1]["mean_cal"] for c in cs]
    n_per = [c[1]["n_seeds"] for c in cs]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(xs, iron, marker="o", label="iron-pair (alpfe+scav_rat)")
    ax1.plot(xs, rpicpoc, marker="s", label="R_PICPOC Cal+")
    ax1.plot(xs, diatomgraz, marker="^", label="diatomgraz Cal+")
    ax1.set_xlabel(lever_name)
    ax1.set_ylabel("rate per seed")
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(loc="best", fontsize=8)
    ax1.grid(alpha=0.3)
    ax1.set_title(f"{title}: per-param recovery")

    ax2.plot(xs, mean_cal, marker="o", color="black")
    for ax in [ax2]:
        ax.set_xlabel(lever_name)
    ax2.set_ylabel("mean # Cal-grade params (out of 6)")
    ax2.set_ylim(0, 6.1)
    ax2.axhline(5, color="red", linestyle="--", alpha=0.5, label="5/6 ceiling")
    ax2.axhline(6, color="green", linestyle="--", alpha=0.5, label="6/6 target")
    ax2.legend(loc="best", fontsize=8)
    ax2.grid(alpha=0.3)
    ax2.set_title(f"{title}: mean_cal (avg n={sum(n_per)/len(n_per):.0f})")
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def main():
    waves = latest_wave_dirs()
    print("Wave dirs:")
    for k, v in waves.items():
        print(f"  {k}: {v}")
    if all(v is None for v in waves.values()):
        print("No wave dirs found.")
        sys.exit(1)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = ROOT / "docs" / "findings" / "modis_arc" / f"all_waves_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    # Aggregate every config from every wave
    all_configs: list[dict] = []
    for wave_label, root in waves.items():
        if root is None:
            continue
        for cfg_dir in sorted(root.iterdir()):
            if not cfg_dir.is_dir():
                continue
            agg = aggregate_config(cfg_dir)
            if agg is None:
                continue
            agg["wave"] = wave_label
            agg["config_name"] = cfg_dir.name
            agg["arc"] = classify_arc(cfg_dir.name, agg["levers"])
            all_configs.append(agg)
            print(f"  [{wave_label}] {cfg_dir.name}: n={agg['n_seeds']}  "
                  f"6+={agg['n_at_6']}  iron-pair={agg['iron_pair_joint']}  "
                  f"mean_cal={agg['mean_cal']:.2f}")

    if not all_configs:
        print("No completed configs found across waves.")
        sys.exit(0)

    # Rank all configs by paper-relevant criteria
    ranked = sorted(all_configs, key=lambda a: (
        -a["n_at_6"], -a["n_at_5"], -a["iron_pair_joint"],
        -a["total_excellents"], -a["mean_cal"],
    ))

    # Group by arc for lever-response plots
    by_arc: dict[str, list[dict]] = defaultdict(list)
    for c in all_configs:
        by_arc[c["arc"]].append(c)

    # Lever-response figures (extract x-axis from levers)
    arc_plots = [
        ("arc1_pic_alone", "pic_abs_w", "PIC_ABS_W (alone)",
         "arc1_pic_alone.png"),
        ("arc2_poc_alone", "poc_abs_w", "POC_ABS_W (alone)",
         "arc2_poc_alone.png"),
        ("arc7_paired", "pic_abs_w", "PIC_ABS_W (paired with POC = PIC/2)",
         "arc7_paired_dose.png"),
        ("arc3_chl1_response", "chl1_w_extra", "CHL1_W_EXTRA",
         "arc3_chl1.png"),
        ("arc5_longer_epochs", "n_epochs", "NB23_N_EPOCHS",
         "arc5_epochs.png"),
    ]
    for arc, lever_key, lever_name, fname in arc_plots:
        cfgs = by_arc.get(arc, [])
        if not cfgs:
            continue
        pts = [(c["levers"].get(lever_key, 0), c) for c in cfgs
               if c["levers"].get(lever_key, 0) is not None]
        if pts:
            plot_lever_response(pts, lever_name, fig_dir / fname,
                                f"{arc}: lever response")

    # Build markdown report
    lines = [
        f"# Basin C overnight 2026-05-19/20 — all-waves analysis ({stamp})",
        "",
        "## Source roots",
        "",
    ]
    for k, v in waves.items():
        lines.append(f"- {k}: `{v}`")
    lines.extend(["", "## Top 20 configs (paper-relevant ranking)", "",
                  "| Rank | Wave | Config | 6+/n | 5+/n | iron-pair | "
                  "R_PICPOC | diatomgraz | mean_cal | tot_exc |",
                  "|---|---|---|---|---|---|---|---|---|---|"])
    for i, c in enumerate(ranked[:20], 1):
        lines.append(
            f"| {i} | {c['wave']} | {c['config_name']} | "
            f"{c['n_at_6']}/{c['n_seeds']} | "
            f"{c['n_at_5']}/{c['n_seeds']} | "
            f"{c['iron_pair_joint']}/{c['n_seeds']} | "
            f"{c['per_param_cal']['R_PICPOC']}/{c['n_seeds']} | "
            f"{c['per_param_cal']['diatomgraz']}/{c['n_seeds']} | "
            f"{c['mean_cal']:.2f} | "
            f"{c['total_excellents']} |"
        )

    # 6/6 hits
    lines.extend(["", "## 6/6 hits", ""])
    six_six = [c for c in all_configs if c["n_at_6"] > 0]
    if six_six:
        for c in six_six:
            lines.append(f"- **{c['wave']}/{c['config_name']}**: "
                         f"{c['n_at_6']}/{c['n_seeds']} seeds at 6/6")
    else:
        lines.append("(none — 5/6 remains the laptop ceiling)")

    # Iron-pair survival summary
    lines.extend(["", "## Iron-pair survival summary", ""])
    iron_holding = [c for c in all_configs if c["iron_pair_joint"] >= 8]
    iron_partial = [c for c in all_configs if 0 < c["iron_pair_joint"] < 8]
    iron_collapsed = [c for c in all_configs if c["iron_pair_joint"] == 0]
    lines.extend([
        f"- **Iron-pair holds (≥8/n):** {len(iron_holding)} configs",
        f"- **Partial (1-7/n):** {len(iron_partial)} configs",
        f"- **Collapsed (0/n):** {len(iron_collapsed)} configs",
        "",
    ])

    # Basin C combined n
    basinC_baselines = by_arc.get("basinC_baseline", [])
    if basinC_baselines:
        total_n = sum(c["n_seeds"] for c in basinC_baselines)
        total_iron = sum(c["iron_pair_joint"] for c in basinC_baselines)
        lines.extend([
            "## Basin C iron-pair recovery across combined seeds",
            "",
            f"Total seeds at Basin C base: **{total_n}**",
            f"Iron-pair (alpfe+scav_rat both Cal+): **{total_iron}/{total_n}** "
            f"({100*total_iron/total_n:.0f}%)",
            "",
        ])
        for c in basinC_baselines:
            lines.append(f"- `{c['config_name']}` ({c['wave']}): "
                         f"iron-pair={c['iron_pair_joint']}/{c['n_seeds']}")
        lines.append("")

    # Figures
    lines.extend(["## Figures", ""])
    for png in sorted(fig_dir.glob("*.png")):
        lines.append(f"![{png.stem}](figures/{png.name})")
        lines.append("")

    summary_path = out_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote {summary_path}")


if __name__ == "__main__":
    main()
