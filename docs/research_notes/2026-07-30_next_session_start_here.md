# START HERE — next session prompt (2026-07-30)

Paste the block below to resume. Self-contained.
Rewritten 2026-07-29 ~16:30 UTC at the end of the working session, replacing the earlier version
whose premises are now stale (it assumed array 232937 would have finished overnight; it was actually
submitted at 11:02 EDT that day and was still draining at session end).

---

Resume ECCO-DarwinDiff. Read these first, then confirm the shape back before acting:

1. `docs/findings/2026-07-29_preregistration_obsonly_and_ladder.md` — **read before any result**
2. `docs/findings/2026-07-29_gnfisher_structural_clause.md` — new, verified, job 233265
3. `docs/findings/2026-07-28_session_evidence_log.md` — every prior number with job IDs and raw paths
4. `docs/findings/2026-07-29_jon_reply_crosscheck.md` and `..._ude_scaling_claim_audit.md`
5. `STATUS.md`

Board: **https://claude.ai/code/artifact/e2546746-1209-46ab-b607-70c5ed678786**
(33 claims scored on confidence / accuracy / completeness, each beside its measured untrained baseline)

## FIRST ACTION: two graders, not one

```
/scratch/qi_zim_neu/overnight/GRADED_232938.log      # obs-only, 4 arms
/scratch/qi_zim_neu/ladder/GRADED_LADDER_233158.log  # parameterisation ladder, 3 arms
```

**Do not grade a partial arm as complete.** Check `squeue -u $USER` and the per-arm JSON counts
first, and refill missing blocks rather than grading short.

### Array 232937 — obs-only

| tasks | arm | question | baseline |
|---|---|---|---|
| 0-4 | `obsonly_mld` | does MLD lift `diatomgraz` on real obs? **2-of-4 vs 3-of-4** | `prior_mld_n50` (2ch) |
| 5-9 | `obsonly_litic` | how much of `alpfe`/`R_PICPOC` rests on Darwin's pickup? | `prior_ctrl_n50` (1ch) |
| 10-14 | `obsonly_mld_litic` | **the strict arm**: obs-only targets AND literature IC | `prior_mld_n50` (2ch) |
| 15-19 | `chl2w20` | does the `Biggrow` dose-response continue past W=8? | `prior_ctrl_n50` (1ch) |

### Array 233157 — the parameterisation ladder (runs from the `~/emulator_poc_pw` CLONE)

| tasks | arm | baseline |
|---|---|---|
| 0-4 | `peraoi_dinn` (`PER_AOI_DINN=1`, 3×406 weights) | `prior_ctrl_n50` (architecturally identical) |
| 5-9 | `pointwise` (`POINTWISE=1`, 17,106 free values on ocean cells) | `pointwise_prior`, from arm 3 |
| 10-14 | `pointwise_prior` (`POINTWISE=1 NB23_LR=0 NB23_N_EPOCHS=1`) | is itself the baseline |

## THE PRE-REGISTRATION IS BINDING

Written 15:39:24 UTC with **zero JSONs on disk in all four arms**, task 0 at epoch 500 of 2000, and
the ladder not yet submitted. Do not reinterpret outcomes against it.

Counts needed to clear the measured architecture-matched baseline at P < 0.05:

| param | 1ch base | **1ch k\*** | 2ch base | **2ch k\*** |
|---|---|---|---|---|
| alpfe | 10/50 | **16** | 16/50 | **23** |
| scav_rat | 0/50 | **7** | 0/50 | **7** |
| Smallgrow | 6/50 | **11** | 7/50 | **12** |
| Biggrow | 0/50 | **7** | 0/50 | **7** |
| diatomgraz | 32/50 | **38** | 34/50 | **40** |
| R_PICPOC | 0/50 | **7** | 0/50 | **7** |

Zero-count baselines use the rule-of-three floor 3/50 = 0.06, deliberately conservative. The
asymmetry is the point: `diatomgraz` needs **40 of 50** to say anything at all while `R_PICPOC`
needs **7**. That is a fact about the bounds, not about the ocean.

**Headline rule, fixed in advance:** observations-only becomes the headline **only if
`obsonly_mld_litic` clears 3-of-4** (alpfe ≥23, R_PICPOC ≥7, diatomgraz ≥40, with `scav_rat` expected
at 0 and reported as a diagnosed failure). 2-of-4 keeps the flagship and makes obs-only the strongest
robustness section, which is not a demotion. Accepted cost either way: the joint trio goes 25/50 → 0/50.

**Ladder rule, fixed in advance:** free field **worse** than DINN → the network regularises and
"per-cell **architecture** is load-bearing" is earned. **Equal** → scope to per-cell **structure** and
drop the word architecture from STATUS and the abstract. **Better** → degrees of freedom are doing the
work; report it first, not last. The free field is *expected* to fit the training loss better (~6 free
values per ocean cell against 178 absolute-anchor observations in total, of which 52 are GEOTRACES
surface iron bins across the three AOIs); the pre-registered metric is
per-AOI recovery against Carroll, **not** training loss.

## WHAT LANDED THIS SESSION

