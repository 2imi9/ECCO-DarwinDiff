# Session evidence log — 2026-07-28

Append-only record of what was **actually run** this session, with the command or artifact that
proves each claim. Rule for this file: **no number appears here without a pointer to raw output.**
Where something is computed rather than measured, it says so. Where a prior claim is weakened, it
says that too.

Companion: [`2026-07-24_overnight_session_summary.md`](2026-07-24_overnight_session_summary.md) (prior verified index).

---

## A. ECCO-Darwin v05 on AICR (spine #163)

### A1. The published llc270 decomposition does not fit AICR — VERIFIED

`v05/llc270/code/SIZE.h` fixes the layout at compile time:

```
sNx = 30, sNy = 30, nSx = 1, nSy = 1, nPy = 1, nPx = 1053-286
```

`nPx = 1053 - 286 = 767` MPI ranks (1053 tiles of 30x30 over LLC270, 286 all-land tiles blanked).

AICR per-user QOS ceilings, read from `sacctmgr -n -P show qos format=Name,MaxTRESPU`:

| partition | max CPU | max GPU | walltime |
|---|---|---|---|
| `cpu` | 64 | none | 1 day |
| `b200-batch` | 512 | 32 | 1 day |
| `rtx-batch` | 512 | 32 | 1 day |
| `b200-devel` / `rtx-devel` | n/a | 2 | 4 h |

**767 > 512 on every partition.** Not a preference; a hard ceiling.

### A2. Re-tile to 468 ranks — BUILT, `RETILE_BUILD_OK` (job 227523)

`data.exch2` gives `dimsFacets = 270,810, 270,810, 270,270, 810,270, 810,270`. At 45x45 tiles,
45 divides both 270 (=6) and 810 (=18), so tiles = 108+108+36+108+108 = **468**, and
`Nx*Ny = (45*468)*45 = 947700 = 13 * 270^2` (checks out). 468 < 512, so **the 286-entry blanklist
can be dropped rather than regenerated** — blanking is a pure optimisation (all-land tiles skipped),
never a correctness requirement.

- Build script: `/scratch/qi_zim_neu/darwindiff_v05/retile.sh`
- Log: `/scratch/qi_zim_neu/darwindiff_v05/retile_227523.log` → `blankList removed OK`, `RETILE_BUILD_OK`
- Overlay (non-destructive): `code_aicr468/SIZE.h`, `input_aicr468/data.exch2`
- Earlier build at the published 767-rank layout also succeeded (job 227366), `mitgcmuv` 4.0 MB,
  linked `mpif90`, no undefined symbols.

**Caveat that must ship with any result from this binary:** 468 ranks is NOT Carroll's published
decomposition, and MITgcm is not bit-reproducible across decompositions (summation order changes).
For a Jacobian study taking differences across runs on a *fixed* decomposition this is defensible,
but it is not a bit-faithful reproduction of v05 and must not be described as one.

### A3. Compiler deviation — AICR has no Intel compiler

`module avail` shows only `gcc/12.5.0` + `openmpi/4.1.8` + `netcdf-fortran/4.6.2` + `hdf5/1.14.6`.
The published optfile is `linux_amd64_ifort+mpi_ice_nas`. The build used a gfortran port
(`linux_amd64_gfortran_aicr`). Second deviation from the published configuration, to be disclosed.

### A4. Two of four required input trees are NOT publicly available — VERIFIED

`v05/llc270/readme.txt` links its run inputs from NASA `/nobackup` paths. Probing
`data.nas.nasa.gov` for real file listings (counting `download="` entries, because the portal is a
single-page app that returns HTTP 200 for *any* path including nonsense ones):

| readme input | status | evidence |
|---|---|---|
| `xx*42.data` (iter42 controls) | **have** | `iter42/input/`, 34 files + `tmp/` (8 more) |
| `NOAA_MBL/*` (atmospheric pCO2) | **have** | it is `ecco_darwin_v5/input/darwin_forcing/apCO2_YYYY`, 31 files |
| `nbp19_dmenemen_public_llc270/*` | **NOT PUBLIC** | 0 files at every probed path |
| `era_xx` / `era_xx_it42_v2` | **NOT PUBLIC** | only on `ecco.jpl.nasa.gov`, unreachable (A5) |

Authoritative directory listing under `/ecco/llc_270/`: exactly `ecco_darwin_v4/`,
`ecco_darwin_v5/`, `grid/` (65 files), `iter42/`. No `forcing/`, no `era_xx/`, no `llc270_FWD/`.

Real download confirmed working: range request on `iter42/input/tile001.mitgrid` returned
**HTTP 206, `application/octet-stream`**, no auth.

**This revises a prior "verified" decision.** The 2026-07-25 handoff recorded "inputs PUBLIC (HTTP
200, no auth)". That check used directory URLs against a SPA that 200s on anything, so it was not
evidence. The conclusion happens to hold for the two trees we do have (confirmed by real byte
fetches); it does **not** hold for the forcing. Self-running v05 is possible on **compute** and
currently blocked on **data**.

Staged so far: **49 GB, 140 files, 0 failures, 0 zero-byte files** at
`/scratch/qi_zim_neu/darwindiff_v05/inputs` (`iter42` 38 G, `ecco_darwin_v5` 12 G, `grid` 445 M).

### A5. `ecco.jpl.nasa.gov` is not serving — 4 independent vantage points

| vantage | result |
|---|---|
| Explorer (via Squid 10.99.0.130:3128) | `ERR_CONNECT_FAIL 111` |
| AICR (no proxy vars, direct) | `connect to 207.151.96.112 port 443 failed: Connection refused` |
| local workstation | inconclusive — own proxy on `localhost:15236` |
| Anthropic WebFetch | `Socket is closed` |

DNS resolves (207.151.96.112). Direct TCP to :443 is **refused**, not timed out, so the host is not
listening rather than filtering. Context: an ecco-support thread from **February 2026** still
directs users to ECCO Drive as the complete source, which points at an outage or an in-progress
migration rather than a completed retirement. NASA is consolidating Earth science data into
Earthdata through end of 2026.

---

## B. Recovery-metric audit — how the accuracy number is actually computed

### B1. The pipeline, read from source

1. `env [C,H,W]` → `DINN` (stack of **1x1 convolutions**, ~438 weights, no spatial coupling)
   → `[6,H,W]` unbounded. `networks.py:119`.
2. `bounded_params`: `p = lo + (hi-lo)*sigmoid(theta)` into the `PARAMS` registry ranges.
   `carroll6.py`.
