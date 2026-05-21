"""MODIS-Aqua PIC anchor sweep -- the Phase 2.A integration test.

Hypothesis (from docs/findings/pace_arc/phase2a_modis_pic_integration.md):
Darwin v05 PIC is ~20x lower than MODIS-Aqua observed PIC in eqpac. PR #63's
paired-anchor sweep used Darwin v05 PIC, which pulled R_PICPOC toward a wrong
magnitude AND dragged alpfe + diatomgraz out of basin A. Switching to MODIS PIC
should:
  (a) recover R_PICPOC at correct magnitude (~20x higher target in eqpac)
  (b) release alpfe + diatomgraz from the false tradeoff

Configurations:
  SMOKE:  1 seed, MODIS_PIC=1.0 alone (validates the patched runner).
  M1:     POSI=1.0 + MODIS_PIC=1.0 + POC_ABS=0.25 -- the closest analogue to
          PR #63's paired anchor, with MODIS PIC replacing Darwin v05 PIC.
  M2:     POSI=1.0 + MODIS_PIC=1.0 only -- isolate the MODIS PIC effect from
          POC pairing.
  M3:     POSI=1.0 + MODIS_PIC=1.0 + POC_ABS=0.25 + USE_MEHRBACH_K1K2=1 --
          stack the working basin-A lever (Mehrbach for scav_rat) on top.

All at n=10 seeds. Wall-clock budget: ~2.5 hours.

Output:
  Per-config JSONs in D:\\runs\\sweep_modis_pic_<stamp>\\
  Aggregated summary in logs\\sweep_modis_pic_<stamp>\\SUMMARY.md
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
# IMPORTANT: this script uses the PATCHED copy with MODIS_PIC_ABS_W support.
RUNNER = HERE / "run_v3.0_with_modis_pic.py"

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"sweep_modis_pic_{STAMP}"
OUTPUT_DIR = Path(rf"D:\runs\sweep_modis_pic_{STAMP}")

BASE_ENV = {
    "AOI_ID_CHANNEL": "1",
    "POC_SUB_W": "0.5",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "NB23_N_EPOCHS": "1500",
    "OUTPUT_DIR": str(OUTPUT_DIR),
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

# Note: PIC_ABS_W stays at 0 across all configs -- the whole point is to NOT
# use the Darwin v05 PIC anchor.
PHASE_SMOKE = [
    ("S1_smoke_modis_only_seed0",
     {"MODIS_PIC_ABS_W": "1.0", "POSI_W": "1.0", "NB23_SEEDS": "0"}),
]

PHASE_MAIN = [
    ("M1_modis_paired",
     {"MODIS_PIC_ABS_W": "1.0", "POC_ABS_W": "0.25", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("M2_modis_solo",
     {"MODIS_PIC_ABS_W": "1.0", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("M3_modis_paired_mehrbach",
     {"MODIS_PIC_ABS_W": "1.0", "POC_ABS_W": "0.25", "POSI_W": "1.0",
      "USE_MEHRBACH_K1K2": "1", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
]

TIMEOUT_PER_RUN = 1800

CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}


def progress(line: str, p: Path) -> None:
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name: str, env_over: dict, log_dir: Path, p: Path) -> dict:
    if (log_dir / "STOP").exists():
        progress(f"STOP -- skipping {name}", p)
        return {"name": name, "status": "SKIPPED_STOP", "elapsed": 0.0, "env": env_over}
    progress(f"START {name}  {env_over}", p)
    env = os.environ.copy()
    env.update(BASE_ENV)
    env.update(env_over)
    log_path = log_dir / f"{name}.log"
    t0 = time.time()
    try:
        with log_path.open("w", encoding="utf-8") as lf:
            r = subprocess.run([sys.executable, str(RUNNER)], env=env, stdout=lf,
                               stderr=subprocess.STDOUT, cwd=str(ROOT),
                               timeout=TIMEOUT_PER_RUN)
        elapsed = time.time() - t0
        status = "OK" if r.returncode == 0 else f"FAIL exit={r.returncode}"
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0; status = f"TIMEOUT {elapsed:.0f}s"
    except Exception as e:
        elapsed = time.time() - t0; status = f"EXCEPTION {type(e).__name__}: {e}"
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", p)
    return {"name": name, "status": status, "elapsed": elapsed, "env": env_over}


def pattern_for(env: dict) -> str:
    """Glob pattern matching JSON outputs for this config."""
    def g(k, default):
        return env.get(k, BASE_ENV.get(k, default))

    parts = [f"run_v3.0_joint_eqpac-natlsubpolar_seed*"]
    parts.append(f"_surf{g('GEOTRACES_W', '0.3')}")
    parts.append(f"_sub{g('GEOTRACES_SUB_W', '1.0')}")
    parts.append(f"_pinn{g('NB23_PINN_WEIGHT', '3.0')}")
    if float(g('POC_SUB_W', '3.0')) > 0:
        parts.append(f"_pocsubW{g('POC_SUB_W', '3.0')}")
    if float(g('GEOTRACES_POC_SUB_W', '0.0')) > 0:
        parts.append(f"_geopocW{g('GEOTRACES_POC_SUB_W', '0.0')}")
    if g('AOI_ID_CHANNEL', '0') == '1':
        parts.append("_aoiid")
    if g('MLD_CHANNEL', '0') == '1':
        parts.append("_mld")
    hd = g('DINN_HIDDEN_DIM', '16')
    if hd != "16":
        parts.append(f"_hd{hd}")
    natl = float(g('AOI_W_NATLSUBPOLAR', '1.0'))
    if natl != 1.0:
        parts.append(f"_w-natlsubpolar{natl}")
    if float(g('CHL1_W_EXTRA', '0.0')) > 0:
        parts.append(f"_chl1W{g('CHL1_W_EXTRA', '0.0')}")
    if float(g('PIC_ABS_W', '0.0')) > 0:
        parts.append(f"_picabsW{g('PIC_ABS_W', '0.0')}")
    if float(g('POC_ABS_W', '0.0')) > 0:
        parts.append(f"_pocabsW{g('POC_ABS_W', '0.0')}")
    if float(g('POSI_W', '0.0')) > 0:
        parts.append(f"_posiW{g('POSI_W', '0.0')}")
    if float(g('F_CO2_ABS_W', '0.0')) > 0:
        parts.append(f"_fco2absW{g('F_CO2_ABS_W', '0.0')}")
    if float(g('MODIS_PIC_ABS_W', '0.0')) > 0:
        parts.append(f"_modispicW{g('MODIS_PIC_ABS_W', '0.0')}")
    if g('USE_MEHRBACH_K1K2', '0') == '1':
        parts.append("_mehrbach")
    if g('COCCOLITH_ONLY', '0') == '1':
        parts.append("_cocco")
    parts.append(".json")
    return str(OUTPUT_DIR) + "/" + "".join(parts)


def aggregate(pat: str) -> dict | None:
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
    cal = [r["n_cal_grade"] for r in runs]
    exc = [r["n_excellent"] for r in runs]
    misses_at_5 = {}
    param_excs = {p: 0 for p in CARROLL}
    param_cals = {p: 0 for p in CARROLL}
    for r in runs:
        for p in CARROLL:
            b = r["params"][p]["joint_band"]
            if b in ("Cal-grade", "Excellent"):
                param_cals[p] += 1
            if b == "Excellent":
                param_excs[p] += 1
        if r["n_cal_grade"] >= 5:
            for p in CARROLL:
                if r["params"][p]["joint_band"] not in ("Cal-grade", "Excellent"):
                    misses_at_5[p] = misses_at_5.get(p, 0) + 1
    return {
        "n": len(runs),
        "n_at_6": sum(1 for c in cal if c >= 6),
        "n_at_5": sum(1 for c in cal if c >= 5),
        "n_at_4": sum(1 for c in cal if c >= 4),
        "mean_cal": sum(cal) / len(cal),
        "total_excellents": sum(exc),
        "param_cals": param_cals,
        "param_excs": param_excs,
        "miss_at_5+": misses_at_5,
    }


def fmt(name: str, a: dict) -> str:
    pcal = ", ".join(f"{p}={a['param_cals'][p]}" for p in CARROLL)
    miss = ", ".join(f"{p}={n}" for p, n in sorted(a.get('miss_at_5+', {}).items())) or "-"
    return (f"  {name}: n={a['n']}  at6={a['n_at_6']}  at5={a['n_at_5']}  at4={a['n_at_4']}  "
            f"mean_cal={a['mean_cal']:.2f}  excs={a['total_excellents']}\n"
            f"    per-param Cal counts: {pcal}\n"
            f"    miss@5+: {miss}")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / "PROGRESS.txt"
    summary = LOG_DIR / "SUMMARY.md"

    progress("=" * 72, p)
    progress("MODIS-Aqua PIC anchor sweep -- Phase 2.A integration test", p)
    progress("=" * 72, p)
    progress(f"  Runner: {RUNNER.name}", p)
    progress(f"  Base: {BASE_ENV}", p)
    progress(f"  JSONs: {OUTPUT_DIR}", p)
    progress(f"  Stop: touch {LOG_DIR / 'STOP'}", p)

    t0 = time.time()
    statuses = []

    progress("=== SMOKE ===", p)
    for name, env in PHASE_SMOKE:
        st = run_one(name, env, LOG_DIR, p)
        statuses.append(st)
        if st["status"] != "OK":
            progress("Smoke FAILED -- aborting.", p)
            return 2

    progress("=== MAIN ===", p)
    results = {}
    for name, env in PHASE_MAIN:
        statuses.append(run_one(name, env, LOG_DIR, p))
        a = aggregate(pattern_for(env))
        if a:
            results[name] = (env, a)
            progress(fmt(name, a), p)

    elapsed = time.time() - t0
    progress("=" * 72, p)
    progress(f"Sweep done in {elapsed/60:.1f} min", p)
    progress("=" * 72, p)

    ranked = sorted(results.items(),
                    key=lambda kv: (kv[1][1]["n_at_6"], kv[1][1]["n_at_5"],
                                    kv[1][1]["mean_cal"], kv[1][1]["total_excellents"]),
                    reverse=True)

    lines = [
        f"# MODIS-Aqua PIC anchor sweep — {STAMP}",
        "",
        f"**Total wall-clock:** {elapsed/60:.1f} min",
        f"**Hypothesis:** Switching from Darwin v05 PIC (PIC_ABS_W) to MODIS-Aqua",
        "observed PIC (MODIS_PIC_ABS_W) recovers R_PICPOC at correct magnitude",
        "AND releases alpfe + diatomgraz from PR #63's false basin-A/B tradeoff.",
        "",
        "## Ranking (n_at_6, n_at_5, mean_cal, excellents)",
        "",
        "| Rank | Config | n | n@6 | n@5 | n@4 | mean | excs | miss@5+ |",
        "|---:|:---|---:|---:|---:|---:|---:|---:|:---|",
    ]
    for i, (name, (env, a)) in enumerate(ranked, start=1):
        miss = ", ".join(f"{p}={n}" for p, n in sorted(a.get('miss_at_5+', {}).items())) or "-"
        lines.append(f"| {i} | `{name}` | {a['n']} | {a['n_at_6']} | {a['n_at_5']} | "
                     f"{a['n_at_4']} | {a['mean_cal']:.2f} | {a['total_excellents']} | {miss} |")

    lines.extend(["", "## Per-parameter Cal-grade counts per config", "",
                  "| Config | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC |",
                  "|:---|---:|---:|---:|---:|---:|---:|"])
    for name, (env, a) in ranked:
        c = a["param_cals"]
        lines.append(f"| `{name}` | {c['alpfe']} | {c['scav_rat']} | {c['Smallgrow']} | "
                     f"{c['Biggrow']} | {c['diatomgraz']} | {c['R_PICPOC']} |")

    lines.extend(["", "## Configurations", ""])
    for name, (env, _) in ranked:
        lines.append(f"### `{name}`\n```")
        for k, v in sorted(env.items()):
            lines.append(f"{k}={v}")
        lines.append("```\n")

    summary.write_text("\n".join(lines), encoding="utf-8")
    progress(f"Summary: {summary}", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
