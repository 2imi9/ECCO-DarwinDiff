# Session handoff, 2026-07-30 (baseline-audit session, context-overflowed)

The predecessor session ("ECCO-DarwinDiff baseline audit") reached **1718 messages** and now returns
`Prompt is too long` on every turn. `/condense` cannot rescue it, because condensing itself needs a
model turn that overflows. Its work is **not lost**: PR **#208 is merged as `1648c73`**, and the
registry-driven trust gate now coexists on `main` with the inert-anchor guard added the same day.

This note is reconstructed from that session's transcript. Sections marked **UNRECOVERED** are
things the transcript rendering dropped. Do not treat this note as complete where it says it is not.

---

## Do this first

**Read the pre-existing daily emulator result.** The session's last living act was noticing that a
daily emulator had *already been trained* before it started, and saying "there may already be a
daily result. Let me read it." It died mid-command.

```bash
ssh aicr 'ls -la /scratch/qi_zim_neu/daily_v5/ | head -40
cat /scratch/qi_zim_neu/daily_v5/daily_train.json'
```

Artifacts to read: `daily_train.json`, `daily_emulator_eqpac.safetensors`, `daily_eqpac_cube.npz`.

**The question it answers.** Job **235995** measured that daily cadence is a decisive negative for
the *parameter learner*: anomaly variance fraction is the same daily as monthly (SST 0.113 vs 0.134,
surfChl1 0.761 vs 0.756, surfChl2 0.777 vs 0.771), and daily lag-1 r of 0.994 to 0.996 gives
**n_eff of about 17 to 24 out of ~8,700 steps**, fewer than the 158 monthly steps already in hand.
But that job explicitly left the *emulator* case open, because for a forward operator autocorrelation
is partly signal rather than noise. A daily emulator already exists. Reading its metrics settles the
emulator half without spending any compute.

The bar it has to clear: the monthly ensemble scores **-0.161 +/- 0.015 against a per-cell seasonal
AR(1) baseline**, with a useful horizon of **1 step**. If the daily model does not beat seasonal
AR(1), daily is closed for both tracks and that is a publishable negative.

---

## Standing directives (carry these over, a fresh session will violate them otherwise)

From the predecessor's GUARDRAILS line, verbatim:

> "verify_run-gate every number and quote PER-AOI ONLY; docs/paper/main.tex is LOCAL-ONLY (diffs,
> wait for my OK, never git-track); commit only when I ask (no Co-Authored-By, non-squash); AICR for
> surrogate runs, Explorer for the GCM build; login nodes reset long ssh so use server-side
> dependent Slurm jobs; simple warm style, no em dashes, no confidence percentages. Never report a
> count without its architecture-matched untrained baseline."

Plus:

- **Never report a count without its architecture-matched untrained baseline.** Baselines are real
  pipeline runs at `NB23_LR=0`, `NB23_N_EPOCHS=1`, n=50, `verify_run` exit 0. Use `prior_mld_n50`
  for MLD arms and `prior_ctrl_n50` for non-MLD arms.
- **n=50 per arm.** "If an arm is short of 50 seeds, refill the missing blocks. Do not grade a
  partial arm as complete."
- **List `/scratch/qi_zim_neu` before staging anything.** This is the rule the session learned the
  hard way (see waste, below).
- **Report relative error alongside pass/fail bands.** The user pushed back on binary +/-40%
  reporting. Median relative error: alpfe 7.6% flagship / 6.1% obs-only, scav_rat 33% / 46%,
  R_PICPOC 22% / 32%, diatomgraz 60% / 11%. "50/50 recovered" means inside +/-40%, not accurate:
  R_PICPOC is 46/50 Cal-grade but only **1/50 Excellent**.
- **Draft email, never send it.** Jon replied 2026-07-28; a draft reply sits in the crosscheck doc,
  unsent, by design.

### Explicitly ruled out

- The per-cell-vs-global 0/50-vs-50/50 contrast as evidence that the rain ratio varies regionally,
  in anything sent to Jon. That is a fact about our estimator. The Daniels 1.6x is the real evidence.
- Gating the UDE on a 0.30 dex span. Gate on **aliasing correlation < 0.95** (0.311 dex already
  failed at aliasing 0.9908).
- Backpropagating "failure configs" into the network when failure means "landed far from Carroll".
  That is training on the answer and makes every recovery count circular. Physically-invalid failures
  are already handled by `POSI_W` and the PINN term.
- AGU Aug 5 as a deadline. Dropped. `docs/agu26_abstract_draft.md` is still tracked and awaiting a
  decision, not deleted.
- Heavy compute on the AICR login node. Bare recursive wget of the NASA daily tree (~5 TB).
  Multi-process CUDA on Windows. Grading a partial arm.

---

## What the predecessor completed

**Parameter learner**

- PR #208 merged as `1648c73` after reconciling 62 commits of main drift. Suite 549 to 664 passing.
- Two real grader bugs fixed: `grade_all_params.py:105` and `contract_report.py:119` hardcoded `>= 2`
  for the per-AOI majority, grading every single-AOI run 0/n; `grade_all_params.py:192` had a
  backslash in an f-string (SyntaxError below Python 3.12).
