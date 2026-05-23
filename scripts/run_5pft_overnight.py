# -*- coding: utf-8 -*-
"""Overnight 5-PFT eqpac-only sweep (2026-05-23).

Plan source: docs/research_notes/2026-05-23_overnight_diff_full_darwin.md

REFRAMING (decided autonomously overnight; see docs/research_notes/
2026-05-23_overnight_executed.md for the full reasoning):

The original plan asked to "swap carroll6_5pft.py for carroll6.py" to test a
"5-PFT vs 2-PFT proxy gap" hypothesis. That premise is incoherent with the
current codebase: v3.1 ALREADY uses the 5-PFT 2-layer integrator
(`carroll6_5pft_2layer_step`) with specific PFT mapping baked in
(`Smallgrow -> ProHL only`, `Biggrow -> lge only`; see
src/darwindiff/carroll6_5pft_2layer.py:241-246). Swapping to the single-layer
`carroll6_5pft.py` would REGRESS by losing the subsurface DFe constraint
that v2.7's 2-layer extension introduced specifically to break the
alpfe/scav_rat surface degeneracy.

The plan's INTENT — test whether Partial-tier param rates (Smallgrow 28%,
Biggrow 47%) shift when training conditions change — is honored differently
here:  we run v3.1's F2 config (Basin C base levers) at single-AOI eqpac
(instead of 3-AOI). This isolates "does multi-AOI training help or hurt the
Partial tier?" — a clean, defensible question using existing infrastructure.

Config matches BASE_ENV from overnight_v3.0_basinC_refine_v2.py with:
  - AOIS = eqpac (was: eqpac,natlsubpolar,southernoceanpac)
  - AOI_W_* knobs for natl/so become no-ops (not in AOIS)
  - everything else identical to F2 = Basin C base

Output: D:\\runs\\bcr_eqp5_<STAMP>\\seeds<X>-<Y>\\*.json

Batches: 0-9, 10-19, 20-29, 30-39 (n=40 to match plan's intent).
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
# AOIS override from env; default = single-AOI eqpac (original plan target).
# Set OVERNIGHT_AOIS=eqpac,natlsubpolar (etc) for 2-AOI ablations.
_aois_env = os.environ.get("OVERNIGHT_AOIS", "eqpac").strip()
_aoi_short = _aois_env.replace(",", "_").replace("southernoceanpac", "so").replace("natlsubpolar", "natl").replace("eqpac", "eqp")
LOG_DIR = ROOT / "logs" / f"overnight_5pft_{_aoi_short}_{STAMP}"
OUTPUT_ROOT = Path(rf"D:\runs\bcr_5pft_{_aoi_short}_{STAMP}")

# F2 = Basin C base, AOIs taken from OVERNIGHT_AOIS env (default single-AOI eqpac)
BASE_ENV = {
    "AOIS": _aois_env,                     # <-- AOI selection
    "AOI_ID_CHANNEL": "1",                 # N_AOIS=1 makes this a constant; harmless
    "POC_SUB_W": "0.5",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "POSI_W": "1.0",
    "CHL1_W_EXTRA": "3.0",
    "NB23_N_EPOCHS": "1500",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

# n=40 in 4 batches of 10 seeds (torch.compile amortizes JIT across batched seeds).
BATCHES = [
    ("seeds00-09", "0,1,2,3,4,5,6,7,8,9"),
    ("seeds10-19", "10,11,12,13,14,15,16,17,18,19"),
    ("seeds20-29", "20,21,22,23,24,25,26,27,28,29"),
    ("seeds30-39", "30,31,32,33,34,35,36,37,38,39"),
]

# Single-AOI runner should be ~3x faster than 3-AOI; allow generous timeout anyway.
TIMEOUT_PER_BATCH = 2400  # 40 min hard cap per 10-seed batch

CARROLL_PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]


def progress(line: str, progress_path: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_batch(name: str, seeds_csv: str, progress_path: Path, stop_path: Path) -> dict:
    if stop_path.exists():
        progress(f"STOP sentinel -- skipping {name}", progress_path)
        return {"name": name, "status": "SKIPPED_STOP", "elapsed": 0.0}

    batch_dir = OUTPUT_ROOT / name
    batch_dir.mkdir(parents=True, exist_ok=True)

    # Resume: skip if all expected seeds already present
    expected = seeds_csv.count(",") + 1
    existing = list(batch_dir.glob("*.json"))
    if len(existing) >= expected:
        progress(f"  RESUME: {name} already has {len(existing)} JSONs; skipping", progress_path)
        return {"name": name, "status": "SKIPPED_RESUME", "elapsed": 0.0,
                "out_dir": str(batch_dir)}

    env = os.environ.copy()
    env.update(BASE_ENV)
    env["NB23_SEEDS"] = seeds_csv
    env["OUTPUT_DIR"] = str(batch_dir)

    log_path = LOG_DIR / f"{name}.log"
    progress(f"START {name}  seeds={seeds_csv}  -> {batch_dir}", progress_path)
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
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", progress_path)
    return {"name": name, "status": status, "elapsed": elapsed,
            "out_dir": str(batch_dir)}


def aggregate_batch(batch_dir: Path) -> dict | None:
    files = sorted(glob.glob(str(batch_dir / "*.json")))
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
    cal_counts = [r.get("n_cal_grade", 0) for r in runs]
    exc_counts = [r.get("n_excellent", 0) for r in runs]
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


def write_summary(progress_path: Path, summary_path: Path) -> None:
    aggs = []
    for name, _csv in BATCHES:
        a = aggregate_batch(OUTPUT_ROOT / name)
        if a is not None:
            aggs.append((name, a))
    if not aggs:
        progress("No batches produced any results; skipping summary.", progress_path)
        return

    # combined across batches
    total_n = sum(a["n_seeds"] for _, a in aggs)
    combined = {
        "n_seeds": total_n,
        "n_at_6": sum(a["n_at_6"] for _, a in aggs),
        "n_at_5": sum(a["n_at_5"] for _, a in aggs),
        "n_at_4": sum(a["n_at_4"] for _, a in aggs),
        "mean_cal": sum(a["mean_cal"] * a["n_seeds"] for _, a in aggs) / total_n,
        "total_excellents": sum(a["total_excellents"] for _, a in aggs),
        "iron_pair_joint": sum(a["iron_pair_joint"] for _, a in aggs),
        "per_param_cal": {
            p: sum(a["per_param_cal"].get(p, 0) for _, a in aggs)
            for p in CARROLL_PARAMS
        },
    }

    lines = [
        f"# 5-PFT eqpac-only overnight sweep -- {STAMP}",
        "",
        f"**Config (F2 = Basin C base, single-AOI eqpac):**",
        "",
    ]
    for k, v in BASE_ENV.items():
        if k in ("PYTHONIOENCODING", "PYTHONUNBUFFERED"):
            continue
        lines.append(f"- `{k}={v}`")
    lines.append("")
    lines.append(f"## Combined (n={combined['n_seeds']})")
    lines.append("")
    lines.append(f"- 6+/n: {combined['n_at_6']}/{combined['n_seeds']}")
    lines.append(f"- 5+/n: {combined['n_at_5']}/{combined['n_seeds']}")
    lines.append(f"- 4+/n: {combined['n_at_4']}/{combined['n_seeds']}")
    lines.append(f"- iron-pair Cal+: {combined['iron_pair_joint']}/{combined['n_seeds']}  ({100*combined['iron_pair_joint']/combined['n_seeds']:.1f}%)")
    lines.append(f"- mean_cal: {combined['mean_cal']:.2f}")
    lines.append(f"- total Excellents: {combined['total_excellents']}")
    lines.append("")
    lines.append("### Per-parameter Cal-grade rate")
    lines.append("")
    lines.append("| Param | Cal+ | Rate |")
    lines.append("|---|---|---|")
    for p in CARROLL_PARAMS:
        n = combined["per_param_cal"][p]
        rate = 100 * n / combined["n_seeds"]
        lines.append(f"| {p} | {n}/{combined['n_seeds']} | {rate:.1f}% |")
    lines.append("")
    lines.append("## Per-batch breakdown")
    lines.append("")
    lines.append("| Batch | n | 6+/n | 5+/n | 4+/n | iron-pair | mean_cal |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, a in aggs:
        lines.append(
            f"| {name} | {a['n_seeds']} | {a['n_at_6']} | "
            f"{a['n_at_5']} | {a['n_at_4']} | "
            f"{a['iron_pair_joint']} | {a['mean_cal']:.2f} |"
        )

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    progress(f"Summary: {summary_path}", progress_path)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "summary.md"
    stop_path = LOG_DIR / "STOP"

    progress("=" * 70, progress_path)
    progress(f"5-PFT eqpac-only overnight sweep ({STAMP})", progress_path)
    progress(f"Output: {OUTPUT_ROOT}", progress_path)
    progress(f"Logs:   {LOG_DIR}", progress_path)
    progress(f"Config: {dict((k,v) for k,v in BASE_ENV.items() if k not in ('PYTHONIOENCODING','PYTHONUNBUFFERED'))}",
             progress_path)
    progress("=" * 70, progress_path)

    overall_t0 = time.time()
    statuses: list[dict] = []
    for name, seeds_csv in BATCHES:
        if stop_path.exists():
            progress(f"STOP at boundary -- exiting", progress_path)
            break
        statuses.append(run_batch(name, seeds_csv, progress_path, stop_path))
        a = aggregate_batch(OUTPUT_ROOT / name)
        if a is not None:
            progress(
                f"    aggregate {name}: 6+/n={a['n_at_6']}/{a['n_seeds']}  "
                f"5+/n={a['n_at_5']}/{a['n_seeds']}  "
                f"4+/n={a['n_at_4']}/{a['n_seeds']}  "
                f"iron-pair={a['iron_pair_joint']}/{a['n_seeds']}  "
                f"mean_cal={a['mean_cal']:.2f}",
                progress_path,
            )

    overall_elapsed = time.time() - overall_t0
    progress("", progress_path)
    progress(
        f"=== sweep done: {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min ===",
        progress_path,
    )

    write_summary(progress_path, summary_path)


if __name__ == "__main__":
    main()
