# Silicate and the observable set — re-profiling the Carroll-6 identifiability claim (2026-07-19)

**Status:** cluster runs IN FLIGHT (Explorer, job array `8479481`). This document records the
audit and the verified premise correction now; the profile table is filled in as tasks land.
Nothing here is tuned toward a preferred answer — the design is a symmetric ablation.

---

## 0. TL;DR

An adversarial review (2026-07-19) alleged an **observable-set category error**: that our
identifiability profiles were computed against **total NPP**, omitting **SiO₂**, the one tracer
that discriminates diatoms — so the `diatomgraz` FLAT verdict and the Smallgrow/Biggrow
degeneracy might be artifacts.

**The premise is wrong in its specifics and worse in its consequence.**

1. **NPP was never in the loss.** `PRIMPROD_W` is unset in the 2026-07-07 config and defaults
   to `0.0` (`scripts/run_v3.0_joint_multi_aoi.py:458`).
2. **A silica observable already was in the loss.** That config exports `POSI_W=1.0` and
   `POSI_DARWIN_W=0.5` (`scripts/slurm/run_identifiability.sbatch:12-15`) — sparse GEOTRACES
   biogenic silica *plus* dense Darwin POSi.
3. **But the `diatomgraz` FLAT verdict was never measured.** The 07-07 job array profiled
   exactly three parameters — `alpfe`, `scav_rat`, `R_PICPOC`. `diatomgraz` appears in that
   findings doc **only in the threshold legend**, as a parenthetical describing what FLAT
   *would* mean. No `rel_span` for it has ever been computed. No profile JSON artifact exists
   for any parameter (the 07-07 jobs were run without `--out`).

That unmeasured parenthetical has since been cited downstream as established fact — including
as a **go/no-go gate on H200 spend**. That, not silicate, is the falsifiable claim.

This session (a) runs the missing profiles, and (b) runs the silicate ablation the review asked
for — symmetric arms with and without the silica observables — so the before/after question is
answered by measurement rather than by argument.

---

## 1. The premise, corrected

### 1.1 What the 2026-07-07 config actually was

`scripts/slurm/run_identifiability.sbatch` lines 12-15:

```
export RPP_ENV=0 RATIO_W=2 RATIO_MAX=2.0 COCCOLITH_ONLY=0 USE_EPPLEY_T=1
export POSI_W=1.0 AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0
export CHL1_W_EXTRA=3.0 POSI_DARWIN_W=0.5 DARWIN_IC=1 JOINT_RECOVERY_MODE=aoiweighted
```

`PRIMPROD_W` never appears. Its default is `0.0`, and the NPP term is gated on
`PRIMPROD_W > 0` (`run_v3.0_joint_multi_aoi.py:1734`). The growth pair was therefore
constrained by Chl₁₋₅ z-patterns, POC/PIC/DIC/ALK, the CO₂-flux term, the PIC:POC ratio anchor,
and **biogenic silica** — not by total NPP.

**The category error as stated does not exist.** The observable-set critique in its literal
form should not be repeated.

### 1.2 What the 07-07 run measured, verified from the job logs

Read directly from `/projects/schultz/qi.zim/runs/dd-fim_82111{01,02,03}.out` on Explorer
(all three `COMPLETED`, ~52 min each on H200):

| Job | `--param` | `rel_span` | Verdict |
|---|---|---|---|
| 8211101 | `alpfe` | 0.207 | SHALLOW |
| 8211102 | `scav_rat` | 0.196 | SHALLOW |
| 8211103 | `R_PICPOC` | 46.643 | CURVED |

Three parameters. `diatomgraz`, `Smallgrow` and `Biggrow` were **not profiled**.

### 1.3 The claim that must not be published as written

`docs/findings/2026-07-07_overnight_h200_identifiability_profiles.md:13` — inside the
*threshold legend*, not the results table:

> **FLAT** `< 0.05` — structural non-identifiability … *(the diatomgraz signature)*

That parenthetical is asserted as measured fact in three downstream documents:

| Location | Text | Consequence |
|---|---|---|
| `docs/research_notes/2026-07-06_ude_phase1_implementation_brief.md:56` | "the diatomgraz flat-profile signature" | frames the distillation oracle |
| same file `:123` | "diatomgraz flat → DISTILL-FAIL" | **go/no-go gate on H200 spend** |
| `docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md:53` | "`diatomgraz` is profile-flat" | supports the identifiability-is-parameter-specific claim |

