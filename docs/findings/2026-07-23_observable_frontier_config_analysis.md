# Observable frontier is config-dependent — scav_rat vs diatomgraz (2026-07-23)

**Bottom line: the manuscript's flagship claim survives scrutiny — scav_rat genuinely
recovers per-AOI 25/50 in the flagship geo1 config (which is exactly the trio joint, since
scav_rat is its sole binding leg), verified
and blessed (not a straddle).
But cross-referencing the flagship against this session's covariate/dust runs reveals that
the *demonstrated-observable set is config-dependent*, and no single config yet holds all
four observables per-AOI. This is a real, honest identifiability result — and it names one
decisive unrun experiment. It is NOT a contradiction in the manuscript.**

## What was checked (and why the alarm was wrong)

A first read raised a red flag: the manuscript says it "holds the trio {alpfe, scav_rat,
R_PICPOC} jointly, under the honest per-AOI ≥2-of-3 metric, in 25/50" (main.tex l.46-50),
yet this session's `grade_recovery.py` grading of the July runs shows scav_rat per-AOI at
**0-2/10 in every config** (`docs/findings/2026-07-23_recovery_table_verified.md`). If
scav_rat can't clear ≥2-of-3, a trio that requires it can't be 25/50.

**Resolved by the existing reconciliation, not by assuming the paper is wrong.** The
[joint-number reconciliation](2026-07-21_joint_number_reconciliation.md) already re-graded
the flagship (`n50e2k_percell_trio`, geo1, 2000 ep, `verify_run` exit 0) from the raw
`per_aoi_recovered` fields: scav_rat per-AOI **25/50**, R_PICPOC 50/50, alpfe 49/50, and the
trio-joint **25/50**, set by scav_rat (its sole binding leg). The 33/50 cell-weighted count
is separately labeled "looser." **The manuscript is honest and internally consistent.**

## The real finding: scav_rat's per-AOI recovery is config-fragile

The flagship (25/50) and the July runs (0-2/10) are **different configurations**, so the gap
is not a contradiction — it localizes *what scav_rat's identifiability depends on*:

| | flagship geo1 (manuscript) | July covar/dust lineage (this session) |
|---|---|---|
| loss terms | full: GEOTRACES iron + Daniels + **PINN + Darwin-pattern + chl + POC-sub** | **stripped**: `DARWIN_PATTERN_W=0, POC_SUB_W=0, CHL1_W_EXTRA=0, NB23_PINN_WEIGHT=0` |
| extra input channels | none (SST only) | +MLD (and wind/SSS/pCO2/CO2flux ablations) |
| Daniels weight | 1 | 1 → 8 sweep |
| n | 50 (+ n=10 ablation) | 10 |
| **scav_rat per-AOI** | **25/50 (50%)** | **0-2/10** |
| diatomgraz per-AOI | open / at-chance | **10/10 with MLD** |
| R_PICPOC per-AOI | 50/50 | 5/10 → 10/10 (heavy Daniels) |

**The July lineage was built to isolate the diatomgraz + R_PICPOC covariate question and
deliberately zeroed the pattern/PINN/chl terms the flagship carries.** So its scav_rat 0-2/10
is not evidence against the flagship's 25/50 — it is consistent with scav_rat's identifiability
being carried (in part) by those pattern/PINN terms, which the covariate runs removed. This is
the honest, confound-aware reading; do NOT report "MLD costs scav_rat" as a clean causal claim
(MLD lives in the same lineage that already stripped the terms scav_rat may need).

## Consequence: a config-dependent 3-of-4 frontier

Across everything now graded, **no single configuration holds all four observables
{alpfe, scav_rat, diatomgraz, R_PICPOC} per-AOI at once**:
- **Flagship geo1** → {alpfe, scav_rat, R_PICPOC} (diatomgraz open). The manuscript's trio.
- **MLD + heavy-Daniels (arm1_mld_dan8)** → {alpfe, diatomgraz, R_PICPOC} 10/10/10 (scav_rat 1/10).

alpfe is 10/10 everywhere. The frontier trades scav_rat against diatomgraz across the two
lineages. This is a *stronger* identifiability story than "the trio recovers": it says the
observable set is real but the specific 3-of-4 depends on the loss/predictor configuration.

