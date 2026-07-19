"""Calendar A/B — how much did the 900s-vs-1200s timestep bug inflate skill-vs-climatology?

FOUND 2026-07-19. `times_days` stored in the cubes was built with a 900 s timestep, but
ECCO-Darwin v05 runs at 1200 s (72 iters/day). Every stored time is exactly 0.75x truth, so
month-of-year bins derived from it are wrong for 94.9% of timesteps in global3d_L10_cube.npz.
A climatology built on scrambled month bins is closer to a TIME-MEAN than a seasonal cycle --
a WEAKER baseline -- so every skill-vs-climatology number we have reported is OVERSTATED.

KEY EFFICIENCY POINT: the model rollout is IDENTICAL under both calendars. Only the
climatology reference changes. So we load the (74 GB) cube once, roll out once per model set,
and score the SAME trajectories against BOTH climatologies. This isolates the baseline error
exactly -- same checkpoints, same data, same trajectories, only the calendar differs.

Usage:
  python calendar_ab.py --cube global3d_L10_cube.npz \
      --arm k8 "/scratch/.../opt3d_seed*.pt" --arm k1 "/scratch/.../opt1_seed*.pt" \
      --log-transform --n-starts 15 --horizons 1,2,3,6,9,12 --out cal_ab.json
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
from diffusion_emulator import FNO2d, load_cube, time_split, zscore  # noqa: E402
from rollout_verify import elapsed_days  # noqa: E402


def moy_from_days(days):
    base = np.datetime64("1992-01-01")
    return (base + days.astype("timedelta64[D]")).astype("datetime64[M]").astype(int) % 12


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cube", required=True)
    p.add_argument("--arm", nargs=2, action="append", metavar=("NAME", "GLOB"), required=True)
    p.add_argument("--horizons", default="1,2,3,6,9,12")
    p.add_argument("--n-starts", type=int, default=15)
    p.add_argument("--log-transform", action="store_true")
    p.add_argument("--log-floor", type=float, default=1e-4)
    p.add_argument("--dt-seconds", type=float, default=1200.0)
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    device = "cpu" if not torch.cuda.is_available() else "cuda"
    H_LIST = [int(h) for h in args.horizons.split(",")]

    # ---------------------------------------------------------------- data (ONCE)
    print("[load] reading cube ...", flush=True)
    state, mask, names = load_cube(args.cube)
    if args.log_transform:
        state = np.log(np.clip(state, args.log_floor, None)).astype(np.float32)
    T, C, Hh, Ww = state.shape
    z, mean, std = zscore(state, mask)
    del state
    Z = torch.from_numpy(z)
    tr_t, va_t = time_split(T)
    print(f"[load] cube {(T, C, Hh, Ww)} | train {len(tr_t)} val {len(va_t)}", flush=True)

    # ------------------------------------------------------- both calendars
    cals = {
        "OLD_times_days": np.asarray(np.load(args.cube, allow_pickle=True)["times_days"], dtype=float),
        "NEW_iters_1200s": elapsed_days(args.cube, T, "iters", args.dt_seconds),
    }
    clim_t, step_days, moys = {}, {}, {}
    for cname, days in cals.items():
        moy = moy_from_days(days)
        moys[cname] = moy
        clim = np.zeros((12, C, Hh, Ww), dtype=np.float32)
        for m_ in range(12):
            idx = [t for t in range(max(tr_t) + 2) if moy[t] == m_]
            clim[m_] = z[idx].mean(axis=0) if idx else 0.0
        clim_t[cname] = torch.from_numpy(clim)
        dv = np.diff(days)[min(va_t):]
        step_days[cname] = float(np.median(dv))
        occ = np.bincount(moy, minlength=12)
        print(f"[cal:{cname}] median val step {step_days[cname]:.1f} d "
              f"({step_days[cname]/30.4375:.2f} mo) | month-bin occupancy {list(occ)}", flush=True)
    n_mismatch = int((moys["OLD_times_days"] != moys["NEW_iters_1200s"]).sum())
    print(f"[cal] month-of-year bins differing between calendars: {n_mismatch}/{T} "
          f"({100*n_mismatch/T:.1f}%)", flush=True)

    mask_t = torch.from_numpy(mask.astype(np.float32))[None, None].to(device)
    mean_t = torch.tensor(mean, device=device).view(1, -1, 1, 1)
    std_t = torch.tensor(std, device=device).view(1, -1, 1, 1)
    maxh = max(H_LIST)
    starts = [t for t in va_t if t + maxh < T][: args.n_starts]
    if not starts:
        print("ERROR: val split too short for max horizon")
        return 2
    print(f"[rollout] {len(starts)} start points, horizons {H_LIST}", flush=True)

    out = {"n_starts": len(starts), "month_bin_mismatch": n_mismatch, "T": T,
           "step_days": step_days, "arms": {}}

    # ------------------------------------------------------------- per arm
    for aname, aglob in args.arm:
        paths = sorted(glob.glob(aglob))
        if not paths:
            print(f"[arm:{aname}] NO CHECKPOINTS matched {aglob} -- skipping", flush=True)
            continue
        models = []
        for pth in paths:
            ck = torch.load(pth, map_location=device, weights_only=False)
            cfg = ck["config"]
            m = FNO2d(C, C, modes1=cfg["modes"], modes2=cfg["modes"], width=cfg["reg_width"]).to(device)
            m.load_state_dict(ck["regression"])
            m.eval()
            models.append(m)
        print(f"\n[arm:{aname}] {len(models)} member(s) from {aglob}", flush=True)

        acc = {h: {"model": 0.0, "persist": 0.0, "neg": 0.0, "mass": 0.0, "n": 0,
                   **{f"clim__{c}": 0.0 for c in cals}} for h in H_LIST}
        with torch.no_grad():
            for s in starts:
                x0 = Z[s: s + 1].to(device)
                x = x0.clone()
                for k in range(1, maxh + 1):
                    # ONE trajectory, scored against BOTH climatologies below
                    x = (torch.stack([x + m(x) for m in models]).mean(0)
                         if len(models) > 1 else x + models[0](x))
                    if k in acc:
                        y = Z[s + k: s + k + 1].to(device)
                        a = acc[k]
                        a["model"] += float((((x - y) ** 2) * mask_t).mean())
                        a["persist"] += float((((x0 - y) ** 2) * mask_t).mean())
                        for cname in cals:
                            cb = clim_t[cname][moys[cname][s + k]].unsqueeze(0).to(device)
                            a[f"clim__{cname}"] += float((((cb - y) ** 2) * mask_t).mean())
                        xp = torch.exp(x * std_t + mean_t) if args.log_transform else (x * std_t + mean_t)
                        yp = torch.exp(y * std_t + mean_t) if args.log_transform else (y * std_t + mean_t)
                        a["neg"] += float(((xp < 0).float() * mask_t).sum() / mask_t.sum() / C)
                        tx, ty = float((xp * mask_t).sum()), float((yp * mask_t).sum())
                        a["mass"] += tx / ty if abs(ty) > 1e-9 else float("nan")
                        a["n"] += 1

        hdr = f"{'h':>4}{'~months':>9}{'vs_PERSIST':>12}"
        for c in cals:
            hdr += f"{'vs_' + c:>20}"
        hdr += f"{'INFLATION':>11}{'neg':>7}{'mass':>10}"
        print(hdr, flush=True)
        rows = {}
        for h in H_LIST:
            a = acc[h]
            n = max(a["n"], 1)
            mm, pp = a["model"] / n, a["persist"] / n
            sp = 1 - mm / max(pp, 1e-12)
            sc = {c: 1 - mm / max(a[f"clim__{c}"] / n, 1e-12) for c in cals}
            infl = sc["OLD_times_days"] - sc["NEW_iters_1200s"]
            rows[h] = {"skill_vs_persistence": sp,
                       "skill_vs_clim_OLD": sc["OLD_times_days"],
                       "skill_vs_clim_NEW": sc["NEW_iters_1200s"],
                       "inflation_OLD_minus_NEW": infl,
                       "neg_fraction": a["neg"] / n, "mass_ratio": a["mass"] / n,
                       "elapsed_months_NEW": h * step_days["NEW_iters_1200s"] / 30.4375}
            line = f"{h:>4}{h*step_days['NEW_iters_1200s']/30.4375:>9.1f}{sp:>+12.3f}"
            for c in cals:
                line += f"{sc[c]:>+20.3f}"
            line += f"{infl:>+11.3f}{a['neg']/n:>7.3f}{a['mass']/n:>10.3f}"
            print(line, flush=True)
        out["arms"][aname] = {"members": len(models), "horizons": rows}

    print("\nINFLATION = skill_vs_clim(OLD) - skill_vs_clim(NEW). Positive => the buggy calendar")
    print("made the climatology baseline WEAKER and our reported skill LOOK BETTER than it is.")
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
        print(f"[out] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
