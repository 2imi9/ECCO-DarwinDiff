# Pre-registration: is scav_rat's Southern Ocean signal surface curvature, or depth structure?

**Written 2026-07-31 BEFORE the run, with zero JSONs on disk for either new arm.**
**Grading:** `verify_run` exit 0 (both arms) then `scripts/analysis/per_aoi_vs_null.py`.
**Parent result:** `2026-07-30_scavrat_is_locally_identifiable_in_the_southern_ocean.md`.

## The question this tests

`scav_rat` recovers **30/50** in a single-AOI `southernoceanpac` fit against an untrained 0/50
(P = 3.15e-24, `verify_run` exit 0 on both arms). The recovery is **local**: with no other basin
present there is nothing to pool from. That result names two candidate mechanisms and establishes
neither.

**H_curvature.** The gauge orbit is *nearly* flat, not flat. Scavenging carries about 79.7% of the
steady-state surface iron sink at Carroll values; biological uptake and vertical exchange carry the
rest and are **not** homogeneous of degree one in the rate. In an iron-limited HNLC region that
residual curvature is at its largest. This mechanism needs **no depth information** — it lives in
the surface budget.

**H_depth.** The subsurface term supplies a second level, and depth is exactly the axis that a
concentration-at-one-level degeneracy argument discards. On this reading the surface term alone
cannot break the gauge symmetry and the recovery is a two-level effect.

These make **opposite** predictions about a surface-only fit, so one ablation separates them.

## The design

Single AOI `southernoceanpac`, everything byte-identical to `so_only` except the two iron weights.
The subsurface iron observation enters the objective through **exactly one term**
(`run_v3.0_joint_multi_aoi.py:1787-1791`); `dfe2` appears nowhere else in the runner except its
unpacking at line 1736. So `GEOTRACES_SUB_W=0` is a clean ablation of depth, not a partial one.

| arm | `GEOTRACES_W` | `GEOTRACES_SUB_W` | live iron obs | bins |
|---|---|---|---|---|
| `so_only` (already run, **30/50**) | 1.0 | 1.0 | surface + subsurface | 27 |
| **`so_surf`** (new) | 1.0 | 0.0 | surface only | 13 |
| **`so_sub`** (new) | 0.0 | 1.0 | subsurface only | 14 |
| `prior_so_abl` (new null) | 1.0 | 0.0 | none (`NB23_LR=0`) | — |

n=50 seeds per arm, seeds shared with `so_only`. All other weights as in the corrected `OBSONLY`
config: `DANIELS_RPICPOC_W=0.0 POSI_W=0.0 DARWIN_PATTERN_W=0.0 POC_SUB_W=0.0 CHL1_W_EXTRA=0.0
NB23_PINN_WEIGHT=0.0 POSI_DARWIN_W=0.0`, plus `MLD_CHANNEL=1 DARWIN_IC=0 NB23_N_EPOCHS=2000`.

### The primary read is the head-to-head, and that is deliberate

Each ablation arm has **half the data** of `so_only` (13 or 14 bins against 27). So comparing either
arm against 30/50 confounds *which channel* with *how much data*. The two ablation arms, however,
are **matched in volume to each other** — 13 against 14 bins. The volume-matched head-to-head
`so_surf` vs `so_sub` is therefore the primary read, and the comparisons against `so_only` are
secondary and explicitly confounded.

## Decision rule, fixed now

Let `k_surf` and `k_sub` be `scav_rat`'s recovered counts out of 50, `p` the untrained rate with the
rule-of-three floor 3/50 = 0.060. An arm **recovers** if `k >= 25` **and**
`P(X >= k | n=50, p) < 0.01` — the same rule as the parent pre-registration, unchanged for symmetry.

- **CURVATURE** if `so_surf` recovers and `so_sub` does not.
- **DEPTH** if `so_sub` recovers and `so_surf` does not.
- **BOTH CHANNELS CARRY IT** if both recover. Neither level is necessary alone.
- **SYNERGY / JOINT-ONLY** if neither recovers while the parent 30/50 stands. That would say the
  two levels are individually insufficient and jointly sufficient, pointing at the *gradient*
  between them rather than either level — a third mechanism, and a more interesting one than either
  candidate above.