- **PR [#208](https://github.com/2imi9/ECCO-DarwinDiff/pull/208)**, 5 commits, branch
  `feat/identifiability-contract-and-ladder`. Suite **561 passed**, 19 skipped, 1 xfailed.
  `verify_run.py` is now registry-driven. Previously it hardcoded `PARAMS` and `CARROLL`, so a
  seventh parameter would have been trained, graded and written by the runner, **skipped by the
  gate**, and the run would still have exited 0 VERIFIED. It now also rejects artifacts carrying
  parameters it does not know. `CONTRIBUTING` gained step 9. `PerCellFreeField` + `POINTWISE` added.
- **GN-Fisher structural clause landed** (job 233265, exit 0). `alpfe`/`scav_rat` under real
  GEOTRACES iron, `diatomgraz` under real bSi. `R_PICPOC` Fisher information is **identically
  0.00e+00 under both** — the formal statement behind the 50/50-vs-6/50 anchor contrast. It
  independently reproduces iron 2x2 condition **2.224** and conditional corr **−0.155** on the real
  loss, and measures the counterfactual in the same job (under bSi the same pair reads cond 9340,
  corr +0.9998). Two orderings from the old synthetic table do **not** survive: it ranked `scav_rat`
  last where its own observable makes it highest, and gave `R_PICPOC` nonzero information where the
  real answer is exactly zero.
- **New issues** [#209](https://github.com/2imi9/ECCO-DarwinDiff/issues/209) pointwise control,
  [#210](https://github.com/2imi9/ECCO-DarwinDiff/issues/210) declarative `Unknown` schema,
  [#211](https://github.com/2imi9/ECCO-DarwinDiff/issues/211) `realdaniels` residual loss.
  Status comments on #120 and #163.

## DECISIONS TAKEN (do not re-litigate)

1. **Run the pointwise arm and gate the structural claim on it.** Until it lands, say per-cell
   "structure", not "architecture". Prompted by ADCME (Xu & Darve), whose standard control for a
   neural field is a free pointwise field, and whose taxonomy puts our DINN in the *function inverse*
   row and the UDE closures in the harder *relation inverse* row.
2. **Manuscript #1 stays the identifiability study** and names the contract as an explicit protocol,
   reporting all four clauses for all six parameters. The declarative wrapper is #210 and is the next
   build, not a rewrite of #1.
3. **Split the Jon reply.** Part 1 (the stable half) is drafted at
   `docs/research_notes/2026-07-29_jon_reply_part1_DRAFT.md` and is **not sent** — Lucas sends it.
   Part 2 (obs-only at n=50, IC dependency closed) goes after the arrays. Reason for splitting: the
   earlier full draft asked Jon to arbitrate the obs-only headline, but `obsonly_mld_litic` answers
   the IC half of that question ourselves.
4. **Run the real-loss Fisher table now, defer clean profile likelihoods.** Done. Growth and Si
   profiles stay excluded because 9 of 13 runs failed a convergence guard; name the gap rather than
   quietly using the artifact.

## STILL OPEN

- **AGU abstract, deadline Aug 5.** The refuted 35/50 is out; the obs-only sentence waits on
  `obsonly_mld_litic`. Roughly 6 days of slack.
- **Send Jon part 1**, then part 2 after the arrays.
- **Does observations-only become the headline?** Answered by the pre-registered rule, not by taste.
- **#211 `realdaniels`** is the missing positive structural clause for `R_PICPOC`.

## GOTCHAS THAT COST TIME TODAY

- **A Slurm job can report `COMPLETED` while doing nothing.** Job 233168 exited 0 having produced no
  artifacts: an sbatch built inside a quoted ssh heredoc let `$HOME` expand on the *workstation*, so
  the job `cd`'d to a nonexistent path, never sourced the venv, died on `ModuleNotFoundError: torch`,
  and nothing checked the return code. **Write sbatch files locally and pipe them through
  `tr -d '\r'`**, never assemble them inside a quoted ssh heredoc, and always guard with an explicit
  import check plus `exit $fail`.
- **`~/emulator_poc` must stay untouched until 232937 fully drains.** Every task reads the tree at
  its own start time, so an edit mid-array splits the batch. Pinned md5s that all 20 tasks stamp into
  their own provenance header: networks `b12ec42d`, runner `c6622e10`. New code runs from
  `~/emulator_poc_pw`, a clone whose `covar_env_common.sh` is retargeted. **After 232937 finishes:**
  `cat src/darwindiff/networks.py | ssh aicr "tr -d '\r' > \$HOME/emulator_poc/src/darwindiff/networks.py"`
- **Codex review is rate-limited** on PR #208 ("reached your Codex usage limits for code reviews").
  Greptile had not commented by session end. Neither bot's silence means clean.
- **No CI run triggered** on the branch. `.github/workflows/tests.yml` exists but `gh pr checks 208`
  reports no checks. Check its trigger conditions before relying on it as a merge gate.
- **Smoke-test a new code path on one GPU task before queuing an array.** The `POINTWISE` smoke was
  27 seconds (job 233156) and validated the whole chain including JSON metadata; a crash discovered
  at task 0 of 15 would have cost the evening.

## GUARDRAILS

`verify_run`-gate every number and quote **per-AOI only**. Never report a count without its
architecture-matched untrained baseline. `docs/paper/main.tex` is LOCAL-ONLY, never git-track it.
Commit only when asked, no `Co-Authored-By`, non-squash merges. AICR for surrogate runs, Explorer for
the GCM build. Login nodes reset long ssh, so use server-side dependent Slurm jobs. Simple warm
style, no em dashes, no confidence percentages.