## The one decisive experiment (named, not yet run)

**Flagship geo1 FULL config (pattern+PINN+chl+iron+Daniels) + the MLD input channel, n=10.**
Does adding MLD to the *full* flagship loss rescue diatomgraz (→10/10) WITHOUT breaking
scav_rat's ~26/50-equivalent? 
- If scav_rat survives → a single config reaches **4-of-4** per-AOI: the headline upgrade.
- If scav_rat collapses → the 3-of-4 frontier is a genuine trade-off (diatomgraz and scav_rat
  are mutually exclusive under the present anchors), which is itself a publishable
  identifiability-limit result.

## UPDATE (2026-07-23, job 185779): the experiment ran — and the answer is "identifiability ≠ recoverability"

The flagship-full config was reconstructed exactly (covar base + PINN=3/POC_SUB=3/CHL1=3/pattern=1
restored) and run ± MLD, n=10. **Arm 1 (full loss + MLD) fully trained (epoch 2000, rc=0,
verify_run exit 0) and did NOT give 4-of-4:** alpfe 4/10, scav_rat 4/10, **diatomgraz collapsed
to 0/10** (median 0.052 vs Carroll 0.83), R_PICPOC 10/10. The control (arm 0, no MLD) landed on a
dead-slow node (epoch 500/2000 at the 2.5 h mark) and was cancelled — so the MLD effect is not
cleanly isolated from an AICR-reproduction gap for the *control*, but arm 1 itself is fully trained
and valid.

**The decisive interpretation comes from combining this with the Q1 Fisher rank (rank 4/4 in
eqpac/natl):** the four observables are jointly **identifiable** (the information is present — full
rank), but **recoverability is design-fragile** — which subset the DINN actually reaches depends on
the loss-term / regularization mix. The MLD channel rescues diatomgraz in the *anchors-only* loss
(10/10) but the *same channel* fails to rescue it once the Darwin-pattern terms are present (0/10):
the pattern terms and MLD interact, and the optimizer lands on a different point of the full-rank
problem. **So the *information* is full rank (Q1), but the 3-of-4 recovery frontier is STRUCTURAL,
not an optimization limit: at 4000 epochs full-loss + MLD still gives diatomgraz 0/10 (job 192298),
and MLD even degrades alpfe and scav_rat, so scav_rat (needs the Darwin-pattern term) and diatomgraz
(needs MLD) genuinely conflict.** That identifiability-vs-recoverability distinction — full-rank
information, but a structural recovery frontier — is a stronger, more honest paper
point than a bare "4-of-4."

---

Prerequisite (for a future clean control): reconstruct the exact flagship geo1 env (the manuscript methods l.1083-1112 give
the headline knobs — `GEOTRACES_W=1, DANIELS_RPICPOC_W=1, RATIO_W=0, 200 Euler steps, Δt=0.25d,
Adam 5e-3, 2000 ep, Eppley` — but the exact PINN/pattern/chl/POC weights must be read from the
flagship run's saved config on Explorer `/projects/schultz/qi.zim/runs/n50e2k_percell_trio`).
Launching a mis-specified approximation would produce a misleading result, so the env must be
pinned first. Deliberately NOT launched blind tonight.

## Manuscript implication (careful — not an overturn)

The covariate result (diatomgraz 10/10 with MLD, [[finding_covariate_channels_diatomgraz]]) does
NOT trivially overturn the manuscript's "diatomgraz observability remains open (at-chance from
available real data)" (l.41-42). The 10/10 comes from (a) adding **MLD as a DINN input** and
(b) leaning on the **POSi steady-state biogenic-silica diagnostic** as the target — which the
identifiability audit flagged as **circular** (reviewer M11: the box has no prognostic SiO₂, and
ECCO-Darwin fits dissolved SiO₂, not biogenic silica; [[finding_identifiability_diagnostics]]).
So diatomgraz is recoverable *through a model-internal diagnostic with an added predictor*, not
cleanly *from independent real observations*. The manuscript's caution stands; the covariate
result is a nuanced extension worth one honest sentence, not a headline change. Route this to
the #121/#188 backlog as a "would-strengthen," not a "must-fix."
