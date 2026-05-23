# -*- coding: utf-8 -*-
"""Extend the 2-AOI eqp+natl sweep from n=40 to n=80 (seeds 40-79).

Single-purpose follow-up: the n=40 run showed 13/40 at 4+/6, mean_cal 3.27,
98% at 3+/6. Worth extending to n=80 to (a) tighten the per-param rate
confidence intervals and (b) test for 5/6 events (none seen at n=40 but the
4+ rate suggests they may exist at very low probability).

Mirror of the F2 base config from run_5pft_overnight.py, with extended seed
range.
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
RUNNER = HERE / "run_v3.0_with_modis_pic.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"extend_eqp_natl_{STAMP}"
# Reuse the existing eqp_natl output root (this is the same config, just more seeds).
EXISTING_ROOT = Path(r"D:\runs\bcr_5pft_eqp_natl_20260523_1058")

BASE_ENV = {
    "AOIS": "eqpac,natlsubpolar",
    "AOI_ID_CHANNEL": "1",
    "POC_SUB_W": "0.5",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "POSI_W": "1.0",
    "CHL1_W_EXTRA": "3.0",
    "NB23_N_EPOCHS": "1500",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

BATCHES = [
    ("seeds40-49", "40,41,42,43,44,45,46,47,48,49"),
    ("seeds50-59", "50,51,52,53,54,55,56,57,58,59"),
    ("seeds60-69", "60,61,62,63,64,65,66,67,68,69"),
    ("seeds70-79", "70,71,72,73,74,75,76,77,78,79"),
]

TIMEOUT_PER_BATCH = 2400


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = LOG_DIR / "PROGRESS.txt"

    def log(msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with progress_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("=" * 70)
    log(f"Extension sweep: eqp+natl seeds 40-79 ({STAMP})")
    log(f"Output: {EXISTING_ROOT}")
    log(f"Logs:   {LOG_DIR}")
    log("=" * 70)

    overall_t0 = time.time()
    for name, seeds_csv in BATCHES:
        batch_dir = EXISTING_ROOT / name
        batch_dir.mkdir(parents=True, exist_ok=True)
        existing = list(batch_dir.glob("*.json"))
        if len(existing) >= 10:
            log(f"  RESUME: {name} has {len(existing)} JSONs; skipping")
            continue

        env = os.environ.copy()
        env.update(BASE_ENV)
        env["NB23_SEEDS"] = seeds_csv
        env["OUTPUT_DIR"] = str(batch_dir)

        log_path = LOG_DIR / f"{name}.log"
        log(f"START {name}  seeds={seeds_csv}")
        t0 = time.time()
        try:
            with log_path.open("w", encoding="utf-8") as logf:
                r = subprocess.run(
                    [sys.executable, str(RUNNER)],
                    env=env, stdout=logf, stderr=subprocess.STDOUT,
                    cwd=str(ROOT), timeout=TIMEOUT_PER_BATCH,
                )
            elapsed = time.time() - t0
            status = "OK" if r.returncode == 0 else f"FAIL exit={r.returncode}"
        except subprocess.TimeoutExpired:
            elapsed = time.time() - t0
            status = f"TIMEOUT {elapsed:.0f}s"
        except Exception as e:
            elapsed = time.time() - t0
            status = f"EXCEPTION {type(e).__name__}: {e}"
        log(f"  -> {name}: {status} ({elapsed:.0f}s)")

    log("")
    log(f"=== extension done: {time.time()-overall_t0:.0f}s ===")


if __name__ == "__main__":
    main()
