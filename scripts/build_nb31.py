"""Build notebooks/31_v3_0_natl_vs_eqpac_single_aoi.ipynb programmatically.

Companion to the v3.0 multi-AOI scoping doc (PR #44 merged 2026-05-17).
Single-AOI test of the v2.8 anchor config on North Atlantic Subpolar AOI,
compared head-to-head with Eq Pacific results from PR #45.

Pure analysis — loads result JSONs already on main + new natlsubpolar
JSONs from the v3.0-natl-single-aoi-test branch.
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parent.parent / "notebooks" / "31_v3_0_natl_vs_eqpac_single_aoi.ipynb"

CELLS: list[tuple[str, str]] = [
    ("md", """\
# v3.0 precursor — North Atlantic Subpolar single-AOI test vs Equatorial Pacific (v2.8 anchor)

**Companion to** [`docs/findings/v3.0_multi_aoi_scoping.md`](../docs/findings/v3.0_multi_aoi_scoping.md) (the design doc merged in PR #44).
**Loads** result JSONs from the v2.8 anchor config (Darwin IC + sub_w=1.0 + POC_SUB_W=3.0, n=10 seeds) run **independently** on two AOIs:
- Equatorial Pacific (HNLC, biology-dominated iron loss)
- North Atlantic Subpolar (iron-replete, scavenging-dominated, deep winter convection)

## Headline

**N Atl produces the project's first reproducible R_PICPOC Cal-grade recovery** (3/10 Cal, 1/10 Excellent at seed 8: 0.0445 vs Carroll 0.0425 = 4.9% off). The v2.6 framing that "R_PICPOC needs PIC observations" was wrong about the intervention — what it actually needed was an iron-replete AOI.

The two AOIs unblock **different stuck parameters**: Eq Pac recovers scav_rat (7/10 Cal), N Atl recovers R_PICPOC (3/10 Cal) + alpfe (5/10 Cal vs Eq Pac's 2/10). Empirical support for v3.0 multi-AOI joint training to recover both simultaneously.
"""),
    ("code", """\
import json
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}
PARAM_ORDER = list(CARROLL.keys())

def _find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / 'pyproject.toml').is_file() and (p / 'scripts').is_dir():
            return p
    raise FileNotFoundError('project root not found')
PROJECT_ROOT = _find_project_root(Path.cwd())
SCRIPTS = PROJECT_ROOT / 'scripts'

print(f'PROJECT_ROOT={PROJECT_ROOT}')
"""),
    ("md", """\
## 1. Load both AOI's runs at the v2.8 anchor

Anchor config: `DARWIN_IC=1, GEOTRACES_SUB_W=1.0, POC_SUB_W=3.0, PINN_drift_w=3.0`, n=10 seeds.
"""),
    ("code", """\
def load(pattern, exclude_natl=False):
    files = sorted(SCRIPTS.glob(pattern))
    if exclude_natl:
        files = [f for f in files if 'natlsubpolar' not in f.name]
    return [json.load(open(f, encoding='utf-8')) for f in files]

eqpac = load('run_v2.7_multilayer_result_seed*_surf0.3_sub1.0_pinn3.0_darwinic_pocsubW3.0.json', exclude_natl=True)
natl  = load('run_v2.7_multilayer_result_seed*_surf0.3_sub1.0_pinn3.0_darwinic_pocsubW3.0_natlsubpolar.json')

print(f'Eq Pac: n={len(eqpac)} seeds')
print(f'N Atl:  n={len(natl)} seeds')
print()
print(f'Eq Pac AOI cells: {eqpac[0].get(\"aoi_name\", \"Equatorial Pacific\")} - implied 21x51 = 1071 cells')
print(f'N Atl AOI cells: {natl[0].get(\"aoi_name\", \"North Atlantic Subpolar\")} - implied 16x31 = 496 native bins (~484 ocean)')
"""),
    ("md", """\
## 2. Per-parameter Cal/Excellent comparison
"""),
    ("code", """\
