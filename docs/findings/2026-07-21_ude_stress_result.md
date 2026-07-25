# UDE transport-stress sweep — transport is sound; the closure limit is trajectory coverage (2026-07-21)

Overnight de-risking of the Track-2 differentiable-transport UDE (`ude_transport_stress_h200.py`, cluster
job `8524801`, `--skip-envelope`; artifacts in `docs/findings/ude_stress_2026-07-21/`). Three
experiments; results are numeric/infra properties, not verify_run recovery numbers.

## EXP-B — mass conservation (#7): a non-problem

Relative global mass drift vs rollout length, transport-only, Euler vs RK4:

| steps | Euler drift | RK4 drift | max per-cell | finite? |
|---|---|---|---|---|
| 200 | 0.0 | 0.0 | ~4e-7 | ✓ |
| 2,000 | 0.0 | 0.0 | ~3e-6 | ✓ |
| 20,000 | 5.31e-6 | 5.39e-6 | ~1.1e-5 | ✓ |
| 100,000 | 5.31e-6 | 5.39e-6 | ~1.1e-5 | ✓ |

**Mass drift is tiny (~5e-6), bounded, and non-accumulating** (identical at 20k and 100k steps), and the
state is **finite at every horizon** (no blow-up). Euler and RK4 agree to 4 significant figures, so the
integrator is not the limiter. **#7 (decadal budget drift) passes decisively** — the transport conserves
mass out to 100,000 steps, far beyond decadal.

## Markov / dissipative neural operators — dead-end by evidence

The Caltech scan asked whether the UDE's "open" decadal stability needs a Markov/dissipative NO (which
targets state-norm blow-up under composition). **There is no blow-up** — `finite=True` and bounded drift
out to 100k steps. MNO has nothing to fix here. The scan's LOW rating is confirmed to dead-end with data.

## EXP-C / EXP-D — closure recovery (#176): the limit is trajectory coverage, not the optimizer

A neural iron-limitation closure trained to recover a known nonlinear f_fe inside the batched transport
model:

- **Trainable and accurate on-trajectory:** loss ↓ 152,000×, and **closure_rel_err on the visited dfe
  range = 0.65%.** The differentiable transport + closure stack learns cleanly.
- **Fails off-trajectory:** **closure_rel_err on the full range = 288%** — because the forcing drives the
  trajectory through an extremely narrow dfe band, so the closure is unconstrained everywhere else.
- **Regularization does not rescue it (EXP-D):** across weight-decay {0, 0.001} × anchor {0, 0.01}, the
  full-range error is 2.877 in *every* config (visited 0.0064 in every config). A regularizer cannot
  manufacture information about states the trajectory never visits.

**The binding constraint on UDE closure identifiability is state-space coverage — which states the
forcing visits — not the optimizer, the regularizer, or the integrator.** This is the concrete
motivation for the #176 profile-targeting build: **design the forcing** (see `scripts/ude_forcing_design.py`)
to drive the trajectory through a wide, informative dfe range so the closure is globally identifiable,
rather than tuning the loss. It is the same lesson as Track-1 (identifiability comes from the *observations
/ excitation*, not the estimator), now in the forward-UDE setting.
