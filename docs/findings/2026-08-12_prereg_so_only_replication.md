# Pre-registration: does the Southern Ocean `scav_rat` result replicate on fresh seeds?

**Written 2026-08-12 BEFORE submission, with zero JSONs on disk for either new arm.**
**Gate:** `verify_run.py` exit 0, then `scripts/analysis/pooler_audit.py` with `--legs`.

## The claim under test

`so_only` (single-AOI `southernoceanpac`, job 238079) is the project's **one established
`scav_rat` claim** and the evidence behind "regionally identifiable in the Southern Ocean". Graded
today against its own architecture-matched untrained null `prior_so_only`, both n=50:

| parameter | arithmetic | geometric | median | null (all poolers) |
|---|---|---|---|---|
| `scav_rat` | 30/50 | **49/50** | 28/50 | 0/50 |
| `alpfe` | 50/50 | 50/50 | 50/50 | 16–17/50 |
| `diatomgraz` | 50/50 | 50/50 | 50/50 | 36/50 |
| `R_PICPOC` | 0/50 | 0/50 | 0/50 | 0/50 |

`scav_rat` geometric P = 6.3e-59 against the null. Paired McNemar arithmetic-vs-geometric: 20
geometric-only vs 1 arithmetic-only, P = 2.1e-05 — note the sign, the geometric collapse is
*stronger* here, the opposite of the North Atlantic case in the flagship.

**Why it needs replication.** `so_only2` (jobs 238079/238080) is **bitwise identical to `so_only`
on all 50 seeds** — it differs only in `danielsW`/`posiW`, which are inert in a single-AOI Southern
Ocean configuration. The 2026-08-04 pooler audit states it directly: *"Anything citing 237913 and
238079/238080 as two results is citing one."* So this number has **no independent replication**,
while the 3-AOI flagship has two.

## The design

Two arms in ONE submission, seeds **50–99** (the original ran 0–49, so these are disjoint).

- **`so_rep`** — trained. The `so_only` configuration exactly:
  `AOIS=southernoceanpac`, `GEOTRACES_W=1.0`, `GEOTRACES_SUB_W=1.0`,
  `DANIELS_RPICPOC_W=0.0`, `POSI_W=0.0` (the Southern Ocean has zero Daniels and zero POSi cells;
  declaring them non-zero is what made job 237913 fail `verify_run` with exit 2),
  `DARWIN_PATTERN_W=0.0`, `POC_SUB_W=0.0`, `CHL1_W_EXTRA=0.0`, `NB23_PINN_WEIGHT=0.0`,
  `POSI_DARWIN_W=0.0`, `MLD_CHANNEL=1`, `DARWIN_IC=0`, `NB23_N_EPOCHS=2000`, `NB23_LR=5e-3`,
  `DINN_HIDDEN_DIM=16`. n=50.
- **`so_rep_prior`** — the architecture-matched untrained null, byte-identical configuration at
  `NB23_LR=0`, `NB23_N_EPOCHS=1`. n=50, same seeds. Required: no count is reportable without it.

The live loss is therefore **GEOTRACES surface and subsurface dissolved iron only**, with MLD as an
input channel and literature initial conditions.

Code is pinned: the AICR checkout was fast-forwarded to `ca72abf` (= local `main`) today, and the
forward model was shown bitwise identical across the intervening refactor in both precisions, for
values *and* gradients (`2026-08-12_the_box_refactor_is_bitwise_neutral.md`). `main` also carries
the coverage-gate fix (`_EXPECTED_ZERO_COVERAGE_AOIS`), which is what lets a zero-Daniels Southern
Ocean run reach `verify_run` exit 0 instead of exit 2.

## Decision rule, fixed now

Primary is the **geometric** collapse, per the standing rule that `scav_rat` is never quoted under
arithmetic alone. Let `k` be `scav_rat`'s geometric count out of 50 in `so_rep`.

Exact two-sided Fisher against the reference 49/50 (both n=50), computed before launch:

| k | 48 | 47 | 46 | 44 | 42 | 41 | 39 | 34 |
|---|---|---|---|---|---|---|---|---|
| P | 1.000 | 0.617 | 0.362 | 0.112 | **0.047** | 0.016 | 0.0038 | 0.0001 |

- **REPLICATES** if `k >= 43` **and** `k` clears the null at P < 0.01 (with the rule-of-three floor
  p = 0.06 if the null count is zero; `k >= 10` already gives P = 6.7e-04).
- **FAILS TO REPLICATE** if `k <= 42`, i.e. P < 0.05 against 49/50.
- No third category is needed here: unlike the flagship trio, the boundary is only a **14%**
  relative drop, so this run is genuinely powered to fail.

The **arithmetic** count is reported alongside, against its reference 30/50, where the P < 0.05
boundary is `k <= 19` **or** `k >= 40`. It is secondary and does not drive the verdict.

## Secondary reads, fixed before seeing anything

1. **`alpfe` must stay ~50/50.** It is 50/50 in the original against an untrained 16–17/50. A
   collapse means the run is broken rather than informative — this is the control that says so.
2. **`R_PICPOC` must stay 0/50.** The Southern Ocean has zero Daniels cells and there is no other
   basin to inherit from, so there is no calcite anchor at all. A non-zero `R_PICPOC` would mean
   the anchor gating is wrong, and would invalidate the run.
3. **`diatomgraz` will not be quoted.** Its untrained rate here is 36/50, so a single-basin count
   carries almost no discriminating power.
4. **Continuous accuracy, not only the count.** Report the distribution of `scav_rat`'s relative
   error (recovered / Carroll) and compare to the original by Mann–Whitney. The count is
   demonstrably blind to accuracy — a 5.14× Southern Ocean accuracy loss once showed up as 9 seeds
   — so a count that replicates while the accuracy distribution shifts must be reported as such.

## What each outcome means

**REPLICATES.** The project's one established `scav_rat` claim survives independent seeds, and
"regionally identifiable in the Southern Ocean" is on two submissions instead of one. This is the
outcome the manuscript needs and cannot currently assert.

**FAILS TO REPLICATE.** The regional claim rests on one unreplicated run, and the honest framing
becomes "two globally recovered, one regionally identifiable (`diatomgraz`, eqpac), `scav_rat`
unreplicated". That would be a material retraction of a headline, and it is exactly why the run is
worth the hours.

Either outcome is reportable, which is the test for whether an experiment should run at all.
