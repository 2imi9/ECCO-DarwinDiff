# Cross-check of Jon Lauderdale's 2026-07-28 reply against documented evidence

Produced 2026-07-29 by an 8-topic adversarially-verified audit (17 agents). Every verifier was
instructed to refute; all 8 findings were downgraded or corrected, and the corrections are
incorporated below. Companion: [`2026-07-28_session_evidence_log.md`](2026-07-28_session_evidence_log.md).


---

# DarwinDiff vs Jon Lauderdale's reply: evidence read-out
**Date: 2026-07-29 · Repo HEAD: `fe1321a` · Prepared for Lucas (Ziming Qi)**

Every number below carries its source. Claims are tagged **[DECISIVE]** (large effect against a measured or verified baseline), **[DIRECTIONAL]** (right sign, not significant), or **[UNTESTED]**. Where a prior internal cross-check overstated something, the corrected position is used.

---

## 1. What Jon asked that we can already answer

### 1.1 The three rain-ratio values, and which one runs — RESOLVED, send this first
**Source: `docs/findings/2026-07-28_session_evidence_log.md` §A6 (lines 490-536).** Resolved first-hand against the cloned v05 config and the pinned `darwin3` source (`24885b71`) on AICR.

| value | location | status at runtime |
|---|---|---|
| 0.04245 | `data.darwin:53`, `&DARWIN_RANDOM_PARAMS`, `val_R_PICPOC` | **inert** |
| 0.0418860 | `data.traits:92`, `&DARWIN_TRAITS`, entries 2 and 3 | **this is what runs** |
| 0.0 | `data.traits:92`, entries 1 and 4-7 | runs, the non-calcifiers |

The array reads `R_PICPOC = 0.0, 2*4.188600000000000E-002, 4*0.0`, so plankton types 2 and 3 (the calcifiers) carry 0.0418860 and the other five carry zero. That is the third value: it is the zero on the non-calcifiers in the same line, not a separate namelist entry.

Precedence, from `pkg/darwin/darwin_init_fixed.F`: `DARWIN_GENERATE_RANDOM` at line 357 fills the array from `val_R_PICPOC`, then `DARWIN_READ_TRAITS` runs **last** at line 382 and overwrites it. `DARWIN_RANDOM_TRAITS` is defined (`code_darwin/DARWIN_OPTIONS.h:149`), so generation does run and is then discarded. The independent proof that the override is live rather than theoretical: the two files disagree, and the loaded value is 0.0418860, not 0.04245.

Two extras worth handing him:
- **`alpfe` and `scav_rat` are safe to edit in `data.darwin`.** They are read by `darwin_read_params.F`, consumed in `darwin_forcing.F`, and appear in neither `darwin_read_traits.F` nor `darwin_generate_random.F` (verified by grep against the pinned source). `R_PICPOC`, `diatomgraz` (`PALAT`) and the growth pair (`PCMAX`) must be edited in `data.traits`.
- **Carroll's published `R_PICPOC` is 0.04245 but v05 integrates 0.0418860**, a 1.35% difference. Well inside our 5% Excellent band so it changes no recovery verdict, but our recovery target and the model's own running value are not the same number. He will probably want to know this.

**Honest caveat to include:** this is a source-precedence argument plus a file disagreement. We have no observed `STDOUT.0000` namelist echo from a real v05 run. `scripts/perturbation/verify_perturbation_loaded.sh` implements the one-command check (hard-codes `FROZEN_RPICPOC=4.188600000000000E-002` and `INERT_RPICPOC=0.04245` at lines 31-32) but has never been run against real model output.

**Worth sending: yes, lead with it.**

### 1.2 v05 has no saturation-gated dissolution at all
**Source: `docs/adr/0001-differentiable-darwin-calcite-port.md` lines 88-92**, verified against v05's own `code_darwin/darwin_plankton.F` at pinned commit `24885b71`: "v05 has NO `disscSelect` switch, constant-rate ONLY. The Omega-dependent Naviaux-2019 / Keir modes are a post-v05 darwin3 addition and do not exist in v05's code."

This is directly relevant to his dissolution point and he may not have it to hand. The version we target cannot express an Omega gate or a saturation horizon in its calcite dissolution. Our own two-layer box dissolves at a constant `R_PIC_DISSOL` over 50-1000 m (`src/darwindiff/carroll6_5pft_2layer.py:192`, applied at line 445), which matches v05's `disscSelect=0` behaviour by construction rather than by accident. **Worth sending: yes.**

