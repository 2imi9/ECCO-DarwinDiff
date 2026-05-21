"""Lower-weight MODIS-Aqua PIC anchor sweep.

Follows up on the W=1.0 sweep (scripts/sweep_modis_pic.py), which found that
MODIS_PIC_ABS_W=1.0 pulls R_PICPOC away from Carroll's published 0.04245
toward the satellite-implied magnitude (15-50x higher in eqpac). At weight
1.0 the satellite anchor dominates; at weight 0 it's off.

This sweep tests intermediate values to find the sweet spot where:
  - R_PICPOC stays near Carroll's published value (Cal-grade)
  - Spatial pattern from MODIS is still respected (regularization-like)
  - Other params (alpfe / diatomgraz) get released from basin-A trap

Configs at n=10 each:
  L1: MODIS_PIC=0.01 + POC=0.25 + POSi=1.0
  L2: MODIS_PIC=0.1  + POC=0.25 + POSi=1.0
  L3: MODIS_PIC=0.3  + POC=0.25 + POSi=1.0
  L4: MODIS_PIC=0.1  + POSi=1.0           (solo, no POC pairing)

Wall-clock: ~20 min.
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
LOG_DIR = ROOT / "logs" / f"sweep_modis_pic_lowW_{STAMP}"
OUTPUT_DIR = Path(rf"D:\runs\sweep_modis_pic_lowW_{STAMP}")

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

CONFIGS = [
    ("L1_modisW0.01_paired",
     {"MODIS_PIC_ABS_W": "0.01", "POC_ABS_W": "0.25", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("L2_modisW0.1_paired",
     {"MODIS_PIC_ABS_W": "0.1", "POC_ABS_W": "0.25", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("L3_modisW0.3_paired",
     {"MODIS_PIC_ABS_W": "0.3", "POC_ABS_W": "0.25", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("L4_modisW0.1_solo",
     {"MODIS_PIC_ABS_W": "0.1", "POSI_W": "1.0",
      "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
]

CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}


def progress(line, p):
    out = f"[{datetime.now().strftime('%H:%M:%S')}] {line}"
    print(out, flush=True)
    with p.open("a", encoding="utf-8") as f: f.write(out + "\n")


def run_one(name, env_over, log_dir, p):
    if (log_dir / "STOP").exists():
        progress(f"STOP -- skipping {name}", p)
        return {"name": name, "status": "STOP", "elapsed": 0.0, "env": env_over}
    progress(f"START {name}  {env_over}", p)
    env = os.environ.copy(); env.update(BASE_ENV); env.update(env_over)
    log_path = log_dir / f"{name}.log"
    t0 = time.time()
    try:
        with log_path.open("w", encoding="utf-8") as lf:
            r = subprocess.run([sys.executable, str(RUNNER)], env=env, stdout=lf,
                               stderr=subprocess.STDOUT, cwd=str(ROOT), timeout=1800)
        elapsed = time.time() - t0
        status = "OK" if r.returncode == 0 else f"FAIL exit={r.returncode}"
    except Exception as e:
        elapsed = time.time() - t0; status = f"EXCEPTION {type(e).__name__}: {e}"
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", p)
    return {"name": name, "status": status, "elapsed": elapsed, "env": env_over}


def aggregate(env):
    """Glob for JSONs matching this env and return summary."""
    def g(k, default): return env.get(k, BASE_ENV.get(k, default))
    parts = ["run_v3.0_joint_eqpac-natlsubpolar_seed*"]
    parts.append(f"_surf{g('GEOTRACES_W', '0.3')}_sub{g('GEOTRACES_SUB_W', '1.0')}_pinn{g('NB23_PINN_WEIGHT', '3.0')}")
    if float(g('POC_SUB_W', '3.0')) > 0:
        parts.append(f"_pocsubW{g('POC_SUB_W', '3.0')}")
    if float(g('GEOTRACES_POC_SUB_W', '0.0')) > 0:
        parts.append(f"_geopocW{g('GEOTRACES_POC_SUB_W', '0.0')}")
    if g('AOI_ID_CHANNEL', '0') == '1':
        parts.append("_aoiid")
    hd = g('DINN_HIDDEN_DIM', '16')
    if hd != "16": parts.append(f"_hd{hd}")
    natl = float(g('AOI_W_NATLSUBPOLAR', '1.0'))
    if natl != 1.0: parts.append(f"_w-natlsubpolar{natl}")
    if float(g('POC_ABS_W', '0.0')) > 0:
        parts.append(f"_pocabsW{g('POC_ABS_W', '0.0')}")
    if float(g('POSI_W', '0.0')) > 0:
        parts.append(f"_posiW{g('POSI_W', '0.0')}")
    if float(g('MODIS_PIC_ABS_W', '0.0')) > 0:
        parts.append(f"_modispicW{g('MODIS_PIC_ABS_W', '0.0')}")
    parts.append(".json")
    pat = str(OUTPUT_DIR) + "/" + "".join(parts)
    files = sorted(glob.glob(pat))
    if not files: return None
    runs = [json.load(open(f, encoding="utf-8")) for f in files]
    cal = [r["n_cal_grade"] for r in runs]
    exc = [r["n_excellent"] for r in runs]
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
        "excs": sum(exc),
        "pcal": pcal,
        "rpicpoc_mean": sum(rpv) / len(rpv),
    }


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / "PROGRESS.txt"
    progress("MODIS-Aqua PIC LOW-WEIGHT sweep", p)
    progress(f"  Runner: {RUNNER.name}", p)
    t0 = time.time()
    statuses = []
    for name, env in CONFIGS:
        statuses.append(run_one(name, env, LOG_DIR, p))
        a = aggregate(env)
        if a:
            pcal = ", ".join(f"{k}={v}" for k, v in a["pcal"].items())
            progress(f"  {name}: n={a['n']}  at6={a['n_at_6']}  at5={a['n_at_5']}  at4={a['n_at_4']}  "
                     f"mean_cal={a['mean_cal']:.2f}  excs={a['excs']}  R_PICPOC_mean={a['rpicpoc_mean']:.4f}\n"
                     f"    Cal counts: {pcal}", p)
    elapsed = time.time() - t0
    progress(f"Sweep done in {elapsed/60:.1f} min", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