- **Corruption audit: no published number was corrupted.** Four independent grader implementations
  agree on `ctrl_n50` (49 / 26 / 2 / 50, trio 25/50). The single-AOI bug was latent.
- **DOF ladder, inverted U** (trio per-AOI): global scalar 6 values 0/50, shared DINN 406 **25/50**,
  per-AOI DINN 1218 3/50, free per-cell field 17,106 0/40. Mechanism is cross-AOI pooling, not
  capacity.
- **Strict observations-only at n=50** (`obsonly_mld_litic`, exit 0): alpfe 50/50, diatomgraz 50/50,
  R_PICPOC 43/50, scav_rat 0/50. Thresholds pre-registered with zero JSONs on disk.
- **R_PICPOC is a global exact structural null** under `realdaniels` (job 233265): the anchor is
  rank-1 with stiff direction R_PICPOC = -1.0, Fisher info 7.40e-01 vs <=4.5e-09 for everything else.
  100x scaling leaves DFe, diatoms and POC bitwise identical.
- **Collapse statistic** (array 233419): scav_rat is 26/50 arithmetic vs 13/50 geometric.
- Novelty challenged in all six fields, none survived: `docs/findings/2026-07-29_contract_prior_art.md`.
- Issues #209, #210, #211, #212 filed. #120 and #163 updated.

**Three retractions it made of its own same-day work** (this register is expected, keep it):
the 10^6 CRLB ratio was `1/ridge` and not a measurement; "6/50 anchor-off is chance-level P=0.078"
was wrong (Fisher exact p=0.0133); `PARAM_LOG_SCALE` defaults to `""`, so **every published run uses
the linear bounding map despite `Param.scale="log"`**, a factor-of-five prior bug.

**Daily data**

- Staging verified clean: 58,755 / 58,755 files, 208 GB, zero wrong-size, era 1992-01-02 to
  2018-12-31. `delta_t = 1200 s` confirmed at source from a `.meta` sidecar.
- Portal method fixed: fetch each 4.1 MB index once, parse explicit URLs, download from manifest.
  **2,481 files/min versus 45 for a recursive crawl, about 55x.**
- Land-mask bug caught before it corrupted a cube: land is `0.0`, not `-999`. Use `Depth > 0`
  (546,695 ocean cells), giving **44,001 ocean bins**, consistent with `bin_average`'s 44,730.
- **The 51%-missing-months discovery.** The local monthly mirror has DIC 278, ALK 283, PIC 280,
  POC 287, FeT 290, Chl1 289 of 324, each missing a *different* ~11%, so the six-way intersection is
  **158 of 324**. That is where `T=158` and `n_train_pairs=110` come from, which means
  **"data quantity is flat from n=55" was measured on an axis crippled by a mirroring accident, not
  an archive limit.** This is a live thread worth pulling.

---

## Waste to not repeat

1. `/scratch/qi_zim_neu/v05_daily` (218 GB) **duplicates** `/scratch/qi_zim_neu/daily_v5` (2.9 TB,
   all 17 daily variables). The session re-downloaded data that already existed.
2. `daily_global_halfdeg_cube.npz` (42 GB) and `daily_global_1deg_cube.npz` (13 GB) already existed
   before it built its own ~9.1 GB cube.
3. **Do not stage daily `surfPCO2`.** Its `fldList` is `pCO2` and it is a 50-level byte duplicate of
   the `pCO2` directory despite the "surf" name. Costs 34.8 GiB for nothing. Monthly `surfPCO2` *is*
   genuinely 2-D.
4. Do not plan a monthly refill against the 237-files / 41.8 GiB audit. That audited the **local**
   mirror. AICR has no monthly tracer tree at all, so the equivalent there is a ~370 GB stage.

---

## Cluster state

| path | size | what | trust |
|---|---|---|---|
| `/scratch/qi_zim_neu` | **3.6 TB** | scratch root | measured |
| `…/daily_v5` | **2.9 TB** | all 17 daily vars + `daily_eqpac_cube.npz`, `daily_emulator_eqpac.safetensors`, `daily_train.json`, `download.sbatch` | the key discovery |
| `…/monthly_v5` | 302 GB | monthly v05 | not audited |
| `…/daily_global_halfdeg_cube.npz` | 42 GB | 0.5 deg cube | provenance unclear |
| `…/daily_global_1deg_cube.npz` | 13 GB | 1 deg cube | provenance unclear, and 13 GB != the 9.1 GB this session built |
| `…/global3d_L10_cube.npz` | 17 GB | 3-D, 10 levels | not audited |
| `…/v05_daily` | 218 GB | **this session's duplicate** | files verified, but redundant |
| `…/daily/v05_binavg_1deg.nc` | 1.87 GB | NASA `bin_average` | verified: **MONTHLY despite the path name**, 276 steps 1995-01 to 2017-12, 44,730 cells |
| `…/overnight/` | | run outputs per arm + `prior_ctrl_n50`, `prior_mld_n50`, `ctrl_n50` | yes |
| `~/emulator_poc` | | tree the Slurm arrays execute from | yes |
| `~/emulator_poc_pw` | | second clone, so edits cannot hit a running array | yes |