### 1.3 Regional rain-ratio variation, with numbers
**Source: `docs/archive/findings/2026-06-26_rainratio_real_vs_darwin.md` Sec. 3(b).** Sarmiento 2002 Table 3 gives an equatorial-max, gyre and Southern-Ocean-min rain ratio spanning 20-30x regionally. The Darwin-independent Daniels 2018 CP:PP production ratio puts eqpac surface geomean near 0.039, about 1.6x the global 0.025. This is genuine independent support for his structural claim. **Worth sending: yes.**

**Do not send** the 0/50-vs-50/50 per-cell-versus-global contrast as support for regional variation. See §3.3.

### 1.4 The measured chance baseline (methodologically the most valuable thing we have)
**Source: `docs/findings/2026-07-28_session_evidence_log.md` §G1, job 227777, n=50, `verify_run` exit 0.** Running the real pipeline at `NB23_LR=0`, `NB23_N_EPOCHS=1` leaves the networks at initialisation and scores them through the identical grading path. Measured untrained per-AOI rates: `alpfe` 0.200, `scav_rat` 0.000, `Smallgrow` 0.120, `Biggrow` 0.000, `diatomgraz` 0.640, `R_PICPOC` 0.000. Untrained joint trio 0/50.

Two consequences he will care about:
- **`diatomgraz` scores 64% untrained.** Its counts largely track where the prior sits. The 35/50 "non-circular handle" result is P = 0.447 against an architecture-matched untrained baseline of 34/50 (`MLD_CHANNEL=1`, job 227876, §G4). It beats an untrained network by one seed.
- **Adding a DINN input channel changes the chance rate with no training at all** (`alpfe` 10/50 to 16/50 on the MLD channel alone, §G4). Any covariate comparison graded against a different-architecture baseline is graded against the wrong null.

**Worth sending: yes, briefly.** This is the kind of control a GCM person will immediately respect, and it is the reason several of our own earlier numbers got downgraded.

### 1.5 The calcite anchor contrast is cleaner than we previously said
**[DECISIVE]** `R_PICPOC` 50/50 per-AOI with the real Daniels anchor (`n50e2k_percell_trio`, STATUS.md line 299) against the epoch-matched anchor-off control at 6/50 (`n50e2k_anchor_off`, 2000 epochs). The new result: **6/50 is itself chance-level** (P = 0.078 against the rule-of-three floor, §G2). So without a real calcite anchor the parameter is not recovered at all. The contrast is 50/50 decisive versus nothing, not 50/50 versus a little.

Note for internal hygiene: quote **6/50** (2000 epochs, epoch-matched) not the 4/50 from the 1500-epoch `n50_anchor_off`. `docs/findings/2026-07-22_anchors_only_n50_verified.md` still cites 4/50 and should be corrected.

### 1.6 Particulate-versus-dissolved: his scepticism matches a retraction we never sent him
**Source: `docs/findings/2026-07-10_iron_partitioning_breaks_the_wall.md`.** We tested a particulate:dissolved iron ratio as a route to `scav_rat`, it looked like a clean win, and it did not survive adversarial verification. The observable reduces algebraically: pFe := `scav_rat*DFe*POC/W_SINK`, so pFe/DFe = `scav_rat*POC/W_SINK` and DFe cancels exactly (lines 20-23). The "~14x tighter" was a grid-and-threshold artifact. Retraction is propagated to `STATUS.md` lines 475-477 and `docs/findings/2026-07-22_iron_bottleneck_solution_map.md` lines 17-19 ("REFUTED, not a candidate. Retract it").

On his realism half we have committed counts rather than an opinion (`docs/findings/iron_coverage_count.json`, GEOTRACES IDP2025, surface <=50 m, QC {49,50}): 76 global and 4 eqpac surface samples carry both Fe_TP and Fe_D; 130 global and 0 eqpac carry Fe_TPL and Fe_D. Where both are measured the log10 span of pFe/DFe is 2.59 (Fe_TP) and 3.69 (Fe_TPL). **Caveat that must travel with the 76:** it is a strict same-station-and-same-sample-index match against 273 total surface Fe_TP samples, so it is a floor on co-location, not a count of ocean locations.

**Important:** I checked whether this retraction was ever sent to Jon. `docs/research_notes/2026-07-10_jon_decision_brief.md` self-labels internal at lines 5-6 and 13, and the most recent Jon-facing document (`docs/research_notes/2026-07-21_jon_update.md`) has zero hits for particulate / partition / pFe / Fe_TP. **This is new to him. Worth sending: yes.**

### 1.7 Sections versus isotopes: we have a formal ranking
**Source: `docs/findings/2026-07-23_observation_design.md` and `.json`.** Differentiable observation design over 8 candidate observables, ranked by iron 2x2 variance reduction along the sloppy direction: a 234Th/210Po scavenging flux 1434x (condition number 2930 to 6.9), subsurface DFe 1261x (to 2.5), subsurface scav flux 311x. Controls: bSi 15.3x, PIC 2.33x, POC 2.33x, and a second identical surface DFe survey exactly 2.00x with the condition number unchanged at 2930. Section-type observables beat any additional surface concentration by two to three orders.

