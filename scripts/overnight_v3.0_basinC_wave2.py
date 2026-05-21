"""Wave 2 — Basin C orthogonal-lever sweep.

Builds on Wave 1 (overnight_v3.0_basinC_refine.py). Attacks the lever subspace
Wave 1 left untouched:

  W2-A: GEOTRACES_W sweep         — surface DFe weight (5 configs)
  W2-B: POC_SUB_W sweep            — POC z-score weight (5 configs)
  W2-C: NB23_PINN_WEIGHT sweep     — drift loss weight (5 configs)
  W2-D: NB23_FET_WEIGHT sweep      — FeT z-score weight (4 configs)
  W2-E: CONSISTENCY_LAMBDA + PER_AOI_DINN at 3-AOI (4 configs)
  W2-F: Basin C n=30 robustness extension (1 config, seeds 20-29)

Total: 24 configs x 10 seeds = ~3 hrs.

All configs share Basin C base (F2: D4 + CHL1_W=3.0). Per-config OUTPUT_DIR
isolates filename collisions for non-tagged levers (PINN_W, FET_W, etc.).

Output:
  Per-config JSONs at D:\\runs\\v3.0_basinC_wave2_<stamp>\\<config>\\.
  Logs + summary at logs/overnight_v3.0_basinC_wave2_<stamp>/.
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
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_basinC_wave2_{STAMP}"
# Use bcr_w2_ prefix (short) to stay under Windows MAX_PATH=260 for any
# multi-lever filenames; consistent with Wave 1 (bcr_) and Wave 3 (bcr_w3_).
OUTPUT_ROOT = Path(rf"D:\runs\bcr_w2_{STAMP}")

# Basin C base config (same as Wave 1).
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

# W2-A: GEOTRACES_W (surface DFe weight) sweep
W2A_GEOTRACES_W = [
    ("w2a_geoW0.1",  {"GEOTRACES_W": "0.1", "NB23_SEEDS": SEEDS_10}),
    ("w2a_geoW0.6",  {"GEOTRACES_W": "0.6", "NB23_SEEDS": SEEDS_10}),
    ("w2a_geoW1.0",  {"GEOTRACES_W": "1.0", "NB23_SEEDS": SEEDS_10}),
    ("w2a_geoW1.5",  {"GEOTRACES_W": "1.5", "NB23_SEEDS": SEEDS_10}),
    ("w2a_geoW2.0",  {"GEOTRACES_W": "2.0", "NB23_SEEDS": SEEDS_10}),
]

# W2-B: POC_SUB_W sweep
W2B_POC_SUB_W = [
    ("w2b_pocsubW0.25", {"POC_SUB_W": "0.25", "NB23_SEEDS": SEEDS_10}),
    ("w2b_pocsubW1.0",  {"POC_SUB_W": "1.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2b_pocsubW1.5",  {"POC_SUB_W": "1.5",  "NB23_SEEDS": SEEDS_10}),
    ("w2b_pocsubW2.0",  {"POC_SUB_W": "2.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2b_pocsubW3.0",  {"POC_SUB_W": "3.0",  "NB23_SEEDS": SEEDS_10}),
]

# W2-C: PINN_W (drift loss) sweep
W2C_PINN_W = [
    ("w2c_pinnW1.0",  {"NB23_PINN_WEIGHT": "1.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2c_pinnW2.0",  {"NB23_PINN_WEIGHT": "2.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2c_pinnW5.0",  {"NB23_PINN_WEIGHT": "5.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2c_pinnW7.0",  {"NB23_PINN_WEIGHT": "7.0",  "NB23_SEEDS": SEEDS_10}),
    ("w2c_pinnW10.0", {"NB23_PINN_WEIGHT": "10.0", "NB23_SEEDS": SEEDS_10}),
]

# W2-D: FET_W (iron z-score loss) sweep
W2D_FET_W = [
    ("w2d_fetW0.5", {"NB23_FET_WEIGHT": "0.5", "NB23_SEEDS": SEEDS_10}),
    ("w2d_fetW2.0", {"NB23_FET_WEIGHT": "2.0", "NB23_SEEDS": SEEDS_10}),
    ("w2d_fetW3.0", {"NB23_FET_WEIGHT": "3.0", "NB23_SEEDS": SEEDS_10}),
    ("w2d_fetW5.0", {"NB23_FET_WEIGHT": "5.0", "NB23_SEEDS": SEEDS_10}),
]

# W2-E: CONSISTENCY_LAMBDA + PER_AOI_DINN at 3-AOI (PER_AOI was falsified at
# 2-AOI; might behave differently at 3-AOI with cross-AOI consistency penalty).
W2E_CONSISTENCY = [
    ("w2e_peraoi_lam0.1", {"PER_AOI_DINN": "1", "CONSISTENCY_LAMBDA": "0.1",
                            "NB23_SEEDS": SEEDS_10}),
    ("w2e_peraoi_lam0.5", {"PER_AOI_DINN": "1", "CONSISTENCY_LAMBDA": "0.5",
                            "NB23_SEEDS": SEEDS_10}),
    ("w2e_peraoi_lam1.0", {"PER_AOI_DINN": "1", "CONSISTENCY_LAMBDA": "1.0",
                            "NB23_SEEDS": SEEDS_10}),
    ("w2e_peraoi_lam2.0", {"PER_AOI_DINN": "1", "CONSISTENCY_LAMBDA": "2.0",
                            "NB23_SEEDS": SEEDS_10}),
]

# W2-F: Basin C n=30 robustness — seeds 20-29 at Basin C base
W2F_BASIN_C_N30 = [
    ("w2f_basinC_seeds20-29", {"NB23_SEEDS": "20,21,22,23,24,25,26,27,28,29"}),
]

ALL_ARCS: list[tuple[str, list[tuple[str, dict]]]] = [
    ("W2-F -- Basin C n=30 robustness", W2F_BASIN_C_N30),
    ("W2-A -- GEOTRACES_W (surface DFe) sweep", W2A_GEOTRACES_W),
    ("W2-B -- POC_SUB_W (POC z-score) sweep", W2B_POC_SUB_W),
    ("W2-C -- NB23_PINN_WEIGHT (drift loss) sweep", W2C_PINN_W),
    ("W2-D -- NB23_FET_WEIGHT (FeT z-score) sweep", W2D_FET_W),
    ("W2-E -- CONSISTENCY_LAMBDA + PER_AOI_DINN at 3-AOI", W2E_CONSISTENCY),
]

TIMEOUT_PER_RUN = 1800
CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']

# Thermal cooldown: prevents laptop overheating during long sweep chains.
COOLDOWN_BASE_S = 60        # sleep after every config
COOLDOWN_DEEP_EVERY = 5     # every Nth config, take a longer rest
COOLDOWN_DEEP_S = 240       # length of deep rest (4 min)
GPU_TEMP_THRESHOLD_C = 75   # if GPU still hotter than this, extend rest
GPU_TEMP_EXTEND_S = 60      # additional sleep per check while hot
GPU_TEMP_MAX_EXTENSIONS = 5 # cap so we don't loop forever


def gpu_temp_c() -> int | None:
    """Return current GPU temperature in C, or None if nvidia-smi unavailable."""
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return int(r.stdout.strip().splitlines()[0])
    except Exception:
        return None


def cooldown(progress_path: Path, config_index: int) -> None:
    """Sleep to let GPU/CPU cool. Deep rest every Nth config; temp-aware
    extension if GPU still hot."""
    base = (COOLDOWN_DEEP_S if (config_index + 1) % COOLDOWN_DEEP_EVERY == 0
            else COOLDOWN_BASE_S)
    t0 = gpu_temp_c()
    progress(f"  cooldown {base}s (GPU={t0}C before)", progress_path)
    time.sleep(base)
    # Extend if still hot
    for i in range(GPU_TEMP_MAX_EXTENSIONS):
        t = gpu_temp_c()
        if t is None or t < GPU_TEMP_THRESHOLD_C:
            if t is not None:
                progress(f"  cooldown done (GPU={t}C)", progress_path)
            break
        progress(f"  GPU still hot ({t}C >= {GPU_TEMP_THRESHOLD_C}); "
                 f"+{GPU_TEMP_EXTEND_S}s", progress_path)
        time.sleep(GPU_TEMP_EXTEND_S)


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

    return {
        "n_seeds": len(runs),
        "n_at_6": sum(1 for c in cal_counts if c >= 6),
        "n_at_5": sum(1 for c in cal_counts if c >= 5),
        "n_at_4": sum(1 for c in cal_counts if c >= 4),
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "total_excellents": sum(exc_counts),
        "iron_pair_joint": iron_pair_hits,
        "per_param_cal": per_param_cal,
    }


def build_summary(statuses: list[dict], stamp: str) -> str:
    rows = []
    for arc_name, configs in ALL_ARCS:
        for name, env_override in configs:
            config_dir = OUTPUT_ROOT / name
            agg = aggregate_config(config_dir)
            if agg is not None:
                rows.append((arc_name, name, env_override, agg))
    rows.sort(key=lambda r: (
        -r[3]["n_at_6"],
        -r[3]["n_at_5"],
        -r[3]["iron_pair_joint"],
        -r[3]["total_excellents"],
        -r[3]["mean_cal"],
    ))

    lines = [
        f"# Overnight v3.0 Basin C Wave 2 sweep -- {stamp}",
        "",
        "## Ranked configs",
        "",
        "| Rank | 6+/n | 5+/n | 4+/n | iron-pair | mean_cal | total exc | config |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, (arc_name, name, env, a) in enumerate(rows, 1):
        cfg = " ".join(f"{k}={v}" for k, v in env.items() if k != "NB23_SEEDS")
        lines.append(
            f"| {i} | {a['n_at_6']}/{a['n_seeds']} | "
            f"{a['n_at_5']}/{a['n_seeds']} | "
            f"{a['n_at_4']}/{a['n_seeds']} | "
            f"{a['iron_pair_joint']}/{a['n_seeds']} | "
            f"{a['mean_cal']:.2f} | "
            f"{a['total_excellents']} | "
            f"{name} ({cfg}) |"
        )

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
        lines.append("(none)")

    lines.extend(["", "## Per-arc breakdown", ""])
    for arc_name, configs in ALL_ARCS:
        lines.append(f"### {arc_name}")
        lines.append("")
        for name, env in configs:
            agg = aggregate_config(OUTPUT_ROOT / name)
            if agg is None:
                lines.append(f"- **{name}**: no JSONs produced")
                continue
            per_param = " ".join(
                f"{p[:3]}={c}" for p, c in agg["per_param_cal"].items()
            )
            lines.append(
                f"- **{name}**: "
                f"6+={agg['n_at_6']}/{agg['n_seeds']}  "
                f"5+={agg['n_at_5']}/{agg['n_seeds']}  "
                f"4+={agg['n_at_4']}/{agg['n_seeds']}  "
                f"iron-pair={agg['iron_pair_joint']}/{agg['n_seeds']}  "
                f"mean_cal={agg['mean_cal']:.2f}  "
                f"per-param-cal=({per_param})"
            )
        lines.append("")

    lines.extend(["", "## Run statuses", ""])
    for s in statuses:
        lines.append(f"- **{s['name']}**: {s['status']} ({s['elapsed']:.0f}s)")

    return "\n".join(lines)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.md"
    stop_path = LOG_DIR / "STOP"

    progress("=" * 70, progress_path)
    progress(f"Wave 2 sweep -- {STAMP}", progress_path)
    progress(f"Runner: {RUNNER}", progress_path)
    progress(f"Output root: {OUTPUT_ROOT}", progress_path)
    progress(f"Log dir: {LOG_DIR}", progress_path)
    progress(f"Graceful stop: touch {stop_path}", progress_path)
    progress("=" * 70, progress_path)

    overall_start = time.time()
    statuses: list[dict] = []
    total_configs = sum(len(configs) for _, configs in ALL_ARCS)
    progress(f"Total Wave 2 configs queued: {total_configs}", progress_path)
    config_counter = 0

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
            # Thermal cooldown between configs (skip if stop sentinel set)
            if not stop_path.exists():
                cooldown(progress_path, config_counter)
            config_counter += 1

    overall_elapsed = time.time() - overall_start
    progress("", progress_path)
    progress(
        f"=== Wave 2 done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===",
        progress_path,
    )

    summary = build_summary(statuses, STAMP)
    summary_path.write_text(summary + "\n", encoding="utf-8")
    progress(f"Summary written: {summary_path}", progress_path)

    # Chain Wave 3
    wave3_script = HERE / "overnight_v3.0_basinC_wave3.py"
    if not stop_path.exists() and wave3_script.is_file():
        progress("", progress_path)
        progress(f"=== Chaining Wave 3: {wave3_script} ===", progress_path)
        try:
            subprocess.run(
                [sys.executable, str(wave3_script)],
                cwd=str(ROOT),
                env=os.environ.copy(),
                check=False,
            )
        except Exception as e:
            progress(f"Wave 3 chain failed: {e}", progress_path)


if __name__ == "__main__":
    main()
