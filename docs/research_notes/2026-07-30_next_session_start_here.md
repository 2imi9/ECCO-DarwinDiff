# START HERE — next session prompt (2026-07-30)

Paste the block below to resume. Self-contained.

---

Resume ECCO-DarwinDiff. Read these first, then confirm the shape back before acting:

1. `docs/findings/2026-07-28_session_evidence_log.md` — every number from the last session, with job IDs and raw paths
2. `docs/findings/2026-07-29_jon_reply_crosscheck.md` — Jon's reply audited against the repo, plus a draft reply
3. `docs/findings/2026-07-29_ude_scaling_claim_audit.md` — whether our scaling pitch survives the UDE proposal
4. `STATUS.md`

Plus the memory index and the SessionStart open-issues list.

## FIRST ACTION: read the overnight results

`/scratch/qi_zim_neu/overnight/GRADED_232938.log` on AICR. Array job **232937** (20 tasks, n=50 per
arm) with a dependent grader on `afterany`, so the log exists even if the array partly failed. It
grades every arm against its **architecture-matched** untrained baseline and prints `verify_run`
verdicts. Four arms:

| arm | question | baseline |
|---|---|---|
| `obsonly_mld` | does MLD lift `diatomgraz` in an obs-only fit? **2-of-4 vs 3-of-4 paper** | `prior_mld_n50` (2ch) |
| `obsonly_litic` | how much of surviving `alpfe`/`R_PICPOC` rests on Darwin's pickup? | `prior_ctrl_n50` (1ch) |
| `obsonly_mld_litic` | both at once: obs-only targets AND a literature IC | `prior_mld_n50` (2ch) |
| `chl2w20` | does the `Biggrow` dose-response continue past W=8? | `prior_ctrl_n50` (1ch) |

Known risk: three tasks of an earlier batch hit a 4h wall under node contention. This one requests
10h and 8 CPUs. If arms are short of 50 seeds, refill the missing blocks rather than grading a partial
arm as if it were complete.

**Provenance note, deliberate.** AICR's `src/darwindiff/networks.py` is one commit behind the local
working tree: local made `n_outputs` default to `N_PARAMS` instead of the literal `6`. This is
**numerically a no-op** here, because `N_PARAMS == 6` and the runner passes `n_outputs=N_PARAMS`
explicitly at every construction site. It was left unsynced ON PURPOSE so that all 20 array tasks run
byte-identical code; syncing mid-batch would have split task 0 from tasks 1-19 for no scientific gain.
**Sync it after the batch finishes**, before any new run:
`cat src/darwindiff/networks.py | ssh aicr "tr -d '\r' > \$HOME/emulator_poc/src/darwindiff/networks.py"`.
Every other file (`carroll6.py`, the runner, `verify_run.py`, `grade_all_params.py`) is confirmed
byte-identical between local and AICR after line-ending normalisation.

## STATE — what changed, and it is mostly methodological

**The central change: recovery counts are now graded against a MEASURED untrained baseline.** Running
the real pipeline at `NB23_LR=0, NB23_N_EPOCHS=1` leaves networks at initialisation and scores them
through the identical path, so the counts *are* the chance rate. n=50, `verify_run` exit 0. Measured:
`diatomgraz` **0.640**, `alpfe` 0.200, `Smallgrow` 0.120, `scav_rat` / `Biggrow` / `R_PICPOC` **0.000**,
untrained trio **0/50**.

**Consequences, all verified:**

- **`diatomgraz` 35/50 is RETIRED.** Against an architecture-matched untrained 34/50 it is **P = 0.447**,
  one seed better than nothing. Cause is structural: its bounds put the Cal band at 52.8 % of the range
  with the midpoint *inside* it. The separate `geo1+MLD` **10/10** stands (P = 0.021) and remains the
  headline verdict. Corrections applied to STATUS and the AGU abstract.
- **`R_PICPOC`'s anchor story got STRONGER.** The anchor-off control at 6/50 is itself chance-level
  (P = 0.078), so the contrast is 50/50 decisive versus *nothing*.