His isotope scepticism matches our own independent NO-GO (`docs/findings/2026-07-22_two_anchor_redteam.md` lines 27-31): Darwin's fixed ligand freezes the scavenging-versus-colloidal-pumping split that carries the sink isotope signal, and uptake and scavenging fractionate dissolved d56Fe in the same direction. Cost is "tracer doubling + 6-7 knobs".

**Worth sending: yes, but with §3.2's correction attached.** The number-two candidate is the one that failed when actually tested.

---

## 2. Where Jon corrects or sharpens us

**2.1 The Omega null is production-side only, and he supplies the mechanism.** Every Omega test we ran was against the surface calcite **production** ratio (Daniels/Marsh CP:PP), never against dissolution or export. `src/darwindiff/closures.py` lines 35-41 confirm the learned calcite closure's drivers feed PIC production. So our robust null (`docs/research_notes/2026-07-09_calcite_identifiability_map.md` Sec. 9: swapping env source from Marsh in-situ to GLODAPv2.2016b flips N. Atlantic bloom from +0.69 to -2.27; the two Omega sources agree only at r = 0.24; point-level corr(log ratio, in-situ Omega) = 0.011) bounds one side of the calcite budget. If Omega mainly governs dissolution, our null is what his mechanism predicts rather than a data-power problem. That upgrades the finding. `STATUS.md:478` and the calcite identifiability map should say "Omega does not predict the surface calcite production ratio".

**2.2 v06 group-specific calcification closes an open item.** `docs/research_notes/2026-07-22_ecco_darwin_v06_research.md` lines 62 and 74 record that no public source documents any v06 calcite / rain-ratio / coccolithophore revision, and warn that any such claim would be unsupported. His statement that the next version more explicitly determines which plankton groups calcify closes that from the inside. It also removes the internal tension with `docs/findings/2026-07-23_v05_perturbation_recipe.md` Sec. 6.

**2.3 The growth-pair naming problem is worse in our box than in Darwin, and we had not written that down.** `src/darwindiff/carroll6_5pft.py` lines 22-40 state the "Option A" design choice explicitly: `Smallgrow` is learned on Pro-HL specifically and `Biggrow` on other large eukaryotes specifically, "instead of an average over multiple species". Lines 107-109 freeze the non-learned PFTs at Carroll's own optima. In the production two-layer box only `mu_proHL = params[I_SMALLGROW]` and `mu_lge = params[I_BIGGROW]` are learned; diatoms, Syn and Pro-LL run frozen, and Syn and Pro-LL share an identical rate. In Darwin they are GEIDER size-class scalars with a spread (`docs/ecco_darwin_parameter_inventory.md:166` lists `Smallgrow`, `Biggrow`, `Smallgrowrange`, `Biggrowrange`), living in `PCMAX` in `data.traits`. So what we recover is not the object he tuned. His framing raises a test we have never run.

**2.4 His isotope answer helps settle an internal split.** Our repo contradicts itself: the red-team says d56Fe is NO-GO, while `docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md` lists dissolved d56Fe as **[primary]** under "the observable that would break the degeneracy". Our NO-GO is literature-and-model-structure reasoned; the gating fixed-versus-dynamic-ligand OSSE has never been run. His independent scepticism is a reason to keep it shelved.

---

## 3. Where our evidence complicates his answer

Stated factually. In several places his point cuts at us too, and that is noted.

**3.1 On "the iron degeneracy is fundamental, not a model artifact": we half-agree, and our own canonical docs sit on the softer side.**

The literature half is well verified in our repo. `docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md` reads Tagliabue 2016 FeMIP Table 2 directly: 13 models, dissolved-Fe residence time 3.7 yr (COBALT) to 626.3 yr (BFM), while mean ocean DFe agrees at 0.58 +/- 0.14 nM and total input flux roams 66.9 +/- 67.1 Gmol Fe/yr, with sources "compensated by variable scavenging rates in order to reproduce the observed DFe concentration". Somes 2021 is the controlled version. In a single well-mixed box the iron Fisher matrix is rank-1 by construction (`docs/research_notes/2026-07-20_iron_degeneracy_math_validation.md` lines 16-24).

