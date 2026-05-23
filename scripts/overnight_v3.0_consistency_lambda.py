"""Overnight v3.0 per-AOI-DINN consistency-lambda sweep.

Goal: test whether per-AOI DINNs with a soft cross-AOI parameter-mean
consistency penalty break the 5/6 shared-MLP architectural ceiling
diagnosed in PR #57. Sweep CONSISTENCY_LAMBDA across 3 orders of magnitude
at n=10 seeds, all other knobs fixed at the PR #57 best config
(AOI ID + GEO POC=0.5 + hd=32 + NAtl_W=2.0 + no Chl1 boost).

  lambda -> 0    : per-AOI DINNs fit independently (no cross-regime pull)
  lambda small   : each regime fits its preferred params, mildly tethered
                   (hypothesized sweet spot, ~0.01-0.1)
  lambda large   : per-AOI params forced to agree (collapses toward shared-MLP)

Wall-clock target: 4 lambdas * ~30 min each ~= 2 hr.
"""
from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNNER = HERE / "run_v3.0_joint_multi_aoi.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_lambda_{STAMP}"

# PR #57 best config + per-AOI DINN flag flipped on.
BASE_ENV = {
    "AOI_ID_CHANNEL": "1",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "NB23_N_EPOCHS": "1500",
    "PER_AOI_DINN": "1",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

LAMBDAS = ["0.01", "0.1", "1.0", "10.0"]
SEEDS_10 = "0,1,2,3,4,5,6,7,8,9"

RUNS = [
    (f"L{lam}", {"NB23_SEEDS": SEEDS_10, "CONSISTENCY_LAMBDA": lam})
    for lam in LAMBDAS
]

TIMEOUT_PER_RUN = 3600  # 60 min cap; observed ~30 min per 10-seed run


def progress(line: str, progress_path: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name: str, env_override: dict, log_dir: Path, progress_path: Path) -> dict:
    if (log_dir / "STOP").exists():
        progress(f"STOP sentinel -- skipping {name}", progress_path)
        return {"name": name, "status": "SKIPPED_STOP", "elapsed": 0.0, "env": env_override}
    progress(f"START {name}  env={env_override}", progress_path)
    env = os.environ.copy()
    env.update(BASE_ENV)
    env.update(env_override)
    log_path = log_dir / f"{name}.log"
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
    return {"name": name, "status": status, "elapsed": elapsed, "env": env_override}


CARROLL = {"alpfe": 0.92831, "scav_rat": 6.0250e-7, "Smallgrow": 0.66098,
           "Biggrow": 0.43148, "diatomgraz": 0.83003, "R_PICPOC": 0.04245}


def pattern_for_lambda(lam: str) -> str:
    # Mirrors the JSON filename emitted by run_v3.0_joint_multi_aoi.py at the
    # fixed BASE_ENV config. Tags appear in this exact order: surf, sub, pinn,
    # pocsubW, geopocW, aoiid, hd, w-natlsubpolar, peraoi_lam.
    return (
        "data/legacy/scripts_json_archive/run_v3.0_joint_eqpac-natlsubpolar_seed*"
        "_surf0.3_sub1.0_pinn3.0"
        "_pocsubW3.0_geopocW0.5"
        "_aoiid_hd32"
        "_w-natlsubpolar2.0"
        f"_peraoi_lam{lam}.json"
    )


def aggregate_pattern(pat: str) -> dict | None:
    files = sorted(glob.glob(pat))
    if not files:
        return None
    runs = [json.load(open(f, encoding="utf-8")) for f in files]
    cal_counts = [r["n_cal_grade"] for r in runs]
    exc_counts = [r["n_excellent"] for r in runs]
    misses = {}
    for r in runs:
        if r["n_cal_grade"] == 5:
            for p in CARROLL:
                if r["params"][p]["joint_band"] not in ("Cal-grade", "Excellent"):
                    misses[p] = misses.get(p, 0) + 1
    return {
        "n_seeds": len(runs),
        "cal_counts": cal_counts,
        "exc_counts": exc_counts,
        "n_at_6": sum(1 for c in cal_counts if c >= 6),
        "n_at_5": sum(1 for c in cal_counts if c >= 5),
        "n_at_4": sum(1 for c in cal_counts if c >= 4),
        "total_excellents": sum(exc_counts),
        "miss_distribution": misses,
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "files": files,
    }


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.txt"
    stop_path = LOG_DIR / "STOP"

    progress("=== Overnight v3.0 CONSISTENCY_LAMBDA sweep (per-AOI DINNs) ===", progress_path)
    progress(f"  Base config: {BASE_ENV}", progress_path)
    progress(f"  Lambdas: {LAMBDAS}  (n_seeds=10 each)", progress_path)
    progress(f"  Graceful stop: touch {stop_path}", progress_path)
    progress(f"  Log dir: {LOG_DIR}", progress_path)

    overall_start = time.time()
    statuses: list[dict] = []
    for name, env in RUNS:
        statuses.append(run_one(name, env, LOG_DIR, progress_path))

    overall_elapsed = time.time() - overall_start
    progress(f"=== Sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===", progress_path)
    progress("Building summary...", progress_path)

    rows = []
    for lam in LAMBDAS:
        pat = pattern_for_lambda(lam)
        a = aggregate_pattern(pat)
        if a:
            rows.append((lam, a))
            progress(
                f"  lam={lam}: n_at_6={a['n_at_6']}/{a['n_seeds']}  "
                f"n_at_5={a['n_at_5']}/{a['n_seeds']}  n_at_4={a['n_at_4']}/{a['n_seeds']}  "
                f"total_exc={a['total_excellents']}  mean_cal={a['mean_cal']:.2f}",
                progress_path,
            )
        else:
            progress(f"  lam={lam}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # Ranked: prefer more 6/6, then more 5/6, then more Excellents.
    rows.sort(key=lambda r: (-r[1]["n_at_6"], -r[1]["n_at_5"], -r[1]["total_excellents"]))

    summary_lines = [
        "=== Overnight v3.0 CONSISTENCY_LAMBDA sweep summary ===",
        f"Started:  {datetime.fromtimestamp(overall_start).isoformat()}",
        f"Finished: {datetime.now().isoformat()}",
        f"Total wall-clock: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min",
        "",
        f"{'Rank':<5} {'lambda':<8} {'6+/n':<7} {'5+/n':<7} {'4+/n':<7} {'mean_cal':<9} {'total_exc':<10} {'5/6 miss distribution'}",
    ]
    for i, (lam, a) in enumerate(rows, 1):
        miss_str = ", ".join(f"{p}:{c}" for p, c in sorted(a["miss_distribution"].items(), key=lambda kv: -kv[1])) or "-"
        summary_lines.append(
            f"{i:<5} {lam:<8} {a['n_at_6']}/{a['n_seeds']:<5} {a['n_at_5']}/{a['n_seeds']:<5} "
            f"{a['n_at_4']}/{a['n_seeds']:<5} {a['mean_cal']:<9.2f} {a['total_excellents']:<10} {miss_str}"
        )

    summary_lines.append("")
    any_six = False
    for lam, a in rows:
        if a["n_at_6"] > 0:
            any_six = True
            for f in a["files"]:
                r = json.load(open(f, encoding="utf-8"))
                if r["n_cal_grade"] >= 6:
                    summary_lines.append(f"  6/6 hit: lam={lam}, seed={r['seed']}  file={Path(f).name}")
    if not any_six:
        summary_lines.append(
            "No 6/6 across the lambda sweep. Compare ranked 5/6 rate to the "
            "shared-MLP baseline (PR #57: 7/15 at 5/6 = 47%) to judge whether "
            "per-AOI DINNs alone shift the ceiling."
        )

    summary_lines.append("")
    summary_lines.append("Per-lambda detail:")
    for lam, a in rows:
        summary_lines.append(
            f"  [lam={lam}] cal_counts={a['cal_counts']} exc_counts={a['exc_counts']}"
        )

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    progress(f"Summary written to {summary_path}", progress_path)


if __name__ == "__main__":
    main()