- **AMBIGUOUS** otherwise, and it will be reported as ambiguous rather than rounded to a story.

Head-to-head significance: two-sided Fisher exact on `k_surf` vs `k_sub`, P < 0.05.
Against the parent: McNemar exact on the per-seed indicator (seeds are shared, so the paired test is
the right one), two-sided, P < 0.05, reported with the discordant-pair counts.

### Power, stated before the result so a null cannot be over-read

At n=50 against a 30/50 reference, an unpaired Fisher test detects a drop to about **15/50** at
P < 0.01 and to roughly **18-20/50** at P < 0.05. **A drop to 25/50 is not detectable** (P ~ 0.4).
So "not significantly different from 30/50" must not be reported as "unchanged". McNemar is more
powerful but its power depends on the discordance rate, which is unknown in advance.

**Exact power curve, computed before any result exists** (the array was still `PENDING` with zero
JSONs on disk; the estimate above was written by hand and the "18-20" end of it was loose):

| `so_surf` or `so_sub` vs parent 30/50 | Fisher two-sided P | detectable? |
|---|---|---|
| 25/50 | 0.4216 | no |
| 22/50 | 0.1609 | no |
| 20/50 | 0.0713 | **no** — the hand estimate was wrong here |
| 18/50 | 0.0272 | P < 0.05 |
| 15/50 | 0.0046 | P < 0.01 |
| 12/50 | 0.0005 | P < 0.01 |

So the P < 0.05 boundary is at **18-19/50**, not 20. **The decision rule above is unchanged** — this
refines a stated approximation, it does not move a threshold. The same validation reproduced the
parent's three published P-values exactly (3.15e-24, 3.75e-24, 7.36e-08), which is the check that
the grader applies the same rule the parent was graded under.

## The falsifier, written now

If **both** ablation arms collapse **and** `alpfe` also collapses in `so_surf`, then a single iron
term is simply too data-poor to fit anything at 13-14 bins, and this experiment does **not**
separate the mechanisms — it only says "one term is not enough data". That reading is pre-registered
here so it cannot later be dressed up as evidence for H_depth. The `alpfe` control is what
distinguishes "this channel carries no scavenging information" from "this arm could not fit at all".

## Pre-registered controls

1. **`alpfe` must stay high in `so_surf`.** It is a surface dust-solubility scalar and the surface
   iron term is its natural constraint; it was 50/50 with both terms live. Collapse here means the
   arm is broken rather than informative — see the falsifier above.
2. **`alpfe` in `so_sub` is an open read, not a control.** Whether subsurface iron alone constrains
   a surface scalar is genuinely unknown, and neither outcome will be treated as a validity check.
3. **`R_PICPOC` must stay 0/50 in both arms.** Zero Daniels cells, no calcite anchor, nothing to
   inherit. Anything above chance means the anchor gating is wrong.
4. **`diatomgraz` will not be quoted.** Its untrained rate is 0.72; a single-basin count carries
   almost no discriminating power.
5. **`prior_so_abl` must reproduce `prior_so_only` bitwise.** At `NB23_LR=0` the parameters never
   move, so the null cannot depend on loss weights. If it differs, the null is not what it claims
   to be and no count in this experiment is reportable.

## Gate note

This is the first run graded by the extended inert-term check. `verify_run._TERM_CELL_KEYS` covered
nine loss terms but **not** `geotraces_w` or `geotraces_sub_w`, and the run JSON did not record
per-AOI GEOTRACES cell counts at all — so the gate could not certify the one term this entire thread
rests on. Both arms here are *defined* by which iron term is live, which made the gap worth closing
first: the runner now records `n_geo_surf_cells_per_aoi` and `n_geo_sub_cells_per_aoi`, and the gate
checks them. Older artifacts are unaffected, because a missing count key is skipped by design.
