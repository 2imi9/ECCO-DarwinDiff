# The integration window is a contested resource: `scav_rat` and `diatomgraz` want opposite ends of it

**Date:** 2026-08-05 · **Job:** 270032 (`dd-flagwin3`, 30 array tasks) + 271120 (graded) ·
**Artifacts:** `/scratch/qi_zim_neu/flagwin3/{fs3_w100,fs3_w200,fs3_w400,fs3_null_w100,fs3_null_w200,fs3_null_w400}` ·
**Lever:** `N_STEPS` ∈ {100, 200, 400} · **Config:** `scripts/configs/flagship_geo1.sh`, sourced, with
only `N_STEPS` overridden · **`NB23_LR=5e-3`**, the value pinned on 2026-08-03 · every arm
`verify_run` **VERIFIED**, `GATE_FAIL=0`.

**Verdict: `N_STEPS` is not a neutral numerical choice. `scav_rat`'s recovered value falls
monotonically through the pass band as the window lengthens — 3.51x Carroll at 100 steps, 0.54x at
200, 0.20x at 400 — so the published window is where a drift happens to cross the target, not a
basin of stability. Over the same range `diatomgraz`'s equatorial-Pacific leg rises monotonically
toward Carroll, reaching 0.95x at 400 steps, where `scav_rat` is dead. No single window serves both
parameters. The WINDOW claim is ONE submission with NO replication and does not close
[#219](https://github.com/2imi9/ECCO-DarwinDiff/issues/219). The `diatomgraz` eqpac result is
different: graded per-leg at ≤0.10 against an EMPTY null (§9) it is 18/50 at `w200`, P = 5.9e-07,
and it reproduces the published width-arm figure from a separate submission — the project's first
genuine out-of-sample replication of a regional identifiability result.**

## 1. The measurement

Six arms in one submission: three windows, each with its own architecture-matched untrained null.
n = 50 seeds per arm. Grading is the per-AOI ≥2-of-3 rule at the canonical Cal band of 0.40.
**Every count is given under all three collapses**, arithmetic / geometric / median.

| arm | `alpfe` | `scav_rat` | `R_PICPOC` | `diatomgraz` | **trio** |
|---|---|---|---|---|---|
| `fs3_w100` | 50 / 50 / 50 | **0 / 0 / 0** | 50 / 50 / 50 | 0 / 0 / 0 | **0 / 0 / 0** |
| `fs3_w200` | 49 / 49 / 49 | **20 / 8 / 19** | 50 / 50 / 50 | 1 / 1 / 2 | **20 / 7 / 19** |
| `fs3_w400` | 46 / 46 / 46 | **0 / 0 / 0** | 50 / 50 / 49 | 8 / 7 / 10 | **0 / 0 / 0** |
| untrained null | 10 / 10 / 10 | 0 / 0 / 0 | 0 / 0 / 0 | 32 / 32 / 32 | — |

Trio = joint {`alpfe`, `scav_rat`, `R_PICPOC`}. Its sole binding leg is `scav_rat`, exactly as at the
flagship operating point.

`scav_rat` at `w200`: P = 3.0e-12 arithmetic, **P = 0.0094 geometric**, P = 3.0e-11 median, against a
null of 0/50. At `w100` and `w400` the null is also 0/50 and so is the trained arm, so there is
nothing to test.

**The three untrained nulls are bitwise identical** — the medians agree to all 16 significant
figures. That is correct rather than suspicious: an untrained parameter head's output does not
depend on the forward integration window at all. The practical consequence is that the
window-matched null is a no-op, and a future sweep should run **one** null instead of three.

## 2. The mechanism: a monotone drift, not a window optimum

The counts above look like a peak at 200 steps. The underlying values show it is not a peak. Per-AOI
medians over 50 seeds, as a multiple of Carroll, read off the `per_aoi_recovered_geom` key:

**`scav_rat`** — monotone decreasing in **every** basin, no exceptions:

| window | eqpac | natlsubpolar | southernoceanpac | pooled |
|---|---|---|---|---|
| `w100` | 4.913x | 3.116x | 2.779x | 3.507x |
| `w200` | 0.425x | 0.433x | **0.881x** | 0.538x |
| `w400` | 0.078x | 0.238x | 0.491x | 0.204x |

The pass band is [0.60x, 1.40x]. The fit starts far above it, ends far below it, and at 200 steps
**only the Southern Ocean leg is inside** (0.881x). eqpac and natlsubpolar are already below the
band's lower edge at the published window. That is why the geometric trio is 7/50 while the
arithmetic one is 20/50: the arithmetic collapse inflates the pooled value by exp(σ²/2), and
`scav_rat`'s natlsubpolar leg carries σ = 0.934, **above the σ = 0.820 threshold at which the
collapse alone can clear the band.**

This corroborates the standing position that the Southern Ocean is the one basin where `scav_rat`
is established, and it adds the reason: it is the only basin whose drift has not yet left the band
by 200 steps.

The pre-registered mechanism holds. Subsurface `DFe_2`, the observable that anchors `scav_rat`, is
only **47.5% converged at 200 steps** and decays toward a 0.0096 nM fixed point, while the `alpfe`
and `R_PICPOC` anchors are 100% converged by 100 steps. A parameter read off an unconverged
transient moves with the window. It does.

**`diatomgraz`** — monotone *increasing* toward Carroll over the same range:

| window | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| `w100` | 0.064x | 0.062x | 0.062x |
| `w200` | 0.859x | 0.166x | 0.129x |
| `w400` | **0.952x** | 0.356x | 0.351x |

The equatorial-Pacific leg count follows: 0/50 → 36/50 → **45/50**, against a window-independent
untrained null of 33/50. Fisher one-sided: P = 1.0, P = 0.333, **P = 0.0035**. Only the 400-step arm
clears its null, and it clears it at the 0.40 band where that null is heavily prior-contaminated.

**§9 regrades this per-leg at ≤0.10, where the null is empty, and the picture changes: the leg is
18/50 at `w200` and 15/50 at `w400` against 0/50, so it does NOT keep climbing with window length.
Most of the 36 → 45 climb above was the null moving, not the fit improving.** The window argument
in this section rests on `scav_rat`, which is where it was measured.

**The two parameters want opposite ends of the lever.** At 100 steps `diatomgraz` is anti-recovered
in all three basins; at 400 steps `scav_rat` is dead in all three. The published 200 gets `scav_rat`
marginally and `diatomgraz` barely.

## 3. What is collapse-invariant here, and what is not

Worth stating precisely, because "pooler-invariant" is easy to over-apply:

- **Invariant — the conclusion.** `w100` and `w400` give **0/50** for `scav_rat` and the trio under
  all three collapses at all three bands tested. That is 18 independent cells, all zero. The death
  of recovery at both neighbours is not a collapse artifact and not a band artifact.
- **NOT invariant — the magnitude at the surviving window.** At `w200` the trio is 20 / 7 / 19. The
  arithmetic and geometric readings differ by a factor of ~3, and only the arithmetic one would
  support the word "recovers".
- **Invariant — `alpfe` and `R_PICPOC`.** Identical under all three collapses at every window, with
  per-AOI log-sd ≤ 0.24. The collapse choice continues to affect `scav_rat` and nothing else.

## 4. Band sensitivity (±0.05), the second of the three required checks

Trio counts, arithmetic / geometric / median:

| window | band 0.35 | band 0.40 | band 0.45 |
|---|---|---|---|
| `w100` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| `w200` | 8 / 3 / 4 | 20 / 7 / 19 | 37 / 11 / 39 |
| `w400` | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

The `w200` count is steeply band-dependent — arithmetic 9 → 20 → 38 for `scav_rat` across ±0.05, a
factor of 4.2. It does **not** peak at the reported threshold (it rises monotonically), so this is
not the threshold-geometry failure mode, but it is a knife edge, and it is the same knife edge
already documented for `scav_rat` at the flagship point. The zeros at `w100` and `w400` are
completely band-insensitive.

## 5. The window does not test `alpfe`; the ceiling does

`alpfe`'s counts barely move (50 → 49 → 46) and are collapse-invariant. That is not window
insensitivity. Per-AOI medians as a multiple of Carroll, against an upper bound of 1.0
(= 1.077x Carroll):

| window | eqpac | natlsubpolar | southernoceanpac | legs ≥ 0.99 |
|---|---|---|---|---|
| `w100` | **0.589x** | 1.058x | 1.075x | 65 / 150 |
| `w200` | 1.069x | 1.077x | 1.076x | 121 / 150 |
| `w400` | 1.057x | 1.073x | 1.070x | 82 / 150 |

natlsubpolar and southernoceanpac sit **at the bound at every window tested**. Only the
equatorial-Pacific leg ever comes off it, and only at 100 steps — where its count drops to 24/50
while the two railed legs score 50/50 each. So the ≥2-of-3 rule is satisfied by the two railed legs
alone, at every window.

This **strengthens** rather than softens the 2026-08-05 bound result: where `alpfe` is not railed,
its recovery is worse. Its window-flatness is the ceiling being flat, not the estimate being stable.
As established, `alpfe`'s ~8% is bound geometry and must not be quoted as an accuracy.

## 6. What this does NOT establish

- **It does not close [#219](https://github.com/2imi9/ECCO-DarwinDiff/issues/219).** One submission,
  no out-of-sample replication. Splitting these 50 seeds in half is not replication — a permutation
  test over re-splits puts P(both halves significant) at 0.926 given a significant aggregate. #219
  needs a second, separately submitted job before any window conclusion is durable.
- **`fs3_w200` is not the flagship.** Same window, same sourced config, but it gives trio 20/50
  arithmetic and 7/50 geometric where the published flagship gives 25/50 and 12/50. Under the
  compare-within-a-job rule this gap cannot be read as a regression — but it does mean the w200 arm
  is a *sibling* of the flagship, not a reproduction of it, and the within-job w100/w200/w400
  comparison is the only comparison this artifact licenses.
- ~~**The `diatomgraz` result is at the wrong band.**~~ **Done — see §9, and it replicates.**
- **Provenance gap:** `code_provenance.git_sha` is `null` in every seed JSON
  ([#218](https://github.com/2imi9/ECCO-DarwinDiff/issues/218)). `code_digest` is `6d3918f8f57038eb`
  and `runner_md5` is `4d31555c309853b86c72de2acd877bf1`; those pin the build, but not to a commit.

## 7. Incidental, and worth not rediscovering

`n_daniels_cells_per_aoi` is `{eqpac: 34, natlsubpolar: 26, southernoceanpac: 0}` — the real Daniels
CP:PP anchor has **zero Southern Ocean coverage**, and the runner emits a `[warn]` and skips the term
there. `R_PICPOC` nonetheless scores 41–50/50 in the Southern Ocean at every window. Whatever is
identifying `R_PICPOC` in that basin, it is not a local calcite observation.

## 8. What this opens

The window is a single global scalar serving parameters whose anchors converge at different rates.
That is a design constraint, not a tuning nuisance, and it suggests the obvious extension: stop
sharing it. A per-parameter or per-basin integration window — or grading each parameter at the
window where its own anchor has converged — is testable with the code that already exists, and this
sweep is the evidence that it would change the answer.

## 9. Addendum — `diatomgraz` at the strict band, and the first out-of-sample replication

Added the same day, on the arms already staged, so it cost one query.

§2 graded `diatomgraz` at the canonical 0.40 band, where its untrained null is 33/50 in the
equatorial Pacific and the comparison is close to meaningless. The standing rule is to grade it
**per-leg at ≤0.10**. Doing that:

| band | window | eqpac leg (arith / geom / median) | null eqpac leg | P (geometric) |
|---|---|---|---|---|
| ≤0.10 | `w100` | 0 / 0 / 0 | 0/50 | — |
| ≤0.10 | `w200` | **18 / 18 / 18** | **0/50** | **5.9e-07** |
| ≤0.10 | `w400` | **15 / 15 / 16** | **0/50** | **8.9e-06** |
| ≤0.05 | `w200` | 8 / 5 / 12 | 0/50 | 0.028 |
| ≤0.05 | `w400` | 7 / 6 / 11 | 0/50 | 0.013 |

The untrained null's eqpac leg is **0/50 at both strict bands under all three collapses**, so this
is the clean comparison the 0.40 band could not give. At ≤0.10 the trained count is
collapse-invariant (18/18/18); at ≤0.05 it is not (8/5/12), and the geometric reading is the one
to quote.

**This is an out-of-sample replication, and that is the check this project most often fails.** The
published `diatomgraz` eqpac result — 40/100 at ≤0.10 and 20/100 at ≤0.05 against an untrained
0/50 — comes from the **width arms**. Job 270032 is a **separate submission** with a different
purpose, and its `w200` arm gives 18/50 at ≤0.10, i.e. 36/100 on the same scale. The repo's own
three-check rule demands "a genuinely fresh submission", and notes that the per-parameter width
effect died exactly here (45/50 vs 34/50 → 38/50 vs 38/50 in a later job). `diatomgraz`'s
equatorial-Pacific leg does **not** die: it reproduces to within 4 counts per 100 at ≤0.10, with a
0/50 null both times.

So the "two regionally identifiable in different basins" half of the honest framing is now the
better-supported half. `diatomgraz` in the equatorial Pacific has an independent replication at a
band where its null is empty. `scav_rat` in the Southern Ocean still does not — the two runs that
looked like a replication were shown on 2026-08-04 to be one result, bitwise identical on 50 seeds.

Note the window interacts here too, but weakly: at ≤0.10 the eqpac leg is 18/50 at `w200` and
15/50 at `w400`, so the strict-band signal does **not** keep climbing with window length the way
the 0.40-band count did (36 → 45). The 0.40-band climb was substantially the null moving, not the
fit improving. The window argument in §2 stands on `scav_rat`, which is where it was measured.
