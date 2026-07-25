# Differentiable observation design: which new measurement breaks the iron degeneracy

Date: 2026-07-23
Script: `scripts/analysis/observation_design.py`
Data: AICR B200 / login-node CPU, `~/emulator_poc`, env = the standard 3-AOI iron config
(`AOIS=eqpac,natlsubpolar,southernoceanpac`, `GEOTRACES_W=GEOTRACES_SUB_W=1`,
`AOI_W_NATLSUBPOLAR=AOI_W_SOUTHERNOCEANPAC=2`, `USE_EPPLEY_T=1`, `NB23_N_EPOCHS=0`).
Artifact JSON: `/scratch/qi_zim_neu/obsdesign/obs_design.json`.

## Four-sentence summary

A surface particulate-Fe **scavenging flux** (a 234Th/210Po-derived removal-rate
observable) is the single best new measurement for breaking the alpfe/scav_rat iron
degeneracy: it cuts the posterior variance along the degenerate iron combination by
about **1400x** and collapses the iron-block condition number from **2930 to about 7**.
A **subsurface dissolved-Fe concentration** is essentially as powerful (about 1260x in
the conditional metric, and the strongest observable, about 25x, in the fully
marginalized cross-check), because in the box alpfe only injects iron at the surface, so
a depth-resolved concentration also breaks the source/sink symmetry that makes surface
[DFe] blind. Observables that the identifiability study showed constrain *other*
parameters (bSi for diatomgraz, PIC for R_PICPOC) and pure "more of the same"
concentration surveys are correctly ranked as near-useless for iron: a second identical
surface-[DFe] survey gives exactly the trivial 2.00x variance drop and leaves the
condition number unchanged at 2930. The defensible novelty for the manuscript is the
**method**, computing each candidate's Fisher-information contribution through the
differentiable surrogate and ranking cruises *before* they are funded, not the already
published existence of the degeneracy.

## Why this is the paper's novel contribution

A reviewer correctly noted that "we discovered the alpfe/scav_rat iron degeneracy" is
not novel. Compensating iron source/scavenging families are established (Frants et al.;
the FeMIP inter-model spread; Tagliabue's residence-time spread at agreed
concentration). What is defensible is a *method*: because the 0-D surrogate is
differentiable, the sensitivity of **any** candidate observable to each Carroll-6
parameter is a cheap Jacobian row `j = d(observable)/d(theta)`. Proposing a survey of
that observable is a structured Fisher update `F -> F + F_obs`, so we can score, before
any ship time is spent, how much each candidate would shrink the sloppy (degenerate)
iron direction. This is optimal experimental design (OED) driven by the surrogate's
Fisher information, and it turns the identifiability diagnostic into a forward-looking
design tool.

## Method

1. **Reuse the surrogate as a fit operator.** Import the runner with training disabled
   (`NB23_N_EPOCHS=0`), exactly as `identifiability_sloppiness.py` does, and take the
   integrated box state from `R.aoi_loss`. One batched integration over the "seed" axis
   carries Carroll plus all 12 central-difference perturbation columns, so the full
   6-parameter Jacobian of every candidate observable is one integration per AOI.

