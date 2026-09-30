# Parameter- and scenario-conditioned path: what perturbed ECCO-Darwin output exists

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

No archived perturbed-parameter output of ECCO-Darwin could be found, so a parameter-conditioned emulator cannot be trained from anything public today. It needs a small, purpose-run v05 ensemble or the Carroll Green's-function (GF) run outputs, if Jon or Carroll still has them.

(1) Carroll 2020 GF (verified from the paper PDF): 18 LLC270 experiments in Table 1, plus #L1–L4 in Table S1, which I did not read. Setup is 1/3°, 50 levels, dt 1200 s, 1992–2017. Only 6 are parameter runs (#12–17), one per parameter, one-sided, from the Brix values: alpfe −20%, scav_rat ×5, Smallgrow and Biggrow +10%, diatom palatability +0.1, PIC:POC +20%. Carroll checked that the response is close to linear: the linear prediction gave 30.85% of the Experiment #1 cost, the actual optimized run 31.90%. Carroll 2022 (v05) did not redo the GF: it inherits the Carroll 2020 values and points to that paper. The data statements only name the NAS portal. The ecco_darwin repo has a recipe to recreate the GF runs (greens_functions_instructions.txt, commit d0df0d9), with per-experiment initial-condition pickups said to be on the portal. Output of runs #1–17 was not found. data.nas.nasa.gov timed out from this machine, so the listing was not re-checked.

(2) Other public runs: OAE runs exist in quantity but no output is public. Tyka et al. 2026 BG ran 44 LLC270 v05 runs; setups are on Zenodo (6.56 GB) and output is "available upon request". Suselj 2025 ran 11 OAE runs on LLC90. OAEMIP has an llc270 config (5 sites × 3 years) whose forcings sit on non-public NAS /nobackup. The one public scenario output is Savelli's riverine sensitivity set (Zenodo 17317011, 3.14 GB of 1° surface .mat fields). Planetary used a "global ECCO/MITgcm model" (secondary source, nothing public). No ECCO-Darwin iron-fertilisation runs were found.

(3) The PhysicsNeMo regional_weather_diffusion recipe (main@536553a) accepts scalar conditions natively, but only for the DiT architecture. The U-Net regression stage, which carries the deterministic skill, can only take parameters as per-sample constant "background" channels.

(4) Training data from the Track-1 box would teach the emulator the box, not ECCO-Darwin: it is 0-D, its growth rates run 2.3–5.4× slow, it has no light limitation, and its sensitivity ranking has never been checked against the GCM.

(5) The ask to Jon is below. One change to a settled row: ECCO Drive answered HTTP 401 (up, auth-gated) on 2026-09-30, where the map records it as not serving.

## Decisions

- **Where the perturbed-parameter training data comes from** → Ask Jon and Carroll for the GF run outputs first, since that costs nothing. At the same time, plan a self-run v05 ensemble from the public pickup: about 40 space-filling runs plus the existing 17 one-at-a-time decks. Do not wait on the OAE groups.
  - why: Nothing public exists [NF]. The GF runs are at most 7 one-sided parameter points on v04 [V], so they can seed a linear GF emulator but not a nonlinear one. The ensemble tooling is already in the repo, and the only external blocker is the forcing, whose host is answering again [V 401].
- **What the emulator predicts** → Predict Δ = y(θ) − y(θ0) given control-run BGC plus the shared physics as 'background', rather than predicting absolute fields.
  - why: ECCO-Darwin has no feedback from BGC to circulation [V, Carroll 2020 §2.3], so every member has identical physics. All the parameter information is in the difference from the control, which is also what the linear-GF null predicts.
- **How θ enters the network** → For the regression U-Net: log(θ/θ0) broadcast as constant channels in the per-sample 'background'. For a later DiT diffusion stage: the recipe's native scalar_conditions. Never put θ in invariants.
  - why: The recipe rejects scalar conditions on U-Nets (trainer.py:375-380), the regression U-Net has no embedding path (nn.py:98, song_unet.py:365-381), and invariants are shared by all samples (trainer.py:357-364) [V].
