"""Two-stage curriculum sweep — pure v05 framing (Carroll-6 proof-of-concept).

Hypothesis (untested in the project): the 2-basin mutex is a property of the
LOSS LANDSCAPE, not of the parameters themselves. Random-init training picks
whichever basin the optimizer's starting point is closest to. If we WARM-START
the network in basin A's neighborhood and apply a Stage-2 fine-tune with basin-B
anchors at reduced learning rate, the optimizer may find a local minimum near
the basin-A init that also satisfies basin-B anchors — bypassing the binary
mutex.

Stage 1: POSi-only (basin A, PR #60-style). 1500 epochs, full LR. SAVE
  checkpoint per seed.
Stage 2 (4 variants): + Darwin paired anchor (PIC_ABS + POC_ABS, PR #63-style).
  LOAD Stage 1 checkpoint as init. Reduced LR + fewer epochs to stay near init.
  - C1: PIC_ABS=0.5 + POC_ABS=0.25  + LR_MULT=0.2 + 500 epochs
  - C2: PIC_ABS=0.2 + POC_ABS=0.1   + LR_MULT=0.2 + 500 epochs (gentler anchor)
  - C3: PIC_ABS=0.5 + POC_ABS=0.25  + LR_MULT=0.1 + 1000 epochs (slower + longer)
  - C4: PIC_ABS=0.1 + POC_ABS=0.05  + LR_MULT=0.5 + 300 epochs (very gentle)

If ANY config keeps alpfe + scav_rat + diatomgraz Cal-grade (from Stage 1 basin A)
WHILE recovering R_PICPOC + Biggrow (from Stage 2 basin B anchor) — that's the
first 6/6 path in the project. Smallgrow is recoverable in both basins.

Wall-clock budget:
  Stage 1: 1 run × n=10 seeds × ~5 min = 5 min
  Stage 2: 4 configs × n=10 seeds × ~3 min (fewer epochs) = 12 min
  Total: ~20 min
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
LOG_DIR = ROOT / "logs" / f"sweep_curriculum_{STAMP}"
STAGE1_DIR = Path(rf"D:\runs\sweep_curriculum_{STAMP}\stage1")
STAGE2_BASE = Path(rf"D:\runs\sweep_curriculum_{STAMP}")

BASE_ENV = {
    "AOI_ID_CHANNEL": "1",
    "POC_SUB_W": "0.5",
    "GEOTRACES_POC_SUB_W": "0.5",
    "DINN_HIDDEN_DIM": "32",
    "AOI_W_NATLSUBPOLAR": "2.0",
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUNBUFFERED": "1",
}

STAGE1_ENV = {
    **BASE_ENV,
    "OUTPUT_DIR": str(STAGE1_DIR),
    "NB23_N_EPOCHS": "1500",
    "POSI_W": "1.0",
    "SAVE_CHECKPOINTS": "1",
    "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9",
}

# Stage 2 configs all inherit Stage 1 baseline + POSi=1.0 (carry the basin-A
# anchor forward so we keep its constraint during fine-tune), add Darwin paired
# anchor, load Stage 1 init, reduce LR + epochs.
def stage2_env(name: str, pic_w: str, poc_w: str, lr_mult: str, epochs: str) -> dict:
    return {
        **BASE_ENV,
        "OUTPUT_DIR": str(STAGE2_BASE / name),
        "NB23_N_EPOCHS": epochs,
        "POSI_W": "1.0",
        "PIC_ABS_W": pic_w,
        "POC_ABS_W": poc_w,
        "LOAD_CHECKPOINT_DIR": str(STAGE1_DIR / "checkpoints"),
        "LR_MULTIPLIER": lr_mult,
        "NB23_SEEDS": "0,1,2,3,4,5,6,7,8,9",
    }


STAGE2_CONFIGS = [
    ("C1_pair0.5_lr0.2_e500", stage2_env("C1_pair0.5_lr0.2_e500", "0.5", "0.25", "0.2", "500")),
    ("C2_pair0.2_lr0.2_e500", stage2_env("C2_pair0.2_lr0.2_e500", "0.2", "0.1",  "0.2", "500")),
    ("C3_pair0.5_lr0.1_e1000", stage2_env("C3_pair0.5_lr0.1_e1000", "0.5", "0.25", "0.1", "1000")),
    ("C4_pair0.1_lr0.5_e300", stage2_env("C4_pair0.1_lr0.5_e300", "0.1", "0.05", "0.5", "300")),
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
    progress(f"START {name}", p)
    env = os.environ.copy()
    env.update(env_over)
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
    return status == "OK"


def aggregate(out_dir: Path):
    files = sorted(glob.glob(str(out_dir / "run_v3.0_joint_*.json")))
    if not files: return None
    runs = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                runs.append(json.load(fh))
        except Exception:
            pass
    if not runs: return None
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
    STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    p = LOG_DIR / "PROGRESS.txt"
    progress("=" * 72, p)
    progress("TWO-STAGE CURRICULUM sweep — pure v05 framing (Carroll-6)", p)
    progress("=" * 72, p)
    progress(f"  Stage 1 dir: {STAGE1_DIR}", p)
    progress(f"  Stage 2 base: {STAGE2_BASE}", p)

    t0 = time.time()

    # ---- STAGE 1: POSi-only basin A ----
    progress("=== STAGE 1: POSi-only (basin A) ===", p)
    if not run_one("Stage1_POSi_basin_A", STAGE1_ENV, LOG_DIR, p):
        progress("Stage 1 FAILED -- aborting", p)
        return 2
    a1 = aggregate(STAGE1_DIR)
    if a1:
        pcal = ", ".join(f"{k}={v}" for k, v in a1["pcal"].items())
        progress(f"  Stage 1: n={a1['n']}  at5={a1['n_at_5']}  mean_cal={a1['mean_cal']:.2f}  R_PIC={a1['rpicpoc_mean']:.4f}\n"
                 f"    Cal counts: {pcal}", p)

    # Verify checkpoints exist
    ckpt_dir = STAGE1_DIR / "checkpoints"
    ckpts = sorted(ckpt_dir.glob("seed*.pt")) if ckpt_dir.is_dir() else []
    progress(f"  Stage 1 checkpoints saved: {len(ckpts)} files in {ckpt_dir}", p)
    if not ckpts:
        progress("  No checkpoints found -- Stage 2 will fall back to random init", p)

    # ---- STAGE 2: paired Darwin anchor fine-tunes ----
    progress("=== STAGE 2: Darwin paired anchor (fine-tune from Stage 1 init) ===", p)
    results = {}
    for name, env in STAGE2_CONFIGS:
        Path(env["OUTPUT_DIR"]).mkdir(parents=True, exist_ok=True)
        run_one(name, env, LOG_DIR, p)
        a = aggregate(Path(env["OUTPUT_DIR"]))
        if a:
            results[name] = a
            pcal = ", ".join(f"{k}={v}" for k, v in a["pcal"].items())
            progress(f"  {name}: n={a['n']}  at6={a['n_at_6']}  at5={a['n_at_5']}  at4={a['n_at_4']}  "
                     f"mean_cal={a['mean_cal']:.2f}  excs={a['excs']}  R_PIC_mean={a['rpicpoc_mean']:.4f}\n"
                     f"    Cal counts: {pcal}", p)

    elapsed = time.time() - t0
    progress("=" * 72, p)
    progress(f"Sweep done in {elapsed/60:.1f} min", p)
    progress("=" * 72, p)

    if results:
        ranked = sorted(results.items(),
                        key=lambda kv: (kv[1]['n_at_6'], kv[1]['n_at_5'], kv[1]['mean_cal']),
                        reverse=True)
        progress(f"BEST: {ranked[0][0]} -- at6={ranked[0][1]['n_at_6']}, at5={ranked[0][1]['n_at_5']}, "
                 f"mean={ranked[0][1]['mean_cal']:.2f}", p)
        if ranked[0][1]['n_at_6'] > 0:
            progress("*** 6/6 PATH FOUND — this is the proof-of-concept headline ***", p)
        elif ranked[0][1]['n_at_5'] > 7:
            progress(f"*** Strong 5/6 result ({ranked[0][1]['n_at_5']}/10) — beats PR #57 baseline 7/15 ***", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
