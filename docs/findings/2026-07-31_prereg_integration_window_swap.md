# Pre-registration: is the Southern Ocean `scav_rat` result a property of depth, or of the integration window?

**Date:** 2026-07-31 · **Written with zero window-swap JSONs on disk** · **Status:** pending

## The problem

`N_STEPS = 200` at `DT = 0.25` (50 days) has been hardcoded since the box was written and has never
been swept. Two facts, both verified from source today, make it a candidate explanation for the
entire 2026-07-31 depth result.

**1. The box is basin-blind in these arms.** They ran `darwin_ic=False`, so `state0` is the uniform
literature vector in every AOI, and the box has no horizontal transport. Forward sensitivities come
out identical across eqpac, natl and sopac to four decimals. **No forward-model quantity can explain
a basin difference the forward model does not have.**

**2. The subsurface observable sweeps through every basin's observed median.** Integrating the real
box at Carroll values, `DFe_2` decays monotonically from the hardcoded 0.5000 nM toward its 0.0096 nM
fixed point, reaching only **47.5%** of the way at the 200-step window:

| window | days | box `DFe_2` | nearest observed basin median |
|---|---|---|---|
| ~73 steps | 18 | 0.4404 nM | **eqpac** (0.4404) |
| 100 steps | 25 | 0.4047 nM | between |
| **200 steps (what ran)** | **50** | **0.2671 nM** | heading toward sopac |
| ~243 steps | 61 | 0.2245 nM | **southernoceanpac** (0.2245) |
| 800 steps | 200 | 0.0291 nM | past all three |

The run's window sits nearest **southernoceanpac**, which is the only basin where `scav_rat`
recovers (33/50, against eqpac 6/50, P = 3.7e-08).

**The competing hypothesis (H_window):** `scav_rat` "recovers" wherever the basin-blind transient
happens to land near that basin's data, and depth structure has nothing to do with it.

**The incumbent (H_depth):** subsurface iron carries `scav_rat` because it is the sink-dominated
stratum, as the 2026-07-22 column OSSE predicted.

## The test

Halve the window. At `N_STEPS=100` the box sits at 0.4047 nM, near **eqpac** rather than the
Southern Ocean. The two hypotheses then predict opposite things.

| | `so_sub` @100 | `eq_sub` @100 |
|---|---|---|
| **H_window** | falls sharply | rises sharply |
| **H_depth** | holds near 33/50 | stays low |

## Arms

Nine arms, 50 seeds each, everything else byte-identical to job 240673 and the southernoceanpac arms
(`GEOTRACES_W=0, GEOTRACES_SUB_W=1, NB23_FET_WEIGHT=1.0, NB23_PINN_WEIGHT=0.0, POC_SUB_W=0.0,
DARWIN_IC=0`, MLD channel on, AOI-ID off, gating ungated, 2000 epochs).

| arm | AOI | window | purpose |
|---|---|---|---|
| `so_sub_w100` | sopac | 100 | primary |
| `eq_sub_w100` | eqpac | 100 | primary |
| `prior_so_w100` | sopac | 100 | untrained null **at this window** |
| `prior_eq_w100` | eqpac | 100 | untrained null **at this window** |
| `eq_surf_w100` | eqpac | 100 | surface control; the surface channel is converged, so it should be window-insensitive |
| `so_sub_w400` | sopac | 400 | monotonicity |
| `eq_sub_w400` | eqpac | 400 | monotonicity |
| `prior_so_w400` | sopac | 400 | null at 400 |
| `prior_eq_w400` | eqpac | 400 | null at 400 |

**The nulls are re-measured at every window and never reused across windows.** The untrained
distribution moves with the integration length, and reusing a 200-step null would manufacture an
effect.

## Decision rule, fixed now

Primary comparison: **`eq_sub` at 100 steps versus `eq_sub` at 200 steps** (6/50), and
**`so_sub` at 100 versus `so_sub` at 200** (33/50), each graded per-AOI, n=50, gated on
`verify_run` exit 0.

- **H_window CONFIRMED** if `eq_sub` rises **and** `so_sub` falls, each against its own
  window-matched untrained null at **Fisher exact two-sided P < 0.01**, and the two arms cross
  (`eq_sub@100 > so_sub@100`).
- **H_depth SURVIVES** if `so_sub@100` stays above its null at P < 0.01 and `eq_sub@100` does not,
  i.e. the ordering is preserved despite the window move.
- **INCONCLUSIVE** otherwise, including the case where both fall. Inconclusive is a real outcome and
  will not be written up as either result.

One threshold, P < 0.01, applied to both tails. This fixes the gap I left in the eqpac
pre-registration, where the band between 0.01 and 0.05 was undefined and the result landed in it.

**Falsifier for "the run is broken rather than the hypothesis":** `eq_surf_w100` must still recover
`alpfe`. The surface channel is near-converged, so halving the window should barely move it. If
`alpfe` collapses there too, the window change broke something global and no conclusion may be drawn.

## Committed interpretations

- **H_window confirmed.** Both 2026-07-31 depth findings are **retracted**, not caveated. The
  "surface identifies the source, subsurface identifies the sink" result becomes an artifact of a
  hardcoded 50-day window meeting basin-specific observations, and `N_STEPS` becomes a first-class
  hyperparameter that every prior recovery number has silently depended on.
- **H_depth survives.** The depth mechanism is materially strengthened, having survived an attack
  designed to kill it, and the anchor-segregated per-parameter routing plan proceeds.
- **Inconclusive.** The subsurface channel is declared too transient to carry a mechanism claim, and
  the next step becomes running to near-equilibrium (800+ steps) rather than arguing about 100.

## Also recorded

- A knife-edge caveat now applies to every untrained null in this project. `alpfe` and `diatomgraz`
  share bounds (0.05, 1.0), so both start at 0.525, which lands 3.4% of the box width **outside**
  `alpfe`'s Cal band and 2.8% **inside** `diatomgraz`'s. Nulls will be reported with their
  midpoint-to-band-edge distance.
- `N_STEPS` is now `int(os.environ.get("N_STEPS", "200"))`, a bitwise no-op at the default.
