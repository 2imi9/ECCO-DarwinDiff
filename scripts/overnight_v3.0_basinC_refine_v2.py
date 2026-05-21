"""Overnight v3.0 Basin C refinement sweep — v2 (MAX_PATH fix).

Resume of the 20260520_0121 sweep after a Windows MAX_PATH crash in Arc 7.
Uses short paths (D:\\runs\\bcr_<stamp>\\<short-arc-name>\\) so picabs+pocabs
combined tags fit under 260 chars.

Skipped vs v1 ALL_ARCS:
  - Arc 6 (n=20 robustness): completed cleanly in v1, JSONs copied to bcr root
  - Arc 7 #1 PIC=0.05/POC=0.025: crashed at JSON write, data recovered from
    log (see scripts/recover_failed_config_log.py)
  - Arc 7 #2 PIC=0.10/POC=0.05: crashed at JSON write, data recovered from log

Run order (preserves the same ordering for paper-relevance):
  Arc 7 (remaining configs #3, #4) → Arc 1 → Arc 2 → Arc 3 → Arc 4 →
  Arc 8 → Arc 9 → Arc 5.

Then auto-chains Wave 2 (overnight_v3.0_basinC_wave2.py).
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

# REUSE stamp 20260520_0121 so all data lives in one place. Logs go to a
# new directory so the v1 STOP file doesn't confuse us.
STAMP = "20260520_0121"
RESUME_STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_basinC_refine_v2_{RESUME_STAMP}"
OUTPUT_ROOT = Path(rf"D:\runs\bcr_{STAMP}")

# Basin C base config (F2: D4 + CHL1_W=3.0). Same as v1.
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

# Arc 7 -- PIC + POC paired anchors on Basin C (remaining 2 configs;
# #1 and #2 already recovered from logs).
ARC7_PAIRED = [
    ("a7_pp_20_10", {"PIC_ABS_W": "0.20", "POC_ABS_W": "0.10",
                     "NB23_SEEDS": SEEDS_10}),
    ("a7_pp_50_25", {"PIC_ABS_W": "0.50", "POC_ABS_W": "0.25",
                     "NB23_SEEDS": SEEDS_10}),
]

ARC1_PIC_DOSE = [
    ("a1_pic_002", {"PIC_ABS_W": "0.02", "NB23_SEEDS": SEEDS_10}),
    ("a1_pic_005", {"PIC_ABS_W": "0.05", "NB23_SEEDS": SEEDS_10}),
    ("a1_pic_010", {"PIC_ABS_W": "0.10", "NB23_SEEDS": SEEDS_10}),
    ("a1_pic_020", {"PIC_ABS_W": "0.20", "NB23_SEEDS": SEEDS_10}),
]

ARC2_POC_DOSE = [
    ("a2_poc_005", {"POC_ABS_W": "0.05", "NB23_SEEDS": SEEDS_10}),
    ("a2_poc_010", {"POC_ABS_W": "0.10", "NB23_SEEDS": SEEDS_10}),
    ("a2_poc_020", {"POC_ABS_W": "0.20", "NB23_SEEDS": SEEDS_10}),
    ("a2_poc_050", {"POC_ABS_W": "0.50", "NB23_SEEDS": SEEDS_10}),
]

ARC3_CHL1_RESPONSE = [
    ("a3_chl_20", {"CHL1_W_EXTRA": "2.0", "NB23_SEEDS": SEEDS_10}),
    ("a3_chl_25", {"CHL1_W_EXTRA": "2.5", "NB23_SEEDS": SEEDS_10}),
    ("a3_chl_35", {"CHL1_W_EXTRA": "3.5", "NB23_SEEDS": SEEDS_10}),
    ("a3_chl_40", {"CHL1_W_EXTRA": "4.0", "NB23_SEEDS": SEEDS_10}),
    ("a3_chl_50", {"CHL1_W_EXTRA": "5.0", "NB23_SEEDS": SEEDS_10}),
    ("a3_chl_70", {"CHL1_W_EXTRA": "7.0", "NB23_SEEDS": SEEDS_10}),
]

ARC4_AOI_WEIGHT = [
    ("a4_so_15",  {"AOI_W_SOUTHERNOCEANPAC": "1.5", "NB23_SEEDS": SEEDS_10}),
    ("a4_so_25",  {"AOI_W_SOUTHERNOCEANPAC": "2.5", "NB23_SEEDS": SEEDS_10}),
    ("a4_so_30",  {"AOI_W_SOUTHERNOCEANPAC": "3.0", "NB23_SEEDS": SEEDS_10}),
    ("a4_rebal",  {"AOI_W_NATLSUBPOLAR": "1.5", "AOI_W_SOUTHERNOCEANPAC": "2.0",
                   "NB23_SEEDS": SEEDS_10}),
]

ARC8_ARCH = [
    ("a8_hd64",   {"DINN_HIDDEN_DIM": "64",  "NB23_SEEDS": SEEDS_10}),
    ("a8_hd128",  {"DINN_HIDDEN_DIM": "128", "NB23_SEEDS": SEEDS_10}),
    ("a8_mld32",  {"MLD_CHANNEL": "1", "NB23_SEEDS": SEEDS_10}),
    ("a8_mld64",  {"MLD_CHANNEL": "1", "DINN_HIDDEN_DIM": "64",
                   "NB23_SEEDS": SEEDS_10}),
]

ARC9_CARBONATE = [
    ("a9_mehr",   {"USE_MEHRBACH_K1K2": "1", "NB23_SEEDS": SEEDS_10}),
    ("a9_fco2",   {"F_CO2_ABS_W": "0.01",    "NB23_SEEDS": SEEDS_10}),
    ("a9_mfco2",  {"USE_MEHRBACH_K1K2": "1", "F_CO2_ABS_W": "0.005",
                   "NB23_SEEDS": SEEDS_10}),
]

ARC5_LONGER = [
    ("a5_ep2000", {"NB23_N_EPOCHS": "2000", "NB23_SEEDS": SEEDS_10}),
    ("a5_ep2500", {"NB23_N_EPOCHS": "2500", "NB23_SEEDS": SEEDS_10}),
    ("a5_ep3000", {"NB23_N_EPOCHS": "3000", "NB23_SEEDS": SEEDS_10}),
]

# Order: Arc 7 first (highest EV, hits the failed configs), then the rest.
ALL_ARCS: list[tuple[str, list[tuple[str, dict]]]] = [
    ("Arc 7 -- PIC+POC paired (remaining)", ARC7_PAIRED),
    ("Arc 1 -- PIC anchor dose-response", ARC1_PIC_DOSE),
    ("Arc 2 -- POC anchor dose-response", ARC2_POC_DOSE),
    ("Arc 3 -- CHL1_W_EXTRA response curve", ARC3_CHL1_RESPONSE),
    ("Arc 4 -- Southern Ocean weight refinement", ARC4_AOI_WEIGHT),
    ("Arc 8 -- DINN capacity + MLD channel", ARC8_ARCH),
    ("Arc 9 -- Carbonate alignment on Basin C", ARC9_CARBONATE),
    ("Arc 5 -- Longer training", ARC5_LONGER),
]

TIMEOUT_PER_RUN = 1800
CARROLL_PARAMS = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']

# Whether to auto-chain Wave 2 after this sweep finishes
CHAIN_WAVE_2 = True
WAVE_2_SCRIPT = HERE / "overnight_v3.0_basinC_wave2.py"


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

    # Skip if already populated (resume logic)
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
    progress(f"v3.0 Basin C refinement -- v2 RESUME ({RESUME_STAMP})", progress_path)
    progress(f"Output root: {OUTPUT_ROOT}", progress_path)
    progress(f"Log dir: {LOG_DIR}", progress_path)
    progress(f"Resume mode: skips configs already present in OUTPUT_ROOT",
             progress_path)
    progress("=" * 70, progress_path)

    overall_start = time.time()
    statuses: list[dict] = []
    total_configs = sum(len(configs) for _, configs in ALL_ARCS)
    progress(f"Total v2 configs queued: {total_configs}", progress_path)

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

    overall_elapsed = time.time() - overall_start
    progress("", progress_path)
    progress(
        f"=== v2 sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===",
        progress_path,
    )

    # Write summary
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
    lines = [f"# v3.0 Basin C refinement v2 -- {RESUME_STAMP}", ""]
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

    # Chain Wave 2
    if CHAIN_WAVE_2 and not stop_path.exists() and WAVE_2_SCRIPT.is_file():
        progress("", progress_path)
        progress(f"=== Chaining Wave 2: {WAVE_2_SCRIPT} ===", progress_path)
        try:
            subprocess.run(
                [sys.executable, str(WAVE_2_SCRIPT)],
                cwd=str(ROOT),
                env=os.environ.copy(),
                check=False,
            )
        except Exception as e:
            progress(f"Wave 2 chain failed: {e}", progress_path)


if __name__ == "__main__":
    main()
