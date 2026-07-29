# The pooled calcite Ω-exponent is a between-basin contrast, not a rain-ratio law (2026-07-29)

**Headline.** In `docs/findings/calcite_omega_identifiability_real.json` and its two siblings, the
`pooled` power-law exponent is **not** an aggregate of the per-AOI exponents. It is dominated
(~90% of the regression's driver variance) by the **between-AOI** contrast, because the AOIs occupy
**disjoint Ω ranges**. The pooled slope is therefore a different estimand from the per-AOI slopes —
a basin-mean contrast confounded with every other basin difference — and in the Marsh and GLODAP
variants it carries the **opposite sign** to the within-AOI signal.

**This does not change the NULL verdict.** All three artifacts already return NON-IDENTIFIABLE and
the note's conclusion is unaffected. What is affected is (i) the `pooled` block's numbers, which
should not be read as an exponent estimate, and (ii) the auto-generated remediation advice
("widen the visited Omega range"), which is actively counter-productive when applied to the pooled fit.

---

## 1. The observation

`docs/findings/calcite_omega_identifiability_real.json` (Daniels CP:PP source):

| scope | `n_hat` | 95% CI | `r2` | `n_points` | Ω range | source line |
|---|---|---|---|---|---|---|
| eqpac | +6.425 | [+1.833, +10.351] | 0.313 | 32 | [4.724, 5.666] | `:7–16` |
| natl | +7.010 | [+0.857, +12.992] | 0.147 | 24 | [3.136, 4.214] | `:23–32` |
| so | NaN | — | — | 0 | — | `:39–48` |
| **pooled** | **+0.890** | **[−0.229, +1.780]** | 0.046 | 58 | [3.136, 5.666] | `:57–66` |

The two siblings are starker:

- `calcite_omega_identifiability_real_marsh.json:9,23,39,57` — per-AOI **+3.404 / +11.096 / −0.048**,
  pooled **−0.471**. The pooled estimate is *negative* while the two well-populated basins are strongly
  *positive*.
- `calcite_omega_glodap_marsh.json:8,24,40` — per-AOI **+1.280 / −1.404** (neither CI excludes 0),
  pooled **−1.796** with CI **[−3.200, −0.275]**, which **does** exclude 0. Pooling manufactures a
  significant exponent out of two non-significant legs.

The recorded verdict blames "small n / narrow Omega support"
(`calcite_omega_identifiability_real.json:70`). That is true but insufficient: narrow support explains
*wide CIs*, not why the pooled point estimate lands ~7× below both per-AOI estimates and, in two of
three artifacts, on the other side of zero.

## 2. The estimator

`scripts/calcite_omega_identifiability_real.py:127–131` concatenates the per-AOI `(Ω, ratio)` arrays
and calls the same oracle used per-AOI. That oracle
(`scripts/symbolic_distill_probe.py:364–431`) is an ordinary least-squares fit of `log(ratio)` on
`log(Ω)` — `:393–398` — after a 1–99% trim on the driver (`support_mask`, `:140–145`). It fits a
**single intercept**. There is no AOI fixed effect, so every between-basin difference in the mean rain
ratio is absorbed into the slope.

## 3. Mechanism — quantified

### 3a. The AOIs occupy disjoint Ω support

Measured on the exact trimmed set the committed pooled fit uses:

| pair | Ω ranges | overlap |
|---|---|---|
| eqpac vs natl (Daniels) | [4.724, 5.647] vs [3.147, 4.214] | **0.000 (0.0% of union)** |
| eqpac vs natl (Marsh) | [4.724, 5.647] vs [3.136, 4.214] | **0.000 (0.0%)** |
| eqpac vs so (Marsh) | [4.724, 5.647] vs [2.363, 3.463] | **0.000 (0.0%)** |
| natl vs so (Marsh) | [3.136, 4.214] vs [2.363, 3.463] | 0.327 (17.7%) |

Within-AOI scatter in `ln Ω` is `sd = 0.051` (eqpac), `0.064` (natl), `0.122` (so); the eqpac–natl
separation of basin means is `0.367` in `ln Ω`, i.e. **~6–7 within-AOI standard deviations**. The
regression sees two (or three) tight, widely-separated clumps.

### 3b. Exact within/between decomposition

For a pooled OLS slope with group structure, `β_pooled = w·β_within + (1−w)·β_between`, with
`w = SS_xx,within / SS_xx,total`. Computed on the exact trimmed set (identity verified to 1e-9):

**Daniels** — pooled `+0.890195` (reproduces the committed value):

| component | slope | weight | SS_xx |
|---|---|---|---|
| within-AOI | **+6.017** | **9.00%** | 0.189468 |
| between-AOI | **+0.383** | **91.00%** | 1.916592 |

`0.0900 × (+6.017) + 0.9100 × (+0.383) = +0.890195` ✓

**Marsh** — pooled `−0.470551` (reproduces the committed value):

| component | slope | weight | SS_xx |
|---|---|---|---|
| within-AOI | **+3.039** | **9.49%** | 0.375509 |
| between-AOI | **−0.838** | **90.51%** | 3.581454 |

`0.0949 × (+3.039) + 0.9051 × (−0.838) = −0.470551` ✓

**This is the mechanism.** ~90% of the pooled regression's leverage is between-AOI. Candidate (a) in
the brief — disjoint ranges, so the fit measures a between-basin offset rather than within-basin
slopes — is confirmed, quantitatively, in both sources. Candidate (c) is confirmed as the *consequence*
in the Marsh case: `β_within = +3.04` and `β_between = −0.84` have opposite signs, so the pooled
estimate inherits the between sign. That is a Simpson's paradox in the strict sense.

Candidate (b), differential variance/leverage, is real but secondary: the SO leg has the widest
within-AOI support (`sd ln Ω = 0.122`) and only 11–12 cells, and it is the only negative within-slope.
It is not the driver of the collapse — the collapse survives dropping it (§3d).

### 3c. Convex-hull test (verifiable from the committed JSONs alone, no external data)

A weighted average of within-group slopes must lie inside their range. It does not, in any artifact:

| artifact | per-AOI `n_hat` | hull | pooled | verdict |
|---|---|---|---|---|
| `..._real.json` | +6.425, +7.010 | [+6.425, +7.010] | +0.890 | **OUTSIDE** |
| `..._real_marsh.json` | +3.404, +11.096, −0.048 | [−0.048, +11.096] | −0.471 | **OUTSIDE** |
| `..._glodap_marsh.json` | +1.280, −1.404 | [−1.404, +1.280] | −1.796 | **OUTSIDE** |

This alone refutes "pooling averages the regional fits" without needing the per-point data.

A second committed-artifacts-only check bounds the Daniels between-slope. The numerator is exact from
`ratio_geomean` (`:17,33`): `ln(0.039151/0.033636) = +0.15183`. The denominator (difference of basin
mean `ln Ω`) is bracketed by the reported `omega_min`/`omega_max` (`:15–16,31–32`) as
`[0.11431, 0.59166]`. Hence `β_between ∈ [+0.257, +1.328]`. The committed pooled `+0.890` falls
**inside** that bracket; both per-AOI slopes (+6.425, +7.010) fall **outside** it. The pooled fit is
estimating the between-basin contrast, and the committed summary statistics are sufficient to show it.

### 3d. Independent corroboration already in the repo

`docs/findings/calcite_driver_scout_marsh.json` computes exactly this decomposition for correlations,
via biome fixed effects (`scripts/calcite_driver_scout.py:69–89`). For `logOmega` (`:5–31`):

- `pooled_r` = **−0.1335**
- `within_r` = **+0.1842**, CI **[+0.031, +0.354]**, `within_significant: true`

A sign flip between the pooled and within-biome correlation, already committed. The two artifacts are
**bit-identical** on the shared quantities — every per-biome `r` and the pooled `r` match
`calcite_omega_identifiability_real_marsh.json` to the last float digit, with matching cell counts
(34/33/12) — confirming they describe the same cell set. The scout's docstring
(`scripts/calcite_driver_scout.py:8–10`) says it was built in response to "the reviewer panel's own
Simpson critique". **The fix was already designed and applied to the correlation analysis; it was never
applied to the power-law exponent analysis.**

Relatedly, `docs/research_notes/2026-07-09_calcite_identifiability_map.md:260` already calls a
different calcite number "a Simpson's-paradox-like aggregation artifact", and
`docs/research_notes/2026-07-10_reproducibility_appendix.md:104–105` already notes that the Ω-band
hold-out "becomes a between-biome extrapolation when pooled". The pattern is recognised in the
project; the pooled exponent is the case that slipped through.

### 3e. The pooled estimate is unstable to basin membership

Leave-one-AOI-out on the Marsh pooled fit:

| dropped | pooled `n_hat` |
|---|---|
| eqpac | **+2.029** (sign flips) |
| natl | −0.341 |
| so | −0.726 |

vs. the full pooled `−0.471`. The pooled number is a function of *which basins are in the pool*, not of
the Ω→ratio relationship.

### 3f. The pooled CI understates uncertainty because the bootstrap ignores clustering

`symbolic_distill_probe.py:402–407` resamples points i.i.d. With ~30 points per basin, an i.i.d.
resample barely moves either basin mean, so the between-basin contrast — which carries 90% of the
leverage and has effectively **`n_groups − 2` = 0 residual degrees of freedom** for a two-group fit — is
treated as if it had ~58 degrees of freedom. Re-running with an AOI-level (cluster) bootstrap:

| source | i.i.d. CI (as committed) | width | cluster CI | width |
|---|---|---|---|---|
| Daniels | [−0.208, +1.912] | 2.120 | [+0.890, +6.041] | 5.151 (2.4×) |
| Marsh | [−1.155, +0.140] | 1.295 | [−0.761, +7.198] | 7.959 (6.1×) |

*(The Daniels cluster bootstrap has only two clusters and is degenerate — resampling `{eqpac, eqpac}`
or `{natl, natl}` removes the between term entirely, which is why its interval runs from the pooled to
the within value. It is reported as evidence of width, **not** as a usable interval, and its apparent
exclusion of zero must not be quoted as significance.)*

### 3g. The consequence: GLODAP nearly emitted a confidently wrong IDENTIFIABLE verdict

Re-applying the gate logic (`symbolic_distill_probe.py:410–416`) to the committed pooled blocks:

| artifact | significant | stable | support | rejected by |
|---|---|---|---|---|
| `..._real.json` | ✗ | ✗ | ✗ (0.254 dex) | all three |
| `..._real_marsh.json` | ✗ | ✗ | ✓ (0.378 dex) | significance + stability |
| `..._glodap_marsh.json` | **✓** | **✓** | ✗ (0.2926 dex) | **support only, by 0.0074 dex** |

The GLODAP pooled fit passed the significance and stability gates on a purely between-basin contrast.
Only the support threshold stopped it, and it missed that threshold by **0.74% of a dex** — 2.5% of the
threshold value. Had either basin spanned marginally more Ω, the pipeline would have written
`"IDENTIFIABLE: power-law exponent n=-1.80 ... significant, stable"` — a sign-inverted result relative
to the within-basin signal, stated with confidence.

Worse, the remediation string the oracle emits on a support failure is *"widen the visited Omega
range"* (`symbolic_distill_probe.py:426–427`). For a **per-AOI** fit that is correct advice. For the
**pooled** fit, the cheapest way to widen the pooled Ω span is to add more basins — which increases
`SS_xx,between` and makes the confound *worse*. The advice is inverted for the estimator it is attached
to.

## 4. Re-derivation status — read this carefully

**The per-point data is NOT committed.** Both inputs are gitignored or off-repo:

- the rain ratio comes from PANGAEA `.tab` files under `data/` (`src/darwindiff/daniels_loader.py:88–91`,
  `src/darwindiff/marsh_loader.py:48`), and `.gitignore:40` is `data/*`;
- Ω is derived from the v05 `.pt` env caches under `D:\ecco_darwin_v5\cache`
  (`src/darwindiff/held_out_obs.py:82–87`).

No committed file contains the per-cell `(Ω, ratio)` pairs. `docs/findings/v3.0_arc/obs_pic_poc_per_aoi.csv`
is Darwin model output at 1071/486 cells, not the 32/24 observation cells, and is not a substitute.

**I did re-derive, from local uncommitted inputs.** Both files happen to be present on this machine, so
I re-ran the exact pipeline. Every committed number reproduced **bit-for-bit** (agreement < 1e-9 on
`n_hat`, `n_ci_lo`, `n_ci_hi`, `r2`, `n_points`, `n_cells`, `omega_min`, `omega_max`,
`corr_logratio_logomega`, `driver_log_span`) for all six per-AOI fits and both pooled fits across the
Daniels and Marsh sources. The decomposition in §3b reconstructs the committed pooled `n_hat` to six
decimals.

So the artifacts are faithful to their inputs — the numbers are right; the *interpretation* of the
pooled block is what fails. But **this re-derivation is not reproducible from the repository alone**,
and a reader without `D:\` and the two `.tab` files cannot check §3a, §3b, §3e or §3f. §3c is
reproducible from committed JSONs alone.

## 5. What I could not verify

- **The GLODAP decomposition.** `calcite_omega_glodap_marsh.json` needs GLODAPv3 bottle data
  (`scripts/glodap_omega_calcite.py`), which is not committed and which I did not locate locally. Its
  within/between split, cluster CI, and leave-one-out behaviour **cannot be verified from committed
  artifacts**. Only the convex-hull test (§3c) and the gate re-application (§3g) — both pure arithmetic
  on the committed JSON — are established for GLODAP.
- **Whether the within-AOI exponents mean anything.** They do not, on this evidence: the committed
  per-AOI verdicts are all NON-IDENTIFIABLE, with CIs like [+1.83, +10.35] on 0.077 dex of support.
  Nothing here licenses "the exponent is ~6". The claim is only that the pooled and per-AOI numbers are
  **different estimands**, and that the pooled one is not an aggregate of the others.
- **Whether the between-basin contrast has any physical content.** With two groups it is a single
  contrast with zero residual degrees of freedom, confounded with every basin difference (temperature,
  assemblage, nutrient and iron regime). `2026-07-09_calcite_identifiability_map.md:186–199` already
  argues on independent grounds (Marañón et al. 2016) that Ω here is likely a regime proxy rather than a
  causal driver. Cannot be resolved from committed artifacts.

## 6. Comparison to the recovery grading convention

The parameter-recovery side of the project already grades around this exact failure mode. `CLAUDE.md:41–43`:
grade on the per-AOI ≥2-of-3 metric, "never the cell-weighted one", because cell-weighted counts
*straddle* — per-AOI legs landing on opposite sides of Carroll — and overstate recovery.
`tests/test_canonical_numbers.py:72–75` pins this as a test: `test_cell_weighted_overstates_the_honest_metric`.

The structural parallel is exact:

| | recovery grading | calcite Ω fit |
|---|---|---|
| aggregate statistic | cell-weighted count | pooled OLS slope |
| per-region legs | per-AOI Cal+ (eqpac/natl/sopac) | per-AOI `n_hat` |
| pathology | legs straddle Carroll; aggregate hides it | legs straddle the pooled slope (and zero) |
| direction of error | **overstates** recovery | **understates** the exponent; **inverts its sign** (Marsh, GLODAP); **overstates** significance (GLODAP) |
| convention | per-AOI is the reported metric | *currently pooled is reported alongside per-AOI* |

One asymmetry worth stating: the recovery straddle inflates a *count*, so the honest fix is to report
the stricter per-AOI number. The calcite pooling is worse than a straddle — it changes the **sign** of the
estimate and can manufacture **significance** where none of the legs has it (GLODAP §3g). The recovery
metric is optimistic; the pooled exponent is *wrong*.

**Yes, the calcite analysis should adopt the per-AOI convention.** It is the same pathology, the repo
already has the precedent, and the correct machinery (biome fixed effects) is already written and
committed in `scripts/calcite_driver_scout.py:69–89` — it was simply never wired into the power-law path.

## 7. Recommendation

**Re-report per-AOI; do not retract the artifact.** Specifically:

1. **Do not quote the pooled `n_hat` as a rain-ratio exponent** — not `+0.890`, not `−0.471`, not
   `−1.796`. It estimates a between-basin contrast. Nothing currently in `STATUS.md` or the manuscript
   quotes it, so this is a forward-looking guard, not a correction of published text. `STATUS.md:479`
   already scopes the calcite limit by *within-region* support, which is the right convention.
   *(Minor, flagged not fixed: `STATUS.md:479` says within-region support is "≤0.16 dex everywhere";
   the maximum across the committed artifacts is 0.171 dex, `calcite_omega_glodap_marsh.json:28`.)*
2. **Relabel the `pooled` block** rather than deleting it — it is a real, correctly-computed quantity.
   Rename it to something like `between_basin_contrast`, or add an explicit
   `"interpretation": "between-AOI contrast; ~90% of driver variance is between-group; NOT an
   aggregate of the per-AOI exponents"` field, plus the `weight_within` value.
3. **Add the fixed-effect fit** as the honest pooled estimate: regress `log ratio` on `log Ω` with AOI
   dummies, exactly as `calcite_driver_scout.py:69–89` already does for correlations. That yields
   `β_within` (+6.02 Daniels, +3.04 Marsh) with an AOI-cluster bootstrap CI.
4. **Fix the remediation string** for pooled fits (`symbolic_distill_probe.py:426–427`). "Widen the
   visited Omega range" is right per-AOI and inverted when pooling across basins.
5. **Guard the gate.** `distill_powerlaw` has no notion of group structure, so it will emit
   `IDENTIFIABLE` on a pure between-group contrast if the support threshold is cleared — GLODAP missed
   that by 0.0074 dex (§3g). Either pass group labels and refuse to certify a fit whose `weight_within`
   is below some floor, or restrict the identifiability verdict to per-AOI fits.
6. **Consider a canonical-numbers test.** The convex-hull check in §3c runs on the committed JSONs with
   no external data and would catch a regression in one assertion.

**The NULL verdict stands.** Both routes agree the data cannot constrain an Ω power law: per-AOI, the
support is 0.077–0.171 dex and every CI is wide; pooled, the estimate is not of the target quantity at
all. The finding here is that they agree *for different reasons*, and only the per-AOI reason is the one
the note actually claims.

---

**Reproduce.** §3c and §3g run on committed JSONs alone. §3a, §3b, §3e, §3f require the gitignored
`data/{daniels,marsh}/*.tab` plus `D:\ecco_darwin_v5\cache\*.pt`, and re-run
`scripts/calcite_omega_identifiability_real.py`'s `_pairs` + `symbolic_distill_probe.support_mask`
before decomposing by AOI.