- **alpfe 49/50, scav_rat 26/50 and 41/50, R_PICPOC 50/50, trio 25/50 are all DECISIVE** against the
  measured null. The flagship also reproduced independently (scav_rat 26/50 vs published 25/50) on
  different hardware, compiler and torch build.
- **Observations-only is graded** (`coord_anchors_pinnOFF`, n=50, verify_run exit 0):
  `alpfe` **50/50**, `R_PICPOC` **28/50**, `scav_rat` **0/50**, `diatomgraz` 11/50, **trio 0/50**.
  Two of four survive on real measurements alone. It still uses Darwin ICs and Darwin forcing, so it is
  observations-only *targets*, not end-to-end independence. That is what `obsonly_litic` tests.
- **A straddle nearly published a false result.** In that run `scav_rat` reads **40/50 cell-weighted**
  and **0/50 per-AOI**. Opposite conclusion, not a rounding difference.
- **Growth pair reframed.** They are NOT mutually degenerate (2x2 cond 1.20, least degenerate of all 15
  pairs) and NOT signal-deleted (z-scoring keeps 0.95 of `Biggrow`). They are **information-starved**
  (rel Fisher info 0.055 / 0.053 vs `diatomgraz` 1.000). `Biggrow`'s signal is concentrated in Chl2;
  `Smallgrow`'s is diffuse and routed through FeT. New lever `CHL2_W_EXTRA` took `Biggrow` 6/50 → 12/50
  while `Smallgrow` stayed flat (Fisher p = 1.000, the discriminating prediction). Arm-to-arm p = 0.192,
  so directional only.
