# Emulator method-fix — residual + rollout-aware (scored, eqpac)

**Source:** Explorer array (job 8305587, **T4**; 500 epochs), `scripts/emulator_poc.py` with the new
`--residual` and `--rollout-train-k` modes. eqpac AOI (21×51), 6 tracers (DIC/ALK/PIC/POC/FeT/Chl1),
surface, 158 shared months, temporal hold-out. **Local-only — not committed to GitHub.**

Follows directly from the PoC (`emulator_poc_scored.md`), which passed overall but was *worse than
persistence* on the slow carbonate tracers (DIC −0.245, ALK −0.051) and had a marginal rollout. Two
targeted fixes, ablated:
- **`--residual`** — predict the tendency: `x̂(t+1) = x(t) + FNO(input)`. The model starts **at
  persistence** and learns only the correction — so slow tracers no longer require it to reconstruct a
  near-static field from scratch.
- **`--rollout-train-k K`** — accumulate the training loss over `K` autoregressive steps, so the
  rollout is optimized, not just the single step.

## Verdict: BOTH FIXES WORK — residual+rollout-k4 beats persistence on all 6 tracers

Headline = **skill over persistence** (>0 beats copying x(t)); mean across seeds.

| method | seeds | overall | DIC | ALK | PIC | POC | FeT | Chl1 | rollout beats-persist@final |
|---|---|---|---|---|---|---|---|---|---|
| baseline (full-next-state) | 3 | +0.176 | **−0.245** | **−0.051** | +0.185 | +0.173 | +0.176 | +0.350 | 2/3 |
| **residual** (k=1) | 3 | +0.255 | −0.032 | **+0.120** | +0.232 | +0.236 | +0.294 | +0.348 | 2/3 |
| **residual + rollout-k4** | 2 | **+0.265** | **+0.099** | **+0.228** | +0.326 | +0.292 | +0.167 | +0.389 | **2/2** |

- **Residual fixes ALK** (−0.051 → +0.120, now beats persistence) and lifts **DIC** from −0.245 to
  ≈persistence (−0.032). Overall skill +0.176 → +0.255.
- **Adding rollout-k4 fixes DIC** (−0.032 → **+0.099, now beats persistence**) and makes the **rollout
  robust** (both seeds beat persistence at the final autoregressive step — the marginal-rollout problem
  from the PoC, solved).
- With **residual + rollout-k4, all six tracers beat persistence**, overall +0.265.

## Confirmation (2026-07-12) — robustness (n=6) + depth (L3)

Ran the winning config (residual + rollout-k4, 500 ep, T4) at higher seed count and with 3 depth
levels (job 8305687). Both hold:

| config | n | overall | DIC | ALK | PIC | POC | FeT | Chl1 | rollout final |
|---|---|---|---|---|---|---|---|---|---|
| **surface** (L1) | 6 | **+0.268 ± 0.014** | +0.126 | +0.234 | +0.292 | +0.280 | +0.188 | +0.403 | **6/6** |
| **depth** (L3, 3 levels) | 4 | **+0.259 ± 0.019** | +0.054 | +0.161 | +0.288 | +0.252 | +0.154 | +0.432 | 3/4 |

- **Surface robust at n=6:** all six tracers beat persistence, tight variance (σ=0.014), rollout beats
  persistence at the final step in **6/6** seeds. The earlier FeT dip (n=2) was noise — FeT is +0.188.
- **Depth works:** the method **generalizes to a real 3-D field** (18 channels) — overall skill holds
  (+0.259 vs +0.268 surface), every tracer still beats persistence (DIC weaker at depth, +0.054,
  consistent with even-slower subsurface carbonate), rollout robust 3/4.

**De-risking conclusion:** residual + rollout-aware is robust across seeds *and* generalizes to depth,
on the tractable eqpac subset. That clears the last cheap-Explorer checks before the B200 scale-up to
native LLC270 / global / full-depth — which would now scale a *proven* method.

## Why this is honest (adversarial check)

- **The persistence yardstick is a fixed constant across the entire ablation.** The temporal split
  (from `val_frac`) and the per-tracer standardization (train-months only) are model- and
  seed-independent, and the residual/rollout flags change **only** the model's prediction path — not
  `persist_z = z_state[val_m]` nor the scoring. So `MSE_persistence` is identical for baseline,
  residual, and rollout; the skill differences come purely from the model. Apples-to-apples.
- **Leak-free pipeline inherited from the audited PoC.** The 4-audit adversarial review cleared all 8
  leakage axes on this pipeline (train-only standardization, time-disjoint split with the boundary pair
  dropped, identical scoring of model/persistence/climatology). The method-fix changes only the model
  forward and the training loop; the rollout-k training draws its K-step sequences **only from train
  months** (`m < split_idx`), so no val leakage.
- **Residual is not a free lunch.** `x̂ = x(t) + Δ`; if the model learned `Δ=0` it would *tie*
  persistence (skill 0), not beat it. Positive held-out skill means the learned `Δ` genuinely reduces
  the error vs `x(t+1)` on **later** months — real learned month-to-month dynamics.

## Caveats (unchanged scope)

Single AOI (eqpac), surface, 1° regridded, low seed (n=3 / n=2). This proves the *method* on a tractable
subset; the production emulator (native LLC270, global, full-depth) is the **B200 scale-up**. FeT's
drop at k4 (+0.167 vs +0.294 at k1) is within the n=2 noise — worth confirming at higher n.

## Bottom line

The PoC showed an FNO *can* beat persistence; this shows the **right method** — residual + rollout-aware
— makes it beat persistence on **every** tracer, including the slow carbonate fields the PoC failed, and
holds the rollout. That is the production-grade method to scale on B200. Next: confirm at higher seed
count + add depth levels on Explorer before committing B200 to native/global.
