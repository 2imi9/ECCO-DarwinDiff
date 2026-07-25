# Session handoff — 2026-07-23 (expert-review + gap-fill session)

Context hit ~1M; starting fresh. This session ran an expert review of the identifiability findings +
a gap-fill experiment round. **Theme: rigor deflated/sharpened nearly every claim.** Read this first,
then STATUS.md and the docs linked below.

## ⏳ PENDING #1 — grade experiment A the moment it finishes (highest priority)
Job **188074** (AICR array, `/scratch/qi_zim_neu/subiron/arm{0,1,2}_subW{1,3,8}`) tests whether
up-weighting SUBSURFACE GEOTRACES iron improves **scav_rat** recovery (the corrected iron finding says
subsurface [DFe] breaks the alpfe/scav_rat degeneracy ~1400×, cond 3022→2.2). Flagship-full config, no MLD,
n=10. Grade each arm:
```
ssh aicr 'cd ~/emulator_poc && source covar_env_common.sh >/dev/null 2>&1
for a in arm0_subW1 arm1_subW3 arm2_subW8; do
  ~/dd_venv/bin/python scripts/grade_recovery.py --expect-seeds 10 \
    --params alpfe,scav_rat,diatomgraz,R_PICPOC /scratch/qi_zim_neu/subiron/$a; done'
```
**✅ GRADED 2026-07-23 (all 3 arms gate-VERIFIED):** subsurface up-weight **FAILED** — scav_rat per-AOI went
**9/10 (subW=1) → 5/10 (subW=3) → 1/10 (subW=8)**, i.e. more subsurface weight HURT recovery (over-weighting
distorts the joint fit; the Fisher conditioning gain did NOT translate to recovery). **Do not pursue
subsurface up-weighting.** BUT the surprise is the control: **the flagship-full config (default weights, NO
MLD) recovered scav_rat 9/10 per-AOI**, but the n=50 reconciliation showed that was seed luck — 26/50 (trio
25/50) remains the flagship number and scav_rat stays the binding leg. Also
reconfirmed MLD hurts scav_rat (earlier flagship+MLD was 4/10).
**→ NEW experiment for scav_rat (replaces the up-weight idea): reconcile 9/10 (n=10 AICR flagship-full) vs
25/50 (n=50 Explorer flagship geo1).** Run the flagship-full config (covar base + PINN3/POCsub3/CHL3/pattern1,
no MLD, GEOTRACES_W=1 SUB_W=1) at **n=50** and grade scav_rat. If it holds ~9/10, scav_rat is NOT the weak leg
and the trio is stronger than the paper claims (update STATUS + the accuracy matrix). If it drops to ~50%,
the n=10 9/10 was a lucky draw. This is the #1 near-term experiment. **[RESOLVED — it ran: at n=50 the
same config gives 26/50, so the n=10 9/10 was a lucky draw; see
`docs/findings/2026-07-23_subiron_scav_rat_result.md`.]**

## What CHANGED this session (do NOT repeat the old claims)
All logged in `docs/research_notes/2026-07-23_expert_review_corrections.md` + the verified checkpoint
`2026-07-23_2hr_checkpoint_verified.md` + `2026-07-23_1hr_run_summary.md`.