- **scav_rat log-scale bounding: NOT adopted.** 26/50 → 35/50 at p = 0.100; earned-only 0.52 → 0.71 at
  p = 0.086 (so the gain is *not* the log map's 16 % head start); but it costs `R_PICPOC` 50/50 → 45/50
  at p = 0.056. Implemented behind `PARAM_LOG_SCALE`, default off, bit-identical when unset.

**The tool itself was hardened** after a fair criticism that it was not good enough as a scientific
instrument:

- `verify_run.py` now leads with **per-AOI**, marks cell-weighted `[DO NOT QUOTE]`, has a **generalised
  straddle guard** for every parameter (was R_PICPOC-only), a `NO_PER_AOI_DATA` flag, `--baseline` with
  per-parameter effect sizes and a rule-of-three floor, and `--require-baseline` → **exit 6**.
- Registry: `N_PARAMS` derived (was 85 hardcoded 6s, zero derived), `Param.scale` for log bounding,
  `Param.model_value` recording that v05 integrates `R_PICPOC` = 0.0418860 against the published
  0.04245, and `prior_midpoint_offset()` with a test that fails any new parameter whose prior sits
  inside the pass band (`diatomgraz` is an xfail in `KNOWN_PRIOR_CONTAMINATED`).
- New `scripts/analysis/grade_all_params.py`, cross-validated to agree exactly with the existing
  trusted grader.
- Suite: **549 passed, 19 skipped, 1 xfailed.**

## JON'S REPLY — answered, not yet sent

He replied 2026-07-28. Draft reply is in the crosscheck doc. Highlights:

- **His open question is answered.** The three rain ratio values are 0.04245 (`data.darwin`, **inert**),
  0.0418860 (`data.traits`, **what runs**, types 2 and 3) and 0.0 (non-calcifiers). `DARWIN_READ_TRAITS`
  at `darwin_init_fixed.F:382` overwrites `DARWIN_GENERATE_RANDOM` at :357. Proof it is live: the two
  files disagree. **Editing `val_R_PICPOC` does nothing.** `alpfe`/`scav_rat` are the opposite case and
  are safe to edit in `data.darwin`.
- **He upgrades one of our nulls.** Every Ω test we ran was against surface calcite *production*, never
  dissolution. If Ω mainly governs dissolution, our null is what his mechanism predicts. Also v05 has no
  `disscSelect` switch at all.
- **His growth-pair intuition is confirmed and split.** He asked "perhaps chlorophyll might help?" It
  helps `Biggrow` specifically, via Chl2, and not `Smallgrow`.
- **Do not send** our per-cell-vs-global 0/50-vs-50/50 as evidence that the rain ratio varies
  regionally. It is a fact about our estimator. The Daniels 1.6x is the real evidence.

## UDE — yes with conditions

The audit found a real inconsistency. Our scaling pitch is a claim about **cost** (one backward pass vs
an N+1 ensemble) and that survives a UDE intact. But a few doc sentences upgraded it to a claim about
**identifiability**, which our own evidence contradicts. `ScavClosure` is **67 free parameters** against
`scav_rat`'s 1; the calcite closure as run is **353**. The 2026-07-21 stress test: 0.0065 relative error
on the visited DFe band, **2.877 on the full range**, identical across all four regularisation configs.

Overclaims fixed in `ecco_darwin_parameter_inventory.md`, `dinn_design.md`, `docs/index.md`. The
inventory fix had been written by our own audit on 2026-07-19 and left unapplied for nine days.

**Cheapest next step for the UDE, do this before booking any GPU:** wire `gather_visited_support` /
`dump_support_npz`, dump the DFe visited support under the intended forcing, and run the Monod branch of
`scripts/symbolic_distill_probe.py`. Gate on the **aliasing correlation below 0.95**, NOT on a 0.30 dex
span (that is the calcite branch's number and 0.311 dex already failed at aliasing 0.9908). CPU-minutes,
and it can veto the whole experiment.

## DECISIONS WAITING ON YOU

1. **Commit and PR everything.** All of it is uncommitted on `main`: `M CONTRIBUTING.md`,
   `M STATUS.md`, `M scripts/verify_run.py`, `M scripts/run_v3.0_joint_multi_aoi.py`,
   `M src/darwindiff/carroll6.py`, `M src/darwindiff/networks.py`, `M docs/index.md`,
   `M docs/dinn_design.md`, `M docs/ecco_darwin_parameter_inventory.md`,
   `M docs/agu26_abstract_draft.md`, plus four new files. Nothing has been through bot review.
2. **AGU abstract, deadline Aug 5.** The refuted 35/50 is removed and replaced with the untrained-baseline
   framing, which is stronger. Needs your read before submission.
3. **Send Jon the reply?** Drafted, not sent.
4. **Does observations-only become the headline?** It is a different and arguably stronger paper: two
   parameters on real measurements alone plus one diagnosable failure, but the flagship's cleanest
   number (trio 25/50) goes to zero. The overnight arms inform this.

## OPEN, not blocked on decisions

- **#163 GCM validation.** Both v05 binaries built on AICR (767-rank and a 468-rank re-tile that fits the
  512-CPU QOS cap), 49 GB staged. **Blocked: 2 of 4 input trees are not public** (`nbp19_dmenemen_public_llc270`
  and `era_xx`), and `ecco.jpl.nasa.gov` refuses connections from four vantage points. Only a slice of
  forcing is needed, so this is a small ask of Jon rather than a resource request.
- **Held-out predictive validation is the real gap.** Until the tool can predict observations it was not
  trained on, it is a consistency check with good hygiene. Returns negative R² in the 0-D box. This is the
  honest answer to "is this good enough as a scientific tool", and it points at Track 2.

## GUARDRAILS

verify_run-gate every number and quote **per-AOI only**; `docs/paper/main.tex` is LOCAL-ONLY (diffs, wait
for OK, never git-track); commit only when asked (no `Co-Authored-By`, non-squash); AICR for surrogate
runs, Explorer for the GCM build; login nodes reset long ssh so use server-side dependent Slurm jobs;
simple warm style, no em dashes, no confidence percentages. Do not report a count without its
architecture-matched untrained baseline.
