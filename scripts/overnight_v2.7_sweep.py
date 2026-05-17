"""Overnight v2.7 sweep — multi-seed extension + SUB_W finer sweep + PINN_DRIFT sensitivity.

Runs 10 batched experiments sequentially via run_v2.7_multilayer_batched.py.
Continues on failure (one bad config doesn't kill the rest). At the end, runs
analyze_v2.7_results.py for a fresh summary.

Phases:
  Phase 1: complete v2.7 n=10 at three SUB_W anchors (seeds 5-9, sub_w in {0.0, 0.3, 1.0})
  Phase 2: finer SUB_W sweep at n=10 (seeds 0-9, sub_w in {0.1, 0.5, 2.0})
  Phase 3: PINN_DRIFT sensitivity at sub=0.3 (seeds 0-4, pinn in {0.0, 1.0, 5.0, 10.0})

All at GEOTRACES_W (surface) = 0.3, 1500 epochs (the v2.7 anchor config).

Outputs:
  - One JSON per (seed, sub_w, pinn) triple in scripts/ (overwrites existing — runs are deterministic)
  - Per-run log + master summary in logs/overnight_v2.7_<timestamp>/
  - Live progress in logs/overnight_v2.7_<timestamp>/PROGRESS.txt (tail this to monitor)

Estimated wall-clock: ~30-40 min on RTX 5090 Laptop.

To kill: find the python.exe PID and Stop-Process, OR delete the STOP sentinel:
  - Create file logs/overnight_v2.7_<timestamp>/STOP to gracefully stop after the current run.
"""
from __future__ import annotations

import io
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
BATCH_SCRIPT = HERE / "run_v2.7_multilayer_batched.py"
ANALYZE_SCRIPT = HERE / "analyze_v2.7_results.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_v2.7_{STAMP}"

# (name, seeds, sub_w, pinn) -- surface always 0.3 to match v2.7 anchor.
# Phase 1a (seeds 5-9 at sub=0.0) completed in the prior aborted run; skipping.
EXPERIMENTS = [
    # Phase 1: complete v2.7 n=10 at three SUB_W anchors
    ("phase1b_sub0.3_seeds5-9",  "5,6,7,8,9",         "0.3", "3.0"),
    ("phase1c_sub1.0_seeds5-9",  "5,6,7,8,9",         "1.0", "3.0"),
    # Phase 2: finer SUB_W sweep at n=10
    ("phase2a_sub0.1_seeds0-9",  "0,1,2,3,4,5,6,7,8,9", "0.1", "3.0"),
    ("phase2b_sub0.5_seeds0-9",  "0,1,2,3,4,5,6,7,8,9", "0.5", "3.0"),
    ("phase2c_sub2.0_seeds0-9",  "0,1,2,3,4,5,6,7,8,9", "2.0", "3.0"),
    # Phase 3: PINN_DRIFT sensitivity at sub=0.3
    ("phase3a_pinn0.0_seeds0-4", "0,1,2,3,4",         "0.3", "0.0"),
    ("phase3b_pinn1.0_seeds0-4", "0,1,2,3,4",         "0.3", "1.0"),
    ("phase3c_pinn5.0_seeds0-4", "0,1,2,3,4",         "0.3", "5.0"),
    ("phase3d_pinn10.0_seeds0-4","0,1,2,3,4",         "0.3", "10.0"),
]

TIMEOUT_PER_RUN = 1200  # 20 min cap per batched run

def progress(line: str, progress_path: Path):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(line, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.txt"
    stop_path = LOG_DIR / "STOP"

    progress(f"=== Overnight v2.7 sweep starting ===", progress_path)
    progress(f"  {len(EXPERIMENTS)} batched runs queued", progress_path)
    progress(f"  Log dir: {LOG_DIR}", progress_path)
    progress(f"  Estimated wall-clock: 30-40 min", progress_path)
    progress(f"  Graceful stop: touch {stop_path}", progress_path)

    overall_start = time.time()
    statuses: list[tuple[str, str, float]] = []  # (name, status, elapsed_s)

    for i, (name, seeds, sub_w, pinn) in enumerate(EXPERIMENTS, 1):
        if stop_path.exists():
            progress(f"STOP sentinel detected — halting before [{i}/{len(EXPERIMENTS)}] {name}", progress_path)
            statuses.append((name, "SKIPPED_STOP", 0.0))
            break

        progress(f"[{i}/{len(EXPERIMENTS)}] {name} (seeds={seeds}, sub={sub_w}, pinn={pinn})", progress_path)
        env = os.environ.copy()
        env["NB23_SEEDS"] = seeds
        env["GEOTRACES_W"] = "0.3"
        env["GEOTRACES_SUB_W"] = sub_w
        env["NB23_PINN_WEIGHT"] = pinn
        env["PYTHONIOENCODING"] = "utf-8"

        log_path = LOG_DIR / f"{name}.log"
        start = time.time()
        try:
            with log_path.open("w", encoding="utf-8") as logf:
                result = subprocess.run(
                    [sys.executable, str(BATCH_SCRIPT)],
                    env=env, stdout=logf, stderr=subprocess.STDOUT,
                    cwd=str(ROOT), timeout=TIMEOUT_PER_RUN,
                )
            elapsed = time.time() - start
            status = "OK" if result.returncode == 0 else f"FAIL exit={result.returncode}"
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            status = f"TIMEOUT after {elapsed:.0f}s"
        except Exception as e:
            elapsed = time.time() - start
            status = f"EXCEPTION {type(e).__name__}: {e}"

        statuses.append((name, status, elapsed))
        progress(f"  -> {status} ({elapsed:.0f}s)", progress_path)

    overall_elapsed = time.time() - overall_start
    progress(f"=== Sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===", progress_path)

    # Run analyze step (regardless of failures — always informative)
    progress("Running analyze_v2.7_results.py...", progress_path)
    analyze_log = LOG_DIR / "analyze.log"
    try:
        with analyze_log.open("w", encoding="utf-8") as logf:
            result = subprocess.run(
                [sys.executable, str(ANALYZE_SCRIPT)],
                stdout=logf, stderr=subprocess.STDOUT,
                cwd=str(ROOT), timeout=600,
            )
        analyze_status = "OK" if result.returncode == 0 else f"FAIL exit={result.returncode}"
    except Exception as e:
        analyze_status = f"EXCEPTION {type(e).__name__}: {e}"
    progress(f"  analyze -> {analyze_status}", progress_path)

    # Write summary
    lines = [
        "=== Overnight v2.7 sweep summary ===",
        f"Started: {datetime.fromtimestamp(overall_start).isoformat()}",
        f"Finished: {datetime.now().isoformat()}",
        f"Total wall-clock: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min",
        f"Runs: {len(statuses)}/{len(EXPERIMENTS)}",
        "",
        "Per-run results:",
    ]
    for name, status, elapsed in statuses:
        lines.append(f"  {name}: {status} ({elapsed:.0f}s)")
    lines.append("")
    lines.append(f"Analyze step: {analyze_status} (see analyze.log)")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    progress(f"Summary written to {summary_path}", progress_path)

if __name__ == "__main__":
    main()
