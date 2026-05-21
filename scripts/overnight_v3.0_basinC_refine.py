"""Overnight v3.0 Basin C refinement sweep — parameter-learner methodology test.

Goal: probe whether Basin C (alpfe + scav_rat 10/10 at F2: D4 + CHL1_W=3.0) is
extendable from 5/6 toward 6/6, and characterize the lever-response landscape
around it for the proof-of-concept paper.

This sweep tests nine orthogonal methodological hypotheses:

  Arc 1 (PIC anchor dose-response, ~30 min):
    Binary-mutex test. Does a low-dose PIC anchor (Basin B's R_PICPOC
    unlock lever) wipe Basin C's iron pair?
      PIC_ABS_W in {0.02, 0.05, 0.10, 0.20}

  Arc 2 (POC anchor dose-response, ~30 min):
    POC alone (no paired PIC) — fourth basin probe.
      POC_ABS_W in {0.05, 0.10, 0.20, 0.50}

  Arc 3 (CHL1_W_EXTRA response curve, ~45 min):
    Fine map of Basin C around the 3.0 optimum.
      CHL1_W_EXTRA in {2.0, 2.5, 3.5, 4.0, 5.0, 7.0}

  Arc 4 (Southern Ocean weight refinement, ~30 min):
    Does tilting toward SO further pull diatomgraz into Cal-grade?
      AOI_W_SOUTHERNOCEANPAC in {1.5, 2.5, 3.0} + 1 rebalance

  Arc 5 (Longer training, ~50 min):
    Does diatomgraz catch up with more epochs?
      NB23_N_EPOCHS in {2000, 2500, 3000}

  Arc 6 (Basin C n=20 robustness, ~10 min):
    Seeds 10-19 at Basin C base. Locks in iron-pair claim at n=20.

  Arc 7 (PIC + POC paired anchors on Basin C, ~30 min):
    Highest-EV combination. Does Basin B's paired-anchor machinery coexist
    with Basin C iron pair at sub-Basin-B doses? Either falsifies binary
    mutex (6/6 path) or strengthens it.
      (PIC, POC) in {(0.05, 0.025), (0.10, 0.05), (0.20, 0.10), (0.50, 0.25)}

  Arc 8 (DINN capacity + MLD channel, ~35 min):
    Architectural axes on Basin C — might find a 4th basin or expand C.
      hd in {64, 128}, MLD_CHANNEL on/off at hd=32 and hd=64

  Arc 9 (Carbonate alignment on Basin C, ~25 min):
    USE_MEHRBACH_K1K2 + F_CO2_ABS_W on Basin C base. PR #62's Smallgrow
    lever was never combined with Basin C.
      Mehrbach=1, F_CO2_ABS_W=0.01, Mehrbach=1 + F_CO2_ABS_W=0.005

Total: 33 configs, est ~4.3 hrs runtime. Hard 5-hour cap via TIME_CAP_S.

Stop sentinel:
  Touch logs/overnight_v3.0_basinC_refine_<stamp>/STOP to cleanly halt
  at the next config boundary.

Output:
  Per-config JSONs at D:\\runs\\v3.0_basinC_refine_<stamp>\\<config>\\.
  Per-config training logs + aggregated summary at
  logs/overnight_v3.0_basinC_refine_<stamp>/.

Runner: scripts/run_v3.0_with_modis_pic.py (Basin C lives here;
MODIS_PIC_ABS_W=0 always, per Jon's "Carroll-6 proof-of-concept first"
directive).
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
import json
import glob
from datetime import datetime
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNNER = HERE / "run_v3.0_with_modis_pic.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_basinC_refine_{STAMP}"
OUTPUT_ROOT = Path(rf"D:\runs\v3.0_basinC_refine_{STAMP}")

# ============================================================================
# Basin C base config (F2: D4 + CHL1_W_EXTRA=3.0)
# ============================================================================
BASE_ENV = {
    "AOIS": "eqpac,natlsubpolar,southernoceanpac",
    "AOI_ID_CHANNEL": "1",
    "POC_SUB_W": "0.5",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "AOI_W_SOUTHERNOCEANPAC": "2.0",
    "POSI_W": "1.0",
    "CHL1_W_EXTRA": "3.0",
    "NB23_N_EPOCHS": "1500",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

SEEDS_10 = "0,1,2,3,4,5,6,7,8,9"


# Each row is (config_name, env_overrides_relative_to_BASE_ENV).
# env_overrides MAY include NB23_SEEDS, NB23_N_EPOCHS, etc.

ARC1_PIC_DOSE = [
    ("arc1_pic_w0.02", {"PIC_ABS_W": "0.02", "NB23_SEEDS": SEEDS_10}),
    ("arc1_pic_w0.05", {"PIC_ABS_W": "0.05", "NB23_SEEDS": SEEDS_10}),
    ("arc1_pic_w0.10", {"PIC_ABS_W": "0.10", "NB23_SEEDS": SEEDS_10}),
    ("arc1_pic_w0.20", {"PIC_ABS_W": "0.20", "NB23_SEEDS": SEEDS_10}),
]

ARC2_POC_DOSE = [
    ("arc2_poc_w0.05", {"POC_ABS_W": "0.05", "NB23_SEEDS": SEEDS_10}),
    ("arc2_poc_w0.10", {"POC_ABS_W": "0.10", "NB23_SEEDS": SEEDS_10}),
    ("arc2_poc_w0.20", {"POC_ABS_W": "0.20", "NB23_SEEDS": SEEDS_10}),
    ("arc2_poc_w0.50", {"POC_ABS_W": "0.50", "NB23_SEEDS": SEEDS_10}),
]

ARC3_CHL1_RESPONSE = [
    ("arc3_chl1W2.0", {"CHL1_W_EXTRA": "2.0", "NB23_SEEDS": SEEDS_10}),
    ("arc3_chl1W2.5", {"CHL1_W_EXTRA": "2.5", "NB23_SEEDS": SEEDS_10}),
    ("arc3_chl1W3.5", {"CHL1_W_EXTRA": "3.5", "NB23_SEEDS": SEEDS_10}),
    ("arc3_chl1W4.0", {"CHL1_W_EXTRA": "4.0", "NB23_SEEDS": SEEDS_10}),
    ("arc3_chl1W5.0", {"CHL1_W_EXTRA": "5.0", "NB23_SEEDS": SEEDS_10}),
    ("arc3_chl1W7.0", {"CHL1_W_EXTRA": "7.0", "NB23_SEEDS": SEEDS_10}),
]

ARC4_AOI_WEIGHT = [
    ("arc4_so_w1.5", {"AOI_W_SOUTHERNOCEANPAC": "1.5", "NB23_SEEDS": SEEDS_10}),
    ("arc4_so_w2.5", {"AOI_W_SOUTHERNOCEANPAC": "2.5", "NB23_SEEDS": SEEDS_10}),
    ("arc4_so_w3.0", {"AOI_W_SOUTHERNOCEANPAC": "3.0", "NB23_SEEDS": SEEDS_10}),
    ("arc4_rebalance", {
        "AOI_W_NATLSUBPOLAR": "1.5",
        "AOI_W_SOUTHERNOCEANPAC": "2.0",
        "NB23_SEEDS": SEEDS_10,
    }),
]

ARC5_LONGER_EPOCHS = [
    ("arc5_epochs2000", {"NB23_N_EPOCHS": "2000", "NB23_SEEDS": SEEDS_10}),
    ("arc5_epochs2500", {"NB23_N_EPOCHS": "2500", "NB23_SEEDS": SEEDS_10}),
    ("arc5_epochs3000", {"NB23_N_EPOCHS": "3000", "NB23_SEEDS": SEEDS_10}),
]

# Arc 6: Basin C n=20 robustness extension
ARC6_BASIN_C_N20 = [
    ("arc6_basinC_seeds10-19", {"NB23_SEEDS": "10,11,12,13,14,15,16,17,18,19"}),
]

# Arc 7: PIC + POC paired anchors on Basin C (highest-EV combination test).
# (PIC, POC) ratios derived from Basin B (PR #63: 0.5, 0.25 = 2:1).
ARC7_PIC_POC_PAIRED = [
    ("arc7_paired_pic0.05_poc0.025",
     {"PIC_ABS_W": "0.05", "POC_ABS_W": "0.025", "NB23_SEEDS": SEEDS_10}),
    ("arc7_paired_pic0.10_poc0.05",
     {"PIC_ABS_W": "0.10", "POC_ABS_W": "0.05",  "NB23_SEEDS": SEEDS_10}),
    ("arc7_paired_pic0.20_poc0.10",
     {"PIC_ABS_W": "0.20", "POC_ABS_W": "0.10",  "NB23_SEEDS": SEEDS_10}),
    ("arc7_paired_pic0.50_poc0.25",
     {"PIC_ABS_W": "0.50", "POC_ABS_W": "0.25",  "NB23_SEEDS": SEEDS_10}),
]

# Arc 8: DINN capacity + MLD channel — architectural axes on Basin C.
ARC8_ARCHITECTURE = [
    ("arc8_hd64",        {"DINN_HIDDEN_DIM": "64",  "NB23_SEEDS": SEEDS_10}),
    ("arc8_hd128",       {"DINN_HIDDEN_DIM": "128", "NB23_SEEDS": SEEDS_10}),
    ("arc8_mld_hd32",    {"MLD_CHANNEL": "1", "NB23_SEEDS": SEEDS_10}),
    ("arc8_mld_hd64",    {"MLD_CHANNEL": "1", "DINN_HIDDEN_DIM": "64",
                          "NB23_SEEDS": SEEDS_10}),
]

# Arc 9: Carbonate alignment levers on Basin C. PR #62 Smallgrow lever combo.
ARC9_CARBONATE = [
    ("arc9_mehrbach",       {"USE_MEHRBACH_K1K2": "1", "NB23_SEEDS": SEEDS_10}),
    ("arc9_fco2_w0.01",     {"F_CO2_ABS_W": "0.01",    "NB23_SEEDS": SEEDS_10}),
    ("arc9_mehrbach_fco2",  {"USE_MEHRBACH_K1K2": "1",
                             "F_CO2_ABS_W": "0.005",
                             "NB23_SEEDS": SEEDS_10}),
]

# Order matters: Arc 6 (n=20 extension) first since it builds the n=20 paper
# baseline; Arc 7 (paired anchors, highest methodological EV) second; then
# the rest in original order. If interrupted by power loss or STOP, the
# critical results land earliest.
ALL_ARCS: list[tuple[str, list[tuple[str, dict]]]] = [
    ("Arc 6 -- Basin C n=20 robustness", ARC6_BASIN_C_N20),
    ("Arc 7 -- PIC+POC paired anchors on Basin C", ARC7_PIC_POC_PAIRED),
    ("Arc 1 -- PIC anchor dose-response (binary-mutex test)", ARC1_PIC_DOSE),
    ("Arc 2 -- POC anchor dose-response (untested combo)", ARC2_POC_DOSE),
    ("Arc 3 -- CHL1_W_EXTRA response curve (Basin C floor)", ARC3_CHL1_RESPONSE),
    ("Arc 4 -- Southern Ocean weight refinement", ARC4_AOI_WEIGHT),
    ("Arc 8 -- DINN capacity + MLD channel", ARC8_ARCHITECTURE),
    ("Arc 9 -- Carbonate alignment on Basin C", ARC9_CARBONATE),
    ("Arc 5 -- Longer training (diatomgraz equilibration)", ARC5_LONGER_EPOCHS),
]

# ============================================================================
# Runner orchestration
# ============================================================================
TIMEOUT_PER_RUN = 1800  # 30 min cap per config (n=10 batch typically ~7 min)


def progress(line: str, progress_path: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name: str, env_override: dict, progress_path: Path, stop_path: Path) -> dict:
    if stop_path.exists():
        progress(f"STOP sentinel -- skipping {name}", progress_path)
        return {"name": name, "status": "SKIPPED_STOP", "elapsed": 0.0,
                "env": env_override}

    config_out_dir = OUTPUT_ROOT / name
    config_out_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(BASE_ENV)
    env.update(env_override)
    env["OUTPUT_DIR"] = str(config_out_dir)

    progress(f"START {name}  overrides={env_override}  -> {config_out_dir}",
             progress_path)
    log_path = LOG_DIR / f"{name}.log"
    t0 = time.time()
    try:
        with log_path.open("w", encoding="utf-8") as logf:
            r = subprocess.run(
                [sys.executable, str(RUNNER)],
                env=env, stdout=logf, stderr=subprocess.STDOUT,
                cwd=str(ROOT), timeout=TIMEOUT_PER_RUN,
            )
        elapsed = time.time() - t0
        status = "OK" if r.returncode == 0 else f"FAIL exit={r.returncode}"
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        status = f"TIMEOUT {elapsed:.0f}s"
    except Exception as e:
        elapsed = time.time() - t0
        status = f"EXCEPTION {type(e).__name__}: {e}"
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", progress_path)
    return {"name": name, "status": status, "elapsed": elapsed,
            "env": env_override, "out_dir": str(config_out_dir)}


# ============================================================================
# Aggregation
# ============================================================================
CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']


def aggregate_config(config_out_dir: Path) -> dict | None:
    files = sorted(glob.glob(str(config_out_dir / "*.json")))
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

    # Default mode reported per-row is cellweighted; aoiweighted lives in
    # joint_recovery_aoiweighted (per the runner notes).
    cal_counts = [r["n_cal_grade"] for r in runs]
    exc_counts = [r["n_excellent"] for r in runs]

    # Iron-pair joint recovery flag: both alpfe AND scav_rat at Cal+
    iron_pair_hits = 0
    for r in runs:
        a = r.get("params", {}).get("alpfe", {}).get("joint_band", "")
        s = r.get("params", {}).get("scav_rat", {}).get("joint_band", "")
        if a in ("Cal-grade", "Excellent") and s in ("Cal-grade", "Excellent"):
            iron_pair_hits += 1

    # Miss distribution at 4+ Cal-grade
    misses_at_4 = {p: 0 for p in CARROLL_PARAMS}
    for r in runs:
        if r["n_cal_grade"] >= 4:
            for p in CARROLL_PARAMS:
                b = r.get("params", {}).get(p, {}).get("joint_band", "")
                if b not in ("Cal-grade", "Excellent"):
                    misses_at_4[p] += 1

    # Per-param Cal-grade-or-better counts (across all seeds)
    per_param_cal = {}
    for p in CARROLL_PARAMS:
        count = 0
        for r in runs:
            b = r.get("params", {}).get(p, {}).get("joint_band", "")
            if b in ("Cal-grade", "Excellent"):
                count += 1
        per_param_cal[p] = count

    return {
        "n_seeds": len(runs),
        "n_at_6": sum(1 for c in cal_counts if c >= 6),
        "n_at_5": sum(1 for c in cal_counts if c >= 5),
        "n_at_4": sum(1 for c in cal_counts if c >= 4),
        "n_at_3": sum(1 for c in cal_counts if c >= 3),
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "total_excellents": sum(exc_counts),
        "iron_pair_joint": iron_pair_hits,
        "misses_at_4plus": misses_at_4,
        "per_param_cal": per_param_cal,
        "cal_counts": cal_counts,
    }


def build_summary(statuses: list[dict], stamp: str) -> str:
    rows = []  # (arc_name, config_name, env_override, agg)
    for arc_name, configs in ALL_ARCS:
        for name, env_override in configs:
            config_dir = OUTPUT_ROOT / name
            agg = aggregate_config(config_dir)
            if agg is not None:
                rows.append((arc_name, name, env_override, agg))

    # Sort by paper-relevant criteria: 6+/n, then 5+/n, then iron_pair_joint,
    # then total_excellents, then mean_cal.
    rows.sort(key=lambda r: (
        -r[3]["n_at_6"],
        -r[3]["n_at_5"],
        -r[3]["iron_pair_joint"],
        -r[3]["total_excellents"],
        -r[3]["mean_cal"],
    ))

    lines = [
        f"# Overnight v3.0 Basin C refinement sweep — {stamp}",
        "",
        "## Sweep design",
        "",
        "Probe whether Basin C (alpfe + scav_rat 10/10 at F2: D4 + CHL1_W=3.0)",
        "is extendable toward 6/6, and characterize its lever-response landscape.",
        "",
        "## Ranked configs (paper-relevant ordering)",
        "",
        f"| Rank | 6+/n | 5+/n | 4+/n | iron-pair | total exc | mean cal | config |",
        f"|---|---|---|---|---|---|---|---|",
    ]
    for i, (arc_name, name, env, a) in enumerate(rows, 1):
        cfg = " ".join(f"{k}={v}" for k, v in env.items() if k != "NB23_SEEDS")
        lines.append(
            f"| {i} | {a['n_at_6']}/{a['n_seeds']} | "
            f"{a['n_at_5']}/{a['n_seeds']} | "
            f"{a['n_at_4']}/{a['n_seeds']} | "
            f"{a['iron_pair_joint']}/{a['n_seeds']} | "
            f"{a['total_excellents']} | "
            f"{a['mean_cal']:.2f} | "
            f"{name} ({cfg}) |"
        )

    # Surface any 6/6 results
    lines.extend(["", "## 6/6 hits", ""])
    six_six = []
    for arc_name, name, env, a in rows:
        if a["n_at_6"] > 0:
            config_dir = OUTPUT_ROOT / name
            for f in sorted(glob.glob(str(config_dir / "*.json"))):
                r = json.load(open(f))
                if r["n_cal_grade"] >= 6:
                    six_six.append(f"- **{name}** seed {r['seed']}: "
                                   f"`{Path(f).name}`")
    if six_six:
        lines.extend(six_six)
    else:
        lines.append("(none — 5/6 ceiling remains the laptop bound)")

    # Per-arc breakdown
    lines.extend(["", "## Per-arc breakdown", ""])
    for arc_name, configs in ALL_ARCS:
        lines.append(f"### {arc_name}")
        lines.append("")
        for name, env in configs:
            agg = aggregate_config(OUTPUT_ROOT / name)
            if agg is None:
                lines.append(f"- **{name}**: no JSONs produced")
                continue
            misses = ", ".join(
                f"{p}:{c}" for p, c in agg["misses_at_4plus"].items() if c > 0
            ) or "(none)"
            per_param = " ".join(
                f"{p[:3]}={c}" for p, c in agg["per_param_cal"].items()
            )
            lines.append(
                f"- **{name}**: "
                f"6+/n={agg['n_at_6']}/{agg['n_seeds']}  "
                f"5+/n={agg['n_at_5']}/{agg['n_seeds']}  "
                f"4+/n={agg['n_at_4']}/{agg['n_seeds']}  "
                f"iron-pair={agg['iron_pair_joint']}/{agg['n_seeds']}  "
                f"mean_cal={agg['mean_cal']:.2f}  "
                f"misses-at-4+={{{misses}}}  "
                f"per-param-cal=({per_param})"
            )
        lines.append("")

    # Run statuses
    lines.extend(["", "## Run statuses", ""])
    for s in statuses:
        lines.append(f"- **{s['name']}**: {s['status']} ({s['elapsed']:.0f}s)")

    return "\n".join(lines)


# ============================================================================
# Main
# ============================================================================
def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.md"
    stop_path = LOG_DIR / "STOP"

    progress("=" * 70, progress_path)
    progress(f"Overnight v3.0 Basin C refinement sweep -- {STAMP}", progress_path)
    progress(f"Runner: {RUNNER}", progress_path)
    progress(f"Output root: {OUTPUT_ROOT}", progress_path)
    progress(f"Log dir: {LOG_DIR}", progress_path)
    progress(f"Graceful stop: touch {stop_path}", progress_path)
    progress(f"Base env: {BASE_ENV}", progress_path)
    progress("=" * 70, progress_path)

    overall_start = time.time()
    statuses: list[dict] = []
    total_configs = sum(len(configs) for _, configs in ALL_ARCS)
    progress(f"Total configs queued: {total_configs}", progress_path)

    for arc_idx, (arc_name, configs) in enumerate(ALL_ARCS, 1):
        if stop_path.exists():
            progress(f"STOP at arc boundary {arc_idx} -- exiting", progress_path)
            break
        progress("", progress_path)
        progress(f"=== {arc_name} ({arc_idx}/{len(ALL_ARCS)}) ===",
                 progress_path)
        for name, env_override in configs:
            statuses.append(run_one(name, env_override, progress_path,
                                    stop_path))
            # Incremental aggregation -- so partial summaries are
            # available if the sweep is interrupted.
            agg = aggregate_config(OUTPUT_ROOT / name)
            if agg is not None:
                progress(
                    f"    aggregate {name}: "
                    f"6+/n={agg['n_at_6']}/{agg['n_seeds']}  "
                    f"5+/n={agg['n_at_5']}/{agg['n_seeds']}  "
                    f"4+/n={agg['n_at_4']}/{agg['n_seeds']}  "
                    f"iron-pair={agg['iron_pair_joint']}/{agg['n_seeds']}  "
                    f"mean_cal={agg['mean_cal']:.2f}",
                    progress_path,
                )

    overall_elapsed = time.time() - overall_start
    progress("", progress_path)
    progress(
        f"=== Sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===",
        progress_path,
    )

    # Build final summary
    summary = build_summary(statuses, STAMP)
    summary_path.write_text(summary + "\n", encoding="utf-8")
    progress(f"Summary written: {summary_path}", progress_path)


if __name__ == "__main__":
    main()