But our own measurements say the **strong** degeneracy is surface-only. `STATUS.md` lines 324-331 explicitly supersede any strong-degeneracy claim: with real surface plus subsurface GEOTRACES the pair is well-conditioned (2x2 condition 2.2), and `scav_rat`'s poor recovery is described as an optimization and coverage limit rather than a hard information wall. Per-AOI `scav_rat` profile likelihoods return CURVED at all three AOIs (`docs/findings/2026-07-23_overnight_recovery_sweep_groupA.md`, jobs 189403 and 189870), which is practical rather than structural non-identifiability. Most tellingly, at 4000 epochs on **identical data** `scav_rat` rises to 41/50 with natlsubpolar going 20/50 to 40/50 (`STATUS.md` line 298); only eqpac (6/50) stays information-limited. And `docs/findings/2026-07-22_iron_bottleneck_solution_map.md` lines 8-14 name our own 0-D box, not the ocean, as the binding blocker.

His point does cut at us, in a way we should concede plainly: `src/darwindiff/carroll6.py:286` is one aeolian source and one first-order scavenging sink, with no sediment, hydrothermal, glacial, ligand or colloid representation. Darwin's own iron cycle carries 11 tunable parameters (`docs/ecco_darwin_parameter_inventory.md:162`). Our own observation-design note (lines 147-154) already predicts that real hydrothermal and sedimentary iron at depth "would re-inject an alpfe-like source term and erode the subsurface discriminating power", and v06 adding hydrothermal-vent iron makes that concrete. **We have never run that test.**

**3.2 On sections: the top-ranked candidate failed when we actually tested it.**

`docs/findings/2026-07-23_subiron_scav_rat_result.md` is a pre-registered hypothesis that was falsified. Up-weighting subsurface GEOTRACES iron makes per-AOI `scav_rat` recovery fall: 9/10 at `GEOTRACES_SUB_W=1`, 5/10 at 3, 1/10 at 8, all three arms `verify_run` exit 0. At n=50, `subW=1` gives 26/50 and surface-only `subW=0` gives 4/10. So the ~1400x Fisher conditioning gain from subsurface DFe (condition 3022 to 2.2, job 188077) does **not** convert into recovery. The cell-weighted "improvement" 7 to 10 to 10 is a straddle artifact.

Also worth being precise with him: what we have tested is the **vertical** axis (subsurface depth bins, plus a synthetic 1-D column). The **horizontal** near-source section gradient, which is what Somes 2021 and our own `STATUS.md:375` argument actually invoke, has never been tested in our model. Those two get conflated in our own wording and a referee will catch it.

**3.3 On regional rain ratio: one of our numbers does not mean what it looks like.**