- **Whether to include the diffusion stage** → Regression first. Add diffusion only after the regression model beats the linear-GF null on held-out members, and then only for calibrated spread.
  - why: This is the same as the 2026-09-30 finding: CorrDiff's diffusion stage adds essentially no deterministic skill, and with ~57 parameter points a diffusion model is at risk of memorising the training set.
- **Using the Track-1 box to generate the ensemble** → Use it only for pipeline tests and optional pretraining, clearly labelled as box physics. Never count it as evidence about ECCO-Darwin.
  - why: The box is 0-D (CV ~1e-15), its growth rates run 2.3–5.4× slow with no light limitation, its sensitivity ranking has not been validated against the GCM, and it failed the real held-out gate [V/S]. An emulator trained on it learns the box.
- **Grading** → Hold out whole runs in parameter space. Compare against three nulls: Δ=0, the linear GF built from the 17 decks, and GP/ridge on PCA of Δ. Also require the emulator's sensitivity signs and ranking to match the finite-difference ones.
  - why: Carroll found the response nearly linear for ±10–20% steps (30.85% vs 31.90%) [V]. Unless the emulator beats a linear GF, the 17 runs themselves are already the fast emulator.
- **OAE / scenario conditioning** → Treat the alkalinity-injection field as a background channel and use a linear impulse-response superposition as the null. Ask for Tyka 2026 output (44 LLC270 v05 runs, available on request).
  - why: The OAE response is flux-normalized and close to linear (Suselj preprint) [V], and the OAEMIP forcings are NAS-internal [V].

## Risks

- The Carroll GF outputs were very likely never archived. The data statements only name the portal, the ecco_darwin repo ships only a recipe, and the repo's earlier cluster and repo search found none. The NAS listing could not be re-checked this session because the host timed out.
- Even if found, the GF runs are v04/Darwin-1, one-sided, and use large steps (scav_rat ×5, i.e. +400%; the repo notes say '+500%', which is slightly wrong). #12 and #13–17 start from different initial-condition bases (experiment_06 and experiment_05), so they are not one-parameter differences from a single control.
- A self-run ensemble is blocked on era_xx_it42_v2 forcing. ECCO Drive answers 401 now, but whether an ordinary Earthdata account can read that path is unverified. Cost per LLC270 run-month on Explorer is unmeasured.
- Silent-failure trap: R_PICPOC and diatomgraz must be edited in data.traits, not data.darwin, and checked in the STDOUT echo. diatomgraz ×1.2 pushes PALAT(43) to 1.015, above 1.
- Darwin's parameters are global scalars (2026-07-31 finding), so an emulator conditioned on θ cannot represent Track-1's per-cell parameter fields.
- What limits generalisation across θ is the number of distinct parameter points (tens), not the number of samples. Diffusion and U-Net models can memorise and interpolate badly between members.
- Short 1–3 yr segments measure transient response. Slow tracers (subsurface FeT, DIC, ALK) will not equilibrate; the recipe requires a convergence-with-integration-length check.
- The recipe needs PyTorch ≥2.10 and natten and is pinned only to a main commit (not in v2.2.2). natten on Windows or sm_100 is unverified.
- Samudra reports that emulators under-represent forcing-trend magnitude, so scenario (OAE) responses could be damped the same way.
- Incidental repo errors, not fixed here because this was read-only: (a) docs/research_notes/2026-07-07_param_conditioned_emulator_decision.md:138 credits ICON-A GMD 18:3681 to Watson-Parris; the first author is Bonnet. (b) docs/findings/2026-07-23_surrogate_jacobian_validation.md:72 gives the v4 scav_rat optimum as 9.32 raw, but Carroll Table 1 and the source say 10.411 (10.41124 in the source). (c) The settled row calling ECCO Drive 'NOT SERVING' is stale as of 2026-09-30.

## Unknowns

