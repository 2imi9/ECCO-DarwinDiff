# Depth emulator — multi-seed robustness of the "no skill vs AR(1)" deflation

**Date:** 2026-07-23
**AOI:** eqpac · **Cube:** `darwin_v05_L5_chl.npz` (48 shared months, 6 tracers × 5 levels = 30 chans, Chl1 log-space)
**Question:** the single-seed (seed 0) result showed the depth emulator adds **no significant skill over persistence** (overall skill +0.068 [-0.033, +0.143], CI straddles zero) and is **worse than a per-cell seasonal AR(1)** (-0.146). Is that robust across training seeds, or is it seed variance?

## TL;DR (4-sentence summary)

The no-skill-vs-AR(1) result **holds across every seed**. Retraining at seeds 1, 2, 3 (identical held-out split, only model init + minibatch order change) gives an overall skill-vs-persistence of **+0.055 ± 0.013** (mean ± std over seeds 0–3), and in all four seeds the 95% block-bootstrap CI straddles zero, so the emulator never significantly beats even plain persistence. Against the strongest free baseline — per-cell **seasonal AR(1)**, selected as best in every seed — the emulator is **significantly worse in all four seeds** (skill -0.161 ± 0.015, and every seed's CI upper bound sits below zero: -0.099 to -0.126). Seed-to-seed variance (±~0.013) is roughly an order of magnitude smaller than each seed's bootstrap CI width (~0.17–0.21), so training-seed noise cannot rescue the emulator — the deflation is a property of the model/task, not of seed 0.

## Setup

- Retrained the depth+Chl emulator with `scripts/emulator_poc.py` at **seeds 1, 2, 3** via a Slurm array (job `188087`, B200, `--account=p2026_0089_neu --partition=b200-batch`), same flags as the seed-0 run: `--load-cube … --no-physicsnemo --epochs 250 --rollout-train-k 4 --log-transform --log-tracers Chl1 --rollout-positivity --rollout-mass-conserve`, adding `--seed {1,2,3}`. Each dumped its own `depth_chl_fields_seed{N}.npz` + `depth_chl_emulator_seed{N}.json`.
- Ran the rigorous `scripts/analysis/emulator_baselines_v2.py` (per-cell seasonal AR(1), tendency-normalized skill, 1000× spatial block-bootstrap CIs) on each seed's fields → `emulator_baseline_matrix_v2_seed{N}.json`.
- **Split is deterministic and identical across seeds** (verified): all seeds share `Nval=8` val pairs, the same `val_iters`, 18 train pairs, 34 train months, 42 950 valid cells, 120 spatial blocks. `--seed` only perturbs torch/numpy init and minibatch order, so this isolates *training-seed* variance (not data resampling).
- Seed 0 = the pre-existing run (`emulator_baseline_matrix_v2.json`), included as a legitimate fourth training seed.

## Results — overall pooled, 95% block-bootstrap CI

Convention (v2): skill = 1 − RMSE_model / RMSE_base, residuals z-normalized per channel and pooled over all 30 channels and 42 950 cells.

| seed | skill vs persistence | skill vs AR(1) per-cell | skill vs BEST simple | best simple | NE(emu) |
|-----:|----------------------|-------------------------|----------------------|-------------|--------:|
| 0    | **+0.068** [−0.033, +0.143] | −0.030 [−0.115, +0.037] | **−0.146** [−0.202, −0.099] | ar1_seasonal_percell | 0.932 |
| 1    | +0.064 [−0.043, +0.141] | −0.034 [−0.118, +0.034] | −0.150 [−0.207, −0.101] | ar1_seasonal_percell | 0.936 |
| 2    | +0.047 [−0.067, +0.130] | −0.053 [−0.150, +0.023] | −0.172 [−0.227, −0.120] | ar1_seasonal_percell | 0.953 |
| 3    | +0.042 [−0.081, +0.129] | −0.058 [−0.160, +0.020] | −0.177 [−0.230, −0.126] | ar1_seasonal_percell | 0.958 |

**Mean ± std across seeds 0–3:**
- skill vs persistence: **+0.055 ± 0.013** (seeds 1–3 only: +0.051 ± 0.012)
- skill vs AR(1) per-cell: **−0.044 ± 0.014**
- skill vs best simple (seasonal AR(1)): **−0.161 ± 0.015** (seeds 1–3 only: −0.167 ± 0.014)
- tendency-normalized error NE = RMSE_model / RMSE_persistence: **0.945 ± 0.012** (>1 would lose to persistence; ~0.94 means only a hair better than copying)

## Interpretation

1. **Skill vs persistence is not significant in any seed** — the point estimate is small and positive (+0.04 to +0.07) but the CI straddles zero for all four seeds. Persistence is not beaten with confidence at any training seed.
2. **The emulator is significantly worse than seasonal AR(1) in every seed** — `ar1_seasonal_percell` is selected as the best free baseline in all four seeds, and the emulator's skill against it is negative with the CI *entirely below zero* (upper bounds −0.099 to −0.126). This is the load-bearing deflation and it is fully robust.
3. **Seed variance is small and one-directional-ish** — the spread across seeds (±~0.013 on skill-vs-persistence) is ~15× narrower than a single seed's bootstrap CI (~0.17–0.21 wide). Seed 0 happens to be the most favorable of the four; seeds 2–3 are slightly weaker, so the original single-seed number was, if anything, a mild over-statement. No seed flips the conclusion.
4. The optimistic-looking headline in `depth_chl_emulator.json` (+0.079 to +0.129 across seeds) uses the unweighted **MSE**-ratio convention and only the *persistence* baseline; the honest RMSE-convention pooled skill against the *best free baseline* is negative everywhere. The two conventions agree on the verdict once the stronger baseline is in play.

## Verdict

**CONFIRMED.** The "depth emulator adds no significant skill over a per-cell seasonal AR(1) baseline, and does not significantly beat persistence" conclusion is robust to training-seed variance. It is not a seed-0 artifact.

## Provenance

- Slurm array job: `188087` (`dd-depthchl-ms`, seeds 1–3), all tasks train rc=0 + baseline rc=0.
- Array script: `/scratch/qi_zim_neu/depth/multiseed_array.sbatch`
- Aggregation: `/scratch/qi_zim_neu/depth/aggregate_multiseed.py`
- Per-seed artifacts (on cluster `aicr`, `/scratch/qi_zim_neu/depth/`):
  - seed 0: `depth_chl_fields.npz`, `depth_chl_emulator.json`, `emulator_baseline_matrix_v2.json`
  - seed N∈{1,2,3}: `depth_chl_fields_seed{N}.npz`, `depth_chl_emulator_seed{N}.json`, `emulator_baseline_matrix_v2_seed{N}.json`
- Shared cube: `/scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz`
- `emulator_baselines_v2.py` re-asserted `persistence == cube.state[source]` and `true == cube.state[target]` (< 1e-3) for every seed, so the dumped fields are verified against the cube snapshots.
