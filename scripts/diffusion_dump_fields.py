"""Resample from a trained diffusion_emulator checkpoint and dump small fields for figures.

Loads the saved regression+diffusion weights, samples an ensemble on held-out val fields, and
writes a compact npz (truth / regression / one sample / ensemble mean+std, first 2 channels) +
per-channel radial spectra. Runs on the cluster where the model + cube live; result is tiny to pull.

Usage: python scripts/diffusion_dump_fields.py --model diff_surf_model.pt \
           --cube global3d_L10_cube.npz --surface-only --out diff_surf_fields.npz
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diffusion_emulator import (  # noqa: E402
    FNO2d, EDMCorrector, edm_sample, load_cube, zscore, time_split, radial_spectrum,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--cube", required=True)
    p.add_argument("--surface-only", action="store_true")
    p.add_argument("--channels", default=None)
    p.add_argument("--modes", type=int, default=24)
    p.add_argument("--width", type=int, default=112)
    p.add_argument("--reg-width", type=int, default=64)
    p.add_argument("--sigma-data", type=float, default=0.5)
    p.add_argument("--n-fields", type=int, default=3)
    p.add_argument("--n-ensemble", type=int, default=24)
    p.add_argument("--sample-steps", type=int, default=24)
    p.add_argument("--map-channels", default="0,1", help="channel indices to save full maps for")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    ck = torch.load(a.model, map_location=dev, weights_only=False)
    cfg = ck.get("config", {})
    modes = cfg.get("modes", a.modes); width = cfg.get("width", a.width); regw = cfg.get("reg_width", a.reg_width)
    sd = cfg.get("sigma_data", a.sigma_data)
    print(f"[load] modes={modes} width={width} reg_width={regw} epoch={ck.get('epoch')} channels={ck.get('channels')}", flush=True)

    state, mask, names = load_cube(a.cube)
    if a.surface_only:
        keep = [i for i, nm in enumerate(names) if nm.endswith("_k0")] or list(range(min(6, len(names))))
        state, names = state[:, keep], [names[i] for i in keep]
    elif a.channels:
        keep = [int(c) for c in a.channels.split(",")]
        state, names = state[:, keep], [names[i] for i in keep]
    T, C, H, W = state.shape
    z, mean, std = zscore(state, mask)
    Z = torch.from_numpy(z)
    _, va_t = time_split(T)
    va_t = va_t[: a.n_fields]

    fno = FNO2d(C, C, modes1=modes, modes2=modes, width=regw).to(dev)
    fno.load_state_dict(ck["regression"]); fno.eval()
    model = EDMCorrector(C, 2 * C, sigma_data=sd, modes=modes, width=width).to(dev)
    model.load_state_dict(ck["diffusion"]); model.eval()

    mc = [int(x) for x in a.map_channels.split(",") if int(x) < C]
    truth = np.stack([z[t + 1] for t in va_t])              # [F,C,H,W]
    reg = np.zeros_like(truth); samp = np.zeros_like(truth)
    emean = np.zeros_like(truth); estd = np.zeros_like(truth)
    spec = {c: {"truth": None, "reg": None, "diff": None} for c in range(C)}  # ALL channels
    with torch.no_grad():
        for fi, t in enumerate(va_t):
            xt = Z[t : t + 1].to(dev)
            mu = xt + fno(xt)
            cond = torch.cat([xt, mu], dim=1)
            ens = torch.stack([mu + edm_sample(model, cond, (1, C, H, W), dev, steps=a.sample_steps)
                               for _ in range(a.n_ensemble)])  # [E,1,C,H,W]
            reg[fi] = mu[0].cpu().numpy()
            samp[fi] = ens[0, 0].cpu().numpy()
            emean[fi] = ens.mean(0)[0].cpu().numpy()
            estd[fi] = ens.std(0)[0].cpu().numpy()
            if fi == 0:
                for c in spec:
                    spec[c]["truth"] = radial_spectrum(truth[0, c], mask)
                    spec[c]["reg"] = radial_spectrum(reg[0, c], mask)
                    spec[c]["diff"] = radial_spectrum(samp[0, c], mask)
    np.savez_compressed(
        a.out, truth=truth.astype("f4")[:, mc], reg=reg.astype("f4")[:, mc],
        sample=samp.astype("f4")[:, mc], ens_mean=emean.astype("f4")[:, mc],
        ens_std=estd.astype("f4")[:, mc], mask=mask,
        channels=np.array(names), map_channels=np.array([names[c] for c in mc]),
        mean=mean, std=std,
        spec_truth=np.stack([spec[c]["truth"] for c in spec]),
        spec_reg=np.stack([spec[c]["reg"] for c in spec]),
        spec_diff=np.stack([spec[c]["diff"] for c in spec]),
        spec_channels=np.array(names),
    )
    import os
    print(f"[dump] wrote {a.out} ({os.path.getsize(a.out)/1e6:.2f} MB) fields={len(va_t)}", flush=True)


if __name__ == "__main__":
    main()