1. **Iron degeneracy — corrected.** It's a source/loss **RATIO S/k, not a product**. Strong degeneracy is
   **surface-only** (cond 3022, conditional +0.999, co-varying sloppy dir = the S/k ratio, confirming the
   expert's algebra). With the REAL surf+subsurface GEOTRACES it's **well-conditioned (cond 2.2)** — my
   "strong −0.77 degeneracy" was the coupling-inflated MARGINAL. scav_rat is *more* identifiable than I said.
2. **Emulator (Track 2) — no real skill.** Vs a per-cell **seasonal AR(1)** baseline with block-bootstrap
   CIs, the depth emulator's skill-vs-persistence CI straddles zero and it's *worse* than AR(1) (−0.16),
   **robust across seeds 0-3** (job 188087). PIC/POC's "win" was mechanical headroom. Retire "beats
   persistence/climatology." (Single AOI eqpac; a different AOI could differ, seed is ruled out.)
3. **Novelty — narrow.** Parameter identifiability in marine models is an established field
   (Biogeosciences bg-14-1647-2017); AD-inference + BGC OSSEs are old. Our novelty is only the *combination*
   (differentiable surrogate + Fisher geometry + observation design, for a non-differentiable GCM), stated
   "to our knowledge," not "first / first to frame as sloppiness."
4. **The Fisher is the SURROGATE's, not the GCM's** — unvalidated until an 8-run v05 perturbation ensemble.
5. **Surrogate is structurally misspecified for silica** — v05 HAS prognostic SiO₂; our box dropped it.
   BUT adding SiO₂ is a **defensibility win (retires M11 circularity + unlocks ~630× GLODAP silicate data),
   NOT a diatomgraz-identifiability fix** — the growth-grazing ridge is the real obstacle; diatomgraz stays
   non-identifiable on real data.
6. **No identifiability frontier** — 4-obs Fisher stays rank 4/4 in eqpac/natl at all anchor weights; the
   softest direction *discretely swaps* (alpfe↔R_PICPOC) with weighting, not a continuous rotation. The
   **Southern-Ocean rank-2 is now fully explained**: R_PICPOC (no Daniels) + **diatomgraz (no bSi bins)** —
   two missing anchors, not one.
7. **Growth pair {Smallgrow,Biggrow}** — "unobservable by construction" is the honest *accounting* call, but
   the precise label is **practical non-identifiability under the current design** (23-yr climatology, no
   group-resolved production). Not an absolute law.
8. **v05 traits-override (critical for any ensemble):** R_PICPOC + diatomgraz are OVERRIDDEN by `data.traits`
   — perturbing them in `data.darwin` does NOTHING (proof: files disagree, R_PICPOC 0.0419 loaded vs 0.0425
   generation). Recipe: `2026-07-23_v05_perturbation_recipe.md`. Note our R_PICPOC target should arguably be
   the loaded **0.0419**, not 0.0425.

## Current parameter-learner accuracy (verify-gated, per-AOI ≥2-of-3)
alpfe 10/10 (weight-conditional) · R_PICPOC 10/10 (anchor-imposed) · diatomgraz 10/10 with MLD (non-circular
— 35/50 per-AOI with `POSI_W=0`, via chlorophyll + MLD — but model-internal, since the Chl target is Darwin's
own output; still trades off against the trio in the full loss) · **scav_rat the weak leg (26/50 flagship;
experiment A tested the subsurface-iron fix and FAILED — see above)** · growth pair excluded. Flagship
trio {alpfe,scav_rat,R_PICPOC} = **25/50 per-AOI** (one seed below scav_rat's binding count). No single
config recovers all 4 (identifiability ≠ recoverability).

## "Solve one by one" — suggested priority for the new session
1. **scav_rat** — grade experiment A (above). If subsurface up-weight works, scav_rat is largely solved.
   **[DONE — it FAILED; the subsurface-up-weight lever is closed.]**
2. **Time-resolved seasonal fit (#85)** — NEVER been run (verified; all fits are 23-yr climatology since
   May 2026, always deferred for storage). The blocker (~1 TB monthly v05 vs old schultz cap) is likely
   removable now: AICR `/scratch` is 10 TiB. Stage monthly v05 snapshots + one 3-AOI time-resolved fit. This
   is the highest-EV lever for the fragile params (diatomgraz, growth) — but a *bet* (Spitz 1998: some
   growth/loss params stay inseparable even with the annual cycle).
3. **Surrogate→GCM validation (#163)** — the 8-run v05 perturbation ensemble (traits-override-safe recipe
   ready). Needs Jon's compute; the gate that turns everything from surrogate-conditional into a GCM claim.
4. **Silica box fix** — schedule the ~40-line 17-tracer extension (IC already in the pickup) for defensibility.
5. **Manuscript re-scoping** — apply ALL the above corrections to `docs/paper/main.tex` (LOCAL-ONLY, never
   git-track); the verified checkpoint gives the exact retreated language. HOLD for user greenlight on the
   core-claim edits.
6. **[User-requested research] FourCastNet lineage → BGC-emulator design.** Trace the neural weather/climate
   emulator literature to design our emulator well: FourCastNet (Pathak et al. 2022, arXiv:2202.11214, the
   "45000× faster, same accuracy" claim) — BACK to FNO (Li/Anandkumar 2020), AFNO (Guibas 2021), ViT
   (Dosovitskiy 2020), ERA5 (Hersbach 2020); FORWARD to SFNO (Bonev 2023), GraphCast, Pangu-Weather,
   NeuralGCM (Kochkov 2024), ACE (Ai2 climate emulator), and the ocean line Samudra/SamudrACE/OceanNet (all
   physical-only → BGC is our whitespace). Use the literature_search skills (fixed) as a workflow; write
   `docs/findings/YYYY-MM-DD_fourcastnet_lineage.md`. **CRITICAL honest caveat:** FourCastNet's headline is
   for ATMOSPHERIC weather at short lead (strong learnable dynamics + 40yr hourly ERA5); our BGC emulator at
   1-month lead just failed to beat a seasonal AR(1) baseline (§Track-2 deflation). Take architecture/geometry
   lessons (SFNO, rollout, spherical), NOT the accuracy claim — and evaluate whether our emulator's real role
   is a longer-horizon/scenario tool (ACE/NeuralGCM line) or the differentiable-surrogate-for-inversion role,
   not a 1-month forward predictor.

## Process notes (carry forward)
- **verify_run gate** every recovery number (grade_recovery.py wraps it). **Manuscript is local-only** —
  never `git add` docs/paper/. Commit only when asked (no Co-Authored-By, non-squash). Compute on AICR B200
  (`ssh aicr`, `~/dd_venv/bin/python`, repo `~/emulator_poc`, base env `source covar_env_common.sh`).
- New analysis tools this session: `scripts/identifiability_sloppiness.py --mode fisher_gn` (GN-Fisher,
  iron_block with ratio/conditional/marginal), `scripts/grade_recovery.py`, `scripts/analysis/{emulator_
  baselines_v2,observation_design,percell_crlb_map,box_silica_prototype}.py`.
- Litsearch skills regressed on Windows again (fcntl) — see `reference_litsearch_skills_windows` memory
  (patch source AND the uv cached wheel).
