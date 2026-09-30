# Topping's Earth-2 recipe on ECCO-Darwin: build spec, data state, and the parameter path

**Date:** 2026-09-30 · **Status:** DESIGN ONLY. Nothing has been built, trained or run through physicsnemo
or earth2studio. · **Cost:** one six-agent design workflow (five readers plus a critic), read-only, about
1.9M subagent tokens · **Pins:** physicsnemo@`536553acf5b03b68ec7283975ba7276d60056a36`, earth2studio@`2067756d489ad9195cf9e1ed52e074a4f8588ca4`
· **Context:** `docs/findings/2026-09-30_earth2_air_pollution_recipe_is_not_a_track2_lever.md` (the
assessment and the owner's decision to build).

The six design parts are banked verbatim in
[`2026-09-30_topping_recipe_build_spec/`](2026-09-30_topping_recipe_build_spec/): `recipe.md`,
`e2s.md`, `data.md`, `eval.md`, `params.md`, and `critic.md`. **Where the parts disagree, the critic
wins**, because the parts, taken literally, will not work together.

## 1. What the owner wants, and what data can serve it

Changing an ECCO-Darwin parameter, or testing a scenario, needs a full rerun. A complex scenario therefore
needs many reruns, and a fast emulator is valuable for that.

**No public ECCO-Darwin output varies a parameter with everything else held fixed** (checked 2026-09-30):

- **The NASA v05 output is a single run with one parameter set.** The public `/ecco/llc_270/` holds only
  `ecco_darwin_v4/`, `ecco_darwin_v5/`, `grid/` and `iter42/`
  (`docs/findings/2026-07-28_session_evidence_log.md:73-74`). v04 and v05 differ in many things at once,
  so they cannot isolate the effect of any one parameter.
- **Carroll et al. 2020's Green's-function runs** (JAMES, doi 10.1029/2019MS001888; v04, Darwin 1):
  - 18 experiments in Table 1. #12-17 are the parameter runs, one per parameter and one-sided: alpfe −20%,
    scav_rat ×5, Smallgrow +10%, Biggrow +10%, palatability +0.1, PIC:POC +20%.
  - **Their output was not found anywhere public.**
  - Carroll 2022 (v05) inherited these runs rather than redoing them.
  - A recipe to recreate them exists at MITgcm-contrib/ecco_darwin@d0df0d9,
    `v04/llc270_JAMES_paper/greens_functions/greens_functions_instructions.txt`.
- **Scenario runs on our exact model:** Tyka, Zhou, Yankovsky and Carroll 2026, *Biogeosciences*
  23:4943-4966, doi 10.5194/bg-23-4943-2026.
  - ECCO-Darwin **v05 at LLC270**: 24 fifteen-year and 20 five-year ocean-alkalinity-enhancement pulse
    runs, plus a 16-run biology on/off ablation (verified on the article page).
  - Output is "available upon request". This comes from the agent's reading; the availability statement was
    not re-confirmed.
- **Public scenario output:** Savelli's riverine-input sensitivity runs, GMD 19:867 (2026), Zenodo
  10.5281/zenodo.17317011. These are 3.14 GB of 1° surface fields from ECCO V4r5 Darwin, a different
  configuration from v05.

**So a parameter-aware emulator needs perturbed runs that do not exist publicly.** The map settles that
we can make them. v05 runs on Explorer (`docs/findings/2026-07-25_surrogate_to_gcm_validation.md`), and
a 17-deck recipe exists (`docs/findings/2026-07-23_v05_perturbation_recipe.md`). The forcing that
self-running needs, `era_xx_it42_v2`, is on ECCO Drive, which answered **HTTP 401 on 2026-09-30**: it is
up and needs an Earthdata login. The owner has an account; credentials go in the owner's own `~/.netrc`.

**More of the same run is not the lever.** The map settles that the monthly emulator's learning curve is
flat from n≈55 (`docs/findings/2026-07-19_two_negatives.md`). The small sample count is a memorisation
risk for a diffusion stage, but volume is not what stops the deterministic stage. **Variation is.**

## 2. Data state on 2026-09-30

| source | state |
|---|---|
| `data.nas.nasa.gov:443` | **unreachable** from the workstation (timeout), AICR (refused) and Explorer, while `www.nas.nasa.gov` answers |
| ECCO Drive | **401** (up, Earthdata-gated) |
| PO.DAAC archive | 200 |
| local monthly mirror `D:\ecco_darwin_v5\output\monthly` | 52 variables, intact |
| local daily mirror | empty (13 MB) |
| AICR `/scratch` daily, monthly and v05-build trees | **purged** (directories present, empty) |
| AICR `/work/neu/p2026_0089_neu/cubes/` (snapshotted, not purged) | daily 1° and 0.5° cubes: 9,463 days × {surfChl1,2,3,5} plus forcing {SST, wspeed}; monthly `global3d_L10_cube.npz`: 158 × 60 channels (DIC, ALK, PIC, POC, FeT, Chl1 × 10 levels), 680×1440 |

**Use the `/work` cubes for plumbing and memory probes only.** Never grade or serve anything built on
them, for four reasons:

- **Wrong clock.** `times_days` equals `iters × 900 s`: every value is 0.75× the true time (verified
  2026-09-30), and the value labels the end of each window. Derive time from `iters × 1200 s`.
- **Not a 1° grid.** The grid is 171 rows spanning −80..89.75 at 0.998538°.
- **Negative targets.** surfChl2, surfChl3 and surfChl5 are 26-41% negative.
- **Unclear provenance.**

**Daily `apCO2` is seawater pCO2, not atmospheric.** It must never go into a background, because it would
leak the target (existing trap).

## 3. Build contract (from the critic)

- **One grid.** Cell-centred, ascending lat −80..80, lon [0, 360).
  - High-res (HR): 0.25°, 640×1440, with a 16-column periodic halo in training.
  - Low-res (LR): 1°, 160×360, defined as an exact 4×4 area × ocean-fraction block mean of HR.
  - Rows north of 80°N are dropped. This is a pre-registration amendment and must be committed before any
    training.
- **One split, written once by the builder and read by name.**
  - Main split G12: train 1992-2005, val 2006-2008, gap 2009, test 2010 to the end.
  - Robustness splits: G6, G24 and a reversed split.
- **One owner for transforms and normalisation:** a `darwindiff.e2data.transforms` module in the main
  package, used by the dataset, the wrappers and the scorer. Invariants are stored pre-normalised.
- **Recipe facts that constrain the design** (physicsnemo `examples/weather/regional_weather_diffusion`):
  - Input and output grids must be the same size, so a coarse input is upsampled inside the dataset.
  - There is no CorrDiff-style patch training.
  - SongUNet sizes must be multiples of 2^(levels−1).
  - The regression and diffusion stages are separate runs, chosen with `training.loss.type`. The handoff is
    `model.regression_weights`, and upstream tests never exercise it.
  - Launch with `torchrun`, even on one GPU (inferred from the code, not executed).
  - The upstream StormCast configs fail the recipe's own validation on main.
  - Land must be zero-filled **after** normalisation. The mask is a per-pixel loss weight.
- **earth2studio chain.** `DiagnosticWrapper` passes the diagnostic only the prognostic's outputs, selected
  by name (`dxwrapper.py:158-167`). So the StormCast-style prognostic must pass the physics background and
  day-of-year through as extra output channels. CorrDiff probably receives `valid_time=None` inside the
  chain (inferred); the first plumbing milestone must assert it.
- **Environment.**
  - `track2/` is a separate, Linux-only uv project on Python 3.12, pinned to the two SHAs above, with
    torch 2.11.0+cu128 and netCDF4 1.7.2. No natten.
  - Build it in a Slurm job, with the cache and venv on `/work`.
  - The 5090 can run the builder and the gate, but not `track2`.
- **Our own wrapper bug.** `src/darwindiff/e2s/prognostic.py` applies `@batch_func()` twice to `__call__`
  (lines 276 and 282). It passes CI only because the conformance test skips without earth2studio and the
  fallback decorator does nothing. Fix it in M1.

## 4. Ordered build plan

| milestone | where | what | done when |
|---|---|---|---|
| **M0** | local CPU | `e2data` builder on the monthly mirror, `build verify`, gate skeleton, pre-registration amendment | verify passes (2232 maps to 1992-01; 546,695 ocean cells; A(HR) equals LR exactly; splits disjoint), and the amendment is committed before any sbatch |
| **M1** | AICR, 1 GPU, one job | build the `track2` env in the job; upstream tests; synthetic smoke of both stages incl. `regression_weights`; `make_package`; parity tests; earth2studio chain on a toy grid and the real grids, with persistence and untrained nulls through the same pipe | parity within 1e-5, land = 0, ocean finite. **Plumbing only, no skill numbers** |
| **M2** | AICR, separate jobs | memory and step-time probes at LR and HR, plus a diffusion inference timing | a budget table |
| **M3** | AICR | **S0: the physics-to-BGC diagnostic**, regression only, 5 seeds, LR 1°, G12, with all nulls in the same job (Job A), then fresh seeds on G6/G24/REV12 (Job B) | the gate exits 0 and a map row is committed. **A STOP closes the CorrDiff/StormCast direction** |
| M4 | AICR | CorrDiff-style LR→HR regression, monthly | only if M3 passes |
| M5 | AICR | diffusion stage, judged against dressed-regression and deep-ensemble nulls | only if M4 passes |
| M6 | AICR CPU | when `data.nas` answers: range-request test, download 12 daily 2-D variables, `build daily` | every file is 3,790,800 bytes and verify passes |
| M7 | AICR | StormCast-style daily prognostic with a physics(t+1) background and no apCO2; nulls: persistence, climatology, seasonal AR(1), ARX(1), untrained | Job A/B |
| M8 | AICR | the chain: `run.deterministic` / `run.ensemble(DiagnosticWrapper(DarwinStormCast, DarwinCorrDiff))` | gate passes |
| M9 | AICR | speed benchmark. The speed-up stays UNKNOWN until ECCO-Darwin's cost per simulated year is measured | map rows plus `check` |

**Parameter-aware version, after perturbed runs exist** (from `params.md`):

- **What it predicts:** Δ = y(θ) − y(θ0), given the control run plus shared physics.
- **How θ enters:** as constant `background` channels for the U-Net regression stage. The recipe's native
  scalar conditions exist only for the DiT architecture.
- **How it is graded:** hold out whole runs in parameter space. The nulls are Δ = 0, the linear
  Green's-function prediction built from the 17 decks, and GP/ridge on the principal components of Δ.
  Sensitivity signs and ranking must also match finite differences.
- **The Track-1 box can generate pipeline-test data only.** It is not evidence about ECCO-Darwin: it is
  0-D, and its growth rates run 2.3-5.4x slow (#257).

## 5. Paired physics: can an MIT GCM supply more physical inputs?

A second workflow (three sweeps plus a critic, banked as `paired_physics_*.md`) asked whether MIT
physical-ocean products paired with ECCO-Darwin can supply richer physical conditioning.

**Exactly paired physics exists only from the v05 run itself.** Darwin is driven online by the LLC270
circulation at every 1200 s step (Carroll et al. 2022, GBC), so the run's own physical diagnostics are the
exact pair (MITgcm-contrib/ecco_darwin@e39a22a, `v05/llc270/input/data.diagnostics`).

- **Daily:** SST, SSSanom, wspeed, SIarea and SIheff only. A daily mixed-layer depth is configured
  (stream 18) but is absent from the portal listing.
- **Monthly:**
  - 3-D: THETA, SALTanom, UE/VN_VEL_C, WVEL and PAR (3-D fields partly missing locally, 280-293 of 324
    months);
  - 2-D: mldDepth, oceanQsw, oceanQnet, SST, SSSanom, sea ice and wspeed;
  - budget streams: ETAN, TFLUX, SFLUX and others.
- **Correction to a settled row:** daily pCO2, pH and surfPCO2 are **full 50-level files** (180.76 MiB
  each), not surface-only.

**ECCO V4r4 is the only public daily physics product in the same family, and it is a different
solution.**

- **What it is:** LLC90 at about 1°, the same 50 levels, 1992-2017, and 80 PO.DAAC collections listed in
  CMR.
- **Access and size:** it needs an Earthdata login. The daily set is about 733 GB at 0.5° or about 866 GB
  on the native grid.
- **Never use it as TRAINING conditioning for v05 targets.** The network would learn p(BGC | physics that
  did not cause it). That is an errors-in-variables problem: sensitivities shrink toward zero, and
  validation on the same mismatched pairs still looks fine, so nothing flags it.
- **As an inference-time scenario background it is legitimate**, and it matches StormCast's own design.
  The V4r4-vs-v05 shift must be measured first, on the five overlapping daily fields and the monthly 3-D
  fields.

**A second trajectory with the same biogeochemistry exists, but its output is not public.**

- `v05/1deg` runs Darwin 3 with namelists identical to v05's (`data.traits` byte-identical; `data.darwin`
  differs only in the iron-dust file) on V4r4 and V4r5 physics.
- It uses a different Darwin code checkpoint, so it is the same settings, a different code build, and a
  different output.
- Its BGC output is not public.
- Other LLC270 variants with the same BGC (v5r1 physics, a 1985 back-extension, repeat-year runs) have no
  public output either.

**Everything else is a different ecosystem**, so it would be a different target, not more ECCO-Darwin
data: CBIOMES, Darwin cs510, ECCO2-Darwin, Manizza 2019, v04 and v06.

**The one complete route to exactly paired daily physics is a re-run of v05.**

- The run itself:
  - Use the full MITgcm + Darwin run (darwin3 24885b71, readme §3 route), with extra daily streams.
  - Take BOTH the physics and the BGC from that one run. LLC270 is eddy-permitting, so any build,
    rank-count or compiler difference grows into mesoscale divergence. A physics-only re-run therefore
    cannot be paired with the PUBLISHED BGC.
- Extra daily streams:
  - 2-D: ETAN, MXLDEPTH, oceQsw, oceQnet, oceFWflx, oceTAUX/Y, SIhsnow and the EXF atmospheric state;
  - 3-D, top 20 levels: THETA, SALTanom, UE/VN_VEL_C, WVEL, GGL90Kr and PAR;
  - optionally, daily DIC, ALK, PIC, POC and FeT.
- Constraints:
  - `numlists=90` is fully used, so raise it at rebuild, or pack fields into streams.
  - Storage is about 37 GB per 2-D daily field and about 0.75 TB per 20-level 3-D field.
- This is the same machinery as the perturbed-parameter runs of §1. Both come from one set of re-runs.

**Next action (for the owner to send, not sent):** one email to Carroll and H. Zhang at JPL. It asks four
things:

1. the daily mixed-layer depth stream;
2. whether daily 3-D physics exists for v05 or the extended 1992-2023 run (Heiser and Wagner's May 2019
   file, Zenodo 10.5281/zenodo.18854567, shows some does);
3. whether they would re-run v05 on Pleiades, where every input already lives, with a supplied
   `data.diagnostics` diff;
4. the public locations of the xx*42 controls and the apCO2 forcing.

Meanwhile, train only on exact pairs: v05 daily surface physics, plus v05 monthly 3-D physics interpolated
to daily as a slow channel.

## 6. Recommendation on record (2026-09-30)

Building this emulator is **not necessary now**:

1. With today's data it cannot answer the motivating question, because nothing public varies a parameter.
2. The perturbed v05 runs that would make it useful are also Track 1's planned GCM cross-check.
3. #257 (growth times used as rates) could move the Track-1 headline results and comes first.

The suggested order is:

1. Fix #257.
2. Get ECCO Drive access and download the forcing.
3. Rebuild v05 on Explorer and measure the cost per simulated year.
4. Run a few perturbed decks.
5. Then build M0-M3 on those runs.

An optional Earth2Studio demo on the `/work` cubes would be a showcase, not a result, and must be labelled
that way.
