#!/usr/bin/env python3
r"""realdata_correlation.py -- the LITERAL data-test correlation.

For a given parameter vector (default = Carroll's published values), integrate the box per AOI
and report the per-AOI SPATIAL Pearson r + RMSE between the box's predicted observable and the
REAL observation:
  - DFe_1   vs  GEOTRACES IDP2025 dissolved iron
  - bSi     vs  GEOTRACES biogenic silica
  - PIC_1   vs  real MODIS-Aqua PIC (if MODIS_PIC_CACHE_PATH set)

A strong correlation (high r) means the parameter's recovery genuinely reproduces the real-obs
PATTERN; a weak r means the box does not match real data even at the 'recovered' value -- i.e.
the data-test correlation is weak and the recovery claim is not real-world-supported.

Usage (cluster, scheduled env):
  AOIS=eqpac,natlsubpolar,southernoceanpac MODIS_PIC_CACHE_PATH=.../modis_pic_clim_2017_2019.npz \
    uv run python scripts/realdata_correlation.py
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _import_runner():
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    os.environ.setdefault("TORCH_COMPILE_BATCHED", "0")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_corr_")
    spec = importlib.util.spec_from_file_location(
        "_dd_runner", ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def main():
    import numpy as np
    import torch
    from darwindiff.carroll6 import CARROLL_VALUES

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    R._RATIO_W_NOW = R.RATIO_W
    theta = CARROLL_VALUES.to(dev).float()

    modis = {}
    mp = os.environ.get("MODIS_PIC_CACHE_PATH")
    if mp and os.path.exists(mp):
        mc = np.load(mp)
        for b in bundles:
            if f"pic_{b['key']}" in mc.files:
                modis[b["key"]] = (mc[f"pic_{b['key']}"].astype("float32") * 1000.0,
                                   mc[f"mask_{b['key']}"])

    def corr(pred2d, tgt2d, mask_bool):
        p = pred2d[mask_bool]
        t = tgt2d[mask_bool]
        if p.numel() < 3:
            return None
        r = torch.corrcoef(torch.stack([p, t]))[0, 1].item()
        rmse = ((p - t) ** 2).mean().sqrt().item()
        return r, rmse, int(p.numel())

    print(f"\n=== DATA-TEST SPATIAL CORRELATION at theta = Carroll | AOIS={[b['key'] for b in bundles]} ===")
    print(f"{'AOI':>16} {'observable':>15} {'n cells':>8} {'Pearson r':>11} {'RMSE':>11}")
    for b in bundles:
        H, W = b["mask_f"].shape
        pb = theta.reshape(6, 1, 1, 1).expand(6, 1, H, W)
        with torch.no_grad():
            _, state = R.aoi_loss(b, pb)          # [15, 1, H, W]
        st = state[:, 0]                          # [15, H, W]

        if b["n_geo_surf"] > 0:
            c = corr(st[R.I_DFE_1], b["geo_surf_target_t"], b["geo_surf_mask_t"])
            if c:
                print(f"{b['key']:>16} {'GEOTRACES Fe':>15} {c[2]:>8} {c[0]:>11.3f} {c[1]:>11.4g}")
        if R.POSI_W > 0 and b["n_posi"] > 0:
            bsi, _ = R.diagnostic_bsi_steady(st[R.I_DIATOM].unsqueeze(0), theta[4].reshape(1, 1, 1))
            c = corr(bsi[0], b["posi_target_t"], b["posi_mask_t"])
            if c:
                print(f"{b['key']:>16} {'GEOTRACES bSi':>15} {c[2]:>8} {c[0]:>11.3f} {c[1]:>11.4g}")
        if b["key"] in modis:
            tgt_np, cmask = modis[b["key"]]
            tgt = torch.tensor(tgt_np, device=dev)
            ocean = (b["mask_f"] > 0).detach().cpu().numpy()
            mb = torch.tensor(ocean & cmask & np.isfinite(tgt_np) & (tgt_np > 0), device=dev)
            c = corr(st[R.I_PIC_1], tgt, mb)
            if c:
                print(f"{b['key']:>16} {'MODIS PIC':>15} {c[2]:>8} {c[0]:>11.3f} {c[1]:>11.4g}")
    print("\n(strong r => box at Carroll reproduces the real-obs spatial pattern; weak r => recovery"
          " not real-world-supported even at the 'right' value)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
