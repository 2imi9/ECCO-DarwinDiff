# E2 pre-registration — held-out calcite (log PIC:POC) recovery, eqpac (2026-07-09)

Registered **before** looking at any real held-out number, so the make-or-break E2 gate is
not p-hacked (split, metric, controls, and pass criterion fixed in advance). The harness
(`darwindiff.held_out_obs` + `scripts/e2_real_calcite_eqpac.py`) is parameterized; this
note fixes the parameters.

## Hypothesis
A learned environment-driven calcite closure `g(env)`, fit on part of a real,
Darwin-independent calcite observation and rolled through **prescribed ECCO-Darwin
transport** (DB-1 iron forcing + DB-2 velocity), predicts the rain ratio at **held-out**
cells better than a constant (null) closure through the *identical* transport. A pass would
turn Track-1's consistency check into a genuine held-out validation — the E2 gate.

## Data (all fixed, real, staged on `D:`)
- **Target:** Daniels et al. 2018 CP:PP geometric-mean rain ratio, eqpac
  (`held_out_calcite_obs`), on the shared 1° grid (21,51). Darwin-independent → non-circular.
  Observable = **log PIC:POC** (log-normal rain ratio; decision #2, our modeling choice).
- **Forcing:** DB-1 Mahowald soluble-iron surface dust (`iron_forcing_loader`).
- **Velocity:** DB-2 v05 `uVel_C`/`vVel_C` → div-free barotropic `(u,v,w)` (`velocity_loader`).
- **IC:** Darwin tracer climatology from the AOI cache (spin-up seed; steady-state washes it out).

## Split (PRIMARY — fixed)
- **Env-regime hold-out**, not spatial blocking (a per-cell env closure interpolates across
  spatial blocks; it must *extrapolate* to an unseen env band).
- **Split channel: Ω_calcite** (calcite saturation state — the literature-standard rain-ratio
  driver). Hold out the **upper quartile** (`hold="upper"`, `q=0.25`), rank-based.
- **`q = 0.25` fixed.** On eqpac this yields **n_val ≈ 6** covered held-out cells (train ≈ 18)
  after the interior-ring (A6) + env-finite + DB-1 coverage ANDs. This is acknowledged
  **low-powered** (decision #1); see robustness below.
- Coverage = Daniels-finite ∧ env-finite ∧ `interior_mask(ring=1)` ∧ DB-1 `coverage_mask`.

## Robustness (pre-registered, secondary)
- **SST as an alternate split channel** (`split_channel="sst"`, same q) — the pass should not
  hinge on the Ω choice.
- **Pool eqpac + natl** to raise n_val (decision #1) — reported as a power check, not the
  primary result. (natl needs its Daniels coverage confirmed ≥ a few cells first.)

## Metric (fixed)
- **Learned − null held-out anomaly-R²** at physical `kh`, where anomaly-R² is scored against
  the **train basin mean** (`anomaly_masked_r2`) so predicting the basin mean scores ~0.
- **Closure surface-gated** (`SurfaceGatedClosure`, on by default) so the delta is
  attributable to *surface* env skill, not subsurface closure behavior transported to Z=0.

## Controls (fixed) — decision #5
1. **Null-closure baseline** (frozen `g≡1` through the identical transport). The learned
   closure must beat it: `delta > 0`.
2. **K_num ablation** — sweep `kh ∈ {50, 200, 800}` (physical → over-smoothed). On REAL,
   out-of-class data the delta must be **largest at physical kh and shrink as kh grows**
   (`K_num-shrinks = True`). A delta that *rises* with kh means the "pass" is numerical
   smoothing, not biology → FAIL. (Unlike the self-twin, where this ablation was flat.)
3. **Permuted-predictor** and **profile-curvature** cross-checks at the claimed-pass kh
   (follow-up if 1–2 pass), to confirm the skill is env-specific and identifiable.

## Pass criterion (fixed, in advance)
**PASS ⇔ `delta > 0` at physical kh AND `K_num-shrinks`.** Anything else is NOT a pass.

## Run config (fixed)
`kh=50, kz=50, n_z=6, dt=0.25 d, dz=10 m, q=0.25, hold=upper, split=omega_c`, physical-kh
plus the {4×, 16×} K_num ladder. Rollout length / epochs set to reach a converged steady
state (the twin used n_steps≈60, epochs≈80; the runner defaults are conservative). Runs
**locally** (native data on `D:`, tiny 21×51×6 training — not a cluster job).

## Honesty guardrail (binding)
Daniels is a **low-powered** anchor (eqpac geomean 0.039 ≈ Darwin 0.042, ~1.6× global): a
pass **corroborates** an environment-conditioned, regionally-variable rain ratio — it does
**not** sharply validate a specific `R_PICPOC`, and it is **not** "confirming the thesis" or
"making Darwin differentiable." Calcite is environment-**dominated** (Ω, SST), composition a
minor modulation. If E2 does not binary-pass, the reportable result is the **identifiability
map** (which real obs can constrain Darwin's closures vs cannot), which stands regardless.

## Decisions status
- #2 log-space — settled (our modeling choice, baked into the observable).
- #3 sinking identity — settled from our side: carroll6 uses a **single `W_SINK`** for POC
  and PIC (no `W_SINK_PIC`) and the 5-tracer box has **no cocco PFT**, so standing-stock
  PIC:POC == the production ratio Daniels measures; no target correction. (Daniels is
  observations, so this is a box property, not a Darwin-v05 config question — no Jon needed.)
- #1 q/pool, #4 pre-registration (this note), #5 controls — fixed above.
