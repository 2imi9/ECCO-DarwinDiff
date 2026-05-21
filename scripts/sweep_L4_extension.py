"""L4-extension sweep: chase the 6/6 path.

L4 (MODIS_PIC_ABS_W=0.1 + POSI_W=1.0 solo) was tonight's breakthrough —
first config in the project's history with simultaneous basin-A recovery
(alpfe 3/10 + scav_rat 7/10). The one missing param is R_PICPOC (mean
0.016 vs Carroll's 0.042 — undershoots).

Hypothesis: add a LIGHT Darwin v05 PIC anchor on top of L4 to pull
R_PICPOC back toward Carroll's value without destroying basin A. The
Darwin PIC anchor has a much smaller target magnitude (0.004 vs MODIS
0.063 mmol C/m^3), so per unit anchor weight Darwin's gradient is
stronger — meaning even light Darwin weights should be load-bearing.

Configs (n=10 each, ~5 min/config, ~20 min total):
  E1: MODIS=0.1 + POSI=1.0 + Darwin PIC=0.1
  E2: MODIS=0.1 + POSI=1.0 + Darwin PIC=0.2
  E3: MODIS=0.1 + POSI=1.0 + Darwin PIC=0.3
  E4: MODIS=0.1 + POSI=1.0 + Darwin PIC=0.5  (PR #63's weight — locates breaking point)

If basin A survives in any config + R_PICPOC lands Cal → first 6/6.
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
LOG_DIR = ROOT / "logs" / f"sweep_L4_ext_{STAMP}"
OUTPUT_DIR = Path(rf"D:\runs\sweep_L4_ext_{STAMP}")

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

L4_BASE = {"MODIS_PIC_ABS_W": "0.1", "POSI_W": "1.0"}

CONFIGS = [
    ("E1_darwinPIC0.1", {**L4_BASE, "PIC_ABS_W": "0.1", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("E2_darwinPIC0.2", {**L4_BASE, "PIC_ABS_W": "0.2", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("E3_darwinPIC0.3", {**L4_BASE, "PIC_ABS_W": "0.3", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
    ("E4_darwinPIC0.5", {**L4_BASE, "PIC_ABS_W": "0.5", "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9"}),
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
    if (log_dir / "STOP").exists():
        progress(f"STOP -- skipping {name}", p)
        return {"name": name, "status": "STOP", "elapsed": 0.0}
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
        elapsed = time.time() - t0; status = f"EXCEPTION {e}"
    progress(f"  -> {name}: {status} ({elapsed:.0f}s)", p)
    return {"name": name, "status": status, "elapsed": elapsed}


def aggregate(env):
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
    if float(g('PIC_ABS_W', '0.0')) > 0:
        parts.append(f"_picabsW{g('PIC_ABS_W', '0.0')}")
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


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / "PROGRESS.txt"
    progress("L4-EXTENSION sweep: chase 6/6 with MODIS+POSi+light Darwin PIC", p)
    progress(f"  Runner: {RUNNER.name}", p)
    progress(f"  JSONs: {OUTPUT_DIR}", p)

    t0 = time.time()
    best = None
    for name, env in CONFIGS:
        run_one(name, env, LOG_DIR, p)
        a = aggregate(env)
        if a:
            pcal = ", ".join(f"{k}={v}" for k, v in a["pcal"].items())
            progress(f"  {name}: n={a['n']}  at6={a['n_at_6']}  at5={a['n_at_5']}  at4={a['n_at_4']}  "
                     f"mean_cal={a['mean_cal']:.2f}  excs={a['excs']}  R_PICPOC_mean={a['rpicpoc_mean']:.4f}\n"
                     f"    Cal counts: {pcal}", p)
            if best is None or (a['n_at_6'], a['n_at_5'], a['mean_cal']) > (best[1]['n_at_6'], best[1]['n_at_5'], best[1]['mean_cal']):
                best = (name, a)

    elapsed = time.time() - t0
    progress(f"Sweep done in {elapsed/60:.1f} min", p)
    if best:
        progress(f"BEST: {best[0]} -- at6={best[1]['n_at_6']}, at5={best[1]['n_at_5']}, mean={best[1]['mean_cal']:.2f}", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