It is also in tension with a measurement we already hold. `docs/findings/posi_dense_diatomgraz.md`
reports dense POSi taking `diatomgraz` recovery from **0/10 → 10/10** (dose `POSI_DARWIN_W=0.5`),
and **20/20** in the +Eppley arm. A parameter that recovers 20/20 under a dose of one observable,
and 0/10 without it, is not plausibly *structurally* non-identifiable — it is a parameter whose
identifiability is **carried by a single observable channel**.

---

## 2. What was run this session

Same script, same AOIs, same config as 07-07, with **one lever changed** — the silica weights —
and `--out` added so a JSON artifact exists this time.

- Script: `scripts/identifiability_sloppiness.py` (unmodified)
- Driver: `scripts/slurm/run_identifiability_silicate.sbatch` (new, cluster-side)
- AOIs: `eqpac,natlsubpolar,southernoceanpac`; `--grid 11 --opt-steps 600`
- Explorer job array `8479481`

| Arm | `POSI_W` | `POSI_DARWIN_W` | Loss | Meaning |
|---|---|---|---|---|
| **si** | 1.0 | 0.5 | `full` | the 2026-07-07 config (silica observables present) |
| **nosi** | 0.0 | 0.0 | `full` | the counterfactual "before silicate" |
| **realbsi** | 1.0 | 0.5 | `realbsi` | REAL GEOTRACES bSi residual only (**n = 11 bottles**) |

Parameters profiled: `diatomgraz`, `Smallgrow`, `Biggrow` (never measured before) in both arms;
`R_PICPOC` in the si arm as a positive control; `alpfe`/`scav_rat` queued as artifact-producing
reproductions of the 07-07 numbers.

Setting `POSI_W=0` and `POSI_DARWIN_W=0` cleanly removes both silica terms — they are gated at
`run_v3.0_joint_multi_aoi.py:1713-1727` — so the arms differ in the observable set and nothing else.

### Cluster notes (for reproduction)

- Explorer QOS `gpu`: `MaxSubmitJobsPerUser=8`, `MaxJobsPerUser=4`, `gres/gpu=4`. A 13-task
  array is rejected outright; it must be split into waves.
- All 32 H200 GPUs were allocated. **The cluster venv's PyTorch is not built for CC 7.0**, so
  V100 nodes die with `cudaErrorNoKernelImageForDevice`; they must be `--exclude`d. Tasks landed
  on Tesla T4 (CC 7.5), which is slower than the 07-07 H200 baseline.
- Nothing was run on the local RTX 5090.

---

## 3. Results

*(in flight — table filled as tasks complete)*

| Param | `rel_span` **nosi** (no silica) | `rel_span` **si** (silica present) | Verdict change |
|---|---|---|---|
| `diatomgraz` | pending | pending | pending |
| `Smallgrow` | pending | pending | pending |
| `Biggrow` | pending | pending | pending |
| `R_PICPOC` | — | pending (control; 07-07 gave 46.643) | — |

---

## 4. The claim that survives regardless of how §3 falls

Independent of the profile outcome, one limitation is structural and already measurable, and it
is the honest version of the reviewer's instinct:

**The box has no dissolved silicate.** `carroll6_5pft_2layer.py:104-124` defines
`N_TRACERS_2LAYER = 15` — DFe, 5 PFTs, POC, PIC, DIC, ALK across two layers. There is no SiO₂
state. `src/darwindiff/silica.py` documents the omission as a deliberate cost decision (15→17
tracers would invalidate every `darwin_ic_cache_*.npz`).

What we call the silica observable is therefore:

1. **A steady-state diagnostic, not a tracer.** `diagnostic_bsi_steady` algebraically back-solves
   bSi from diatom biomass.
2. **Explicitly parameterised by `diatomgraz`.** bSi production includes
   `graze_diatom = g_diatom · G0_GRAZE · P_diatom`, so `diatomgraz` enters the *observation
   operator*, not only the dynamics. Some of the constraint is definitional rather than dynamical.
3. **Mostly model-circular.** The dense arm's target is Darwin's own POSi field. Our own reviewer
   panel already flagged this — M11, `docs/research_notes/2026-06-19_reviewer_panel_ultra.md:50`:
   bSi "is a steady-state diagnostic of the model's own Si budget (circular) yet drives the
   diatomgraz/SO claim."
4. **Real-data-thin.** The genuinely observational component is 11 GEOTRACES bSi bottles —
   eqpac 7, natlsubpolar 4, southernoceanpac **0** (from the 8211101 job log). The Southern
   Ocean, the basin where `diatomgraz` is contested, contributes **no real silica observation at all**.

