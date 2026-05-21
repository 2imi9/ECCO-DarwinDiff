"""3-AOI sweep — adds Southern Ocean Pacific to the existing eqpac + natlsubpolar.

Hypothesis (from v3.0 scoping doc): a third spatially-distinct AOI breaks more
parameter-conservation degeneracies than the eqpac/natlsubpolar pair alone.
Southern Ocean is the canonical high-particle-flux + carbonate-rich + iron-
replete regime — fundamentally different physics from eqpac (HNLC) and
natlsubpolar (deep-mixed iron-replete bloom).

Pure v05 framing (Carroll-6 proof-of-concept; no MODIS).

Configs at n=10 each, ~7-8 min per config (3 AOIs vs 2):
  D1: baseline (no anchors)                                  -- 3-AOI floor
  D2: + POSI_W=1.0                                            -- basin A boost
  D3: + POSI_W=1.0 + PIC_ABS_W=0.5 + POC_ABS_W=0.25          -- full PR #63 paired
  D4: + POSI_W=1.0 + AOI_W_SOUTHERNOCEANPAC=2.0 (per-AOI tilt)

Total wall-clock: ~30-35 min.
"""
from __future__ import annotations
import io, os, subprocess, sys, time, json, glob
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
LOG_DIR = ROOT / "logs" / f"sweep_3aoi_{STAMP}"
OUTPUT_DIR = Path(rf"D:\runs\sweep_3aoi_{STAMP}")

BASE_ENV = {
    "AOIS": "eqpac,natlsubpolar,southernoceanpac",
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

CONFIGS = [
    ("D1_baseline_3aoi",         {"NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("D2_posi_3aoi",             {"POSI_W": "1.0", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("D3_posi_paired_3aoi",      {"POSI_W": "1.0", "PIC_ABS_W": "0.5", "POC_ABS_W": "0.25",
                                  "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("D4_posi_tilt_3aoi",        {"POSI_W": "1.0", "AOI_W_SOUTHERNOCEANPAC": "2.0",
                                  "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
]

CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}


def progress(line, p):
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(out + "\n")


def run_one(name, env_over, log_dir, p):
    progress(f"START {name}  {env_over}", p)
    env = os.environ.copy(); env.update(BASE_ENV); env.update(env_over)
    log_path = log_dir / f"{name}.log"
    t0 = time.time()
    try:
        with log_path.open("w", encoding="utf-8") as lf:
            r = subprocess.run([sys.executable, str(RUNNER)], env=env, stdout=lf,
                               stderr=subprocess.STDOUT, cwd=str(ROOT), timeout=2400)
        elapsed = time.time() - t0
        status = "OK" if r.returncode == 0 else f"FAIL exit={r.returncode}"
    except Exception as e:
        elapsed = time.time() - t0; status = f"EXCEPTION {e}"
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", p)
    return status == "OK"


def aggregate_glob(pat):
    files = sorted(glob.glob(pat))
    if not files: return None
    runs = [json.load(open(f, encoding="utf-8")) for f in files]
    cal = [r["n_cal_grade"] for r in runs]
    pcal = {p: 0 for p in CARROLL}
    rpv = []
    for r in runs:
        for p in CARROLL:
            if r["params"][p]["joint_band"] in ("Cal-grade", "Excellent"):
                pcal[p] += 1
        rpv.append(r["params"]["R_PICPOC"]["joint_recovered"])
    return {
        "n": len(runs),
        "n_at_6": sum(c >= 6 for c in cal),
        "n_at_5": sum(c >= 5 for c in cal),
        "n_at_4": sum(c >= 4 for c in cal),
        "mean_cal": sum(cal) / len(cal),
        "excs": sum(r["n_excellent"] for r in runs),
        "pcal": pcal,
        "rpicpoc_mean": sum(rpv) / len(rpv),
    }


def build_pattern(env):
    """Build the glob pattern for this config's JSON outputs."""
    # 3-AOI filename: eqpac-natlsubpolar-southernoceanpac
    parts = ["run_v3.0_joint_eqpac-natlsubpolar-southernoceanpac_seed*"]
    parts.append("_surf0.3_sub1.0_pinn3.0_pocsubW0.5_geopocW0.5_aoiid_hd32_w-natlsubpolar2.0")
    if "AOI_W_SOUTHERNOCEANPAC" in env:
        parts.append(f"-southernoceanpac{env['AOI_W_SOUTHERNOCEANPAC']}")
    if "PIC_ABS_W" in env and float(env["PIC_ABS_W"]) > 0:
        parts.append(f"_picabsW{env['PIC_ABS_W']}")
    if "POC_ABS_W" in env and float(env["POC_ABS_W"]) > 0:
        parts.append(f"_pocabsW{env['POC_ABS_W']}")
    if "POSI_W" in env and float(env["POSI_W"]) > 0:
        parts.append(f"_posiW{env['POSI_W']}")
    parts.append(".json")
    return str(OUTPUT_DIR) + "/" + "".join(parts)


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / "PROGRESS.txt"
    progress("3-AOI sweep: eqpac + natlsubpolar + southernoceanpac", p)
    progress(f"  Runner: {RUNNER.name}", p)
    progress(f"  JSONs: {OUTPUT_DIR}", p)
    progress(f"  Base: {BASE_ENV}", p)

    t0 = time.time()
    results = {}
    for name, env in CONFIGS:
        run_one(name, env, LOG_DIR, p)
        pat = build_pattern(env)
        a = aggregate_glob(pat)
        if a:
            results[name] = a
            pcal = ", ".join(f"{k}={v}" for k, v in a["pcal"].items())
            progress(f"  {name}: n={a['n']}  at6={a['n_at_6']}  at5={a['n_at_5']}  at4={a['n_at_4']}  "
                     f"mean_cal={a['mean_cal']:.2f}  excs={a['excs']}  R_PIC={a['rpicpoc_mean']:.4f}\n"
                     f"    Cal counts: {pcal}", p)
        else:
            progress(f"  {name}: NO_JSONS  pattern={pat}", p)

    elapsed = time.time() - t0
    progress("=" * 72, p)
    progress(f"Sweep done in {elapsed/60:.1f} min", p)
    if results:
        ranked = sorted(results.items(),
                        key=lambda kv: (kv[1]['n_at_6'], kv[1]['n_at_5'], kv[1]['mean_cal']),
                        reverse=True)
        progress(f"BEST: {ranked[0][0]} -- at6={ranked[0][1]['n_at_6']}, at5={ranked[0][1]['n_at_5']}, "
                 f"mean={ranked[0][1]['mean_cal']:.2f}", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
