"""Overnight v3.0 max-lever stack sweep.

Hypothesis: the 5/6 ceiling is a 2-basin observation lock-in diagnosed at
pairs / triples of levers (PR #61-#63). The full superset has never been
tested. If 6/6 is reachable without satellite data, it lives at the stack
of every basin-A and basin-B lever simultaneously.

Phases:
  Phase SMOKE: 1 seed at the max-lever stack (~5 min). Aborts if it
    errors out -- catches env-var typos before burning overnight time.
  Phase A: full max-lever stack, n=10 seeds (~50 min).
  Phase B: stack + one extra knob each, n=5 seeds per variant (~75 min)
    - B1: + COCCOLITH_ONLY=1            (PR #63 untested at scale)
    - B2: + CHL1_W_EXTRA=3.0            (diatomgraz lever from PR #57)
    - B3: + MLD_CHANNEL=1               (richer DINN input)
  Phase C: top-2 from A+B at n=10 robustness on seeds 10-19 (~100 min).
  Phase D: final aggregation + ranked report.

Wall-clock budget: ~4 hrs total at ~5 min/seed on RTX 5090 Laptop.

Stop sentinel:
  Touch logs/overnight_v3.0_maxlever_<stamp>/STOP to cleanly halt at the
  next phase boundary.

Output:
  All JSONs land in scripts/ (default location of run_v3.0_joint_multi_aoi.py).
  Per-config logs and aggregated summary land in logs/overnight_v3.0_maxlever_<stamp>/.
  No git commit, no push -- pure on-disk.
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
LOG_DIR = ROOT / "logs" / f"overnight_v3.0_maxlever_{STAMP}"
# Windows MAX_PATH=260 forces a short prefix for the JSON outputs (the
# worktree path alone is 102 chars; max-lever filenames push us past 260).
# Use D:\runs\<stamp>\ for run JSONs; logs stay in the worktree.
OUTPUT_DIR = Path(rf"D:\runs\v3.0_maxlever_{STAMP}")

# ============================================================================
# Configuration
# ============================================================================
# Baseline knobs (project-defined "best baseline" before basin levers).
# These are inherited across every phase.
BASE_ENV = {
    "AOI_ID_CHANNEL": "1",
    "POC_SUB_W": "0.5",            # PR #63 baseline (NOT the runner-default 3.0).
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "NB23_N_EPOCHS": "1500",
    "OUTPUT_DIR": str(OUTPUT_DIR),   # redirect JSONs to short D:\runs path
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

# Max-lever stack -- every basin-A and basin-B lever turned on together.
# This is the untested-as-a-stack configuration.
#   POSI_W=1.0           : POSi anchor (basin A diatomgraz unlock, PR #60)
#   F_CO2_ABS_W=0.01     : absolute CO2 flux anchor (basin A Smallgrow, PR #62)
#   USE_MEHRBACH_K1K2=1  : Mehrbach K1/K2 carbonate (basin shift, PR #61)
#   PIC_ABS_W=0.5        : absolute PIC anchor (basin B R_PICPOC, PR #63)
#   POC_ABS_W=0.25       : absolute POC anchor (basin B R_PICPOC, PR #63)
MAX_LEVER = {
    "POSI_W": "1.0",
    "F_CO2_ABS_W": "0.01",
    "USE_MEHRBACH_K1K2": "1",
    "PIC_ABS_W": "0.5",
    "POC_ABS_W": "0.25",
}

# Phase configs (env_override -- BASE_ENV is applied first, then MAX_LEVER,
# then phase-specific keys overwrite).

PHASE_SMOKE = [
    ("S1_smoke_seed0", {**MAX_LEVER, "NB23_SEEDS": "0"}),
]

PHASE_A = [
    ("A1_maxlever_seeds0-9", {**MAX_LEVER, "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
]

PHASE_B = [
    ("B1_maxlever_cocco_seeds0-4",
     {**MAX_LEVER, "COCCOLITH_ONLY": "1", "NB23_SEEDS": "0,1,2,3,4"}),
    ("B2_maxlever_chl1W3_seeds0-4",
     {**MAX_LEVER, "CHL1_W_EXTRA": "3.0", "NB23_SEEDS": "0,1,2,3,4"}),
    ("B3_maxlever_mld_seeds0-4",
     {**MAX_LEVER, "MLD_CHANNEL": "1", "NB23_SEEDS": "0,1,2,3,4"}),
]

# Phase C is built at runtime from top-2 of Phase A+B.
def make_phase_c(top_envs: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    runs = []
    for i, (name, env) in enumerate(top_envs[:2]):
        # n=10 on a different seed range so JSONs don't collide.
        new_env = {**env, "NB23_SEEDS": "10,11,12,13,14,15,16,17,18,19"}
        runs.append((f"C{i+1}_{name}_seeds10-19", new_env))
    return runs


TIMEOUT_PER_RUN = 1800  # 30 min cap -- observed runs ~240-300s, n=10 batch ~50 min


def progress(line: str, progress_path: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with progress_path.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name: str, env_override: dict, log_dir: Path, progress_path: Path) -> dict:
    """Run a single config; return status dict."""
    if (log_dir / "STOP").exists():
        progress(f"STOP sentinel -- skipping {name}", progress_path)
        return {"name": name, "status": "SKIPPED_STOP", "elapsed": 0.0, "env": env_override}

    progress(f"START {name}  env_override={env_override}", progress_path)
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


# ============================================================================
# Aggregation
# ============================================================================
CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}


def pattern_for(env: dict[str, str]) -> str:
    """Glob pattern matching the JSONs that this env will produce.

    Mirrors the filename construction in run_v3.0_joint_multi_aoi.py:1256.
    """
    def g(k, default):
        return env.get(k, BASE_ENV.get(k, default))

    surf = g("GEOTRACES_W", "0.3")
    sub = g("GEOTRACES_SUB_W", "1.0")
    pinn = g("NB23_PINN_WEIGHT", "3.0")
    poc_sub_w = g("POC_SUB_W", "3.0")
    geo_poc = g("GEOTRACES_POC_SUB_W", "0.0")
    aoi_id = g("AOI_ID_CHANNEL", "0") == "1"
    mld = g("MLD_CHANNEL", "0") == "1"
    hd = g("DINN_HIDDEN_DIM", "16")
    natl = g("AOI_W_NATLSUBPOLAR", "1.0")
    chl1 = g("CHL1_W_EXTRA", "0.0")
    per_aoi = g("PER_AOI_DINN", "0") == "1"
    cons_lam = g("CONSISTENCY_LAMBDA", "0.0")
    pic_abs = g("PIC_ABS_W", "0.0")
    poc_abs = g("POC_ABS_W", "0.0")
    posi = g("POSI_W", "0.0")
    fco2 = g("F_CO2_ABS_W", "0.0")
    mehrbach = g("USE_MEHRBACH_K1K2", "0") == "1"
    cocco = g("COCCOLITH_ONLY", "0") == "1"

    parts = [f"run_v3.0_joint_eqpac-natlsubpolar_seed*"]
    parts.append(f"_surf{surf}_sub{sub}_pinn{pinn}")
    if float(poc_sub_w) > 0:
        parts.append(f"_pocsubW{poc_sub_w}")
    if float(geo_poc) > 0:
        parts.append(f"_geopocW{geo_poc}")
    if aoi_id:
        parts.append("_aoiid")
    if mld:
        parts.append("_mld")
    if hd != "16":
        parts.append(f"_hd{hd}")
    if float(natl) != 1.0:
        parts.append(f"_w-natlsubpolar{natl}")
    if float(chl1) > 0:
        parts.append(f"_chl1W{chl1}")
    if per_aoi:
        parts.append(f"_peraoi_lam{cons_lam}")
    if float(pic_abs) > 0:
        parts.append(f"_picabsW{pic_abs}")
    if float(poc_abs) > 0:
        parts.append(f"_pocabsW{poc_abs}")
    if float(posi) > 0:
        parts.append(f"_posiW{posi}")
    if float(fco2) > 0:
        parts.append(f"_fco2absW{fco2}")
    if mehrbach:
        parts.append("_mehrbach")
    if cocco:
        parts.append("_cocco")
    parts.append(".json")
    return str(OUTPUT_DIR) + "/" + "".join(parts)


def aggregate_pattern(pat: str) -> dict | None:
    files = sorted(glob.glob(pat))
    if not files:
        return None
    runs = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                runs.append(json.load(fh))
        except Exception:
            pass
    if not runs:
        return None
    cal_counts = [r["n_cal_grade"] for r in runs]
    exc_counts = [r["n_excellent"] for r in runs]
    misses = {}
    for r in runs:
        if r["n_cal_grade"] >= 5:
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
        "miss_distribution_at_5plus": misses,
        "mean_cal": sum(cal_counts) / len(cal_counts),
        "files": [Path(f).name for f in files],
    }


def fmt_result(name: str, agg: dict) -> str:
    misses = ", ".join(f"{p}={n}" for p, n in sorted(agg.get("miss_distribution_at_5plus", {}).items()))
    return (
        f"  {name}: n={agg['n_seeds']}  "
        f"n_at_6={agg['n_at_6']}  n_at_5={agg['n_at_5']}  n_at_4={agg['n_at_4']}  "
        f"mean_cal={agg['mean_cal']:.2f}  "
        f"excs={agg['total_excellents']}  "
        f"miss@5+={{{misses}}}"
    )


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    progress_path = LOG_DIR / "PROGRESS.txt"
    summary_path = LOG_DIR / "SUMMARY.md"
    stop_path = LOG_DIR / "STOP"

    progress("=" * 72, progress_path)
    progress(f"Overnight v3.0 MAX-LEVER STACK sweep", progress_path)
    progress("=" * 72, progress_path)
    progress(f"  Base config: {BASE_ENV}", progress_path)
    progress(f"  Max-lever stack: {MAX_LEVER}", progress_path)
    progress(f"  Stop sentinel: touch {stop_path}", progress_path)
    progress(f"  Log dir: {LOG_DIR}", progress_path)
    progress(f"  JSONs land in: {OUTPUT_DIR}/run_v3.0_joint_*.json", progress_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    overall_start = time.time()
    statuses: list[dict] = []

    # ---- Phase SMOKE: gate on a single-seed run ----
    progress("=== PHASE SMOKE: single-seed max-lever stack ===", progress_path)
    for name, env in PHASE_SMOKE:
        st = run_one(name, env, LOG_DIR, progress_path)
        statuses.append(st)
        if st["status"] != "OK":
            progress(f"  Smoke FAILED ({st['status']}). Aborting overnight. Check {LOG_DIR / (name + '.log')}.", progress_path)
            return 2

    # ---- Phase A: n=10 max-lever ----
    progress("=== PHASE A: max-lever stack, n=10 (seeds 0-9) ===", progress_path)
    for name, env in PHASE_A:
        statuses.append(run_one(name, env, LOG_DIR, progress_path))

    # Aggregate Phase A.
    phase_results: dict[str, tuple[dict, dict]] = {}
    progress("Phase A aggregation:", progress_path)
    for name, env in PHASE_A:
        pat = pattern_for(env)
        a = aggregate_pattern(pat)
        if a:
            phase_results[name] = (env, a)
            progress(fmt_result(name, a), progress_path)
        else:
            progress(f"  {name}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # ---- Phase B: stack variants at n=5 ----
    progress("=== PHASE B: stack variants, n=5 each ===", progress_path)
    for name, env in PHASE_B:
        statuses.append(run_one(name, env, LOG_DIR, progress_path))

    progress("Phase B aggregation:", progress_path)
    for name, env in PHASE_B:
        pat = pattern_for(env)
        a = aggregate_pattern(pat)
        if a:
            phase_results[name] = (env, a)
            progress(fmt_result(name, a), progress_path)
        else:
            progress(f"  {name}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # ---- Pick top-2 from A+B ----
    if phase_results:
        ranked = sorted(
            phase_results.items(),
            key=lambda kv: (kv[1][1]["n_at_6"], kv[1][1]["n_at_5"], kv[1][1]["mean_cal"], kv[1][1]["total_excellents"]),
            reverse=True,
        )
        top = [(name, env) for name, (env, _) in ranked[:2]]
        progress(f"Top-2 for Phase C: {[t[0] for t in top]}", progress_path)
    else:
        top = []
        progress("No Phase A/B results -- skipping Phase C", progress_path)

    # ---- Phase C: n=10 robustness on top-2 ----
    if top and not stop_path.exists():
        progress("=== PHASE C: top-2 robustness on seeds 10-19 ===", progress_path)
        for name, env in make_phase_c(top):
            statuses.append(run_one(name, env, LOG_DIR, progress_path))

        progress("Phase C aggregation:", progress_path)
        for name, env in make_phase_c(top):
            pat = pattern_for(env)
            a = aggregate_pattern(pat)
            if a:
                phase_results[name] = (env, a)
                progress(fmt_result(name, a), progress_path)
            else:
                progress(f"  {name}: NO_JSONS_FOUND  pattern={pat}", progress_path)

    # ---- Final ranked summary ----
    overall_elapsed = time.time() - overall_start
    progress("=" * 72, progress_path)
    progress(f"Sweep done in {overall_elapsed:.0f}s = {overall_elapsed/60:.1f} min", progress_path)
    progress("=" * 72, progress_path)

    ranked = sorted(
        phase_results.items(),
        key=lambda kv: (kv[1][1]["n_at_6"], kv[1][1]["n_at_5"], kv[1][1]["mean_cal"], kv[1][1]["total_excellents"]),
        reverse=True,
    )

    lines = [
        f"# Overnight v3.0 max-lever stack sweep — {STAMP}",
        "",
        f"**Total wall-clock:** {overall_elapsed/60:.1f} min",
        f"**Configs run:** {len(statuses)}  (smoke + A + B + C)",
        "",
        "## Headline ranking (by n_at_6, n_at_5, mean_cal, excellents)",
        "",
        "| Rank | Config | n_seeds | n@6 | n@5 | n@4 | mean_cal | excs | misses@5+ |",
        "|---:|:---|---:|---:|---:|---:|---:|---:|:---|",
    ]
    for i, (name, (env, agg)) in enumerate(ranked, start=1):
        misses = ", ".join(f"{p}={n}" for p, n in sorted(agg.get("miss_distribution_at_5plus", {}).items())) or "-"
        lines.append(
            f"| {i} | `{name}` | {agg['n_seeds']} | {agg['n_at_6']} | {agg['n_at_5']} | {agg['n_at_4']} | "
            f"{agg['mean_cal']:.2f} | {agg['total_excellents']} | {misses} |"
        )
    lines.extend([
        "",
        "## Per-config env overrides",
        "",
    ])
    for name, (env, _) in ranked:
        lines.append(f"### `{name}`")
        lines.append("```")
        for k, v in sorted(env.items()):
            lines.append(f"{k}={v}")
        lines.append("```")
        lines.append("")

    lines.extend([
        "## Run statuses",
        "",
        "| Config | Status | Elapsed |",
        "|:---|:---|---:|",
    ])
    for st in statuses:
        lines.append(f"| `{st['name']}` | {st['status']} | {st['elapsed']:.0f}s |")

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    progress(f"Summary written: {summary_path}", progress_path)
    progress(f"JSONs in: {OUTPUT_DIR}/run_v3.0_joint_*.json", progress_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