### 4.1 How much real dissolved silicate is actually available (measured here, local CPU)

Counted this session from `D:\glodap\GLODAPv3_{Pacific,Atlantic}_Ocean.csv`, QC flag
`silicatef == 2`, `-9999` → NaN, using the runner's own AOI boxes
(`src/darwindiff/ecco_darwin_loader.py:94-123`):

| Basin | rows | QC-good silicate | ≤10 m | ≤100 m | years |
|---|---|---|---|---|---|
| Pacific | 579,004 | 470,209 | 22,204 | 90,983 | 1973-2022 |
| Atlantic | 533,563 | 352,117 | 17,472 | 70,962 | 1972-2023 |

In-AOI, QC-good, dissolved silicate:

| AOI | ≤10 m | **≤50 m** (the runner's `POSI_DEPTH_MAX`) | ≤100 m |
|---|---|---|---|
| `eqpac` | 449 | **1,267** | 2,255 |
| `natlsubpolar` | 1,884 | **4,364** | 6,759 |
| `southernoceanpac` | 442 | **1,337** | 2,188 |
| **total** | 2,775 | **6,968** | 11,202 |

**6,968 real dissolved-silicate bottles are available in-AOI at the depth cut we already use,
against the 11 bSi bottles currently in the loss — a ~630× increase in genuine observations,
and it takes the Southern Ocean from 0 to 1,337.** This is the quantitative case for the
prognostic-SiO₂ extension, and it is the strongest reason the reviewer's instinct was directionally
right even though the specific charge was wrong.

---

## 5. Work order — prognostic silicate (NOT attempted; scope decision for the user)

This is a scientific scope change, not a flag change, so it was deliberately left undone. Cost
and risk, for a decision when awake:

| Item | Where | Cost | Risk |
|---|---|---|---|
| Add SiO₂ + POSi as tracers (15 → 17) | `src/darwindiff/carroll6_5pft_2layer.py:104-124` | ~1 day | **Invalidates every `darwin_ic_cache_*.npz`**; every 2-layer result needs revalidation |
| `f_Si` co-limitation term in diatom growth | growth kernel; already scoped at `docs/research_notes/2026-06-11_darwin_utilization_audit.md` §2.2 | ~0.5 day | Changes the forward model → all prior recovery numbers become a different model's numbers |
| GLODAPv3 **bottle** loader for silicate | new; `src/darwindiff/glodap_loader.py` reads only the gridded 2016b climatology, though it already maps `"Si" → "silicate"` with a µmol/kg → mmol/m³ converter | ~0.5 day | Low — the data is verified present (§4.1) |
| Rebuild IC + target caches, revalidate | cluster | ~1 day | Medium |

**Total ≈ 3 days plus revalidation. It is a follow-on, not a precondition for Paper #1.**

---

## 6. Required documentation corrections

Independent of §3, these are wrong as written and should be fixed before Paper #1:

1. `docs/findings/2026-07-07_overnight_h200_identifiability_profiles.md:13` — remove
   "*(the diatomgraz signature)*" from the legend, or annotate it as a hypothesis with no
   measurement behind it.
2. `docs/research_notes/2026-07-06_ude_phase1_implementation_brief.md:56,:123` — the H200 spend
   gate cites an unrun result. Re-anchor to §3 of this document.
3. `docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md:53` — "`diatomgraz`
   is profile-flat" must be replaced with the measured value.
4. Any published phrasing of the form "*carries no observational signal*" should be replaced with
   the defensible statement: **`diatomgraz` is constrained only through a steady-state
   biogenic-silica diagnostic and Darwin's own POSi field, not through a prognostic silicate
   cycle or an independent silicate observation** — plus the measured POSi recovery
   (0/10 → 10/10; 20/20 under Eppley).

---

## 7. Reproduce

```bash
ssh explorer
cd /projects/schultz/qi.zim/ecco-darwindiff
sbatch -p gpu --array=4,10,2,3,8,9,12,5%4 scripts/slurm/run_identifiability_silicate.sbatch
# results: docs/findings/silicate_scope/fim_<param>_<si|nosi|realbsi>.json
# logs:    /projects/schultz/qi.zim/runs/dd-fim-si_<jobid>_<task>.out
```

Local silicate inventory (CPU only, no GPU):
`D:\glodap\GLODAPv3_{Pacific,Atlantic}_Ocean.csv`, filter `silicatef == 2`, AOI boxes from
`src/darwindiff/ecco_darwin_loader.py:94-123`.
