"""Overnight v3.0 parameter-learner refinement sweep.

Goal: find the configuration that most reliably reaches 5+/6 Cal-grade and
ideally 6/6 in any seed. Base config is AOI ID + GEO POC + hd=32 + NAtl_W=2.0
(yesterday's best, 7/15 seeds at 5/6 with diatomgraz the dominant miss).

Phases:
  Phase A: CHL1_W_EXTRA sweep at n=10  (4 runs)
    - 1.0, 3.0, 5.0, 10.0 -- tests whether boosting the diatom-chl loss
      pulls diatomgraz into Cal-grade for the seeds that hit 5/6.
  Phase B: AOI weight refinement at the best Chl1 weight (3 runs)
    - NAtl_W in {1.5, 2.5, 3.0} -- tests whether tilting the joint loss
      further toward N Atl unblocks anything.
  Phase C: Extra seeds at the winning config (1 run, n=10 more seeds 15-24)
    - tries to find a 6/6 seed by luck of init.
  Phase D: Final aggregation + ranked summary.

Each run logs to its own file; aggregation runs at the end. The wrapper
continues on failure so one bad config doesn't kill the rest.

Wall-clock target: ~40-50 min.
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
RUNNER = HERE / "run_v3.0_joint_multi_aoi.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_{STAMP}"

# Base config: yesterday's best (PR #54). Phases A/B vary one knob at a time.
BASE_ENV = {
    "AOI_ID_CHANNEL": "1",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "NB23_N_EPOCHS": "1500",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

PHASE_A = [
    ("A1_chl1W1.0",  {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": "1.0"}),
    ("A2_chl1W3.0",  {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": "3.0"}),
    ("A3_chl1W5.0",  {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": "5.0"}),
    ("A4_chl1W10.0", {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": "10.0"}),
]

# Phase B is parameterized at runtime based on Phase A winner
def make_phase_b(best_chl1_w: str) -> list[tuple[str, dict]]:
    return [
        ("B1_natlW1.5", {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": best_chl1_w, "AOI_W_NATLSUBPOLAR": "1.5"}),
        ("B2_natlW2.5", {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": best_chl1_w, "AOI_W_NATLSUBPOLAR": "2.5"}),
        ("B3_natlW3.0", {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9", "CHL1_W_EXTRA": best_chl1_w, "AOI_W_NATLSUBPOLAR": "3.0"}),
    ]

def make_phase_c(winning_env: dict[str, str]) -> list[tuple[str, dict]]:
    return [
        ("C1_winning_seeds15-24", {**winning_env, "NB23_SEEDS": "15,16,17,18,19,20,21,22,23,24"}),
    ]


TIMEOUT_PER_RUN = 1500  # 25 min cap; observed runs ~240s


def progress(line: str, progress_path: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name: str, env_override: dict, log_dir: Path, progress_path: Path) -> dict:
    """Run a single experiment; return (status, elapsed, name)."""
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


# ====== Aggregation helpers ======================================================

CARROLL = {'alpfe':0.92831,'scav_rat':6.0250e-7,'Smallgrow':0.66098,
           'Biggrow':0.43148,'diatomgraz':0.83003,'R_PICPOC':0.04245}


def aggregate_pattern(pat: str) -> dict | None:
    files = sorted(glob.glob(pat))
    if not files:
        return None
    runs = [json.load(open(f)) for f in files]
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
    }


def pattern_for(env: dict[str, str]) -> str:
    """Construct the JSON glob pattern that this env will produce."""
    surf = env.get("GEOTRACES_W", BASE_ENV.get("GEOTRACES_W", "0.3"))
    sub  = env.get("GEOTRACES_SUB_W", BASE_ENV.get("GEOTRACES_SUB_W", "1.0"))
    pinn = env.get("NB23_PINN_WEIGHT", BASE_ENV.get("NB23_PINN_WEIGHT", "3.0"))
    pocs = env.get("POC_SUB_W", BASE_ENV.get("POC_SUB_W", "3.0"))
    geop = env.get("GEOTRACES_POC_SUB_W", BASE_ENV.get("GEOTRACES_POC_SUB_W", "0.5"))
    hd   = env.get("DINN_HIDDEN_DIM",   BASE_ENV.get("DINN_HIDDEN_DIM", "16"))
    natl = env.get("AOI_W_NATLSUBPOLAR",BASE_ENV.get("AOI_W_NATLSUBPOLAR", "1.0"))
    chl1 = env.get("CHL1_W_EXTRA",      BASE_ENV.get("CHL1_W_EXTRA", "0.0"))

    base = ("data/legacy/scripts_json_archive/run_v3.0_joint_eqpac-natlsubpolar_seed*_"
            f"surf{surf}_sub{sub}_pinn{pinn}_pocsubW{pocs}_geopocW{geop}_aoiid")
    if hd != "16":
        base += f"_hd{hd}"
    if float(natl) != 1.0:
        base += f"_w-natlsubpolar{natl}"
    if float(chl1) > 0:
        base += f"_chl1W{chl1}"
    return base + ".json"


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.txt"
    stop_path = LOG_DIR / "STOP"

    progress(f"=== Overnight v3.0 parameter-learner sweep ===", progress_path)
    progress(f"  Base config: {BASE_ENV}", progress_path)
    progress(f"  Graceful stop: touch {stop_path}", progress_path)
    progress(f"  Log dir: {LOG_DIR}", progress_path)

    overall_start = time.time()
    statuses: list[dict] = []

    # ---- Phase A: CHL1_W_EXTRA sweep ----
    progress("=== PHASE A: CHL1_W_EXTRA sweep ===", progress_path)
    for name, env in PHASE_A:
        statuses.append(run_one(name, env, LOG_DIR, progress_path))
    progress("Phase A done. Aggregating...", progress_path)
    phase_a_results = {}
    for name, env in PHASE_A:
        pat = pattern_for({**BASE_ENV, **env})
        a = aggregate_pattern(pat)
        if a:
            phase_a_results[name] = (env, a)
            progress(f"  {name}: n_at_6={a['n_at_6']}/{a['n_seeds']}  n_at_5={a['n_at_5']}/{a['n_seeds']}  n_at_4={a['n_at_4']}/{a['n_seeds']}  total_exc={a['total_excellents']}", progress_path)
        else:
            progress(f"  {name}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # Pick best Phase A by (n_at_6, n_at_5, total_excellents)
    if phase_a_results:
        best_a_name, (best_a_env, best_a_agg) = max(
            phase_a_results.items(),
            key=lambda kv: (kv[1][1]["n_at_6"], kv[1][1]["n_at_5"], kv[1][1]["total_excellents"]),
        )
        best_chl1_w = best_a_env["CHL1_W_EXTRA"]
        progress(f"Phase A winner: {best_a_name} (CHL1_W_EXTRA={best_chl1_w})", progress_path)
    else:
        best_chl1_w = "3.0"
        progress(f"Phase A produced no results; defaulting CHL1_W_EXTRA={best_chl1_w} for Phase B", progress_path)

    # ---- Phase B: AOI weight refinement at best Chl1 weight ----
    progress(f"=== PHASE B: AOI weight refinement at CHL1_W_EXTRA={best_chl1_w} ===", progress_path)
    phase_b = make_phase_b(best_chl1_w)
    for name, env in phase_b:
        statuses.append(run_one(name, env, LOG_DIR, progress_path))
    progress("Phase B done. Aggregating...", progress_path)
    phase_b_results = {}
    for name, env in phase_b:
        pat = pattern_for({**BASE_ENV, **env})
        a = aggregate_pattern(pat)
        if a:
            phase_b_results[name] = (env, a)
            progress(f"  {name}: n_at_6={a['n_at_6']}/{a['n_seeds']}  n_at_5={a['n_at_5']}/{a['n_seeds']}  n_at_4={a['n_at_4']}/{a['n_seeds']}  total_exc={a['total_excellents']}", progress_path)
        else:
            progress(f"  {name}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # Phase B winner: best across A + B by same criteria
    all_results = {**{k: v for k, v in phase_a_results.items()}, **phase_b_results}
    if all_results:
        best_name, (best_env, best_agg) = max(
            all_results.items(),
            key=lambda kv: (kv[1][1]["n_at_6"], kv[1][1]["n_at_5"], kv[1][1]["total_excellents"]),
        )
        progress(f"Phase A+B overall winner: {best_name}  env={best_env}", progress_path)
        progress(f"  -> n_at_6={best_agg['n_at_6']}  n_at_5={best_agg['n_at_5']}  total_exc={best_agg['total_excellents']}", progress_path)
    else:
        best_env = {**PHASE_A[1][1]}
        progress(f"No Phase A/B results; Phase C using default env", progress_path)

    # ---- Phase C: more seeds at the winner ----
    progress(f"=== PHASE C: extra seeds 15-24 at the winning config ===", progress_path)
    for name, env in make_phase_c(best_env):
        statuses.append(run_one(name, env, LOG_DIR, progress_path))

    # ---- Final aggregation ----
    overall_elapsed = time.time() - overall_start
    progress(f"=== Sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===", progress_path)
    progress("Building final summary...", progress_path)

    # Re-aggregate every config with the post-Phase-C JSONs in place.
    rows = []
    for src_name, src_env in (
        [(n, e) for n, e in PHASE_A]
        + [(n, e) for n, e in make_phase_b(best_chl1_w)]
        + [(n, e) for n, e in make_phase_c(best_env)]
    ):
        pat = pattern_for({**BASE_ENV, **src_env})
        a = aggregate_pattern(pat)
        if a:
            rows.append((src_name, src_env, a))

    rows.sort(key=lambda r: (-r[2]["n_at_6"], -r[2]["n_at_5"], -r[2]["total_excellents"]))

    summary_lines = [
        "=== Overnight v3.0 parameter-learner sweep summary ===",
        f"Started:  {datetime.fromtimestamp(overall_start).isoformat()}",
        f"Finished: {datetime.now().isoformat()}",
        f"Total wall-clock: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min",
        "",
        f"{'Rank':<5} {'6+/n':<6} {'5+/n':<6} {'4+/n':<6} {'mean_cal':<9} {'total_exc':<10} {'config'}",
    ]
    for i, (name, env, a) in enumerate(rows, 1):
        cfg = " ".join(f"{k}={v}" for k, v in env.items() if k != "NB23_SEEDS")
        summary_lines.append(
            f"{i:<5} {a['n_at_6']}/{a['n_seeds']:<5} {a['n_at_5']}/{a['n_seeds']:<5} {a['n_at_4']}/{a['n_seeds']:<5} "
            f"{a['mean_cal']:<9.2f} {a['total_excellents']:<10} {name}  {cfg}"
        )

    # If any config hit 6/6, surface the winning seeds.
    summary_lines.append("")
    six_six_found = False
    for name, env, a in rows:
        if a["n_at_6"] > 0:
            six_six_found = True
            pat = pattern_for({**BASE_ENV, **env})
            for f in sorted(glob.glob(pat)):
                r = json.load(open(f))
                if r["n_cal_grade"] >= 6:
                    summary_lines.append(f"  6/6 in {name}, seed {r['seed']}: file {Path(f).name}")
    if not six_six_found:
        summary_lines.append("No 6/6 achieved across the sweep. Top 5+/6 rate identifies the config nearest the ceiling.")

    summary_lines.append("")
    summary_lines.append("Per-config detail:")
    for name, env, a in rows[:10]:
        summary_lines.append(f"  [{name}] cal_counts={a['cal_counts']} exc_counts={a['exc_counts']}  miss_dist={a['miss_distribution']}")

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    progress(f"Summary written to {summary_path}", progress_path)


if __name__ == "__main__":
    main()
