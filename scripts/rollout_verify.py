"""Long-horizon rollout verification — does the emulator survive past a few steps?

Why this is THE test: a next-step surrogate that cannot roll out isn't a simulator, and the
emulator's whole value proposition is speed (measured: 7.5 ms/global month, ~9 s/simulated century).
Speed is worthless if the trajectory falls apart. We already know it goes non-physical fast
(negative concentrations + mass drift by ~6 steps).

BASELINES — this is the crux. Skill-vs-persistence is MISLEADING at long horizons: persistence
decays as the field decorrelates, so "beating persistence" gets EASIER the longer you roll, and a
drifting model can look like it is improving. Climatology is the honest long-lead baseline:
  - short lead  -> persistence is strong, climatology is weak
  - long lead   -> persistence is weak, CLIMATOLOGY is the bar to beat
A model that drifts to mush loses to climatology. We report BOTH, plus physics at every step.

Climatology = month-of-year mean over the TRAINING period only (no leakage).

Run:
  python scripts/rollout_verify.py --cube global3d_L10_cube.npz --model 'de3d_seed*.pt' \
      --horizons 1,3,6,12,24,36 --out rollout.json
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
from darwindiff.safe_load import safe_torch_load  # noqa: E402
from diffusion_emulator import FNO2d, load_cube, time_split, zscore  # noqa: E402


def elapsed_days(cube_path, T, calendar="iters", dt_seconds=1200.0):
    """Model time in days per timestep.

    CALENDAR BUG (found 2026-07-19). `times_days` stored in the cubes was built with a
    900 s timestep, but ECCO-Darwin v05 runs at **1200 s** (72 iterations/day). Every
    stored `times_days` value is therefore exactly 0.75x the true model time, and the
    month-of-year bins derived from it are wrong for 94.9% of timesteps in
    `global3d_L10_cube.npz` -- which silently corrupts the CLIMATOLOGY baseline into
    something closer to a time-mean than a seasonal cycle, i.e. an easier bar.

    `iters` (the raw MITgcm iteration numbers) are ground truth; prefer them.
    """
    z = np.load(cube_path, allow_pickle=True)
    if calendar == "iters" and "iters" in z:
        return np.asarray(z["iters"], dtype=float) * dt_seconds / 86400.0
    return np.asarray(z["times_days"], dtype=float)


def month_of_year(cube_path, T, calendar="iters", dt_seconds=1200.0):
    """Month index 0-11 per timestep (epoch 1992-01-01). Falls back to t%12."""
    try:
        days = elapsed_days(cube_path, T, calendar, dt_seconds)
        base = np.datetime64("1992-01-01")
        dates = base + days.astype("timedelta64[D]")
        return dates.astype("datetime64[M]").astype(int) % 12
    except Exception:
        return np.arange(T) % 12


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cube", required=True)
    p.add_argument("--model", nargs="+", required=True)
    p.add_argument("--horizons", default="1,3,6,12,24,36")
    p.add_argument("--n-starts", type=int, default=6, help="rollout start points in the val split")
    p.add_argument("--log-transform", action="store_true")
    p.add_argument("--log-floor", type=float, default=1e-4)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--out", default=None)
    p.add_argument("--calendar", choices=["iters", "times_days"], default="iters",
                   help="source of model time. 'iters' is ground truth; 'times_days' reproduces "
                        "the pre-2026-07-19 behaviour and is WRONG (0.75x, see elapsed_days docstring).")
    p.add_argument("--dt-scaled-residual", action="store_true",
                   help="the checkpoints emit a PER-MONTH TENDENCY (trained with "
                        "diffusion_emulator.py --dt-scaled-residual); apply each step as "
                        "x + f(x)*dt_months instead of x + f(x). Rolling such a model out with "
                        "the plain map under-predicts every step and compounds over the horizon.")
    p.add_argument("--dt-seconds", type=float, default=1200.0,
                   help="ECCO-Darwin v05 timestep (72 iters/day). Only used with --calendar iters.")
    args = p.parse_args(argv)
    device = "cpu" if (args.cpu or not torch.cuda.is_available()) else "cuda"
    H_LIST = [int(h) for h in args.horizons.split(",")]

    paths = sorted({q for m in args.model for q in glob.glob(m)})
    state, mask, names = load_cube(args.cube)
    if args.log_transform:
        state = np.log(np.clip(state, args.log_floor, None)).astype(np.float32)
    T, C, Hh, Ww = state.shape
    z, mean, std = zscore(state, mask)
    del state
    Z = torch.from_numpy(z)
    tr_t, va_t = time_split(T)
    moy = month_of_year(args.cube, T, args.calendar, args.dt_seconds)

    # Horizons are STEP counts, not months. The cube is not a contiguous monthly series
    # (median val-split spacing ~61 days), so label every horizon with true elapsed time.
    _days = elapsed_days(args.cube, T, args.calendar, args.dt_seconds)
    _tr, _va = time_split(T)
    _dv = np.diff(_days)[min(_va):] if len(_va) else np.diff(_days)
    _step_days = float(np.median(_dv)) if len(_dv) else float("nan")
    print(f"[calendar] {args.calendar} dt={args.dt_seconds:.0f}s | "
          f"median val step = {_step_days:.1f} days ({_step_days/30.4375:.2f} months)")
    print("[calendar] horizon k = k STEPS, i.e. "
          + ", ".join(f"{h}->{h*_step_days/30.4375:.1f}mo" for h in H_LIST))
    # Per-step gap in months, used only by --dt-scaled-residual. Padded to length T so an
    # index at the final step is safe.
    _gm = np.diff(_days) / 30.4375
    _gap_mo = np.concatenate([_gm, [_gm[-1]]]) if len(_gm) else np.ones(T)
    if args.dt_scaled_residual:
        print(f"[dt-scaled] applying x + f(x)*dt_months | val-step gaps "
              f"median {np.median(_gm[min(_va):]) if len(_va) else float('nan'):.2f} mo")

    # ---- climatology from TRAINING period only (no leakage) ----
    clim = np.zeros((12, C, Hh, Ww), dtype=np.float32)
    for m_ in range(12):
        idx = [t for t in range(max(tr_t) + 2) if moy[t] == m_]
        clim[m_] = z[idx].mean(axis=0) if idx else 0.0
    clim_t = torch.from_numpy(clim)

    models = []
    for pth in paths:
        ck = safe_torch_load(pth, map_location=device)
        cfg = ck["config"]
        m = FNO2d(C, C, modes1=cfg["modes"], modes2=cfg["modes"], width=cfg["reg_width"]).to(device)
        m.load_state_dict(ck["regression"]); m.eval(); models.append(m)
    print(f"[rollout] {len(models)} member(s) | cube {(T,C,Hh,Ww)} | horizons {H_LIST}", flush=True)

    mask_t = torch.from_numpy(mask.astype(np.float32))[None, None].to(device)
    mean_t = torch.tensor(mean, device=device).view(1, -1, 1, 1)
    std_t = torch.tensor(std, device=device).view(1, -1, 1, 1)
    maxh = max(H_LIST)
    starts = [t for t in va_t if t + maxh < T][: args.n_starts]
    if not starts:
        print("ERROR: val split too short for max horizon"); return 2
    print(f"[rollout] {len(starts)} start points", flush=True)

    acc = {h: {"model": 0.0, "persist": 0.0, "clim": 0.0, "neg": 0.0, "mass": 0.0, "n": 0} for h in H_LIST}
    with torch.no_grad():
        for s in starts:
            x0 = Z[s : s + 1].to(device)
            x = x0.clone()
            for k in range(1, maxh + 1):
                # autoregressive step; ensemble = mean of member steps.
                #   plain              : x_{t+1} = x_t + f(x_t)
                #   --dt-scaled-residual: x_{t+1} = x_t + f(x_t) * dt_months(t)
                # The dt-scaled model emits a PER-MONTH TENDENCY, so rolling it out with the
                # plain map applies a one-month rate across a ~2-month step and under-predicts
                # every step, compounding over the horizon. Matches train_regression's
                # dt_months branch in diffusion_emulator.py. See commit 79717cc for the same
                # bug in the single-step reporting path.
                _s = float(_gap_mo[s + k - 1]) if args.dt_scaled_residual else 1.0
                if len(models) > 1:
                    x = torch.stack([x + m(x) * _s for m in models]).mean(0)
                else:
                    x = x + models[0](x) * _s
                if k in acc:
                    y = Z[s + k : s + k + 1].to(device)
                    cb = clim_t[moy[s + k]].unsqueeze(0).to(device)
                    a = acc[k]
                    a["model"] += float((((x - y) ** 2) * mask_t).mean())
                    a["persist"] += float((((x0 - y) ** 2) * mask_t).mean())
                    a["clim"] += float((((cb - y) ** 2) * mask_t).mean())
                    # physics in PHYSICAL units — exp() inverse if log-trained, else negatives/mass
                    # would be measured in log space (log<0 for conc<1) = a meaningless ~66% "violation".
                    xp = torch.exp(x * std_t + mean_t) if args.log_transform else (x * std_t + mean_t)
                    yp = torch.exp(y * std_t + mean_t) if args.log_transform else (y * std_t + mean_t)
                    a["neg"] += float(((xp < 0).float() * mask_t).sum() / mask_t.sum() / C)
                    tot_x = float((xp * mask_t).sum()); tot_y = float((yp * mask_t).sum())
                    a["mass"] += tot_x / tot_y if abs(tot_y) > 1e-9 else float("nan")
                    a["n"] += 1

    print(f"\n{'horizon':>8}{'skill_vs_PERSIST':>18}{'skill_vs_CLIM':>15}{'neg_frac':>10}{'mass_ratio':>12}")
    rows = {}
    for h in H_LIST:
        a = acc[h]; n = max(a["n"], 1)
        mm, pp, cc = a["model"] / n, a["persist"] / n, a["clim"] / n
        sp = 1 - mm / max(pp, 1e-12)
        sc = 1 - mm / max(cc, 1e-12)
        rows[h] = {"skill_vs_persistence": sp, "skill_vs_climatology": sc,
                   "neg_fraction": a["neg"] / n, "mass_ratio": a["mass"] / n,
                   "mse_model": mm, "mse_persist": pp, "mse_clim": cc,
                   "elapsed_months": h * _step_days / 30.4375}
        print(f"{h:>8}{sp:>+18.3f}{sc:>+15.3f}{a['neg']/n:>10.3f}{a['mass']/n:>12.3f}")
    print("\nskill_vs_CLIMATOLOGY is the honest long-lead bar (persistence decays, so beating it gets EASIER).")
    print("mass_ratio 1.0 = conserved; neg_frac 0 = physical. If skill_vs_clim goes <=0 the rollout is dead.")
    if args.out:
        Path(args.out).write_text(json.dumps({"horizons": rows, "n_members": len(models),
                                              "n_starts": len(starts)}, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
