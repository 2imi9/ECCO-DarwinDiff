# The per-parameter trunk effect does not replicate — 45/50 vs 34/50 became 38/50 vs 38/50

**Date:** 2026-08-03 · **Job:** 258256 (extension of 257056) · **Both arms `verify_run` exit 0,
100/100 seeds** · **Verdict: the architecture effect is REJECTED at the project's own bar, and
the fresh half is an exact tie.**

## What was outstanding

`2026-08-03_per_parameter_trunks_lift_scav_rat_but_not_the_frontier.md` reported `scav_rat`
45/50 for per-parameter trunks against 34/50 for a capacity-matched shared trunk, and stated
honestly that the architecture's own contribution was **P = 0.0128**, which does not clear the
0.01 bar the pre-registration used everywhere else. It named the fix: n=100.

This is that run. Seeds 50–99 were added to both arms and pooled onto the existing 0–49.

## Result

```
                        n=100     seeds 0-49        seeds 50-99
pp_head   (6 trunks)    83/100    45/50             38/50
pp_ctrl39 (width 39)    72/100    34/50             38/50
Fisher exact P          0.0897    0.0128            1.0000
```

**The replication half is an exact tie.** 38/50 against 38/50, P = 1.0000. The entire measured
effect lives in the first seed block and none of it survives into an independent one. Pooled
over all 100 seeds the difference is **P = 0.0897** — it does not clear the pre-registered 0.01
bar, and it does not clear 0.05 either.

The pre-registration was right to refuse the n=50 number, and the refusal was worth more than
the number: had 45/50 vs 34/50 been published at P = 0.0128 with a caveat, the caveat would
have been carrying a result that is not there.

## Controls, and one result that is not a control at all

Each arm against **its own** architecture-matched untrained null, all four pooled to n=100:

| | pp_head | its null | pp_ctrl39 | its null |
|---|---|---|---|---|
| `alpfe` | 100/100 | 25/100 | 98/100 | 30/100 |
| `scav_rat` | 83/100 | **0/100** | 72/100 | **0/100** |
| `R_PICPOC` | 100/100 | **0/100** | 100/100 | **0/100** |
| `diatomgraz` (0.40 band) | **0/100** | **70/100** | **1/100** | **77/100** |

`scav_rat` and `R_PICPOC` clear nulls of 0/100 in both arms — so **both architectures recover
them**; they simply do not differ from each other. The untrained `alpfe` rates (25/100, 30/100)
confirm again that nulls are architecture-dependent and cannot be borrowed.

### `diatomgraz` is not merely unrecovered — training moves it AWAY from Carroll

This is new at n=100 and it is a stronger statement than anything previously recorded. At the
0.40 band the **untrained** networks score **70/100 and 77/100**, because the prior midpoint
(rel 0.367) sits inside that band. The **trained** networks score **0/100 and 1/100**.

Training does not fail to find `diatomgraz`. It actively drives it out of a band the untrained
network was already in, in both architectures, on 100 seeds. The observable set is not
uninformative about `diatomgraz` — it is **misleading** about it, which is consistent with the
standing concern that the bSi target is partly circular, being algebraically back-solved from
diatom biomass (`ded116`).

Two consequences. Any future `diatomgraz` result quoted at the 0.40 band is uninterpretable
without its untrained null on the same architecture, since the null is the *higher* number. And
the honest framing is no longer "not established" but "the current observable set has the wrong
sign for this parameter" — which makes a genuinely independent silica observation the only way
forward, not more optimisation.

## The per-AOI legs say something the aggregate hides

| | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| pp_head | **11/100** | **81/100** | 95/100 |
| pp_ctrl39 | **11/100** | 70/100 | **100/100** |

Two things worth carrying forward:

1. **eqpac is 11/100 in both arms — identical to the seed.** It is now unmoved by capacity, by
   epochs, by information weighting, and by removing representation sharing. Whatever eqpac's
   problem is, it is not addressable by the estimator.
2. **Per-parameter trunks trade basins.** natl **+11**, sopac **−5**. The aggregate gain of 11
   is a net of two opposite movements, not a uniform lift. The capacity-matched control is the
   one that reaches a clean 100/100 in the Southern Ocean.

## What survives

**Capacity does, architecture does not.** The width-39 shared trunk reaches `scav_rat` 72/100
where the published flagship (width 16, 2000 epochs) is 25/50. That is the replicated,
non-architectural lever, consistent with the 4000-epoch result (25 → 41/50) being an
optimisation effect on the same data.

**Caveat on that comparison, stated rather than buried:** the flagship number comes from a
different experiment, so 72/100-vs-25/50 is cross-run. The within-experiment width-16 control
is `adq_ctrl` in job 258314, which is the arm to quote once it is graded.

## Consequences

- **Do not quote 45/50.** The n=100 value for that arm is **83/100**, and its comparison
  against the matched control is not significant.
- `scav_rat`'s honest best remains a **capacity/optimisation** result, not an architectural one.
- The `PER_PARAM=1` arm costs ~4.7x the weights and roughly double the wall clock for an effect
  that does not replicate. It should not be adopted.
- The natl-vs-sopac trade is new and was invisible at n=50; it is the part of this run most
  worth following up.
