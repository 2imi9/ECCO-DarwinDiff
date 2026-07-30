"""Deep-ensemble UQ baseline — the CONTROL the diffusion corrector never had.

We invested in an EDM diffusion corrector to get calibrated uncertainty, but never compared it
against the trivial baseline: train N independent models (different seeds) and ensemble them.
Our data ablation proved calibration (spread/residual) is the one metric still improving and
unsaturated — so the honest question is whether a diffusion is even the right instrument for it.

This script loads N regression checkpoints (built with `diffusion_emulator.py --regression-only
--seed k`), evaluates their ensemble on the SAME held-out split with the SAME metric definitions
used for the diffusion, and reports a head-to-head.

Metric parity (so the comparison is fair):
  calib_ratio = ensemble_spread / RMSE(ensemble_mean)   # 1.0 = calibrated, <<1 = over-confident
The diffusion's ratio is computed identically in diffusion_emulator.evaluate().

Run:
  python scripts/deep_ensemble_eval.py --cube daily_eqpac_cube.npz \
      --models /scratch/.../de_eqpac_seed*.pt --out de_eqpac.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
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
from diffusion_emulator import FNO2d, _batch, load_cube, time_split, zscore  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cube", required=True)
    p.add_argument("--models", nargs="+", required=True, help="checkpoint paths or globs")
    p.add_argument("--surface-only", action="store_true")
    p.add_argument("--log-transform", action="store_true", help="MUST match the models' training transform")
    p.add_argument("--log-floor", type=float, default=1e-4)
    p.add_argument("--eval-batch", type=int, default=8)
    p.add_argument("--cpu", action="store_true")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    device = "cpu" if (args.cpu or not torch.cuda.is_available()) else "cuda"

    paths = sorted({q for m in args.models for q in glob.glob(m)})
    if not paths:
        print(f"ERROR: no checkpoints matched {args.models}"); return 2
    print(f"[de] {len(paths)} ensemble members", flush=True)

    state, mask, names = load_cube(args.cube)
    if args.surface_only:
        keep = [i for i, nm in enumerate(names) if nm.endswith("_k0")] or list(range(min(6, len(names))))
        state, names = state[:, keep], [names[i] for i in keep]
    if args.log_transform:
        state = np.log(np.clip(state, args.log_floor, None)).astype(np.float32)
    T, C, H, W = state.shape
    z, _, _ = zscore(state, mask)
    del state
    Z = torch.from_numpy(z)
    tr_t, va_t = time_split(T)
    mask_t = torch.from_numpy(mask.astype(np.float32))[None, None].to(device)
    print(f"[de] state {(T,C,H,W)} val pairs={len(va_t)} device={device}", flush=True)

    models = []
    for pth in paths:
        ck = safe_torch_load(pth, map_location=device)
        cfg = ck["config"]
        m = FNO2d(C, C, modes1=cfg["modes"], modes2=cfg["modes"], width=cfg["reg_width"]).to(device)
        m.load_state_dict(ck["regression"]); m.eval()
        models.append(m)
        print(f"    loaded seed={ck.get('seed')} <- {Path(pth).name}", flush=True)

    va = torch.tensor(va_t)
    ncell = mask_t.sum().item()
    sp = single = ensm = spread = 0.0
    n = 0
    with torch.no_grad():
        for k in range(0, len(va), args.eval_batch):
            bt = va[k : k + args.eval_batch]
            xt, yt = _batch(Z, bt, device)
            mus = torch.stack([xt + m(xt) for m in models])      # [N,B,C,H,W]
            em = mus.mean(0)
            sp += float((((xt - yt) ** 2) * mask_t).sum())
            single += float((((mus - yt.unsqueeze(0)) ** 2) * mask_t).sum()) / len(models)
            ensm += float((((em - yt) ** 2) * mask_t).sum())
            spread += float((mus.std(0) * mask_t).sum())
            n += len(bt)
    den = max(n * C * ncell, 1e-9)
    persist, single_mse, ens_mse, spd = sp / den, single / den, ensm / den, spread / den
    rmse_ens = math.sqrt(max(ens_mse, 1e-12))
    res = {
        "n_members": len(models),
        "persistence_mse": persist,
        "single_model_skill": 1 - single_mse / max(persist, 1e-12),
        "ensemble_mean_skill": 1 - ens_mse / max(persist, 1e-12),
        "ensemble_spread": spd,
        "rmse_ensemble_mean": rmse_ens,
        "calib_ratio": spd / max(rmse_ens, 1e-12),
    }
    print("\n=== DEEP ENSEMBLE (control) ===")
    for k2, v in res.items():
        print(f"  {k2:22s} {v:+.4f}" if isinstance(v, float) else f"  {k2:22s} {v}")
    print("\ncalib_ratio: 1.0 = calibrated; <<1 = over-confident.")
    print("Compare against the diffusion corrector's ratio on the SAME cube/split.")
    if args.out:
        Path(args.out).write_text(json.dumps({"deep_ensemble": res, "members": paths}, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
