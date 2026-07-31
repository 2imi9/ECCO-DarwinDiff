# No NASA account. ECCO-Darwin v05 is already built on our own cluster, and the real blocker is a decision

**Date:** 2026-07-31 · **Method:** 6 lenses over MITgcm-contrib/ecco_darwin, darwinproject/darwin3,
NAS/HECC and Earthdata policy pages, each adversarially screened · **Run:** `wf_f69cbfb1-d51` ·
**Answers:** "should we ask for an account to access the model via a NASA academic account?"

**Answer: no.** Register a free Earthdata Login instead. We are not blocked on access or on compute.

## 1. We already built it, and that was verified before writing this

| | |
|---|---|
| binaries | `/scratch/qi_zim_neu/darwindiff_v05/darwin3/build/mitgcmuv` (767-rank, job 227366) and `build468/mitgcmuv` (468-rank re-tile, job 227523, `RETILE_BUILD_OK`) |
| inputs | **49 GB / 140 files** at `/scratch/qi_zim_neu/darwindiff_v05/inputs` (`iter42` 38 G, `ecco_darwin_v5` 12 G, `grid` 445 M), 0 failures |
| record | `docs/findings/2026-07-28_session_evidence_log.md` §A1-A4 |

Both binaries were confirmed present on disk while writing this note, not taken from the log.

**The Darwin biogeochemical pickup is public and already staged.**
`data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/input/darwin_initial_conditions/pickup_ptracers.0000000001.data`,
11.75 GB, **no login**. Its `.meta` gives `timeStepNumber = 78912` = 1096 days = three model years, so
it is an **end-of-spin-up state near 1995-01-01**, not a cold 1992 start. `pickupStrictlyMatch=.FALSE.`
in `data` is what lets a renamed spun-up restart load at `nIter0=1`.

So the premise behind the question, that we need NASA access to reach the model, is false. What is
missing is narrower.

## 2. Exactly one input tree is missing, and an account would not obviously fix it

`era_xx` / `era_xx_it42_v2` (atmospheric forcing) and `nbp19_dmenemen_public_llc270` are **not** on
the public NAS portal. The forcing lives on ECCO Drive, which is Earthdata-gated and **currently not
serving**: TCP:443 refused from four independent vantage points since 2026-07-28, while
`podaac.jpl`, `urs.earthdata` and `nas.nasa.gov` all return 200. So the host is down, not our access.

An Earthdata Login is free and takes about 15 minutes. Whether an ordinary registrant can read
`ECCO2/LLC270/era_xx_it42_v2` specifically is **unverified** (verified only for the 1-degree Release5
path), so register, retry when the host returns, and ask publicly on the
`MITgcm-contrib/ecco_darwin` issue tracker in parallel. That last costs 30 minutes and no goodwill.

## 3. The nearest real blocker is scientific and costs zero compute

**Our recovery is per-cell. Darwin has no slot for that.**

| parameter | where it lives in Darwin | shape |
|---|---|---|
| `ALPFE` | `data.darwin` `&DARWIN_PARAMS` | single **global scalar** |
| `SCAV_RAT` | `data.darwin` `&DARWIN_PARAMS` | single **global scalar** |
| `R_PICPOC` | `data.traits` `&DARWIN_TRAITS` | 7-entry array over **plankton type** |
| `PALAT` (diatomgraz) | `data.traits` `&DARWIN_TRAITS` | array over **plankton type** |

**None of the four has a spatial dimension.** So Route B requires a stated rule for reducing the
recovered per-cell field to a scalar *before* any forward run, and the global-scalar configuration is
precisely the one we measured at **0/50** on the DOF ladder.

That is uncomfortable and it is the most useful thing this investigation produced. It is a decision,
not a job: it costs no compute, it gates every route, and the honest reduction may make Route B a
weaker test than #163 currently assumes. Better to find that out now than after a run campaign.

This also sharpens Jon's 2026-07-07 correction, that `alpfe` is a global scalar on already-soluble
iron, from a remark about one parameter into a structural statement about all four.

## 4. What to actually do

1. **Decide the per-cell → scalar reduction rule** and restate the Route B hypothesis. Zero compute,
   about a day of thinking, and it gates everything else.
2. **Register an Earthdata Login** (15 min, free) and retry ECCO Drive when it returns. Ask on the
   `ecco_darwin` issue tracker in parallel.
3. **Run the `v05/3deg` plumbing test this week regardless.** 21.8 MB, everything committed in-repo,
   serial or 8 ranks, ships reference output, and its `data.traits` is the **byte-identical git blob**
   to llc270's (5334 bytes). So the trait-override trap the perturbation recipe was written to catch
   is bit-for-bit the same, and this proves a namelist edit actually reaches the model before
   anything expensive runs. Caveat: the shipped verification is 4 timesteps while the namelist says
   24, so `nTimeSteps` needs editing before the readme's `%MON` diff comes out clean.
4. **Then one baseline plus one perturbation at llc270**, to replace every unmeasured cost estimate
   with a real one. Disclose that 468 ranks is not Carroll's decomposition and MITgcm is not
   bit-reproducible across decompositions: defensible as a fixed-decomposition difference study,
   **not** a reproduction.

## 5. Not worth doing

- **NAS/HECC account.** Eligibility requires a NASA grant, cooperative agreement, contract or WBS
  number, a Space Act Agreement or MOA/MOU, or NASA center employment. Only a PI can submit an
  allocation request, and the NASA Identity form needs a project GID that exists only after an award.
  The 2027 operational-year window closed **2026-07-20**. The people who own the missing files are at
  JPL, so the account routes through the same people as a file request, with paperwork added. And we
  do not need the machine time.
- **Asking Jon to run the 17-deck ensemble.** We already did the build he would have had to do.
  `docs/findings/2026-07-25_jon_gcm_ensemble_ask_DRAFT.md` already concluded "I think we can run it on
  Explorer ourselves."
- **Standing up `v05/1deg` as a cheaper vehicle.** It needs a *second* full build from a different
  fork (`jahn/darwin3`, branch `backport_ckpt68g`) plus three non-public directories from two people.
  Given llc270 is already built, this is not the cheap path.
- **Regional CCS / RedSea.** All 31 biogeochemical tracers are prescribed at three open boundaries,
  which makes it a poor testbed for `scav_rat`, the sole binding leg.