3. per-cell params → differentiable box model → tracer fields → loss vs observations.
4. **per-AOI collapse = arithmetic mean over ocean cells.**
   `run_v3.0_joint_multi_aoi.py:2006` (`per_cell_sum / n_ocean_f`).
5. `rel = |mean - carroll| / |carroll|`, banded 5 / 40 / 80 % (`diagnostics.py:46-77`).
6. "Recovered" = Cal-grade or better = **rel <= 0.40**.
7. per-AOI >=2-of-3 = at least two of {eqpac, natlsubpolar, southernoceanpac}.
   `grade_joint_percell.py:50`.

### B2. Chance rates — COMPUTED (not measured); the empirical control is task #3

Fraction of the initialization distribution (`theta ~ N(0,1)` through the sigmoid into each
parameter's bounds) that already scores Cal-grade, i.e. **before any training**. 200k samples,
seed 0. This is arithmetic on the registry bounds + the 0.40 band, so it is exact given those
inputs; it is *not* a measurement of the trained pipeline.

| param | bounds | Carroll | pass band | % of range | chance Cal-grade |
|---|---|---|---|---|---|
| alpfe | 0.05–1.0 | 0.92831 | [0.557, 1.0] | 46.6 % | **44.8 %** |
| scav_rat | 3e-8–3e-6 | 6.025e-7 | [3.62e-7, 8.44e-7] | 16.2 % | 14.6 % |
| Smallgrow | 0.10–2.0 | 0.66098 | [0.397, 0.925] | 27.8 % | 35.1 % |
| Biggrow | 0.10–2.0 | 0.43148 | [0.259, 0.604] | 18.2 % | 14.6 % |
| diatomgraz | 0.05–1.0 | 0.83003 | [0.498, 1.0] | 52.8 % | **54.6 %** |
| R_PICPOC | 0.005–1.5 | 0.04245 | [0.0255, 0.0594] | 2.3 % | **0.1 %** |

`diatomgraz`'s range midpoint is 0.525, rel offset **0.367**, which is *inside* the 0.40 band. An
untrained network sitting near theta=0 scores `diatomgraz` as recovered.

### B3. Reported counts re-read as effect sizes

Binomial `P(>= observed | chance)`:

| result | n | chance | P | verdict |
|---|---|---|---|---|
| scav_rat 41/50 (4000 ep) | 50 | 14.6 % | 3e-26 | decisive |
| alpfe 49/50 | 50 | 44.8 % | 2e-16 | decisive |
| Smallgrow natl 9/10 seasonal | 10 | 35.1 % | 0.0006 | real |
| **diatomgraz 35/50** | 50 | 54.6 % | **0.019** | **marginal** |
| diatomgraz eqpac time-mean 8/10 | 10 | 54.6 % | 0.095 | not significant |
| **Biggrow 0/7** | 7 | 14.6 % | 0.33 (of <=0) | **uninformative** |

Two corrections to the record:

- **"Biggrow is a genuine null" is not supported by 0/7.** Under chance you expect ~1 of 7, and
  P(0 of 7) = 0.33. The support for `Biggrow` being unobservable is *mechanistic* (total NPP gives
  only the biomass-weighted mean, Spitz 1998), not this count.
- **`diatomgraz` 35/50 is the one number this audit dents.** 70 % against a 54.6 % baseline.

Unaffected: the per-cell vs global-scalar ablation (both arms share bounds, metric and loss; trio
joint chance ~6e-5, so global-scalar 0/50 is exactly chance and per-cell 25/50 is far above it),
and the `R_PICPOC` anchor-off contrast (same metric both sides).

**Independent cross-check that the chance calculation is sound:** the seasonal doc's own
within-experiment control has `Smallgrow` time-mean at **5/10**; the computed chance rate is 35.1 %,
which predicts P(>=5) = 0.25. The measured control sits right at the predicted chance level.

### B4. Provenance correction — those rows are three different experiments

`grade_joint_percell.py:12` is `TRIO = ["alpfe", "scav_rat", "R_PICPOC"]`; the n=50 flagship grades
**three** parameters only. `Biggrow 0/7` is from the **synthetic** `silicate_scope` sweep;
`Smallgrow natl 9/10` is the n=10 seasonal prototype (single AOI, Chl-only, simplified trainer);
`diatomgraz 35/50` is job 190529. Putting one chance column beside counts from different n,
different AOI scope, and in one case synthetic data was an error in presentation.

### B5. Second summary-statistic concern — NOT yet tested

`scav_rat` is collapsed per AOI by an **arithmetic** mean over a parameter spanning two decades,
where a geometric mean or median is the natural summary. Arithmetic mean is dominated by the
largest-valued cells. Flagged because EKI independently reports `scav_rat` biased *low* while this
summary would bias *high*.

---

## C. A real parameterisation bug in `bounded_params`

### C1. The finding — COMPUTED

`bounded_params` interpolates **linearly** between `(lo, hi)`. For `scav_rat` that range spans 100x:

| | linear (current) | log (proposed) |
|---|---|---|
| median start | 1.517e-6 (**2.52x Carroll**) | 3.010e-7 (0.50x Carroll) |
| P(start below Carroll) | **7.5 %** | 73.3 % |
| chance Cal-grade | 14.6 % | 26.9 % |

Lower decade (3e-8..3e-7) occupies **9.1 %** of the linear range; upper decade **90.9 %**. So nearly
every seed starts well above Carroll with almost no resolution on the way down. This is a plausible
contributor to `scav_rat` being the binding leg, and it fits the otherwise-odd pattern that the
prior is biased high while EKI finds the recovered value biased low.

### C2. Implementation — landed locally, synced, guards verified

- `Param.scale` field (`"linear"` default, `scav_rat` declared `"log"`), **metadata only**.
- `N_PARAMS = len(PARAMS)`, `PARAM_LOG_MASK`, `log_mask_from_names()`.
- `bounded_params(..., log_mask=None)` — geometric interpolation where masked.
- Runner env var `PARAM_LOG_SCALE` (comma-separated names), default empty.

Verified locally and again on AICR after sync:

- **default path bit-identical** to the original formula (`torch.equal` → True) — so every prior run
  reproduces;
- log mask changes **only** `scav_rat`;
- at theta=0 the log map returns exactly the geometric mean of the bounds;
- at theta=0 `scav_rat` rel offset is **0.502**, still *outside* the 0.40 Cal band, so the change
  does **not** hand the metric a free recovery;
- length guard and unknown-name guard both raise;
- existing suite: `tests/test_param_registry.py`, `test_carroll6_5pft.py`,
  `test_carroll6_carbonate.py` → **34 passed**.

### C2b. The skew is now MEASURED, and it is worse than predicted

The prior control (§G) doubles as an empirical test of C1, because untrained networks show exactly
where the optimiser starts. From the real n=50 untrained run:

| quantity | predicted (C1, from bounds) | **measured (job 227777)** |
|---|---|---|
| `scav_rat` median start | 2.52x Carroll | **2.46x Carroll** |
| fraction of seeds starting BELOW Carroll | 7.5 % | **0.0 %** |

The median prediction lands within 2.5 %. The tail prediction was conservative: **not one of 50 seeds
starts below Carroll.** Under the linear map the optimiser is always approaching the target from
above, through the compressed 9.1 % of the range, on every seed.

For contrast, `diatomgraz` starts at 0.63x Carroll with 100 % of seeds below it, and `alpfe` at
0.54x with 100 % below — both approach from the other side, and both recover.

### C2a-bis. A confound the same data rules out — skew alone is NOT sufficient

`R_PICPOC` has a **worse** parameterisation skew than `scav_rat` and recovers perfectly:

| param | bound span | linear midpoint | measured untrained start | recovery |
|---|---|---|---|---|
| scav_rat | 100x | 2.51x Carroll | 2.46x Carroll | 25/50 |
| **R_PICPOC** | **300x** | **17.7x Carroll** | **~17x Carroll** | **50/50** |

So "wide bounds mapped linearly" cannot by itself explain a recovery failure, and the log-map
hypothesis must not be stated as though it does. The distinguishing feature is what pulls the
parameter back: `R_PICPOC` has a real **absolute** anchor (Daniels calcite) that fixes its magnitude
outright, while `scav_rat` has none — at steady state iron concentration constrains only the
source/loss **ratio** (alpfe/scav_rat), not either term alone.

**Sharpened hypothesis for the A/B:** the linear map should hurt most for a parameter with **no
absolute anchor**, because there the optimiser must find the magnitude from a ratio constraint alone,
and the linear map gives it almost no resolution on the approach. That is `scav_rat` and only
`scav_rat` among the four. If the A/B shows no effect, this whole line is dead and gets recorded as
dead.

### C2a-ter. AGAINST my own hypothesis — the local geometry at the optimum does NOT favour log

Recorded **before** the A/B result, so it cannot be retrofitted. Evaluating each map at the theta
that lands exactly on Carroll:

| map | theta* | dp/dtheta | Δtheta for +10 % | relative resolution per 0.1 theta |
|---|---|---|---|---|
| linear | −1.432 | 4.62e-7 | 0.130 | **7.7 %** |
| log | +0.625 | 6.30e-7 | 0.096 | 10.5 % |

**At the optimum the LINEAR map gives finer relative resolution, not coarser.** Carroll sits at
sigmoid ≈ 0.19 under the linear map, which is a perfectly reachable, well-conditioned place to be.
Adam is also approximately scale-invariant per parameter, so raw gradient magnitude matters less
than the naive argument assumed.

So the linear penalty, if it exists at all, is confined to (a) the **starting position** — measured,
0 of 50 seeds start below Carroll — and (b) the compressed bottom decade, which needs theta < −2.2.
It is **not** a local-conditioning problem at the target.

This is a materially weaker mechanism than "the optimiser has no resolution on the way down", which
is how I first framed it. The honest statement is: *the prior is demonstrably skewed; whether that
skew is what costs recovery is exactly what the A/B tests, and the local-geometry argument runs
against it.* If `logsr` does not beat `ctrl`, that is the expected outcome under this analysis and
will be reported as a negative result, not explained away.

### C2c. Noise / independence check — the n really is 50

50 seeds, **50 distinct recovered values for every parameter and every per-AOI leg**, seed CV
0.08–0.14. No hidden duplication, so the binomial P values in §G2 are not overstating the effective
sample size. The per-AOI legs also vary independently, so the >=2-of-3 rule is doing real work.

### C3. The A/B — RUNNING, result not yet in

`logscale_ab.sbatch`, 10 array tasks, n=50 per arm, epoch-matched to the flagship (2000 ep),
identical BASE, one variable changed. Tasks 0-4 `ctrl` (linear), 5-9 `logsr` (log).
Output `/scratch/qi_zim_neu/logscale/{ctrl,logsr}_n50`.

**Pre-registered falsification condition:** `ctrl` must reproduce `scav_rat` ~25/50 per-AOI. If it
does not, the comparison is void and will be reported as void.

### C3-RESULT. Control arm COMPLETE — and it REPRODUCES the published flagship

`ctrl_n50`, n=50, `verify_run` **exit 0 VERIFIED & COMPLETE**. Graded per-AOI ≥2-of-3 against the
measured untrained baseline:

| param | **this re-run** | published flagship | measured chance | P |
|---|---|---|---|---|
| alpfe | **49/50** | 49/50 | 0.200 | 2.3e-33 decisive |
| **scav_rat** | **26/50** | **25/50** | ≤0.06 | 5.0e-19 decisive |
| R_PICPOC | **50/50** | 50/50 | ≤0.06 | 8.1e-62 decisive |
| Smallgrow | 7/50 | — | 0.120 | 0.39 not above chance |
| Biggrow | 6/50 | — | ≤0.06 | 0.078 not above chance |
| diatomgraz | 2/50 | — | 0.640 | 1.00 **far BELOW chance** |

**The pre-registered falsification condition is SATISFIED** — the control reproduces `scav_rat` at
26/50 against the published 25/50, one seed apart. So the A/B is valid and the `logsr` arm can be
interpreted when it lands. This is also an **independent reproduction of the flagship** on a
different machine, compiler and torch build, which is a reproducibility result in its own right.

Incidental but notable: under this config (`MLD_CHANNEL=0`, `POSI_W=1`) `diatomgraz` lands at 2/50,
**far below** its 0.64 untrained rate. Training actively moves it *away* from Carroll here. That is
consistent with the established finding that `diatomgraz` needs the MLD channel, and it is further
evidence that its recovery counts are dominated by where the prior sits rather than by constraint.

### C3b. A statistical flaw in my own grader, found and fixed

The first grading run reported `Biggrow` 6/50 as **"decisive, P=1.6e-17"**. That was wrong. The
measured baseline for `Biggrow` is 0/50, and the grader used a literal `p = 0.000`, against which any
nonzero count is infinitely significant.

Fixed with the **rule of three**: 0 events in N trials gives a 95 % upper bound of 3/N on the true
rate, so zero-count baselines now floor at 3/50 = 0.06 and the applied floor is printed in the
header. Re-graded, `Biggrow` 6/50 is **P = 0.078, not above chance** — the honest answer. Counts that
were genuinely large are unaffected (`scav_rat` 26/50 is still P = 5e-19 at the floor).

### C3a. The two arms have DIFFERENT baselines — now measured (job 227876, n=50 each)

| arm | untrained `scav_rat` median | % starting below Carroll | % starting IN the Cal band | **measured chance** |
|---|---|---|---|---|
| `ctrl` (linear) | 1.481e-6 = **2.46x** Carroll | 0.0 % | 0.0 % | **0/50** |
| `logsr` (log) | 2.921e-7 = **0.48x** Carroll | 100.0 % | 18.0 % | **8/50 = 16 %** |

**The log map hands `scav_rat` a 16 % free recovery rate before any training.** So the arms cannot be
compared as raw counts. A `logsr` result of, say, 30/50 is 60 % against a 16 % baseline, while a
`ctrl` result of 25/50 is 50 % against a **0 %** baseline — the latter is the larger effect.

**Correction to something asserted earlier in this session.** I wrote that the log map "does not hand
the metric a free recovery" because at theta = 0 it sits at rel 0.502, outside the 0.40 band. That is
true at theta exactly 0 and **too strong** once initialisation spread is included: 18 % of untrained
seeds land inside the band. The test docstring in `tests/test_param_registry_wiring.py` has been
corrected to say so.

**Consequence for how the A/B gets reported:** the headline must be the excess over each arm's own
measured baseline, not the raw tally, and if `logsr`'s entire advantage is explained by its starting
position then the log map is a *metric artifact* rather than an identifiability improvement. That
possibility is now explicitly on the table and will be reported if the numbers show it.

---

### C4. LOG-SCALE A/B — FINAL RESULT. Directional, never significant, and it costs `R_PICPOC`.

Both arms n=50, `verify_run` **exit 0** on each. Control reproduced the flagship (§C3-RESULT), so
the comparison is valid.

| param | `ctrl` (linear) | `logsr` (log) | Fisher exact |
|---|---|---|---|
| **scav_rat** | 26/50 | **35/50** | **p = 0.100** |
| alpfe | 49/50 | 50/50 | p = 1.000 |
| **R_PICPOC** | 50/50 | **45/50** | **p = 0.056** |
| trio joint (per-AOI) | 25/50 | 31/50 | p = 0.314 |
| Biggrow | 6/50 | 3/50 | p = 0.487 |
| Smallgrow | 7/50 | 8/50 | p = 1.000 |

**The gain is NOT the free head start.** Per-seed attribution over matched seeds 0–49:

- Of the 8 `logsr` seeds that started **inside** the band, only 5 ended recovered — 3 were pushed
  **out** by training.
- P(recover | started in) = **0.62** vs P(recover | started out) = **0.71**. Starting inside is, if
  anything, slightly *worse*. Association Fisher **p = 0.683**, i.e. none.
- Restricting to **earned** recoveries (started outside the band, ended inside):
  `ctrl` **26/50 = 0.52** vs `logsr` **30/42 = 0.71**, Fisher **p = 0.086**.

So the effect survives full baseline correction and is not a metric artifact. It is simply
**underpowered**: every angle lands at p ≈ 0.086–0.100 and none crosses 0.05.

**Verdict: NOT established.** The log map is directionally better for `scav_rat` (+9 seeds, and +0.19
on the earned rate) and borderline worse for `R_PICPOC` (−5 seeds, p = 0.056). The trio joint rises
25→31 but at p = 0.31. Recommendation: **do not adopt, do not discard** — this needs a larger n, and
if adopted it must be `scav_rat`-only so `R_PICPOC` is not put at risk. The C2a-ter analysis
(recorded *before* the result) predicted exactly this ambiguity, since the local geometry at the
optimum does not favour the log map.

---

### H6. GROWTH PAIR — FINAL RESULT at n=50. P2 confirmed cleanly, P1 directional only.

`chl2w8.0` n=50, `verify_run` **exit 0**. Control = `ctrl_n50` (config-identical, n=50).

| prediction | param | W=0 | W=8 | Fisher exact | verdict |
|---|---|---|---|---|---|
| **P1** | Biggrow | 6/50 = 0.12 | **12/50 = 0.24** | p = 0.192 | directional only |
| **P2** | Smallgrow | 7/50 = 0.14 | 6/50 = 0.12 | **p = 1.000** | **CONFIRMED** |
| **P3** | alpfe | 49/50 | 50/50 | p = 1.000 | no damage |
| **P3** | R_PICPOC | 50/50 | 50/50 | identical | no damage |
| — | scav_rat | 26/50 | 23/50 | p = 0.689 | unaffected |

**The discriminating prediction held.** `Smallgrow` is perfectly flat (p = 1.000) across a ladder
that doubles `Biggrow`. The Fisher-information analysis (H3) predicted this asymmetry from the
per-field decomposition — `Biggrow`'s signal concentrated in Chl2, `Smallgrow`'s diffuse and routed
through FeT — and it is the strongest evidence that H3's interpretation is right.

**But P1 itself is not significant.** `Biggrow` doubles, and it crosses a meaningful threshold
relative to its untrained baseline — W=0 gives P = 0.078 (*not* above chance) while W=8 gives
**P = 3.1e-05** (decisively above chance) — yet the arm-to-arm test is **p = 0.192** because both
counts are small.

**What can honestly be said:** the growth pair is **not mutually degenerate** (2x2 cond 1.20, the
least degenerate of all 15 pairs) and **not signal-deleted** (`Biggrow` keeps 0.95 of its response
through z-scoring). It is **information-starved**, and adding weight to the observable the Fisher
says carries `Biggrow` moves it from indistinguishable-from-untrained to decisively-above-untrained
without touching `Smallgrow` or damaging the iron pair.

**What cannot yet be said:** that `CHL2_W_EXTRA` reliably improves `Biggrow`. That needs more n.

**STATUS is NOT to be rewritten on this.** The current claim that `Biggrow` "stays unobservable by
construction (never recovers, seasonal included)" is now in tension with 12/50 at P = 3.1e-05 against
its untrained baseline, but a 24 % recovery rate is not "recovers", and the lever's effect is
p = 0.192. The honest framing is **"information-limited, not unobservable-by-construction"**, and
that reframe should wait for confirmation.

---

## D. Extensibility audit — can the framework take more parameters?

Measured, not estimated:

- **85** hardcoded `n_outputs=6` / literal-6 sites (`grep -rn "n_outputs=6\|n_outputs = 6" --include=*.py`).
- **0** sites derive the count from the registry (`grep -rn "len(PARAMS)\|len(PARAM_NAMES)\|N_PARAMS"` → no matches before this session).
- The flagship runner hardcodes it at three network constructions (lines 1590, 1601, 1608) plus
  `torch.zeros(6)`.

So the registry was a single source of truth for parameter **values** and not for parameter
**count**. `N_PARAMS` now exists (C2); the call sites are task #4.

What is already right: `Param` is a declarative frozen dataclass with a `learned` flag,
CONTRIBUTING.md documents the add/remove procedure, the box model reads by named index
(`params[P.alpfe]`), `bounded_params` is generic over `bounds.shape[0]`, and the per-cell head is a
1x1 conv so widening the parameter axis is one integer.

---

## E. Tooling bug fixed (affects every science skill on this machine)

`.claude/skills/science_skills_common/http_client.py` — three defects:

1. bare `import fcntl` (absent on Windows);
2. `/tmp` hardcoded instead of `tempfile.gettempdir()`;
3. **the real one:** the rate limiter persists `time.monotonic()` to a lock file and compares it
   across processes. `time.monotonic()` has a per-boot epoch, so a value written before a reboot
   exceeds the current reading, `(now - last_ts)` goes negative, and the computed sleep is enormous.

Measured: stored `227759.1` vs current `175111.2` → implied sleep **52648 s = 14.6 hours**. That was
the hang. Fixed to wall clock plus a clamp to one interval. A previous session had patched the uv
*cache* rather than the source, and that patch was itself incomplete (referenced an undefined
`_tempfile_shim`).

---

## F. Literature grounding (OpenAlex, this session)

The field's standard for "is this recovery real" is **cross-validation on held-out data** and
**profile likelihood**, not a prior chance baseline.

- Schartau et al. 2017, Biogeosciences 14:1647 — the domain review. Names our two difficulties
  verbatim: imperfect models, data too sparse to constrain all parameters. Treats model complexity
  as settled by cross-validation, and has a section on time/space-dependent parameter values (the
  per-cell idea).
- Raue et al. 2009, Bioinformatics — canonical profile-likelihood structural vs practical
  identifiability.
- Gutenkunst et al. 2007, PLoS Comput Biol — sloppiness.
- Prieß et al. 2013, Ocean Modelling — surrogate-accelerated parameter identification in a 3D marine
  BGC model. Direct prior art for the DarwinDiff strategy.
- Kuhn & Fennel 2019, Ocean Modelling — evaluating ecosystem model complexity against data.

**Honest consequence:** the project's weakest flank against this community is not the chance
baseline — it is that held-out cross-validation, their primary tool, is structurally unavailable to
us (the held-out GEOTRACES test returns negative R² because the box has no spatial structure). That
should be stated explicitly in the manuscript rather than left implicit.

---

## A6. ANSWER to Jon's open question: the three R_PICPOC values, and which one runs

Jon (email, 2026-07-28): *"I actually notice three rain ratio values in data.darwin and data.traits,
and I'm not sure which are used."* Resolved first-hand against the cloned v05 config and the pinned
`darwin3` source (`24885b71`) on AICR.

**The three values:**

| value | where | status at runtime |
|---|---|---|
| **0.04245** | `data.darwin:53`, `&DARWIN_RANDOM_PARAMS`, `val_R_PICPOC` | **INERT** |
| **0.0418860** | `data.traits:92`, `&DARWIN_TRAITS`, entries 2 and 3 | **THIS IS WHAT RUNS** |
| **0.0** | `data.traits:92`, entries 1 and 4–7 | runs, for the non-calcifiers |

`R_PICPOC = 0.0, 2*4.188600000000000E-002, 4*0.0` — so plankton types **2 and 3 (the calcifiers)**
carry 0.0418860 and the other five carry zero.

**Why the `data.darwin` value is inert** — call order in `pkg/darwin/darwin_init_fixed.F`:

```
354:  CALL DARWIN_RANDOM_INIT(darwin_seed, myThid)
356:  #ifdef DARWIN_RANDOM_TRAITS
357:  CALL DARWIN_GENERATE_RANDOM(myThid)      <- uses val_R_PICPOC = 0.04245 to FILL the array
360:  #endif
382:  CALL DARWIN_READ_TRAITS(iUnit, oUnit1, myThid)   <- runs LAST, OVERWRITES from data.traits
```

`DARWIN_RANDOM_TRAITS` **is** defined (`code_darwin/DARWIN_OPTIONS.h:149`), so generation does run,
and then `DARWIN_READ_TRAITS` (which carries `R_PICPOC` in its namelist, `darwin_read_traits.F:74`)
overwrites it at line 382.

**Independent proof the override is live, not theoretical:** the two files **disagree**. If generation
were authoritative the loaded array would read 0.04245. It reads 0.0418860.

**Practical consequence:** editing `val_R_PICPOC` in `data.darwin` changes **nothing**. Any
perturbation experiment must edit the `R_PICPOC` array in `data.traits`. Same for `diatomgraz`
(it lives in `PALAT`) and the growth pair (`PCMAX`).

**By contrast `alpfe` and `scav_rat` are safe to edit in `data.darwin`**: they are read by
`darwin_read_params.F`, consumed in `darwin_forcing.F`, and appear in **neither**
`darwin_read_traits.F` nor `darwin_generate_random.F`. Verified by grep against the pinned source.

**A detail worth flagging to Jon:** Carroll's *published* R_PICPOC is **0.04245**, but the value v05
actually integrates is **0.0418860**, a **1.35 %** difference. It is far inside our 5 % Excellent
band so it changes no recovery verdict, but our recovery target and the model's own running value are
not the same number.

---

## G. EMPIRICAL prior control — the chance baseline, measured (jobs 227777 / 227843)

Method: `NB23_LR=0` with `NB23_N_EPOCHS=1`, so the optimizer takes one step of size zero and the
networks stay **exactly at initialization**. Everything downstream is the production pipeline — same
per-AOI arithmetic-mean collapse, same 5/40/80 bands, same per-AOI ≥2-of-3 rule, same JSON schema.
The counts it produces therefore **are** the chance rate, measured through the code that reports
results. New reusable grader: `scripts/analysis/grade_all_params.py` (all six parameters, each count
printed beside its baseline and a binomial P).

`N_EPOCHS=0` is not usable: `loss_history[-1]` would index an empty tensor. Hence lr=0 with 1 epoch.

### G1. Measured vs analytic baseline — COMPLETE at n=50 (job 227777, BASE arch)

| param | **measured (n=50)** | analytic estimate |
|---|---|---|
| alpfe | 0.200 | 0.448 |
| scav_rat | **0.000** | 0.146 |
| Smallgrow | 0.120 | 0.351 |
| Biggrow | **0.000** | 0.146 |
| **diatomgraz** | **0.640** | 0.546 |
| R_PICPOC | **0.000** | 0.001 |

The analytic estimate assumed `theta ~ N(0,1)`. Real untrained DINN outputs are far more
concentrated (small default init on the final 1x1 conv), so values cluster near the **range
midpoint**. That sharpens the picture rather than blurring it: a parameter whose midpoint falls
inside the Cal band scores near-always, one whose midpoint falls outside scores near-never. Exactly
what is measured — `diatomgraz` (midpoint rel 0.367, inside) 0.633; everything else (midpoint
outside) 0.00–0.23.

### G2. Reported counts re-tested against the MEASURED baseline

Zero-count baselines use the rule-of-three upper bound 3/30 = 0.10, so those P values are deliberately
conservative upper bounds.

| result | count | measured chance | P(>=obs) | verdict |
|---|---|---|---|---|
| alpfe | 49/50 | 0.200 | 2.3e-33 | **decisive** |
| scav_rat (2000 ep) | 25/50 | <=0.06 | 8.1e-18 | **decisive** |
| scav_rat (4000 ep) | 41/50 | <=0.06 | 1.2e-41 | **decisive** |
| R_PICPOC | 50/50 | <=0.06 | 8.1e-62 | **decisive** |
| trio joint | 25/50 | <=0.06 | 8.1e-18 | **decisive** |
| Smallgrow natl seasonal | 9/10 | 0.120 | 4.6e-08 | **decisive** |
| **R_PICPOC anchor-off** | **6/50** | <=0.06 | **0.078** | **chance-level — see below** |
| **diatomgraz** | **35/50** | **0.640** | **0.233** | **NOT above chance** |

**Net effect of this control: six results get materially stronger, one gets stronger in a way that
was not anticipated, and one does not survive.**

**The unanticipated win.** The `R_PICPOC` **anchor-off control at 6/50 is itself chance-level**
(P = 0.078). Previously 6/50 could be read as "a little residual recovery without the anchor". It is
not — it is indistinguishable from an untrained network. That makes the anchor contrast *cleaner*
than it was: **50/50 decisive vs 6/50 chance**, i.e. without a real calcite anchor the parameter is
not recovered at all. This strengthens the central `R_PICPOC` claim.

**The casualty.** `diatomgraz` at 35/50 (70 %) against a measured 64 % untrained baseline gives
P = 0.233. The "non-circular handle via Chl+MLD" result is **not distinguishable from chance** under
the per-AOI ≥2-of-3 metric. Note this does not say `diatomgraz` is unrecoverable — the separate
10/10 result under a different config is a much stronger signal (P = 0.64^10 ≈ 0.012 even against
this baseline) — it says *this particular 35/50 number cannot carry the claim it is being used for*.

### G3. The baseline artifacts are gated and the new grader is cross-validated

- `scripts/verify_run.py /scratch/qi_zim_neu/logscale/prior_ctrl_n50 --expect-seeds 50`
  → **`[VERIFIED] 50/50 seeds`, exit 0**. The artifacts are complete and every band re-derives from
  the raw values against the canonical `CARROLL_VALUES`.
- The new `grade_all_params.py` reproduces the existing trusted `grade_joint_percell.py`
  **exactly** on the trio: per-AOI `alpfe` 10/50, `scav_rat` 0/50, `R_PICPOC` 0/50, trio 0/50. The
  only differences against `verify_run`'s printout (alpfe 11, diatomgraz 33, Smallgrow 5) are the
  **cell-weighted** metric, which CLAUDE.md instructs never to headline. The new grader reports
  per-AOI, matching the metric the flagship counts use.
- **The untrained trio joint is 0/50.** So the flagship's 25/50 trio is measured against a hard zero,
  not an assumed one.

### G4. Architecture-matched baseline — CLOSED, and it is worse for `diatomgraz`

`diatomgraz`'s 35/50 came from the `dgchl` config, which sets `MLD_CHANNEL=1`, changing the network's
input width and hence its initialisation distribution. Job **227876** ran the matched control
(`MLD_CHANNEL=1`, n=50, `verify_run` exit 0).

| | `diatomgraz` untrained |
|---|---|
| BASE architecture (`MLD_CHANNEL=0`) | 32/50 = 0.64 |
| **matched architecture (`MLD_CHANNEL=1`)** | **34/50 = 0.68** |
| **reported result (`dgchl`)** | **35/50 = 0.70** |

**P(>=35 | n=50, p=0.68) = 0.447.** The reported result beats an untrained network of the same
architecture **by a single seed**. It is a coin flip.

**Verdict: the 35/50 "non-circular handle" number cannot support the claim it is being used for.**
What it measures is essentially the fraction of the `diatomgraz` prior that falls inside the ±40 %
band, which is 0.68 for this architecture.

This does **not** say `diatomgraz` is unrecoverable. The separate **10/10** result under `geo1+MLD`
is a genuinely different signal: against this same 0.68 baseline, P(10/10) = 0.68^10 = **0.021**. So
that one is significant, though at n=10 and p≈0.02 it is far weaker than the alpfe / scav_rat /
R_PICPOC results, and it should not be quoted with the same confidence.

**Why the matched baseline was necessary — measured.** Adding the MLD channel moves untrained
baselines by itself:

| param | MLD off | MLD on | Δ |
|---|---|---|---|
| alpfe | 10/50 | **16/50** | **+6** |
| diatomgraz | 32/50 | 34/50 | +2 |
| Smallgrow | 6/50 | 7/50 | +1 |
| scav_rat / Biggrow / R_PICPOC | 0/50 | 0/50 | 0 |

`alpfe`'s chance rate rises by 60 % relative purely from an architecture change with **no training**.
Any covariate-channel comparison graded against a different-architecture baseline is graded against
the wrong null. This is now a documented requirement in CONTRIBUTING.md.

---

## G5. OBSERVATIONS-ONLY run, re-graded against the measured baseline (answers Jon's directive)

Jon (2026-07-28): *"what would wrap up track 1 is dropping the ECCO-Darwin model output and just
trying to fit observations."* That configuration **already exists and has been run at n=50**
(`coord_anchors_pinnOFF`, Explorer). It had never been graded against a measured untrained baseline.
Done here, zero new compute.

**Confirmed genuinely observations-only** from the run's own metadata: `darwin_pattern_w = 0.0`,
`chl1_w_extra = 0.0`, `posi_darwin_w = 0.0`, `pinn_w = 0.0`. Live targets are all real measurements:
GEOTRACES dissolved iron (surface + subsurface), GEOTRACES bSi, Daniels calcite ratio.
`verify_run --expect-seeds 50` → **exit 0 VERIFIED & COMPLETE**.

**Architecture matched to the baseline** (both `n_input_channels=1`, `mld=False`, `aoi_id=False`,
`hidden=16`), so this is graded against the correct null.

| param | obs-only n=50 | flagship (`ctrl_n50`) | measured untrained | P(>=obs) | verdict |
|---|---|---|---|---|---|
| **alpfe** | **50/50** | 49/50 | 0.200 | 1.1e-35 | **DECISIVE** |
| **R_PICPOC** | **28/50** | 50/50 | ≤0.06 | 1.5e-21 | **DECISIVE but halved** |
| **scav_rat** | **0/50** | 26/50 | ≤0.06 | 1.00 | **GONE** |
| diatomgraz | 11/50 | 2/50 | 0.640 | 1.00 | below chance |
| Smallgrow | 0/50 | 7/50 | 0.120 | 1.00 | none |
| Biggrow | 0/50 | 6/50 | ≤0.06 | 1.00 | none |
| **trio joint** | **0/50** | **25/50** | 0/50 | — | **GONE** |

**A textbook straddle, and it is a trap.** `scav_rat` scores **40/50 cell-weighted** in this run but
**0/50 per-AOI**. Every seed lands Cal-grade in exactly one AOI (always southernoceanpac), so no
2-of-3 majority ever forms. The trio is likewise 24/50 cell-weighted against 0/50 per-AOI.
`verify_run` independently raised `RPICPOC_STRADDLE` on this directory. **Anyone quoting the
cell-weighted number would report a strong observations-only iron result that does not exist.**

**What this means for the paper.** Dropping Darwin's output costs the flagship's cleanest
quantitative result: the joint trio goes **25/50 → 0/50**. What survives is two parameters recovering
from real measurements alone, one failing outright with a diagnosable reason (`scav_rat` was leaning
on the Darwin-pattern terms, not on the iron data), and one input-limited.

**Two dependencies remain, and both must be disclosed.** The run still uses `use_darwin_ic = True`
and still takes T, S, wind, atmospheric pCO2 and its DINN input channel from Darwin fields. So
"observations-only" currently means **observations-only *targets***, not end-to-end independence.
And recovery is still graded as "inside ±40 % of Carroll's published value", so even a fully
obs-only fit remains a consistency check until the held-out real-data test (#163) works.

---

## H. Why the growth pair fails — two hypotheses tested, BOTH REFUTED

### H1. "z-scored Chl targets delete the growth-rate magnitude signal" — REFUTED

Reasoning was: growth rates act by scaling biomass; every Chl target is z-scored; a z-score is
invariant to positive scaling; therefore the signal is deleted by construction. It is also true that
absolute (`*_ABS_W`) targets exist for PIC, POC, ALK and CO2 flux but **no absolute chlorophyll or
biomass target exists anywhere in the runner**.

Measured on the real 2-layer box, 240-cell synthetic AOI, +10 % perturbation, ratio of z-scored to
raw field response:

| param | target field | z/raw | verdict |
|---|---|---|---|
| Smallgrow | P_proHL (Chl5) | 0.610 | survives |
| Biggrow | P_lge (Chl2) | 0.949 | survives |
| diatomgraz | P_diatom (Chl1) | 0.332 | most weakened, yet recovers |
| alpfe | DFe_1 | 1.303 | survives |
| scav_rat | DFe_1 | 1.012 | survives |
| R_PICPOC | PIC_1 | 2.486 | amplified |

Nothing is nulled. `Biggrow` keeps 95 % of its signal. The parameter *most* damaged by z-scoring is
`diatomgraz`, which recovers. **Hypothesis dead.** (The absence of an absolute Chl target remains
true, but it is not the explanation.)

### H2. "the growth pair is mutually degenerate" — REFUTED

Gauss-Newton Fisher in log-parameter space on the same synthetic self-twin, residual = z-scored
per-PFT Chl + FeT + POC + PIC. All 15 pairwise 2x2 condition numbers:

| pair | cond | note |
|---|---|---|
| scav_rat+diatomgraz | 38.7 | most degenerate |
| Biggrow+diatomgraz | 21.0 | |
| Smallgrow+diatomgraz | 20.6 | |
| alpfe+diatomgraz | 19.6 | |
| alpfe+scav_rat | 5.42 | the published FeMIP iron degeneracy |
| … | | |
| **Smallgrow+Biggrow** | **1.20** | **LEAST degenerate pair of all 15** |

Conditional correlation of the growth pair is **-0.088**, i.e. essentially orthogonal. They are
**not** entangled with each other. This contradicts the standard framing that the growth pair is
degenerate because "total NPP gives only the biomass-weighted mean" — under this objective each has
its own PFT target (`Smallgrow`→P_proHL/Chl5, `Biggrow`→P_lge/Chl2) and they separate cleanly.

### H3. What the data actually says the problem is — INFORMATION STARVATION

Fisher information on the diagonal, normalised to the largest:

| param | rel. Fisher info |
|---|---|
| diatomgraz | 1.000 |
| alpfe | 0.140 |
| R_PICPOC | 0.099 |
| **Biggrow** | **0.055** |
| **Smallgrow** | **0.053** |
| scav_rat | 0.026 |

The growth pair is separable but the objective barely sees it — ~20x less information than
`diatomgraz`. Per-field decomposition of where each one's signal lives:

- **`Biggrow` is clean and concentrated**: Chl2/P_lge carries 25.9 against ~2.5–3.1 from every other
  field. It has one specific, well-localised observable.
- **`Smallgrow` is diffuse and iron-dominated**: its single largest contribution is **FeT (14.4)**,
  above its own Chl5 (9.3), with Chl1 (9.9), Chl3 (8.9) and Chl4 (8.9) all comparable. So it is read
  partly *through iron*, which puts it in competition with `alpfe`/`scav_rat`.
- **Chl3 and Chl4 sensitivities are bit-identical** (8.8854 for `Smallgrow`, 2.5110 for `Biggrow`),
  and Chl5 shares the `Biggrow` value. The small PFTs are dynamically near-interchangeable in the
  box, so those channels carry redundant rather than independent information.

**Consequent prediction, not yet tested:** `Biggrow` should respond to up-weighting its own Chl2
term — the same lever `CHL1_W_EXTRA` provides for Chl1/`diatomgraz`, which does not currently exist
for Chl2. `Smallgrow` should not respond as well, because its signal is diffuse and partly routed
through the iron field.

**Scope caveat that must travel with H1–H3:** synthetic self-twin on a synthetic AOI. This
characterises the STRUCTURE of the objective, not real-data recoverability. It is a hypothesis
generator for real runs, not a recovery result.

### H4. The test this motivated — job 227851, RUNNING

New lever `CHL2_W_EXTRA` (the Chl2 analogue of the existing `CHL1_W_EXTRA`), default 0.0 so every
prior run is bitwise unchanged. Arms `{0.0, 3.0, 8.0}`, n=20 each, BASE config.

Pre-registered predictions:

- **P1** `Biggrow` recovery rises with `CHL2_W_EXTRA`.
- **P2** `Smallgrow` does **not** rise comparably (diffuse, iron-routed signal).
- **P3** the iron pair is not badly damaged at moderate weight.

**P2 is the discriminating prediction.** If both growth parameters rise, the effect is generic
up-weighting rather than the specific Chl2→`Biggrow` channel, and the Fisher interpretation in H3 is
wrong. Baseline for grading: measured untrained `Biggrow` 0/50, `Smallgrow` 6/50 (§G1), so any
consistent `Biggrow` recovery is above chance.

### H5. RESULT (n=20 per arm, both `verify_run` exit 0) — P2 confirmed, P1 directional

| `CHL2_W_EXTRA` | **Biggrow** | **Smallgrow** | alpfe | R_PICPOC |
|---|---|---|---|---|
| 0 (= `ctrl_n50`, n=50) | 6/50 = 0.12 | 7/50 = 0.14 | 49/50 | 50/50 |
| 3 (n=20) | 4/20 = 0.20 | 4/20 = 0.20 | 20/20 | 19/20 |
| 8 (n=20) | **6/20 = 0.30** | **2/20 = 0.10** | 20/20 | 20/20 |

- **P2 (discriminating) — CONFIRMED.** `Smallgrow` is flat across the ladder; W=8 vs W=0 Fisher exact
  **p = 1.000**. The effect is not generic up-weighting.
- **P1 — directional but UNDERPOWERED.** `Biggrow` rises monotonically 0.12 → 0.20 → 0.30, and at
  W=8 it clears the untrained baseline (P = 8.7e-4). But the arm-to-arm comparison that actually
  tests the lever, W=8 vs W=0, is Fisher exact **p = 0.088** — *not significant* at n=20.
- **P3 — CONFIRMED.** The iron pair is undamaged: `alpfe` 20/20 and `R_PICPOC` 19–20/20 at both
  weights.

**Two different questions, two different answers, and they must not be conflated.** "Is `Biggrow`
recovering at all at W=8?" → yes, 6/20 against a ≤0.06 untrained baseline, P = 8.7e-4. "Does
`CHL2_W_EXTRA` *improve* `Biggrow`?" → not established, p = 0.088. The n=50 confirmation of the W=8
arm (job 229691) is running to settle P1.

**Provisional significance if it holds.** STATUS currently says `Biggrow` "stays unobservable by
construction (never recovers, seasonal included)". Even the present data is uncomfortable with
"never": 6/20 at W=8 is above its untrained rate. The Fisher analysis says why — `Biggrow` is not
degenerate, it is starved, and Chl2 is where its signal lives. **Do not rewrite the STATUS claim
until the n=50 arm lands.**

---

## I. Should we feed "all the ECCO-Darwin factors" into the DINN? — NO, and here is the ordering

### I1. What is wired today

DINN input channels: **SST** (always), plus optional **AOI-ID** and optional **MLD**. Maximum three.

### I2. What the target cache already carries but does not use as a channel

`sst`, `sss`, `wind`, `mld`, `pco2_atm_field`, `co2_flux_obs`, **`darwin_lats`**, `darwin_lons`,
plus the tracer targets.

### I3. Why "add everything" is the wrong answer — already measured

STATUS records that **wind / SSS / pCO₂ / CO₂-flux carry a genuine calcite confound**: no anchor
weight rescues `R_PICPOC` under them (0/10, median pinned ~0.21 even at DANIELS_RPICPOC_W=8). MLD is
described as *mechanistically* the unique safe covariate because it carries a mixing signal rather
than a carbonate one. So adding the full factor set is **known-harmful**, not merely untested.

### I4. The ordering that follows from the physics and from H3

1. **Latitude (`darwin_lats`) — free, and the obvious next test.** Already in the cache, costs no new
   data staging, and is the cheapest available proxy for light climatology and seasonality. Growth
   rates are light-driven, and light is the one first-order driver with **no representation at all**
   in the current input set. `DINNDeep`'s own docstring already lists latitude as a natural 4th
   channel.
2. **PAR / shortwave irradiance — the actual driver, and it is ABSENT.** A grep across `src/` and the
   runner finds no PAR, irradiance, or shortwave field anywhere; the only mention is a comment in
   `closures.py`. This is the largest physically-motivated gap for the growth pair specifically.
   It would need staging from the v05 cube or the ECCO forcing.
3. **Nutrients (NO₃/PO₄/SiO₂)** — cannot enter as box state (15 tracers, no dissolved SiO₂ or NO₃),
   so they could only ever be DINN *inputs*, which is a weaker form of information.

### I5. Methodological requirement for every new channel — two gates, not one

- **Confound gate.** Each candidate must be tested against `R_PICPOC` the way MLD was. MLD passed;
  wind/SSS/pCO₂/CO₂-flux failed. Adding a channel is not free.
- **Baseline gate (new, from this session).** Adding a channel changes `n_input_channels`, which
  changes the network architecture, which changes the **untrained initialization distribution** and
  therefore the chance rate. So every covariate experiment needs its **own architecture-matched
  prior control**. This is exactly why job **227843** exists: `diatomgraz`'s 35/50 came from a
  `MLD_CHANNEL=1` config, so it cannot be graded against a `MLD_CHANNEL=0` baseline.

  Generalised: **a covariate-channel result and its chance baseline must share an architecture.**
  Any past covariate comparison that did not do this is graded against the wrong null.
