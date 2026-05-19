"""Inspect R_PICPOC per-AOI recovery at the raised bound [0.005, 1.5].

Reads the most-recent POSi=1.0 JSONs (which the raised-bound run overwrites in
the worktree) and compares to the committed bound=0.20 baseline from PR #62.

Usage:
    python scripts/compare_rpicpoc_bound.py [path-to-old-baseline-json-dir]
"""
from __future__ import annotations
import glob, json, sys
import numpy as np

PATTERN = "scripts/run_v3.0_joint_eqpac-natlsubpolar_seed*_surf0.3_sub1.0_pinn3.0_pocsubW3.0_geopocW0.5_aoiid_hd32_w-natlsubpolar2.0_posiW1.0.json"

def main() -> None:
    files = sorted(glob.glob(PATTERN), key=lambda f: int(f.rsplit('seed', 1)[1].split('_', 1)[0]))
    print(f'R_PICPOC bound 0.20 -> 1.5 diagnostic, n={len(files)} JSONs')
    print(f'{"seed":>4s}  {"eqpac":>10s}  {"natlsub":>10s}  {"joint":>10s}  {"natl > 0.20?":>14s}  {"joint band":>12s}')
    n_above = 0
    n_joint_cal = 0
    for f in files:
        d = json.load(open(f))
        rp = d['params']['R_PICPOC']
        eq = rp['per_aoi_recovered']['eqpac']
        na = rp['per_aoi_recovered']['natlsubpolar']
        joint = rp['joint_cellweighted_recovered']
        band = rp.get('joint_cellweighted_band', rp.get('joint_band', '?'))
        above = na > 0.20
        n_above += above
        n_joint_cal += band in ('Cal-grade', 'Excellent')
        print(f'  {d["seed"]:>2d}  {eq:>10.4f}  {na:>10.4f}  {joint:>10.4f}  {("YES" if above else "no"):>14s}  {band:>12s}')
    print(f'\nSeeds with natl R_PICPOC > 0.20 (old bound): {n_above}/{len(files)}')
    print(f'Seeds with R_PICPOC joint Cal/Excellent: {n_joint_cal}/{len(files)}')
    print(f'\nCarroll target: 0.04245')
    print(f'Observed PIC/POC ratio: eqpac median 0.031, natl median 0.722')

    # Also show what other params look like to verify nothing broken
    PARAMS = ['alpfe','scav_rat','Smallgrow','Biggrow','diatomgraz','R_PICPOC']
    print('\nPer-seed all-param bands:')
    print(f'{"seed":>4s}  ' + '  '.join(f'{p[:5]:>5s}' for p in PARAMS) + '  nCal')
    for f in files:
        d = json.load(open(f))
        bands = []; n = 0
        for p in PARAMS:
            b = d['params'][p].get('joint_cellweighted_band') or d['params'][p].get('joint_band')
            bands.append(b[:5] if b else '???')
            if b in ('Cal-grade', 'Excellent'): n += 1
        print(f'  {d["seed"]:>2d}  ' + '  '.join(f'{b:>5s}' for b in bands) + f'  {n}')

if __name__ == "__main__":
    main()