def aggregate(runs):
    out = {}
    for p in PARAM_ORDER:
        vals = np.array([r['params'][p]['recovered'] for r in runs])
        rels = np.array([r['params'][p]['abs_rel_offset'] for r in runs])
        out[p] = {
            'mean': vals.mean(),
            'mean_off': rels.mean(),
            'cal': int((rels <= 0.40).sum()),
            'exc': int((rels <= 0.05).sum()),
            'n': len(runs),
        }
    out['agg_4plus'] = sum(1 for r in runs if r['n_cal_grade'] >= 4)
    return out

a_eq = aggregate(eqpac)
a_na = aggregate(natl)

import pandas as pd
rows = []
for p in PARAM_ORDER:
    e = a_eq[p]; n = a_na[p]
    winner = 'EqPac' if e['cal'] > n['cal'] else ('NAtl' if n['cal'] > e['cal'] else 'tie')
    rows.append({
        'param': p,
        'carroll': CARROLL[p],
        'EqPac mean': e['mean'], 'EqPac off': e['mean_off'], 'EqPac Cal': f\"{e['cal']}/{e['n']}\", 'EqPac Exc': e['exc'],
        'NAtl mean': n['mean'], 'NAtl off': n['mean_off'], 'NAtl Cal': f\"{n['cal']}/{n['n']}\", 'NAtl Exc': n['exc'],
        'winner': winner,
    })
