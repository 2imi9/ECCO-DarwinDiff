# Reproducibility + inverse-method baselines — appendix draft (2026-07-24)

Consolidates the exact reproducibility trail and the inverse-method baseline citations for the manuscript
methods/appendix (issue #117). Every headline number is `verify_run.py`-gated (exit 0 = re-derived from raw).
This is a methods/reproducibility appendix — NOT a core-claim change.

## 1. Recovery metric (exact definition)
- **Per-AOI ≥2-of-3 Cal-grade+** is the honest headline metric: a seed "recovers" a parameter if ≥2 of the 3
  AOIs {eqpac, natlsubpolar, southernoceanpac} land Cal-grade+ (`diagnostics.band_of`: Excellent ≤5% off
  Carroll; Cal-grade ≤40%; Loose ≤80%). Count over the seed ensemble → N/50 (or N/10).
- **Cell-weighted (joint-cw)** OVERSTATES the per-AOI metric via a **straddle** (per-AOI legs on opposite
  sides of Carroll whose weighted mean lands near it); tonight it overstated scav_rat by +5 to +10 seeds. The
  grader flags straddles explicitly. **Report per-AOI; disclose the straddle.**
- Recovery is graded against **Carroll's published Green's-functions optima** (bit-identical v04/v05), not
  against prior notebooks.

## 2. Key configurations (env-var recipe; `run_v3.0_joint_multi_aoi.py`)
All sourced from `covar_env_common.sh` first (sets data roots + Eppley defaults), then the override. AOIs
eqpac,natlsubpolar,southernoceanpac; default per-AOI weights {1,2,2}; Darwin IC; per-cell DINN (SST channel).

| config | override (beyond base) | result (n=50 unless noted) | job |
|---|---|---|---|
| flagship geo1 (n50e2k) | GEOTRACES_W=1, DANIELS_RPICPOC_W=1, PINN=3, POC_SUB_W=3, CHL1_W_EXTRA=3, DARWIN_PATTERN_W=1, 2000ep | trio 25/50; alpfe 49/50; R_PICPOC 50/50; scav_rat 25/50 | 188532 |
| ep4k (optimization limit) | flagship + NB23_N_EPOCHS=4000 | scav_rat **41/50** (natl 40, eqpac 6) | 190529 |
| dgchl (non-circular diatomgraz) | MLD_CHANNEL=1, DARWIN_PATTERN_W=0, PINN=0, POC_SUB_W=0, GEOTRACES_W=0.3, POSI_W=0, DANIELS=8 | diatomgraz **35/50** | 190529 |
| 4-of-4 test | flagship + MLD_CHANNEL=1 + 4000ep (TORCH_COMPILE_BATCHED=0) | diatomgraz 0/10 (no 4-of-4) | 192298 |
| global-scalar control | GLOBAL_SCALAR=1 | trio 0/50 | (geo1) |
| anchor-off (R_PICPOC) | DANIELS_RPICPOC_W=0 | R_PICPOC 4/50 | (geo1) |

n≥50 is run as 5× 10-seed array blocks pooled into one OUTPUT_DIR (never 50 seeds in one process — CUDA-OOM).

## 3. Estimator-independence (closes the "single-method / DINN+autograd artifact" attack)
The identifiability verdict is reproduced by three independent estimators:
- **DINN-free global-scalar recovery** + **gradient-free Nelder-Mead** both reach alpfe's optimum (#172).
- **Ensemble Kalman Inversion** (Iglesias-Law-Stuart 2013, derivative-free, immune to the θ\* saddle; job
  189754): alpfe 0.999 / R_PICPOC 0.0364 Cal-grade, scav_rat 2.09e-7 Loose (biased low) — **same verdict as
  backprop**. Report the posterior MEAN only (the ILS-2013 ensemble collapses; a calibrated CI needs the
  EKS/CES sample stage — future work).

## 4. Identifiability geometry (methods)
- **GN-Fisher** `JᵀJ` (`identifiability_sloppiness.py --mode fisher_gn`): PSD by construction, valid curvature
  at Carroll where the loss Hessian is an indefinite saddle. Residual reconstruction reproduces the loss to
  1e-7 (verified). Per-AOI iron sloppiness 5.19/5.99/4.99 decades; joint 3-AOI 2.69 decades (24-start,
  saddle-fixed, job 8515339).
- **Profile-likelihood / Hessian** (`--mode global --param P`): scav_rat profiles CURVED in all 3 AOIs
  (constrained → practical, not structural, non-ID); span eqpac 3.69 > natl 1.30 > sopac 1.12.
- **Per-AOI 2×2 iron conditioning** {alpfe, scav_rat}: sopac 2.22 (not ratio-degenerate) < eqpac 34.7 < natl
  50.8 (both ratio-degenerate); the aggregate cond 3022→2.2 (job 188077) is Southern-Ocean-driven.

## 5. Inverse-method baseline citations (for the methods/related-work section)
- **Sloppiness / Fisher-geometry lineage:** Gutenkunst et al. 2007 (PLoS Comp Biol, sloppy models);
  Transtrum, Machta, Sethna 2011/2015 (parameter-space geometry, information geometry of sloppiness);
  Brown & Sethna 2003.
- **Profile likelihood for identifiability:** Raue et al. 2009 (Bioinformatics, structural + practical
  identifiability via profile likelihood).
- **Ensemble Kalman Inversion / sampling:** Iglesias, Law, Stuart 2013 (Inverse Problems, EKI); Garbuno-Iñigo
  et al. 2020 (EKS); Cleary et al. 2021 (Calibrate-Emulate-Sample / CES).
- **Marine-BGC parameter identifiability (domain):** Spitz et al. 1998 (some growth/loss params inseparable
  even with the annual cycle); Ward et al. 2010 (twin-experiment identifiability); Biogeosciences bg-14-1647-2017.
- **The iron degeneracy (external validation):** Tagliabue et al. 2016 GBC (FeMIP: residence time 3.7–626 yr
  while [DFe] pinned at 0.58±0.14 nM); Somes et al. 2021 (controlled 5-run demonstration); Frants et al. 2016
  (overlapping-source compensation, "consistent with," not an identity); Parekh, Follows & Boyle 2005 (Darwin
  iron model — NOT the 2006 DOI).
- **Calcite / rain-ratio anchor:** Daniels et al. 2018 (CP:PP production ratio ≈ Darwin 0.042).

## 6. Honest limits (state in the paper)
- The Fisher is the **surrogate's**, not the GCM's — validating it needs an 8-run v05 perturbation ensemble
  (#163; traits-override-safe recipe ready). Until then, all Fisher claims are surrogate-conditional.
- The surrogate gap is **dimensional** (0-D box relaxes to CoV ~1e-15 at uniform Carroll vs the model's O(1)
  structure) — box-vs-model pattern correlations are NOT fidelity metrics; identifiability comes from real
  absolute anchors.
- Held-out GEOTRACES cross-validation returns negative R² (the box has no spatial structure to predict
  per-cell iron) — the recovery pins the iron *magnitude*, not which cell has how much.
