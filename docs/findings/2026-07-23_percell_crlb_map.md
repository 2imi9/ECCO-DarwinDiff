# Per-cell spatial identifiability map — "which parameter is constrained where" (#152)

**Date:** 2026-07-23 · **Run:** AICR b200 job 186741 · **Script:**
`scripts/analysis/percell_crlb_map.py` · **Config:** `covar_env_common.sh`
(AOIS = eqpac, natlsubpolar, southernoceanpac; GEOTRACES_W = GEOTRACES_SUB_W =
DANIELS_RPICPOC_W = POSI_W = 1.0; NB23_N_EPOCHS = 0).

## What this is

The 0-D box integrates every grid cell **independently** (no horizontal transport in
the surrogate). A per-cell parameter therefore affects the state — and the loss — only
at its own cell, so the field Fisher information is **block-diagonal**: a separate 6×6
per cell, no KFAC / cross-cell coupling needed. This localizes each Carroll-6
parameter's identifiability spatially, the companion coverage map to the aggregate
`identifiability_sloppiness.py --mode peraoi` / `--mode fisher_gn` eigen-analyses.

**Method.** Import the runner with training disabled (NB23_N_EPOCHS = 0) so the REAL
per-AOI bundles and the exact `aoi_loss` are available. For each AOI, build a per-cell
theta **field** `tf` of shape `[6, 1, H, W]` (every cell = Carroll), one box
integration `l, state = aoi_loss(b, tf)`, then `torch.autograd.grad` for a per-cell
gradient field `gf` `[6, 1, H, W]`. The per-cell per-parameter Fisher self-information
is `g_cell[i]**2 · |carroll_i|**2` (the `|carroll_i|**2` makes it dimensionless — the
diagonal of the peraoi empirical Fisher, kept per-cell instead of summed) — a `[6, H,
W]` field. This is done **per real observational term**, reconstructed bit-for-bit from
`aoi_loss` (real-term sum reproduces the full loss to rel. err ≈ 2e-8):

| observation term | tracer / quantity | anchors |
|---|---|---|
| GEOTRACES dissolved iron (surf DFe₁ + sub DFe₂) | mmol Fe/m³ | alpfe, scav_rat |
| Daniels 2018 CP:PP calcite rain-ratio (PIC/POC) | dimensionless | R_PICPOC |
| GEOTRACES biogenic silica (bSi) | mmol Si/m³ | diatomgraz |

Because each real term multiplies its residual by an **observation mask** and the box is
per-cell independent, the per-cell gradient — hence the information — is **exactly zero**
where there is no observation.

## Observational coverage (cells with data, per AOI)

| AOI | ocean cells | GEOTRACES surf / sub | Daniels (R_PICPOC) | POSi (bSi) |
|---|---|---|---|---|
| eqpac | 1071 | 26 / 28 | **34** | 7 |
| natlsubpolar | 484 | 13 / 13 | **26** | 4 |
| southernoceanpac | 1296 | 13 / 14 | **0** | **0** |

## Result — per-cell information localizes onto real observational coverage

Self-information summed over cells, from each parameter's **dedicated** real term
(`info_sum`, dimensionless):

| AOI | alpfe (iron) | scav_rat (iron) | diatomgraz (POSi) | R_PICPOC (Daniels) |
|---|---|---|---|---|
| eqpac | 1.6e-3 | 8.7e-3 | **3.1e-1** | **2.2e-2** |
| natlsubpolar | 2.4e-3 | 1.4e-2 | **8.8e-2** | **2.6e-2** |
| southernoceanpac | 1.8e-2 | 2.8e-2 | **0 (no POSi)** | **0 (no Daniels)** |

Confirmations:

1. **Iron information (alpfe, scav_rat) is present wherever GEOTRACES sampled** — all
   three AOIs, since all three carry iron bottles. It is *strongest* in the Southern
   Ocean (scav_rat 2.8e-2), where iron is the only anchor. The maps
   (`percell_crlb_alpfe.png`, `percell_crlb_scav_rat.png`) place the information on the
   GEOTRACES station cells.

