"""Post-sweep analysis for overnight Basin C refinement run.

Reads per-config JSONs from D:\\runs\\v3.0_basinC_refine_<stamp>\\, produces:
  - Cross-arc ranked table (markdown)
  - Per-arc lever-response figures (matplotlib PNG)
  - Iron-pair recovery summary
  - Mutex-binarity diagnostic (Arc 7 paired doses)

Run with: python scripts/analyze_basinC_refine.py [--stamp YYYYMMDD_HHMM]
If --stamp omitted, picks the most recent v3.0_basinC_refine_* on D:\\runs\\.

Output: docs/findings/pace_arc/basinC_refine_<stamp>/  with summary.md +
  figures/*.png.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNS_ROOT = Path(r"D:\runs")

CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']


def find_latest_stamp() -> tuple[str, Path]:
    """Returns (stamp, sweep_root). Prefers bcr_* (v2 short-path) over
    v3.0_basinC_refine_* (v1)."""
    bcr = sorted(RUNS_ROOT.glob("bcr_*"),
                 key=lambda p: p.name, reverse=True)
    if bcr:
        stamp = bcr[0].name.removeprefix("bcr_")
        return stamp, bcr[0]
    v1 = sorted(RUNS_ROOT.glob("v3.0_basinC_refine_*"),
                key=lambda p: p.name, reverse=True)
    if v1:
        stamp = v1[0].name.removeprefix("v3.0_basinC_refine_")
        return stamp, v1[0]
    print("No bcr_* or v3.0_basinC_refine_* directories found on D:\\runs\\")
    sys.exit(1)


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
    rpicpoc_cal = 0
    diatomgraz_cal = 0
    for r in runs:
        params = r.get("params", {})
        a = params.get("alpfe", {}).get("joint_band", "")
        s = params.get("scav_rat", {}).get("joint_band", "")
        rp = params.get("R_PICPOC", {}).get("joint_band", "")
        dg = params.get("diatomgraz", {}).get("joint_band", "")
        if a in ("Cal-grade", "Excellent") and s in ("Cal-grade", "Excellent"):
            iron_pair_hits += 1
        if rp in ("Cal-grade", "Excellent"):
            rpicpoc_cal += 1
        if dg in ("Cal-grade", "Excellent"):
            diatomgraz_cal += 1

    per_param_cal = {}
    for p in CARROLL_PARAMS:
        per_param_cal[p] = sum(
            1 for r in runs
            if r.get("params", {}).get(p, {}).get("joint_band", "")
               in ("Cal-grade", "Excellent")
        )

    return {
        "n_seeds": len(runs),
        "n_at_6": sum(1 for c in cal_counts if c >= 6),
        "n_at_5": sum(1 for c in cal_counts if c >= 5),
        "n_at_4": sum(1 for c in cal_counts if c >= 4),
        "n_at_3": sum(1 for c in cal_counts if c >= 3),
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "total_excellents": sum(exc_counts),
        "iron_pair_joint": iron_pair_hits,
        "rpicpoc_cal": rpicpoc_cal,
        "diatomgraz_cal": diatomgraz_cal,
        "per_param_cal": per_param_cal,
        "cal_counts": cal_counts,
        "seeds": [r.get("seed") for r in runs],
    }


def build_cross_arc_table(rows: list[tuple[str, dict]]) -> str:
    rows_sorted = sorted(rows, key=lambda r: (
        -r[1]["n_at_6"],
        -r[1]["n_at_5"],
        -r[1]["iron_pair_joint"],
        -r[1]["total_excellents"],
        -r[1]["mean_cal"],
    ))
    lines = [
        "| Rank | Config | 6+/n | 5+/n | 4+/n | iron-pair | R_PICPOC | diatomgraz | mean_cal | tot_exc |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, (name, a) in enumerate(rows_sorted, 1):
        lines.append(
            f"| {i} | {name} | {a['n_at_6']}/{a['n_seeds']} | "
            f"{a['n_at_5']}/{a['n_seeds']} | {a['n_at_4']}/{a['n_seeds']} | "
            f"{a['iron_pair_joint']}/{a['n_seeds']} | "
            f"{a['rpicpoc_cal']}/{a['n_seeds']} | "
            f"{a['diatomgraz_cal']}/{a['n_seeds']} | "
            f"{a['mean_cal']:.2f} | {a['total_excellents']} |"
        )
    return "\n".join(lines)


def plot_lever_response(configs: list[tuple[float, dict]],
                        lever_name: str, out_path: Path, title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available; skipping plot")
        return

    configs_sorted = sorted(configs, key=lambda c: c[0])
    xs = [c[0] for c in configs_sorted]
    n = [c[1]["n_seeds"] for c in configs_sorted]
    iron = [c[1]["iron_pair_joint"] / max(c[1]["n_seeds"], 1) for c in configs_sorted]
    rpicpoc = [c[1]["rpicpoc_cal"] / max(c[1]["n_seeds"], 1) for c in configs_sorted]
    diatomgraz = [c[1]["diatomgraz_cal"] / max(c[1]["n_seeds"], 1) for c in configs_sorted]
    mean_cal = [c[1]["mean_cal"] for c in configs_sorted]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(xs, iron, marker="o", label="iron-pair (alpfe+scav_rat) rate")
    ax1.plot(xs, rpicpoc, marker="s", label="R_PICPOC Cal+ rate")
    ax1.plot(xs, diatomgraz, marker="^", label="diatomgraz Cal+ rate")
    ax1.set_xlabel(lever_name)
    ax1.set_ylabel("recovery rate (per seed)")
    ax1.set_ylim(-0.05, 1.05)
    ax1.legend(loc="best", fontsize=8)
    ax1.grid(alpha=0.3)
    ax1.set_title(f"{title}: per-param recovery")

    ax2.plot(xs, mean_cal, marker="o", color="black")
    ax2.set_xlabel(lever_name)
    ax2.set_ylabel("mean # Cal-grade params (out of 6)")
    ax2.set_ylim(0, 6.1)
    ax2.axhline(5, color="red", linestyle="--", alpha=0.5, label="5/6 ceiling")
    ax2.axhline(6, color="green", linestyle="--", alpha=0.5, label="6/6 target")
    ax2.legend(loc="best", fontsize=8)
    ax2.grid(alpha=0.3)
    ax2.set_title(f"{title}: mean_cal across {n[0]} seeds")

    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=None,
                    help="Sweep stamp (YYYYMMDD_HHMM). Defaults to latest.")
    args = ap.parse_args()
    if args.stamp:
        stamp = args.stamp
        # Try bcr_ first, fall back to v3.0_basinC_refine_
        sweep_root = RUNS_ROOT / f"bcr_{stamp}"
        if not sweep_root.is_dir():
            sweep_root = RUNS_ROOT / f"v3.0_basinC_refine_{stamp}"
        if not sweep_root.is_dir():
            print(f"Sweep dir not found for stamp {stamp}")
            sys.exit(1)
    else:
        stamp, sweep_root = find_latest_stamp()
    print(f"Analyzing sweep at {sweep_root}")

    out_dir = ROOT / "docs" / "findings" / "pace_arc" / f"basinC_refine_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    # Aggregate every config dir
    all_configs: dict[str, dict] = {}
    for cfg_dir in sorted(sweep_root.iterdir()):
        if not cfg_dir.is_dir():
            continue
        agg = aggregate_config(cfg_dir)
        if agg is None:
            print(f"  {cfg_dir.name}: no JSONs (sweep may still be running)")
            continue
        all_configs[cfg_dir.name] = agg
        print(f"  {cfg_dir.name}: n={agg['n_seeds']}, "
              f"6+={agg['n_at_6']}, 5+={agg['n_at_5']}, "
              f"iron-pair={agg['iron_pair_joint']}, "
              f"mean_cal={agg['mean_cal']:.2f}")

    if not all_configs:
        print("No completed configs to analyze.")
        sys.exit(0)

    # Cross-arc ranked table
    cross_table = build_cross_arc_table(list(all_configs.items()))

    # Lever-response figures
    arc1 = [(float(k.replace("arc1_pic_w", "")), v)
            for k, v in all_configs.items() if k.startswith("arc1_pic_w")]
    arc2 = [(float(k.replace("arc2_poc_w", "")), v)
            for k, v in all_configs.items() if k.startswith("arc2_poc_w")]
    arc3 = [(float(k.replace("arc3_chl1W", "")), v)
            for k, v in all_configs.items() if k.startswith("arc3_chl1W")]
    arc5 = [(int(k.replace("arc5_epochs", "")), v)
            for k, v in all_configs.items() if k.startswith("arc5_epochs")]
    if arc1:
        plot_lever_response(arc1, "PIC_ABS_W",
                            fig_dir / "arc1_pic_dose_response.png",
                            "Arc 1 — PIC anchor dose-response (Basin C base)")
    if arc2:
        plot_lever_response(arc2, "POC_ABS_W",
                            fig_dir / "arc2_poc_dose_response.png",
                            "Arc 2 — POC anchor dose-response (Basin C base)")
    if arc3:
        plot_lever_response(arc3, "CHL1_W_EXTRA",
                            fig_dir / "arc3_chl1_response.png",
                            "Arc 3 — CHL1_W_EXTRA response (Basin C optimum)")
    if arc5:
        plot_lever_response(arc5, "NB23_N_EPOCHS",
                            fig_dir / "arc5_epochs_response.png",
                            "Arc 5 — training length response (Basin C base)")

    # Arc 7 paired (PIC + POC) — index by PIC dose for plotting
    arc7 = []
    for k, v in all_configs.items():
        if k.startswith("arc7_paired_pic"):
            try:
                pic = float(k.split("_pic")[1].split("_")[0])
                arc7.append((pic, v))
            except Exception:
                continue
    if arc7:
        plot_lever_response(arc7, "PIC_ABS_W (paired with POC = PIC/2)",
                            fig_dir / "arc7_paired_dose_response.png",
                            "Arc 7 — PIC+POC paired anchors (binary mutex test)")

    # Write the markdown summary
    body = [
        f"# Basin C refinement sweep — {stamp}",
        "",
        f"Sweep root: `{sweep_root}`",
        f"Completed configs: {len(all_configs)} / 33",
        "",
        "## Cross-arc ranked results (paper-relevant ordering)",
        "",
        cross_table,
        "",
        "## Figures",
        "",
    ]
    for png in sorted(fig_dir.glob("*.png")):
        body.append(f"![{png.stem}](figures/{png.name})")
        body.append("")

    # Key findings — programmatically derived
    body.extend(["", "## Key findings (auto-derived)", ""])
    six_six = [(k, v) for k, v in all_configs.items() if v["n_at_6"] > 0]
    if six_six:
        body.append("### 6/6 unlock")
        body.append("")
        body.append("**Configs with at least one 6/6 seed:**")
        body.append("")
        for k, v in six_six:
            body.append(f"- `{k}`: {v['n_at_6']}/{v['n_seeds']} seeds at 6/6")
        body.append("")
    else:
        body.append("No 6/6 unlock across the sweep. 5/6 remains the laptop ceiling.")
        body.append("")

    # Basin C baseline (arc 6 + base configs)
    basin_c_runs = [(k, v) for k, v in all_configs.items()
                    if k == "arc6_basinC_seeds10-19"]
    if basin_c_runs:
        k, v = basin_c_runs[0]
        body.append(f"### Basin C n=20 baseline (Arc 6)")
        body.append("")
        body.append(
            f"- iron-pair recovery: {v['iron_pair_joint']}/{v['n_seeds']} seeds "
            f"({100*v['iron_pair_joint']/v['n_seeds']:.0f}%)"
        )
        body.append(
            f"- mean_cal: {v['mean_cal']:.2f}  "
            f"6+/n: {v['n_at_6']}/{v['n_seeds']}  "
            f"5+/n: {v['n_at_5']}/{v['n_seeds']}"
        )
        body.append("")

    # Arc 7 binary-mutex verdict
    if arc7:
        body.append("### Arc 7 — binary mutex verdict")
        body.append("")
        for pic, v in sorted(arc7):
            verdict = "iron pair holds" if v["iron_pair_joint"] >= 7 else "iron pair collapses"
            body.append(
                f"- PIC={pic} POC={pic/2}: iron-pair={v['iron_pair_joint']}/{v['n_seeds']} "
                f"({verdict}), R_PICPOC Cal+: {v['rpicpoc_cal']}/{v['n_seeds']}"
            )
        body.append("")

    summary_path = out_dir / "summary.md"
    summary_path.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"\nWrote analysis to {summary_path}")


if __name__ == "__main__":
    main()
