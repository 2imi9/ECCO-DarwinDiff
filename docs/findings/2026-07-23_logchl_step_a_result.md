# Emulator step (a) — log-space chlorophyll: WIRED IN + honest result (2026-07-23)

**Bottom line: log-space z-scoring is now wired into `emulator_poc.py` and the plumbing
works — Chl no longer poisons the model (overall skill went from *negative* under linear
z-scoring to +0.129 "MAKE"). But chlorophyll itself does NOT beat persistence, even in log
space: all five Chl1 depth levels score negative vs persistence (−0.47 to −0.61). Chl joins
the persistence-dominated cluster (DIC/ALK/FeT), not the learnable one (PIC/POC). Step (a)
is CLOSED — with a negative result for Chl skill, a positive result for the log plumbing.**

## What was done

`emulator_poc.py` gained `--log-transform` + `--log-tracers` (the design assumed these
existed; they did not — the surface globe's log lived only in the plotter). Implementation:
`build_log_mask()` stem-matches channel names (`name.split("_k")[0]`), `standardize()` logs
the masked channels *before* z-scoring, de-standardize `exp`'s them back, and the rollout
round-trips through exp/clamp/log. The per-tracer `rmse_physical` mislabel was fixed so the
physical RMSE is computed in physical (exp'd) units and a `log_space` flag is recorded per
tracer. Job 185256 (B200), depth cube `[48, 25, 171, 360]`, 6 tracers × 5 levels + Chl1×5.

## Result (job 185256, log-z for Chl1)

| field | k0 | k1 | k2 | k3 | k4 | reading |
|---|---|---|---|---|---|---|
| **Chl1** (log-z) | −0.47 | −0.46 | −0.48 | −0.46 | −0.61 | **worse than persistence at every level** |

Context (same run, surface k0): PIC +0.37, POC +0.45–0.50 (**beat persistence**); DIC −1.04,
ALK −1.69, FeT −1.85 (persistence-dominated). **Overall skill +0.129 → verdict MAKE**, carried
by PIC/POC — must not be reported alone.

## Reading

1. **The log transform was necessary and it works.** Linear z-scoring on a field with a
   2.8×10⁶ dynamic range gave *negative global* skill (Chl dominated the loss and dragged the
   whole model down — see [[finding_global_chl_needs_log_space]]). In log space the global
   verdict is back to MAKE. The plumbing is validated; Chl can now ride in any depth/global run.
2. **Chl is persistence-dominated, not learnable-beyond-persistence.** At a 1-month horizon on
   the 1° grid, surface chlorophyll is near-persistent: next month ≈ this month, so persistence
   is near-unbeatable and the operator adds noise → negative skill. This is the *same* structural
   ceiling as the subtropical gyres and the near-conserved carbonate tracers. It is NOT a bug and
   NOT a plumbing failure — it is the honest physics of the 1-step operator.
3. **The learnable/unlearnable split is now clean across 6 tracers:** only the fast, patchy,
   particulate tracers (**PIC, POC**) beat *persistence* at 1 month — an edge that does not survive
   a free per-cell seasonal AR(1) baseline
   ([`2026-07-23_emulator_baselines_v2.md`](2026-07-23_emulator_baselines_v2.md)). Everything slowly-varying or
   near-conserved (DIC, ALK, FeT, **Chl**) does not. This is the crisp, defensible headline for
   the Track-2 emulator, and it re-confirms [[finding_rollout_horizon_and_speed]] /
   [[finding_physics_verify_third_validator]]: the ceiling is structural, not architectural.

## Consequence for the emulator roadmap

Step (a) closed. The remaining emulator steps inherit the same structural ceiling:
- **(b) DIC/ALK tendency/anomaly target** — the *only* path that could make a slowly-varying
  tracer beat persistence is to change the target (predict the tendency, or lengthen the horizon
  to where the carbonate system actually evolves). This is the real open question, but the
  surface finding says the ceiling is structural at 1 month regardless of target framing — so
  this is a *research bet*, not a sure win.
- **(c) global SFNO swap** — kills polar artifacts, does not change the persistence ceiling.

Neither (b) nor (c) changes the PIC/POC-vs-rest split. The emulator's genuine, first-of-kind
asset (the first depth-resolved ocean-BGC `PrognosticModel` in the Earth-2 stack, PIC/POC
skill at every depth) is already in hand. Further emulator work has diminishing returns against
the manuscript #1 critical path.

Artifacts: `/scratch/qi_zim_neu/depth/depth_chl_emulator.json` + `depth_chl_fields.npz` (B200),
`scripts/emulator_poc.py` (`--log-transform`/`--log-tracers`).