Submission shape: `--account=p2026_0089_neu`, `--partition=b200-batch`. QOS caps **32 GPUs** and
**512 CPUs**. Graders run as dependent jobs (`--dependency=afterany:<job>_*` plus `tee`).

Jobs referenced: 232937 (20-task array), 232938 and 233158 (graders), 233265 (GN-Fisher),
233385 (Daniels), 233419 (collapse), 235416 (global-scalar obs-only), 235995 (daily vs monthly n_eff).

---

## Traps

**Process**

- **A Slurm job can report `COMPLETED` while doing nothing.** The first GN-Fisher job built its
  sbatch inside a quoted ssh heredoc, so `$HOME` expanded on the **Windows** side. It cd'd nowhere,
  never sourced the venv, died on `ModuleNotFoundError: torch`, and exited 0. Fixed with an import
  guard plus `exit $fail`.
- **Editing `~/emulator_poc` hits any array task that has not started yet.** Hence the second tree.
- **`pytest | tail` masks exit status** in an `&&` chain. Capture `rc=$?` directly.
- **Backticks in `gh issue create -b` and `git commit -m` get command-substituted.** This mangled
  issue #212 and silently stripped a word from a commit message. Use `-F` or a quoted heredoc.

**Data**

- **`surfChl4` is negative in 100% of ocean cells** at the median timestep. surfChl5 41.3%,
  surfChl3 39.7%, surfChl2 26.5%, surfChl1 9.4%. Negatives persist all 27 years, so not spin-up.
  Per-PFT chlorophyll is not trustworthy as a target until `TRAC27`-`TRAC31` are resolved against
  Darwin's tracer table. Log-space training needs clipping, and the clipped fraction must be recorded.
  SST (26.1% negative, min -1.961 C, max 33.08 C) is physical and validates the pipeline end to end.
- **`apCO2` means different things in the two trees.** Monthly is `EXFapco2` (atmospheric), daily is
  `surfpCO2` (seawater). There is **no atmospheric pCO2 at daily cadence**. Routing the daily tree
  through `TRAC_MAPPING` (`src/darwindiff/llc270_loader.py:54-86`) mislabels it.
- **The daily archive has no DIC, ALK, PIC, POC or FeT.** 17 dirs, 15 unique fields, all surface.
  The current prognostic set cannot be trained daily.
- **Existing "global 1 deg" runs are not on a 1 deg grid.** `--aoi-bounds -80,89.75,...` gives 171
  rows at 0.998538 deg, never co-registered with `bin_average` or any satellite regrid.
- **Portal listings truncate inconsistently.** Two scrapes of the same directory gave
  `max=355320, n=9796` then `max=553824, n=7638`. Never establish era or file count by scraping.
  Missing files return **HTTP 500, not 404**.

---

## Open items

1. **Read the daily emulator result.** Highest value, costs nothing. See the top of this note.
2. **Move the cube off `/scratch`.** The session fetched `https://docs.aicr.ai/files/overview/` and
   concluded "the authoritative policy says the cube is in the wrong place", pointing at a `/work`
   path. `/scratch` is on a **30-day purge**. **UNRECOVERED:** the verbatim policy and the exact
   `/work` path. Re-fetch the page.
3. **Era conflict, one day.** The manifest says the daily era ends **2018-12-31**; a HEAD probe of
   iter 710064 returned HTTP 500 for both surfChl1 and SST, implying **2018-12-30**. Both are in the
   transcript. Resolve before anchoring a pre-registered test.
4. **The 158-of-324 mirroring accident.** "Data quantity is flat from n=55" rests on it. Refilling
   the monthly mirror could reopen the data-quantity axis. On AICR this is a ~370 GB stage.
5. **`PARAM_LOG_SCALE` defaults to `""`.** Every published run used the linear map despite
   `Param.scale="log"`. Decide whether to re-run or to document.
6. **`verify_run.py` STRADDLE flags are advisory** and never touch the exit code, so a run can exit
   0 VERIFIED while printing a metric inversion. The inert-term check added 2026-07-29 does gate.
   The per-AOI majority rule has **eight implementations**, two of which were wrong. There is still
   **no config-selection null**.
7. **Duplicate cleanup.** `v05_daily` (218 GB) is redundant. Confirm against `daily_v5` before
   deleting anything.

## UNRECOVERED from the transcript

- The exact final Bash command (transcript renders tool calls without arguments).
- The verbatim docs.aicr.ai storage policy and the correct `/work` path.
- The user's verbatim FourCastNet message and the message that triggered the relative-accuracy
  correction. Only the replies survive.
- The user's verbatim answers to the six `/grill-me` questions. Recorded only as "accepted all five".
- Whether `daily_global_{halfdeg,1deg}_cube.npz` pre-existed or were written by that session.
- The absolute path of the cube that session built.
