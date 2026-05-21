"""Wave 5 — drill into w2e_peraoi_lam0.1 (the 5/6 breakthrough).

Wave 2's w2e_peraoi_lam0.1 (PER_AOI_DINN=1 + CONSISTENCY_LAMBDA=0.1) produced
the first 5/6 Cal-grade recovery in DarwinDiff history (seed 3: alpfe Excellent
+ scav_rat/Smallgrow/Biggrow/diatomgraz Cal-grade; only R_PICPOC missed).
Iron pair holds 10/10 across the batch.

This wave answers three paper-critical questions:

  W5-A: dose-response — is 0.1 the sweet spot? Test CONSISTENCY_LAMBDA on a
        finer grid: {0.05, 0.15, 0.20, 0.30}. Combined with the existing
        Wave 2 values {0.1, 0.5, 1.0, 2.0}, this gives 8 points on the
        consistency-lambda curve.

  W5-B: combination synergy — does the 5/6 breakthrough survive when
        combined with other strong levers (N_EPOCHS=2000, GEOTRACES_W=0.1,
        NB23_FET_WEIGHT=5.0)?

  W5-C: robustness — is the 1/10 seed at 5/6 a fluke, or does the
        breakthrough hold at n=20 (seeds 10-19)?

Total: 8 configs x 10 seeds = ~70 min with cooldowns.

Output: D:\\runs\\bcr_w5_<stamp>\\<config>\\.
Logs: logs/overnight_v3.0_basinC_wave5_<stamp>/.

Runner: scripts/run_v3.0_with_modis_pic.py.
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
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_basinC_wave5_{STAMP}"
OUTPUT_ROOT = Path(rf"D:\runs\bcr_w5_{STAMP}")

# Basin C base + PER_AOI_DINN=1 (the architectural lever from w2e).
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
    "PER_AOI_DINN": "1",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

SEEDS_10 = "0,1,2,3,4,5,6,7,8,9"
SEEDS_10_19 = "10,11,12,13,14,15,16,17,18,19"

# W5-A: CONSISTENCY_LAMBDA dose-response around 0.1
W5A_LAM_DOSE = [
    ("w5a_lam0.05", {"CONSISTENCY_LAMBDA": "0.05", "NB23_SEEDS": SEEDS_10}),
    ("w5a_lam0.15", {"CONSISTENCY_LAMBDA": "0.15", "NB23_SEEDS": SEEDS_10}),
    ("w5a_lam0.20", {"CONSISTENCY_LAMBDA": "0.20", "NB23_SEEDS": SEEDS_10}),
    ("w5a_lam0.30", {"CONSISTENCY_LAMBDA": "0.30", "NB23_SEEDS": SEEDS_10}),
]

# W5-B: PER_AOI + lam=0.1 + other top levers (synergy probe)
W5B_COMBOS = [
    ("w5b_lam01_ep2000",
     {"CONSISTENCY_LAMBDA": "0.1", "NB23_N_EPOCHS": "2000",
      "NB23_SEEDS": SEEDS_10}),
    ("w5b_lam01_geoW01",
     {"CONSISTENCY_LAMBDA": "0.1", "GEOTRACES_W": "0.1",
      "NB23_SEEDS": SEEDS_10}),
    ("w5b_lam01_fetW5",
     {"CONSISTENCY_LAMBDA": "0.1", "NB23_FET_WEIGHT": "5.0",
      "NB23_SEEDS": SEEDS_10}),
]

# W5-C: n=20 robustness at the winning config
W5C_N20 = [
    ("w5c_lam01_n20", {"CONSISTENCY_LAMBDA": "0.1",
                       "NB23_SEEDS": SEEDS_10_19}),
]

ALL_ARCS: list[tuple[str, list[tuple[str, dict]]]] = [
    ("W5-C -- n=20 robustness at w2e_peraoi_lam0.1", W5C_N20),
    ("W5-A -- CONSISTENCY_LAMBDA dose-response", W5A_LAM_DOSE),
    ("W5-B -- PER_AOI + lam=0.1 + best-lever combos", W5B_COMBOS),
]

TIMEOUT_PER_RUN = 1800
CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']

# Thermal cooldown
COOLDOWN_BASE_S = 60
COOLDOWN_DEEP_EVERY = 5
COOLDOWN_DEEP_S = 240
GPU_TEMP_THRESHOLD_C = 75
GPU_TEMP_EXTEND_S = 60
GPU_TEMP_MAX_EXTENSIONS = 5


def gpu_temp_c() -> int | None:
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
    base = (COOLDOWN_DEEP_S if (config_index + 1) % COOLDOWN_DEEP_EVERY == 0
            else COOLDOWN_BASE_S)
    t0 = gpu_temp_c()
    progress(f"  cooldown {base}s (GPU={t0}C before)", progress_path)
    time.sleep(base)
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

    # Resume logic
    existing = list(config_out_dir.glob("*.json"))
    expected_seeds = env_override.get("NB23_SEEDS", "0").count(",") + 1
    if len(existing) >= expected_seeds:
        progress(f"  RESUME: {name} already has {len(existing)} JSONs; skipping",
                 progress_path)
        return {"name": name, "status": "SKIPPED_RESUME", "elapsed": 0.0,
                "env": env_override, "out_dir": str(config_out_dir)}

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


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.md"
    stop_path = LOG_DIR / "STOP"

    progress("=" * 70, progress_path)
    progress(f"Wave 5 sweep -- {STAMP}", progress_path)
    progress(f"Goal: drill into w2e_peraoi_lam0.1 (first 5/6 breakthrough)",
             progress_path)
    progress(f"Output: {OUTPUT_ROOT}", progress_path)
    progress(f"Log: {LOG_DIR}", progress_path)
    progress("=" * 70, progress_path)

    overall_start = time.time()
    statuses: list[dict] = []
    total = sum(len(c) for _, c in ALL_ARCS)
    progress(f"Total Wave 5 configs queued: {total}", progress_path)
    config_counter = 0

    for arc_idx, (arc_name, configs) in enumerate(ALL_ARCS, 1):
        if stop_path.exists():
            progress(f"STOP at arc boundary {arc_idx} -- exiting", progress_path)
            break
        progress("", progress_path)
        progress(f"=== {arc_name} ({arc_idx}/{len(ALL_ARCS)}) ===",
                 progress_path)
        for name, env_override in configs:
            statuses.append(run_one(name, env_override, progress_path, stop_path))
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
            if not stop_path.exists():
                cooldown(progress_path, config_counter)
            config_counter += 1

    overall_elapsed = time.time() - overall_start
    progress("", progress_path)
    progress(
        f"=== Wave 5 done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===",
        progress_path,
    )

    # Summary
    rows = []
    for arc_name, configs in ALL_ARCS:
        for name, env_override in configs:
            agg = aggregate_config(OUTPUT_ROOT / name)
            if agg is not None:
                rows.append((arc_name, name, env_override, agg))
    rows.sort(key=lambda r: (
        -r[3]["n_at_6"], -r[3]["n_at_5"],
        -r[3]["iron_pair_joint"], -r[3]["total_excellents"],
        -r[3]["mean_cal"],
    ))
    lines = [f"# Wave 5 sweep -- {STAMP}", "",
             "Drill into w2e_peraoi_lam0.1 (first 5/6 breakthrough).", ""]
    lines.append("| Rank | 6+/n | 5+/n | 4+/n | iron-pair | mean_cal | tot_exc | config |")
    lines.append("|---|---|---|---|---|---|---|---|")
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
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    progress(f"Summary: {summary_path}", progress_path)


if __name__ == "__main__":
    main()
