# Recovered: a 12-agent daily-data design workflow that finished, then was thrown away

**Date:** 2026-07-30 · **Run:** `wf_64044b84-290` (`darwindiff-daily-data-design`) ·
**Verdict: the growth pair cannot enter the observable denominator through daily data. The route is
structurally circular, and the repo contains the proof.**

## What happened to it

The predecessor session launched a 6-question, 2-stage design workflow (design, then hostile
adversarial review of each design) and it **completed**: 12 of 12 agents returned, about 290 KB of
costed design and recomputed cost audits. The session then hit `Prompt is too long` and was
archived, having consumed **three** incidental facts from it. The rest sat unread on disk.

Nothing was re-run to produce this note. The payload was read back out of the run journal.

## Verdicts

All six designs came back **SOUND-AFTER-FIX**. None SOUND outright, none INFEASIBLE. The reviewers
recomputed the storage and GPU-hour arithmetic independently and it reproduced to the byte in every
case, so cost is not what is wrong with the programme.

| # | design question | verdict |
|---|---|---|
| 1 | cube-spec | SOUND-AFTER-FIX |
| 2 | emulator-training | SOUND-AFTER-FIX |
| 3 | param-learner-seasonal | SOUND-AFTER-FIX |
| 4 | integration-cost | SOUND-AFTER-FIX |
| 5 | validation-and-163 | SOUND-AFTER-FIX |
| 6 | phase-error-risk | SOUND-AFTER-FIX |

## The convergent finding

Five of the six reviews independently reached the same blocker, and it is a **structural** one, not
a tuning problem.

**The seasonal loss requires PFT-resolved chlorophyll, and the only PFT-resolved chlorophyll that
exists is Darwin's own.** Verified in the repo:

- `src/darwindiff/seasonal.py:122-134` — `seasonal_chl_loss_batched` takes `chl_z` of shape
  **`[12, 5, *spatial]`**. Five PFTs.
- `src/darwindiff/seasonal.py:74` — the docstring says, in the repo's own words, "z-scored
  **Darwin** Chl targets".
- MODIS-Aqua L3 supplies **one** total-chlorophyll field. It cannot be reshaped into `[12, 5, ...]`,
  so the stated loss is **not constructible** from the only real time-resolved observable available.

Both branches therefore fail:

- **PFT-resolved target** → Darwin's own Chl1-5 → the model constraining itself against a rescaling
  of terms it already contains. This is precisely the pattern the diatomgraz audit
  (`2026-07-19_diatomgraz_claim_audit.md`, reviewer item M11) already ruled out.
- **Bulk MODIS target** → re-imposes the exact degeneracy that excludes the growth pair in the first
  place. Total chlorophyll gives only the biomass-weighted mean, which is `STATUS.md`'s stated
  mechanism for why `Smallgrow` and `Biggrow` are not separable.

So a daily or seasonal fit does not move the denominator from 4 to 6. It moves the circularity from
the time-mean to the seasonal cycle.

## Two specific defects in the prototype this was built on

**The 9/10 `Smallgrow` result inherits the diatomgraz circularity.** The prototype was fitted to
Darwin's own spatially z-scored Chl (`seasonal.py:74`), recovering a Carroll value that Darwin was
run with.

**Its significance used the wrong null.** The quoted `P = 4.6e-08` is measured against a chance rate
of **0.120**, which comes from the **time-mean** production pipeline (job 227777). A seasonal fit has
its own chance rate, and it has never been measured. This is a direct violation of the project's own
standing rule that no count is reported without its architecture-matched untrained baseline, and it
is the rule that would have caught it.

**A proposed gate threshold was arithmetically wrong.** The design gated on ">= 4/20 at each decoy,
binomial P < 0.05 against a measured 0.100 null". Recomputed here:

| threshold | P(X >= k \| n=20, p=0.10) | passes P < 0.05? |
|---|---|---|
| 4/20 | **0.1330** | no |
| **5/20** | **0.0432** | yes |
| 6/20 | 0.0113 | yes |

The correct per-decoy threshold is **5/20**, not 4/20.

## What survives, and is worth keeping

**The emulator arm is not circular.** Its target is v05 output, which is the correct target for an
emulator, and the design says so plainly: its job is to reproduce v05, phase error included. MODIS
is correctly scoped there to validating v05 rather than the emulator. That arm stands.

The cube specification, the storage arithmetic and the calendar regression check are all sound and
are reusable whatever cadence is chosen.

## How this composes with what was measured after

The workflow was told, as a premise, not to propose staying monthly. Two measurements since then
have overtaken that premise from opposite directions:

- **Job 235995:** daily buys almost no information for the parameter learner. Anomaly variance
  fraction is the same daily as monthly, and daily lag-1 r of 0.994 to 0.996 gives **n_eff of about
  17 to 24 out of ~8,700 steps**, fewer than the 158 monthly steps already held.
- **This note:** even if daily bought information, the growth-pair route it was meant to unlock is
  circular by construction.

**Together those close the daily thread for Track 1.** The denominator stays at 4. The exclusion of
`{Smallgrow, Biggrow}` is not a gap waiting on cadence, it is a property of the available
observables, and that is a cleaner statement than the one the manuscript currently makes.

For Track 2 the question is still open, but the pre-existing daily emulator does **not** answer it:
see `2026-07-30_daily_emulator_artifact_is_contaminated.md`.