The per-cell versus global-scalar contrast (trio 25/50 versus 0/50, `R_PICPOC` 50/50 versus 0/50) is an identifiability fact about our estimator, not observational evidence that the true rain ratio varies regionally. `STATUS.md` lines 405-411 explain why: at uniform Carroll parameters the 0-D box relaxes to a near-uniform state (tracer CV ~1e-15 against Darwin's O(1)), so the surrogate gap is dimensional and identifiability has to come from real absolute anchors. Needing per-cell structure to recover a scalar is not the same as measuring regional structure. The Daniels 1.6x is the legitimate regional evidence; that one is fine to send.

**3.4 On chlorophyll for the growth pair: real but underpowered, and circular in its target.**

See §4 of this section and the reply. Two caveats belong on it. First, all our Chl targets are Darwin's own Chl1-5 output, z-scored (`scripts/run_v3.0_joint_multi_aoi.py` lines 1712-1723), so a chlorophyll result inherits exactly the circularity caveat attached to `diatomgraz`. There is no absolute chlorophyll or biomass target anywhere in the runner (confirmed by grep: `CHL_ABS` returns nothing). Second, the Fisher analysis that motivated the lever is a synthetic self-twin on a 240-cell synthetic AOI, and the real-loss per-cell CRLB map gives the opposite ordering of the pair (`docs/findings/2026-07-23_percell_crlb_map.md`).

**3.5 On the UDE: we want to do it, and we know the binding constraint.**

Transport is sound: relative global mass drift ~5e-6, bounded and non-accumulating, identical at 20k and 100k steps (`docs/findings/2026-07-21_ude_stress_result.md`, job 8524801). But the learned iron-limitation closure trained cleanly (loss down 152,000x) to 0.65% relative error on the visited DFe range and **288% on the full range**, and weight decay and anchoring did not change it in any config. "The binding constraint on UDE closure identifiability is state-space coverage, not the optimizer." Separately, the make-or-break out-of-sample transport E2 on real calcite failed: learned R2 -0.05 against a null of +0.50, replicated across 10 seeds (`docs/findings/2026-07-10_e2_powered_result.md`). We also have a symbolic-distillation identifiability oracle (`scripts/symbolic_distill_probe.py`, 677 lines, 22 tests) that quantifies "excitation cures equifinality": DISTILL-FAIL 0/2 at a visited span of 0.31 dex, DISTILL-PASS 2/2 at 1.8 dex. Applied to three real datasets (Daniels, Marsh, in-situ GLODAPv3) it returns NON-IDENTIFIABLE everywhere.

None of this argues against his UDE suggestion. It says the first thing to design is the forcing, not the network.

---

## 4. Genuine open gaps, ranked by how much they block the manuscript

| # | Gap | Blocking severity |
|---|---|---|
| 1 | **Grading is still against Carroll's published values.** Even an observations-only fit is a consistency check, not a discovery. The one held-out real-data GEOTRACES test returns negative R2 because the 0-D box homogenizes (`docs/results_matrix.md` lines 103-108). Issue #163 is OPEN. | **Blocks the central claim.** Everything else is downstream. |
| 2 | **No Darwin-free run exists.** `USE_DARWIN_IC` defaults to 1 (runner:302); T, S, wind and atmospheric pCO2 all come from the v05 target cache (runner lines 1694-1706); DINN inputs are Darwin SST and Darwin `mldDepth`. A repo-wide search finds **no** observational MLD product (no de Boyer Montegut, no Argo, no WOA). | **High.** A referee finds this in one pass. |
| 3 | **The observations-only x MLD arm has never run at n=50.** The only positive `diatomgraz` number in an obs-only config is 10/10 at n=10 (`docs/findings/2026-07-22_covariate_channels_result.md`). Against the architecture-matched 0.68 baseline that is P = 0.021: real, but far weaker than alpfe / R_PICPOC. | **High.** It is the difference between 2-of-4 and 3-of-4 in an obs-only paper. |
| 4 | **No sink-rate anchor has ever entered a fit.** Grep for `cochran`/`black2020`/`rufas2024` in `run_v3.0_joint_multi_aoi.py` returns **0**. `scav_rat` has no observations-only path at all (0/50 anchors-only, 0/10 in every covariate arm). Loaders and data are built (`docs/two_anchor_execution_plan.md` P1 DONE, P2 geometry gate passed, `\|rho\|` 0.472 to 0.061 in the real-box self-twin, job 179387) but "self-twin != real recovery (still 0/10 on real data)". | **High** for the scav_rat leg. |
| 5 | **The observations-only run has never been graded against the measured untrained baseline.** Artifacts are on disk and `verify_run`-gated; this is a grading task, not compute. | **Medium**, and cheap. |
| 6 | **No multi-source iron conditioning test.** Our ~1400x subsurface gain is measured in a box whose only subsurface iron source is remineralisation. | **Medium.** It is the experiment Jon's point most directly implies. |
| 7 | **No observed `STDOUT.0000` namelist echo** confirming the `R_PICPOC` precedence claim on a real run. | **Low** for the manuscript, but it is the one thing that would make §1.1 airtight. |
| 8 | **v05's exact `Kdissc` is unknown.** ADR 0001 line 233 records ~1/300 per day; our `R_PIC_DISSOL` default is 0.05/day, roughly 15x faster. Explicitly Jon-gated at ADR lines 305 and 405. | **Low** now, blocking for any Track-2 calcite port. |
| 9 | **`CHL2_W_EXTRA` arm-to-arm is underpowered** (p = 0.192 at n=50 per arm). Roughly 3x the seeds needed for p < 0.05. | **Low.** Affects one sentence. |
| 10 | **Nothing on the nitrogen cycle.** Grep across `docs/` finds only that denitrification is on and diazotrophy off. We cannot support or contest his extension. | **Not blocking.** Do not claim it. |

**Doc hygiene items found while verifying (fix before the manuscript):** the evidence log states the rule-of-three floor as `3/50 = 0.06` at lines 329-330 but as `3/30 = 0.10` at line 570; the tables use 0.06. `docs/findings/2026-07-22_anchors_only_n50_verified.md` cites the 1500-epoch 4/50 anchor-off control where CLAUDE.md requires the epoch-matched 6/50. Three documents still carry the retracted "(scav_rat, W_SINK) are perfectly degenerate" claim (`docs/research_notes/2026-07-09_track2_identifiability_writeup.md:179`, `docs/research_notes/2026-07-10_jon_decision_brief.md:78`, and `scripts/iron_partitioning_controls.py` docstring lines 13-15).

---

## 5. The critical path: what "drop ECCO-Darwin output, fit observations only" concretely requires

This is the most important section, so it is worked in full.

### 5.1 It is not one switch, and it has already been run once
The Darwin-output targets are spread across several levers. Turning them off means `DARWIN_PATTERN_W=0` (the entire base z-scored block of FeT, Chl1-5, POC, PIC, DIC, ALK and CO2 flux, runner lines 1712-1723), plus `POC_SUB_W=0`, plus `CHL1_W_EXTRA=0` and `CHL2_W_EXTRA=0`. A further set of Darwin-target levers (`RATIO_W`, `PIC_ABS_W`, `POC_ABS_W`, `POSI_DARWIN_W`, `PRIMPROD_W`, `F_CO2_ABS_W`) already default to 0.0.

**That configuration has been run at n=50 and is verified.** Batch `coord_anchors_pinnOFF`, Slurm 8536393, `verify_run --expect-seeds 50` exit 0 (`docs/findings/2026-07-22_anchors_only_n50_verified.md`). Real anchors on: GEOTRACES iron surface and subsurface, Daniels calcite, GEOTRACES bSi. PINN also off in that run.

### 5.2 Which observables survive

| parameter | obs-only, n=50, per-AOI | flagship (geo1) | measured untrained | verdict |
|---|---|---|---|---|
| `alpfe` | **50/50** | 49/50 | 0.200 | **[DECISIVE]** anchor-driven, survives cleanly. P = 1.1e-35 |
| `R_PICPOC` | **28/50** | 50/50 | <=0.06 | **[DECISIVE]** but degraded. P = 1.5e-21 |
| `scav_rat` | **0/50** | 25/50 (2000 ep), 41/50 (4000 ep) | 0.000 | **gone.** Pattern-driven, not anchor-driven |
| `diatomgraz` | 11/50 | 10/10 with MLD at n=10 | 0.640 | **below chance** without MLD (lower-tail P = 1.6e-09) |
| **joint trio** | **0/50** | **25/50** | 0/50 | **gone.** `scav_rat` is the sole blocker |

The `scav_rat` cell-weighted 40/50 in the obs-only arm is a **straddle** and must never be quoted: all 50 seeds land Cal+ in exactly one AOI (always southernoceanpac), so no 2-AOI majority ever forms.

Note the P-values in the first column are computed here from the two documented counts and the measured baselines. They are arithmetic on verified inputs, not themselves `verify_run`-gated, and should be labelled that way until the re-grade runs.

### 5.3 What the paper becomes
The flagship's cleanest quantitative result, the joint trio at 25/50 against an untrained 0/50, **goes to zero**. The headline changes from a joint three-parameter recovery to:

> Two parameters recover from real observations alone (`alpfe` decisively, `R_PICPOC` decisively but at roughly half the flagship rate), one fails outright (`scav_rat`, and we can say exactly why: it needs spatial structure that absolute surface anchors do not supply), and one is input-limited rather than structural (`diatomgraz`, pending the n=50 MLD arm).

That is a defensible and arguably stronger identifiability story than the current one, because every surviving number is anchored to a real measurement. But it is a **different paper**, and the choice should be made deliberately rather than discovered in revision.

### 5.4 The residual dependency he has not seen, and the deeper issue
Two things must be said plainly to him.

First, **the run is still not Darwin-free.** It keeps Darwin v05 initial conditions, Darwin forcing for T, S, wind and atmospheric pCO2, and Darwin-derived DINN input channels. "Observations only" currently means "observations-only **targets**". Replacing the forcing and inputs with observational products (satellite or WOA SST, an Argo or de Boyer Montegut MLD climatology, reanalysis wind and pCO2) is unstaged work: nothing observational is wired today.

Second, and larger: **dropping the Darwin targets closes only the training-side circularity.** Recovery is still graded as "lands inside a +/-40% band around Carroll's published value". Every count in §5.2 is that metric. The one test that would settle the consistency-versus-discovery question directly is the held-out real-data test, and it returns negative R2 in the current 0-D box (`docs/results_matrix.md` lines 103-108). The machinery exists (`GEOTRACES_HOLDOUT_FRAC` at runner line 299, `src/darwindiff/held_out_obs.py`). Issue #163 is open for exactly this.

### 5.5 Concrete cost

| step | cost | unblocks |
|---|---|---|
| Re-grade the existing obs-only n=50 run against the measured baselines with `scripts/analysis/grade_all_params.py` | **zero compute.** Artifacts on disk, `verify_run`-gated | Promotes obs-only from red-team ablation to headline. Already queued as manuscript Diff 7 in `docs/handoff_2026-07-26_session.md:60` |
| Obs-only + `MLD_CHANNEL=1` at n=50, with its architecture-matched untrained control (already measured, job 227876: `diatomgraz` 34/50 untrained) | **one array job**, ~n=50 seeds at 2000 epochs | Decides 2-of-4 versus 3-of-4. The single highest-value missing cell |
| Obs-only with `DARWIN_IC=0` at n=50, using the literature-IC path (runner lines 804-819) | **one array job** | Measures how much of surviving `alpfe`/`R_PICPOC` rests on Darwin's pickup state |
| Wire a `SINK_ANCHOR_W` term mirroring the existing `DUST_ANCHOR_W` pattern, fed by `cochran_gp15_po_pb_loader.scavenging_1deg_grid` and `black2020_fe_flux_loader.fe_export_province` | **a few days of code** plus one A/B | The only candidate route to an obs-only `scav_rat`. Red-team bound: bounding to a factor of a few, not point-identified |
| Replace Darwin forcing and DINN inputs with observational products | **weeks.** Nothing staged; no observational MLD product exists in the repo | End-to-end independence |
| Held-out real-data validation at scale (#163) | Gated on Track-2 transport, not cheap | Consistency check to discovery |

**Recommended order:** re-grade (free), then the MLD n=50 arm, then `DARWIN_IC=0`. Those three settle what the observations-only paper can actually claim, and the first is free. The sink anchor is the only path to keeping `scav_rat`, and it should be scoped as bounding from the start.

---

## 6. Draft reply to Jon

> Subject: Re: rain ratio values, and dropping the Darwin output
>
> Hi Jon,
>
> Thanks for this. Taking your open question first, since I think we have it pinned.
>
> **The three rain ratio values.** In the v05 llc270 deck, `data.darwin` line 53 has a generation scalar `val_R_PICPOC = 0.04245` under `&DARWIN_RANDOM_PARAMS`. `data.traits` line 92 has a frozen array under `&DARWIN_TRAITS`, `R_PICPOC = 0.0, 2*4.1886E-2, 4*0.0`. That array is the second and third values you are seeing: 0.0418860 on plankton types 2 and 3, the calcifiers, and 0.0 on the other five.
>
> The model loads the `data.traits` one. In `darwin_init_fixed.F`, `DARWIN_GENERATE_RANDOM` runs at line 357 and fills the array from `val_R_PICPOC`, then `DARWIN_READ_TRAITS` runs last at line 382 and overwrites it. The proof this is live rather than theoretical is that the two files already disagree, and the loaded number is 0.0418860, not 0.04245. So editing `val_R_PICPOC` in `data.darwin` does nothing. We checked this against the cloned v05 config and the pinned darwin3 source, `24885b71`.
>
> Two things fell out that you might want. First, `alpfe` and `scav_rat` are the opposite case. They are read by `darwin_read_params.F` and appear in neither the traits reader nor the generator, so editing them in `data.darwin` does work. `diatomgraz` lives in `PALAT` and the growth pair lives in `PCMAX`, both in `data.traits`. Second, Carroll's published `R_PICPOC` is 0.04245 but the value v05 actually integrates is 0.0418860. That is a 1.35 percent difference. It is far inside our tolerance so it changes no result, but our recovery target and the model's running value are not quite the same number.
>
> One honest caveat. This is a source precedence argument plus the file disagreement. We have not yet grepped the namelist echo out of `STDOUT.0000` on a real run. We have a script that does it in one command if you want it, or if you point us at your input directory we can confirm it there.
>
> **On dissolution.** Your point changed how we read one of our own negatives, in a good way. We tested whether Omega drives the calcite ratio and found nothing. But our test was against the surface production ratio, not against dissolution. If Omega mainly governs dissolution, and shallow dissolution above the horizon is grazing mediated rather than saturation driven, then our null is what you would expect rather than a data problem. Related, and you may already know this: v05 has no `disscSelect` switch at all. The Omega dependent modes are a later darwin3 addition, so v05 dissolves calcite at a constant rate by construction. Our own box does the same thing between 50 and 1000 m. If you have the actual `Kdissc` v05 runs at, that would help, since our default looks roughly an order of magnitude fast.
>
> **On the rain ratio varying regionally.** We agree, and the independent data says so. The Daniels CP:PP production ratio puts the equatorial Pacific around 1.6 times the global mean, and Sarmiento 2002 spans 20 to 30 times regionally. I want to flag one thing we will not claim, because it looks like support and is not. In our learner a single global scalar recovers the ratio in 0 of 50 seeds while a per cell field recovers it in 50 of 50. That is a fact about our estimator needing spatial structure, not a measurement that the true ratio is regional. The Daniels number is the real evidence.
>
> **On the growth pair and chlorophyll.** Your instinct matches what we measured, and it splits the pair in a useful way. A Fisher analysis says the two rates are not tangled with each other. They are starved of information. Biggrow's signal sits almost entirely in the large eukaryote chlorophyll channel, while Smallgrow's is diffuse and its largest single contribution comes through iron rather than its own chlorophyll. So we up weighted that one chlorophyll term. Biggrow went from 6 of 50 seeds to 12 of 50, and Smallgrow did not move at all, 7 of 50 to 6 of 50, which is what the analysis predicted. The clean result here is the asymmetry, not the improvement. Arm to arm, the Biggrow change is not significant at 50 seeds, so we can say chlorophyll is where the signal lives but not yet that this knob is the fix. We are running more seeds.
>
> I should also flag something we had not written down. Our box assigns Smallgrow to one small type and Biggrow to one large type, while in Darwin they are size class scalars with a spread. So what we recover is not quite the thing you tuned, which may be part of why you feel they do not line up with any class. We want to test that directly by making them act across the whole size class the way Darwin does. Also, all the chlorophyll in our loss is Darwin's own output rather than satellite. We have MODIS chlorophyll compared against v05 but it is bulk, not per class, so it would not separate the two rates on its own. If you know of a size fractionated or per class chlorophyll product for the 2003 to 2018 era, that would help us more than anything else here.
>
> **On dropping the Darwin output.** This is the one I most want your read on, because we have a first version already run and the answer is mixed.
>
> There is a configuration that turns off every target coming from Darwin's own output and keeps only the real observations, which are GEOTRACES dissolved iron surface and subsurface, GEOTRACES biogenic silica, and the Daniels calcite ratio. At 50 seeds, alpfe recovers 50 of 50 and R_PICPOC recovers 28 of 50, both far clear of a measured untrained baseline. scav_rat goes to 0 of 50, so it was leaning on the spatial pattern terms rather than on the iron data. diatomgraz lands below what an untrained network scores unless we give the network mixed layer depth as an input, and that arm is only at 10 seeds.
>
> Two things we owe you before calling that observations only. The run still starts from Darwin initial conditions and still takes its forcing and its network inputs from Darwin fields, so it is not independent end to end. And our cleanest joint result, the three parameter one, goes to zero without the pattern terms.
>
> There is also a deeper version of your point that we think is the real bar. Dropping the Darwin targets removes the circularity on the training side, but we still grade recovery against Carroll's published values. The test that would settle it is holding out real observations and scoring on them, and in our current zero dimensional box that comes back negative because the box has no spatial structure to generalise across. That is honestly the main thing standing between a consistency check and a discovery, and it is why the transport work matters to us.
>
> So: would you rather we make the observations only run the headline as it stands, two parameters recovering and one documented failure, or hold it until we close the initial condition and forcing dependency? And on the UDE, we have a learned scavenging closure already built on the Parekh backbone, unit tested and never trained on data. If you think that is the right first target ahead of the calcite closure, we will run it. Our one worry there is coverage. In a stress test the closure was accurate on the states the trajectory actually visited and badly wrong everywhere else, and regularisation did not help, so designing the forcing matters more than the optimizer.
>
> One last small thing. A while back we tested a particulate to dissolved iron ratio as a route to the scavenging rate. It looked like a clean win and it did not survive checking, so we retracted it. I do not think we ever told you. Your scepticism is the right one: the ratio reduces algebraically to the scavenging rate times POC over the sinking rate, so dissolved iron cancels exactly. And on your realism question, in GEOTRACES IDP2025 surface data only 76 samples worldwide carry both total particulate and dissolved iron under strict co location, 4 of them in our equatorial Pacific box, and where both exist the ratio spans about 2.6 orders of magnitude.
>
> Thanks again. The rain ratio precedence answer alone saved us a wasted perturbation experiment.
>
> Best,
> Lucas

---

### Statistical hygiene for whoever sends this

- **Decisively established:** `alpfe` 49/50 and 50/50 obs-only; `R_PICPOC` 50/50 with anchor versus 6/50 chance-level without; `scav_rat` 25/50 at 2000 epochs and 41/50 at 4000; the trio at 25/50 against an untrained 0/50; the flagship's independent reproduction (`scav_rat` 26/50 versus published 25/50); the `Smallgrow` flatness under `CHL2_W_EXTRA` (Fisher p = 1.000); the measured chance baselines themselves.
- **Directional but underpowered, do not harden:** `Biggrow` 6/50 to 12/50 (arm-to-arm p = 0.192); `scav_rat` log-scale bounding 26/50 to 35/50 (p = 0.100, and it costs `R_PICPOC` 50/50 to 45/50 at p = 0.056); the obs-only `diatomgraz` 10/10 at n=10 (P = 0.021 against the matched 0.68 baseline).
- **Refuted or superseded, do not quote:** the `diatomgraz` 35/50 "non-circular handle" (P = 0.447 against a matched untrained 34/50); the "-0.77 alpfe/scav_rat degeneracy" (that is the full-6 marginal, superseded by `STATUS.md:324`); the particulate:dissolved "14x tighter"; any cell-weighted count as recovery.