- Whether outputs of Carroll 2020 experiments #1–17 or #L1–L4 exist anywhere: the NAS ecco_darwin_v4 listing was not re-checked (host timeout), and Carroll's archive was not asked.
- What Carroll 2020 Table S1 (#L1–L4) contains: the supplement was not read.
- Whether v06 GF optimisation produced sensitivity-run output that could be shared.
- Whether Tyka 2026, Suselj 2025 or OAEMIP OAE output can be obtained on request, and in what format.
- Whether an ordinary Earthdata login can read ECCO2/LLC270/era_xx_it42_v2, and the non-public nbp19_dmenemen_public_llc270 tree.
- Wall-clock and core-hours per LLC270 v05 model-year on Explorer at 468 ranks: never benchmarked.
- Whether the Suselj JAMES final version's data statement differs from the preprint (Wiley page blocked).
- Which model the ESS Open Archive OIF preprint (10.22541/essoar.173557508.81096097) used (403).
- The Loeppky n≈10d sample-size rule and the CAM6 PPE numbers are secondary: not re-read this session.
- Whether earth2studio's generic CorrDiff wrapper can take θ as extra constant input variables without code changes: not read, inferred only.

## Spec

LABELS: [V]=verified by me this session from the primary file; [S]=secondary (repo note, review or search snippet I did not re-derive); [I]=inferred; [NF]=searched, not found.

== 1. Carroll GF calibration: what exists ==
[V] Carroll et al. 2020 JAMES, doi 10.1029/2019MS001888. Read from the local PDF C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\references\carroll_2020_ecco_darwin.pdf: §2.2–2.4 and Table 1 on p.6.
- Setup: LLC270 (~1/3°, ~18 km at high latitudes), 50 levels, dt 1200 s, integration Jan 1992–Dec 2017.
- Table 1 has 18 experiments:
  - #1: first guess (Brix 2015 initial conditions and parameters).
  - #2–11: initial-condition experiments. The optimized initial condition is their linear combination (weights in column D, summing to 1).
  - #12–17: one parameter run each, one-sided, relative to the Brix values:
    - #12 alpfe −20% (1 → optimized 0.9283)
    - #13 scav_rat ×5 (3 → 10.411)
    - #14 Smallgrow +10% (0.7 → 0.6609)
    - #15 Biggrow +10% (0.4 → 0.4314)
    - #16 diatom palatability +0.1 (0.85 → 0.8300)
    - #17 PIC/POC +20% (0.04 → 0.04245)
  - #18: optimized run (released as v04).
- Linearity: the linear prediction gave 30.85% of Experiment #1 cost against 31.90% actual.
- Stated limit: "not able to conduct an exhaustive exploration of model parameter space".
- Data statement: "ECCO-Darwin model fields are available at https://data.nas.nasa.gov/ecco", plus zenodo 3829965 (code).
- Also verified: "there are no feedbacks between biogeochemistry and circulation". Every parameter or OAE member therefore shares identical physics.

[V] GF recreation recipe: MITgcm-contrib/ecco_darwin@d0df0d9 (2020-07-13, unchanged at HEAD e39a22a), v04/llc270_JAMES_paper/greens_functions/greens_functions_instructions.txt.
- Per-experiment initial conditions are at eccodata/llc_270/ecco_darwin_v4/input/darwin_initial_conditions. #12 starts from pickup_ptracers_experiment_06; #13–17 start from experiment_05.
- Perturbed values: alpfe 1 → 0.8; scav_rat 3 → 15; Smallgrow 0.7 → 0.77; Biggrow 0.4 → 0.44; diatomgraz 0.85 → 0.95; R_PICPOC 0.04 → 0.048.
- Extra runs #L1–L4 are listed. #L4 is a second alpfe 1 → 0.8 run. The Table S1 details were NOT read.
- Unit check [V]: v04 darwin_init_fixed.F sets scav_rat = 10.41124 × 0.005/86400 = 6.025e-7 s^-1, which equals v05 SCAV_RAT.

[V] Carroll et al. 2022 GBC, doi 10.1029/2021GB007162 (Europe PMC full text of PMC9286438).
- v05 = LLC270, 50 levels, dt 1200 s. The six ecological parameters were adjusted by GF; "A detailed description ... is presented in Carroll et al. (2020)". There is no new GF table.
- Two extra sensitivity runs are described (reduced apCO2; nutrients re-initialized); no archive is given.
- Data: http://data.nas.nasa.gov/ecco/ plus zenodo.org/record/6091603.
- [V] The v05 data.darwin values equal Table 1 (quoted in C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\docs\findings\2026-07-23_v05_perturbation_recipe.md:244-250), so v05 inherited the 2020 optimum.

[NF] Output of GF experiments #1–17, anywhere.
- The repo search already settled this (docs\findings\2026-07-23_surrogate_jacobian_validation.md:18-22).
- The NAS portal timed out from this workstation on 2026-09-30 (TCP connect timeout, WebFetch failed), so the ecco_darwin_v4 listing was NOT re-checked.
- [S] The portal is a single-page app that returns HTTP 200 for any path. /ecco/llc_270/ holds only ecco_darwin_v4/, ecco_darwin_v5/, grid/, iter42/ (docs\findings\2026-07-28_session_evidence_log.md:62-74).
- [I] Even if found, these runs are v04/Darwin-1, one-sided, use large steps, start from two different initial-condition bases, and give 7 parameter points. That is enough for a linear GF emulator, not a nonlinear conditioned one.

== 2. Other ECCO-Darwin runs with different parameters or forcing ==
- [V] Tyka, Zhou, Yankovsky, Carroll 2026, BG 23:4943, doi 10.5194/bg-23-4943-2026. v05 LLC270 OAE pulses: 12 sites × {1992, 1999} × 15 yr, plus 4 sites × 5 pulse years × 5 yr, for 44 runs. Setups at doi 10.5281/zenodo.20436524 (one tgz, 6.56 GB). "Pre-calculated simulation data is available upon request."
- [V] Suselj et al., JAMES 2025, doi 10.1029/2024MS004847. Read from the Zenodo preprint 10.5281/zenodo.10632054. LLC90 1° (ECCO V4r4) ECCO-Darwin, 1995–2017. 5 continuous OAE sites plus 3 pulse variants at 2 sites, so about 11 perturbed runs and a baseline. The Open Research section names only the NAS portal and zenodo 10562714; whether the OAE runs are on the portal is unverified. The Wiley page is behind a 403/Cloudflare wall.
- [V] OAEMIP llc270 config: MITgcm-contrib/ecco_darwin@e39a22a, v05/llc270_oaemip/README.txt. Sites kuroshio, tasmania, labrador, california, oman; years 1997, 1999, 2003. Forcings are at /nobackup/rsavelli/OAEMIP (NAS-internal); inputs need ECCO Drive (Earthdata). Sibling configs: v05/1deg_oaemip, v05/1deg_CDR (includes a rapid_mCDR 1-D model), v05/3deg_CDR, v05/3deg_CDR_MacroA, v04/llc270_OAE_ship_track_paper, llc270_N2O, llc270_RADIv1, 1deg_RADIv2, jra55do{,_mangroves,_nutrients}.
- [V] Savelli riverine-input sensitivity: GMD 19:867 (2026); data at doi 10.5281/zenodo.17317011 (3.14 GB: CO2flux, pCO2, PP, SIarea .mat for ECCO_V4r5 1°, plus code). This is the only public ECCO-Darwin scenario output found.
- [V] Offline LLC90 Darwin driven by archived ECCOv4r6 daily physics, 1992–2025, dt 3600 s: ecco_darwin@e83aefb9f (2026-08-27), offline/V4r6_darwin_offline/readme.txt. It is a different ecosystem (6 phytoplankton + 4 zooplankton, radtrans), not v05's.
- [V] v05/3deg: a verification experiment built on tutorial_global_oce_biogeo, with the v05 llc270 Darwin code and namelists and EIG_*_2000 forcing files. [I] It is a cheap multi-fidelity tier with toy physics.
- [S] Planetary/Isometric Halifax credits: "A global ECCO/MITgcm model" (Carbon to Sea review, 2025-11-25). No public output.
- [NF] ECCO-Darwin iron-fertilisation runs. One ESS Open Archive OIF preprint returned 403, so which model it used is unverified.
- [S] v06 is "in optimization" with GF (Carroll, ECCO meeting 2023 slides). No archive found.
- [V] Change from the settled row: https://ecco.jpl.nasa.gov/drive/ returned HTTP 401 (up, auth-gated) on 2026-09-30. The map says NOT SERVING (docs\findings\2026-07-31_no_nasa_account_needed_v05_is_already_built.md:30-37). Whether era_xx_it42_v2 is readable with an ordinary Earthdata login is still unverified.

== 3. How to condition, and what the recipe supports natively ==
All [V] at NVIDIA/physicsnemo main@536553acf5b03b68ec7283975ba7276d60056a36, under examples/weather/regional_weather_diffusion/.
- datasets/dataset.py:74-76: `scalar_condition_channels()`. The batch key is "scalar_conditions" (utils/nn.py:255-259), packed as TensorDict {cond_concat, cond_vec} (nn.py:219-224).
- utils/trainer.py:375-380 raises "Scalar conditions are only supported for the 'dit' architecture." README.md:137 and :331 say the same.
- The DiT takes them through condition_dim with conditioning_embedder 'dit', 'edm' or 'zero' (nn.py:103-157).
- The U-Net regression net is StormCastUNet(embedding_type="zero") (nn.py:95-100). physicsnemo/models/diffusion_unets/song_unet.py:365-381 builds map_label only when embedding_type != "zero", so there is no label path in the regression U-Net.
- regression_model_forward drops scalar conditions (nn.py:373-392).
- Invariants are one array repeated for every sample (trainer.py:357-364), so they cannot carry per-member θ. The only zero-code route for the U-Net is to broadcast log(θ/θ0) as constant channels inside the per-sample "background".
- Optional per-pixel "mask" (dataset.py:42-54). The dataset registry picks up any StormCastDataset subclass in datasets/<mod>.py as "<mod>.<Class>" (datasets/__init__.py:21-34). requirements.txt needs torch>=2.10 and natten.
- The repo already has a FiLM layer, though only on σ: C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\scripts\diffusion_emulator.py:84-119. Adding a θ-embedding to `e` is the in-repo alternative.
- src\darwindiff\e2s\prognostic.py:79 (DarwinBGCPrognostic) has no parameter input [V, grep].

Literature, all [V] by arXiv/OpenAlex metadata:
- FiLM, arXiv 1709.07871.
- EDM label conditioning, arXiv 2206.00364.
- DiT adaLN, arXiv 2212.09748.
- SC-FNO, arXiv 2505.08740: forward accuracy does not guarantee accurate dθ-sensitivities.
- cBottle, arXiv 2505.06474: an Earth-2 generator conditioned on SST and solar position. This is the scenario-as-boundary-field pattern.
- Samudra, arXiv 2412.03795: "struggles to capture the correct magnitude of the forcing trends".

PPE sizes:
- CAM6 PPE: 262 members × 45 parameters, LHS (GMD 17:7835, 2024) [S].
- WOMBAT-lite: 512 runs × 26 parameters, GP surrogate (BG 22:5349) [V abstract].
- ICON-A PPE plus ML emulator plus history matching (GMD 18:3681) [V abstract]. First author is Bonnet, not Watson-Parris as the repo note says.
- MOPS: TMM plus CMA-ES calibration (GMD 10:127) [V abstract].
- [S, not re-read] n≈10×d rule for GP emulators (Loeppky et al. 2009).

== 4. Could the Track-1 box generate training data? ==
Mechanically yes: carroll6_tendency(params[6]) at src\darwindiff\carroll6.py:319 is cheap. It would carry the surrogate gap:
- [V] It is 0-D per AOI; tracer CV is ~1e-15 against Darwin's O(1) (docs\findings\2026-07-23_surrogate_jacobian_validation.md:47-51).
- [V] Growth parameters are used as rates, not times, so every phytoplankton type grows 2.3–5.4× slower than Darwin. There is also no light limitation (docs\findings\2026-09-26_growth_parameters_are_timescales_in_darwin.md).
- [V] The box's sensitivity ranking is surrogate-only; the GCM side has not been run (docs\findings\2026-07-25_surrogate_to_gcm_validation.md:66-90).
- [S settled] The real held-out R² gate failed: −0.05 against a null of +0.50.
- [S] The repo's own 2026-07-07 verifier already dismissed this route (docs\research_notes\2026-07-07_param_conditioned_emulator_decision.md:63).
- Allowed use: plumbing tests and pretraining, labelled as box physics. Never as evidence about ECCO-Darwin.

== 5. Build spec (future, only once a PPE exists) ==
PPE:
- 4 observable parameters in log space: alpfe, scav_rat, R_PICPOC as data.traits R_PICPOC(2:3), and diatomgraz as data.traits PALAT entries 36 and 43.
- ~40-member Sobol/LHS design over ±20–50%, plus the existing 17 one-at-a-time decks as a local-derivative test set. The decks come from scripts\perturbation\make_v05_oat_ensemble.py and each load is checked with scripts\perturbation\verify_perturbation_loaded.sh.
- Short segments from the public v5 pickup (timeStepNumber 78912 ≈ 1995-01-01).
- The control run must be re-run in the same decomposition (468 ranks); MITgcm is not bit-reproducible across decompositions.
- [I] Storage: ~3.8 MB per 2-D LLC270 field-month, so 20 fields × 36 months × 57 runs ≈ 156 GB.

Code:
- New uv project track2/ with its own pyproject.toml and uv.lock, depending on darwindiff by path. Pin physicsnemo to git commit 536553a, not a release. Copy the recipe folder into it.
- Dataset: datasets/ecco_darwin_ppe.py::EccoDarwinPPEDataset(StormCastDataset), regridded to a regular 1° or 1/3° lat-lon grid.
  - background = physics fields (SST, SSSanom, mldDepth, oceanQsw, oceanQnet, wspeed, SIarea), shared across members, plus control-run BGC at time t, plus broadcast log(θ/θ0) channels.
  - state = the Δ fields, y(θ) − y(θ0), for DIC, ALK, FeT, PIC, POC and log Chl.
  - scalar_conditions = log(θ/θ0), used by the DiT only.
  - invariants = land mask, bathymetry, sin/cos of lat and lon.
  - mask = ocean mask.
- Stage A: config model.architecture=unet, regression_conditions=["background","invariant"].
- Stage B (diffusion): only after Stage A passes, and only for calibrated spread: architecture=dit with scalar conditions.

Grading:
- Hold out whole members in θ-space (leave-k-runs-out, including corners). Never hold out time only.
- Nulls:
  - (a) Δ=0, the parameter-blind control. This is what a model trained on one trajectory effectively gives.
  - (b) Linear GF: Δ̂ = Σ S_i Δlogθ_i, with S_i from central differences over the 17 decks. This is Carroll's own method.
  - (c) GP or ridge regression on PCA scores of Δ.
- Pass: beat (b) with a block-bootstrap CI above 0 on each parameter's own observable (FeT for alpfe and scav_rat, PIC for R_PICPOC, diatom biomass/Chl for diatomgraz), and match the finite-difference sensitivity signs and ranking (SC-FNO lesson).
- Stop: if it cannot beat (b), the ensemble plus a linear GF already is the fast emulator.
- OAE scenarios: the alkalinity-source field goes in as a background channel; the null is a linear impulse-response superposition, since efficiency is flux-normalized and roughly amplitude-independent (Suselj preprint §2.2.3).

== 6. Ask to Jon (plain, no em dashes) ==
"I would like the fast emulator to predict what a parameter change does, so it needs v05 runs at more than one set of parameters. Do the output fields from the Carroll et al. 2020 Green's-function parameter runs (Table 1, runs 12 to 17), or from any v06 optimisation sensitivity runs, still exist anywhere, even as monthly surface fields? If not, is it fine for me to run a small v05 ensemble from the public pickup on Explorer, and who could share the era_xx_it42_v2 forcing that is not on the NAS portal?"