2. **Equal-footing Fisher per observable.** For each candidate `o`, build a
   dimensionless Gauss-Newton Fisher
   `F_o = sum_AOI w_b * (1/N_b) * G_b^T G_b`, with
   `G_b[cell,i] = |theta_i| * (dy_cell/dtheta_i) / rms_b(y)`.
   Each observable is treated as a survey of the AOI ocean cells measured with the
   **same unit fractional noise**, and is scaled by its own per-AOI magnitude
   `rms_b = sqrt(mean(y^2))` (matching the runner's `scale = mean(target^2)`). This is
   an apples-to-apples comparison of observable *type*, not of who has the biggest raw
   numbers.

3. **Base and scoring.** Base Fisher `F0` = surface-[DFe] concentration ("iron
   concentration only"). Take its iron 2x2 sub-block `{alpfe, scav_rat}`, its smallest
   eigenvector `v` (the degenerate combination), and its condition number. For each
   candidate `F1 = F0 + F_o`, report:
   - `var_reduction_sloppy = (v^T F0^-1 v)/(v^T F1^-1 v)` on the prior-free 2x2 iron
     block (primary);
   - `var_reduction_full6` on the full 6x6 with a weak isotropic prior `tau*I`
     (`tau=1e-2`), which marginalizes over the other four parameters (cross-check);
   - the iron-block condition number after, the smallest-eigenvalue lift, the
     D-optimality gain `logdet(F1_iron) - logdet(F0_iron)`, and the alignment
     `|cos(top eigenvector of F_o's iron block, v)|` (the geometric reason).

## Base: what surface [DFe] alone constrains

| quantity | value |
|---|---|
| iron 2x2 eigenvalues (sloppy / stiff) | 1.08e-3 / 3.18 |
| condition number | **2930** |
| sloppy (degenerate) direction | alpfe -0.63, scav_rat -0.77 |
| stiff (constrained) direction | alpfe -0.77, scav_rat +0.63 |
| conditional corr(alpfe, scav_rat) | +0.999 |

The physics is exactly as expected. Surface [DFe] responds to (source minus sink), so
the **difference** direction (alpfe up, scav_rat down) is well constrained (stiff), and
the **covariation** direction (alpfe up, scav_rat up, [DFe] fixed) is nearly invisible
(sloppy). The conditional correlation of +0.999 within the iron pair is the 2x2-block
statement of the same degeneracy the GN-Fisher `realiron` run reports as a marginal
corr of about -0.77 (different quantity: 2x2 conditional vs full-6 marginal, and
surface-only vs surface+subsurface; both say "degenerate").

## Ranking of candidate new observations

Sorted by the primary metric (2x2 conditional variance reduction along the sloppy iron
direction). Higher `var_red` and lower `cond_after` are better.

| candidate | var_red (2x2) | var_red (full-6) | cond after | align w/ sloppy | verdict |
|---|---:|---:|---:|---:|---|
| **scavflux_surf** (234Th/210Po scavenging flux) | **1434** | 9.1 | **6.9** | 0.70 | breaks it (hypothesis) |
| **dfe_sub** (subsurface [DFe]) | 1261 | **24.8** | **2.5** | 0.97 | breaks it (symmetry) |
| scavflux_sub (deep scavenging flux) | 311 | 13.0 | 9.9 | 0.89 | breaks it |
| bsi_surf (biogenic silica) | 15.3 | 2.3 | 2152 | 0.02 | iron-useless (constrains diatomgraz) |
| pic_surf (calcite) | 2.33 | 1.08 | 2170 | 0.02 | iron-useless (constrains R_PICPOC) |
| poc_surf (POC concentration) | 2.33 | 1.09 | 2170 | 0.02 | iron-useless control |
| dfe_surf_2 (2nd identical [DFe] survey) | 2.00 | 1.09 | **2930** | 0.00 | trivial control |
| feupt_surf (biological Fe uptake flux) | 1.98 | 1.08 | 2497 | 0.01 | iron-useless |

### What the two metrics agree on (the paper's point)

- **The method discriminates.** The `dfe_surf_2` control (a second identical
  surface-[DFe] survey) gives exactly the trivial `2.00x` variance drop and leaves the
  condition number **unchanged** at 2930, alignment 0.00. More of the same data halves
  the variance isotropically and does not rotate the degeneracy. Unrelated surface
  concentrations (POC, PIC) and the biological Fe-uptake flux behave the same way
  (about 2x / cond about 2200 to 2500). This is exactly the behavior a working OED
  criterion must show.
- **The degeneracy-breakers are the symmetry-breakers.** Only two classes of
  observation collapse the iron condition number by two to three orders of magnitude:
  the **scavenging flux** (which multiplies `scav_rat` explicitly, so it sees the sink
  directly) and **subsurface [DFe]** (where alpfe's surface-only source is absent, so
  the concentration is no longer source/sink-symmetric).
- **Specificity is correct.** bSi and PIC, which the identifiability study showed
  constrain diatomgraz and R_PICPOC, are correctly flagged near-useless for the iron
  pair (alignment about 0.02, condition number essentially unchanged). The method does
  not just say "measure more", it says "measure the right thing for *this* degeneracy".

### Where the two metrics differ (honest nuance)

The conditional 2x2 metric ranks the **surface scavenging flux first** (1434x). The
fully marginalized full-6 metric ranks **subsurface [DFe] first** (24.8x), with the
scavenging fluxes close behind (13x deep, 9x surface). Both are legitimate: the 2x2
metric answers "if the other four parameters were known, which observable best resolves
the iron combination", and the full-6 metric answers "marginalizing over everything
else, which observable most shrinks the iron combination". The robust, metric-independent
conclusion is that a **flux observable and a depth-resolved concentration are the two
ways to break the surface source/sink symmetry, and both beat any second surface
concentration by two to three orders of magnitude.**

## Interpretation and honest limitations

- **The hypothesis is confirmed against a *surface* concentration, not against depth.**
  The scavenging flux beats a second surface-[DFe] survey (1434x vs 2.0x) and every
  other surface concentration decisively. It does **not** uniquely beat a subsurface
  concentration; `dfe_sub` is comparable, and stronger under marginalization. The
  correct paper claim is "a scavenging-flux observable, or a depth-resolved iron
  profile, breaks the degeneracy that any amount of surface concentration cannot",
  not "only the flux works".
- **The scavenging flux is the structurally more robust recommendation.** The
  subsurface-[DFe] result leans on the box's clean 2-layer structure, in which alpfe
  acts only at the surface and the sole subsurface iron source is remineralization. In
  the real ocean and in Darwin-3 there are also hydrothermal and sedimentary iron
  sources at depth, which would re-inject an alpfe-like source term and erode the
  subsurface discriminating power. The scavenging flux's power comes from the explicit
  `scav_rat * DFe * POC` dependence, which holds regardless of where iron enters, so it
  is the more transferable design.
- **Sensitivities are numerically resolvable.** No candidate is below the float32
  finite-difference floor (`fd_floor_uninformative = false` for all). The surface
  scavenging flux at Carroll is about 3.7e-5 mmol Fe/m^3/d and its parameter
  sensitivities are well above numerical noise, so the ranking is not an artifact of
  tiny magnitudes.
- **This is a 0-D surrogate design, not a field OED.** The box homogenizes the spatial
  structure the real problem has, and the equal-footing "unit fractional noise"
  assumption ignores that 234Th/210Po flux measurements are noisier and sparser than a
  bottle [DFe]. The result is a *relative* ranking of observable **types** under a
  common assumption, which is the right granularity for a "what should we go measure"
  argument, and the natural place to add realistic per-observable noise budgets in a
  follow-on.
- **The base can be surface-only or surface+subsurface.** Here `F0` is surface [DFe]
  ("iron concentration only"). If the existing GEOTRACES constraint is taken as
  surface+subsurface (the `realiron` configuration behind the -0.77 marginal
  correlation), then `dfe_sub` is already partly spent and the scavenging flux is the
  genuinely new information. The script exposes the base observable set for that variant.

## Reproduction

```bash
# AICR B200 (confirmatory) or login-node CPU (fast; forward-only, no GPU required):
cd ~/emulator_poc && source ~/dd_venv/bin/activate
export PYTHONPATH=$HOME/emulator_poc/src
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5 GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces
export AOIS=eqpac,natlsubpolar,southernoceanpac GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0
export AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 USE_EPPLEY_T=1 POSI_W=1.0
export NB23_N_EPOCHS=0 NB23_SEEDS=0 TORCH_COMPILE_BATCHED=0
python -u scripts/analysis/observation_design.py --out docs/findings/2026-07-23_observation_design.json
# GPU confirmatory: sbatch ~/emulator_poc/obsdesign_aicr.sbatch
```

The primary metric is prior-free (2x2 iron block); the `--tau` flag only affects the
full-6 marginal cross-check, and `--rel-eps` sets the Jacobian finite-difference step
(default 2e-2, matching the identifiability Hessian FD).