df = pd.DataFrame(rows)
print(f\"Aggregate 4+/6 seeds: EqPac {a_eq['agg_4plus']}/{len(eqpac)} | NAtl {a_na['agg_4plus']}/{len(natl)}\")
df
"""),
    ("md", """\
## 3. Per-parameter recovery distributions side-by-side

Bar plots: per-seed recovered value, colored by band. Each parameter side-by-side.
"""),
    ("code", """\
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
color_map = {'Excellent': 'green', 'Cal-grade': 'C0', 'Loose': 'orange', 'Drifted': 'red'}
for ax, p in zip(axes.flat, PARAM_ORDER):
    e_vals = np.array([r['params'][p]['recovered'] for r in eqpac])
    e_bands = [r['params'][p]['band'] for r in eqpac]
    n_vals = np.array([r['params'][p]['recovered'] for r in natl])
    n_bands = [r['params'][p]['band'] for r in natl]
    xs = np.arange(10)
    w = 0.4
    ax.bar(xs - w/2, e_vals, w, color=[color_map[b] for b in e_bands],
           edgecolor='black', linewidth=0.5, label='Eq Pac')
    ax.bar(xs + w/2, n_vals, w, color=[color_map[b] for b in n_bands],
           edgecolor='black', linewidth=0.5, hatch='//', label='N Atl')
    ax.axhline(CARROLL[p], color='k', linestyle='--', linewidth=1.5)
    ax.set_title(f'{p}  (Carroll = {CARROLL[p]:.3g})')
    ax.set_xlabel('seed')
    ax.set_xticks(xs)
    ax.legend(loc='upper right', fontsize=9)
    if p == 'scav_rat':
        ax.set_yscale('log')
plt.suptitle('v2.8 anchor: per-seed Carroll-6 recovery, Eq Pac vs N Atl Subpolar', y=1.02)
plt.tight_layout(); plt.show()
"""),
    ("md", """\
## 4. The R_PICPOC unblock

**The critical finding.** Across the 100+ prior v2.6/v2.7 experiments on Eq Pacific, R_PICPOC sat at ~2.7-2.9 off Carroll (Drifted, undershoots after Darwin IC swap). Adding multi-AOI capability + running on N Atlantic alone produces 3/10 Cal-grade with 1 Excellent.

This contradicts the long-standing v2.6 framing that "R_PICPOC needs independent PIC observations". The intervention that helps is **regime change**, not new observations.
"""),
    ("code", """\
# Highlight the seed-8 N Atl R_PICPOC Excellent result
print('N Atl seed-by-seed R_PICPOC recovery (Carroll target: 0.04245):')
print(f\"{'seed':<5} {'recovered':>12} {'rel_off':>9}  band\")
for r in natl:
    pdata = r['params']['R_PICPOC']
    marker = ' ⭐' if pdata['band'] == 'Excellent' else ''
    print(f\"{r['seed']:<5} {pdata['recovered']:>12.4e} {pdata['abs_rel_offset']:>9.3f}  {pdata['band']}{marker}\")

# Compare to Eq Pac
print('\\nEq Pac seed-by-seed R_PICPOC (always Drifted, ~50% of Carroll):')
for r in eqpac:
    pdata = r['params']['R_PICPOC']
    print(f\"{r['seed']:<5} {pdata['recovered']:>12.4e} {pdata['abs_rel_offset']:>9.3f}  {pdata['band']}\")
"""),
    ("md", """\
## 5. Why the regimes recover different parameters

Reading the science from the table:

**Eq Pacific (HNLC, biology-dominated iron loss)**:
- Strong iron-limitation → biology rates (Smallgrow, Biggrow, diatomgraz) are well-constrained because their growth × iron-availability product determines the surface FeT field
- scav_rat constrained by the L2 POC×DFe iron sink (v2.8's POC_SUB loss anchors it)
- R_PICPOC undetermined: PIC formation in HNLC is small and surface-only, so the integrator can satisfy surface PIC obs with any plausible R_PICPOC

**N Atlantic Subpolar (iron-replete, scavenging-dominated, deep winter convection)**:
- Iron is plentiful → biology rates are NOT iron-limited → harder to constrain Smallgrow / Biggrow
- scav_rat fits weakly because scavenging is fast enough that surface obs don't disambiguate it
- BUT: deep winter convection produces strong PIC export → R_PICPOC IS the dominant parameter for surface PIC dynamics, so it's recoverable

The two AOIs are complementary: each unblocks parameters the other can't.

## 6. Implication for v3.0 multi-AOI joint training

Joint training with a shared Carroll-6 vector would force the optimizer to find parameter values that satisfy *both* AOIs simultaneously. The unstuck parameters in each AOI would constrain the joint solution:

- Eq Pac evidence pins scav_rat, Smallgrow, Biggrow, diatomgraz
- N Atl evidence pins alpfe (partially), R_PICPOC

In principle, the joint solution should hit 5-6/6 Cal-grade simultaneously — substantially better than either AOI alone.

This is the strongest empirical case for v3.0 multi-AOI training to date.

## 7. Limitations

1. **Single AOI per seed** — not yet joint training. The cross-regime constraint hasn't been imposed; we're just observing that each AOI alone identifies a different parameter set.
2. **Phyto biomass IC stays at literature defaults** in both AOIs — N Atl phyto biology likely differs significantly (cold-water diatoms vs warm-water cyanobacteria). The 7-PFT → 5-PFT mapping is still an open task.
3. **No GEOTRACES subsurface POC** for either AOI — the POC_SUB loss uses Darwin self-target. Swapping in GEOTRACES `POC_LPT_CONC + POC_SPT_CONC` is the methodological cleanup.
4. **N Atl PINN drift loss may be miscalibrated** for the iron-replete regime — the v2.7-original PINN balance was tuned to HNLC physics.

## 8. Recommended next step

Implement the multi-AOI joint training (PR #44 §3 design). The empirical case here justifies the ~1-1.5 hr code lift.
"""),
]


def main():
    nb = nbf.v4.new_notebook()
    for kind, src in CELLS:
        if kind == "md":
            nb.cells.append(nbf.v4.new_markdown_cell(src))
        elif kind == "code":
            nb.cells.append(nbf.v4.new_code_cell(src))
        else:
            raise ValueError(f"unknown cell kind: {kind}")
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3 (ipykernel)",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "version": "3.11"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"wrote {OUT}  ({len(CELLS)} cells)")


if __name__ == "__main__":
    main()