2. **R_PICPOC information is present only where Daniels sampled and is EXACTLY ZERO in
   the Southern Ocean** (0 Daniels cells → term gated off → information identically 0).
   This is the spatial signature of the rank-2 finding: no calcite observable → no
   R_PICPOC constraint in the SO. See `percell_crlb_R_PICPOC.png` (greyed "no coverage"
   panel for southernoceanpac).

3. **The Daniels rain-ratio is cleanly orthogonal to iron/growth**: within the Daniels
   term, all non-R_PICPOC parameters carry ≈ 1e-11–1e-15 information (numerical zero) —
   only R_PICPOC lights up. The calcite anchor adds R_PICPOC information without
   disturbing the iron pair.

4. **diatomgraz information tracks the sparse POSi bottles** (7 cells eqpac, 4 cells
   natl; zero in SO) — `percell_crlb_diatomgraz.png`.

## The growth pair {Smallgrow, Biggrow} — honest caveat

The expectation was "growth pair ≈ 0 everywhere = unobservable." The map confirms the
**spatial** half of this cleanly but **not** a literal-zero diagonal self-information:

- **No independent spatial footprint.** The growth pair lights up *only* the cells that
  already carry iron / Daniels / POSi coverage (its `n_info_cells` equals the union of
  the anchored terms' cells, never any cell of its own). There is **no observable
  dedicated to growth anywhere** — its information is entirely parasitic on the other
  anchors, borrowed through biomass.

- **But the diagonal magnitude is not negligible.** Growth rate perturbs phytoplankton
  biomass, which perturbs POC (→ iron scavenging + uptake) and diatom biomass (→ bSi),
  so growth leaks real sensitivity into the iron and silica terms. Full-loss
  `info_sum`: Smallgrow ≈ 1.8e-2 / 1.3e-2 / 1.0e-2 across eqpac / natl / SO, with
  Biggrow ~6× smaller. Smallgrow's ≈ 1.8e-2 in eqpac is comparable to alpfe (2.8e-2)
  and R_PICPOC (2.2e-2). See `percell_crlb_growth_pair.png`.

- **Interpretation.** Diagonal self-information measures *sensitivity*, not
  *separability*. The "unobservable by construction" verdict for the growth pair is a
  **non-separability / degeneracy** statement (the two growth rates trade off against
  each other and against biomass), which lives in the **off-diagonal** Fisher structure —
  the peraoi 4-observable-block rank and the GN sloppy eigenvector — not in the diagonal
  map. So this per-cell map is correctly read as a **coverage** map (which anchor
  illuminates which cell), with the growth-pair identifiability claim resting on the
  eigenstructure companion analyses, which exclude the pair by construction.

## Files (reproducible)

- Script: `scripts/analysis/percell_crlb_map.py` (standalone; no edits to
  `identifiability_sloppiness.py`).
- Fields NPZ: `docs/findings/2026-07-23_percell_crlb/percell_crlb.npz`
  (`{aoi}__{term}__selfinfo` `[6,H,W]`, `{aoi}__mask`, `{aoi}__lat`, `{aoi}__lon`).
- Aggregate JSON: `docs/findings/2026-07-23_percell_crlb/percell_crlb_summary.json`.
- Maps: `docs/findings/2026-07-23_percell_crlb/percell_crlb_{alpfe,scav_rat,diatomgraz,R_PICPOC,growth_pair}.png`.
- Cluster copies: `/scratch/qi_zim_neu/identif/percell_crlb*`; sbatch
  `~/emulator_poc/percell_crlb_aicr.sbatch`; log
  `/scratch/qi_zim_neu/identif/dd-percell-crlb_186741.out`.

Reproduce:
```
ssh aicr
source ~/emulator_poc/covar_env_common.sh
~/dd_venv/bin/python scripts/analysis/percell_crlb_map.py \
    --out-dir /scratch/qi_zim_neu/identif --tag percell_crlb
```
