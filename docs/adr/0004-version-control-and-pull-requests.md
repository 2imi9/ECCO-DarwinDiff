# ADR-0004 — version control and pull requests for a single-implementer research repo

**Date:** 2026-08-04 · **Status:** accepted · **Supersedes:** nothing; formalises and corrects
practice previously scattered across `CONTRIBUTING.md` and `CLAUDE.md`.

**Method.** Surveyed the Linux kernel, Kubernetes, Rust, LLVM, Chromium, scientific Python
(NumPy/SciPy/Astropy/xarray), research-software practice (JOSS, FAIR, Zenodo), and the published
empirical work on review effectiveness vs change size. Every convention was then screened against
this repo's actual git history, and kept only where a **concrete failure it would have caught**
could be named. 54 survived, 40 were rejected as ceremony. The rejected list is as load-bearing as
the kept one and is recorded in §7.

---

## 1. The rule in six lines

1. **Push when `git diff --name-only origin/main...HEAD | wc -l` crosses ~40.** Not when the work
   is done.
2. **Hard cap a PR at 100 changed files.** Above it the only reviewer that exists silently declines.
3. **No line-count rule.** Lines are a meaningless axis here.
4. **One PR = one finding**, plus the evidence, corpus row and guard test it needs.
5. **The map quadruple moves together in one commit**, or the mirror lies.
6. **`exp(` commits carry their run provenance as trailers**, because the cluster artifacts expire.

---

## 2. Size: files, never lines

The binding constraint is **mechanical, external, and measured**. Greptile declines any PR over
**100 changed files** with a 154-character stub:

> `Too many files changed for review. (105 files found, 100 file limit)`

Observed twice — **#189** (105 files) and **#180** (125 files). Both merged with **zero review**.
For contrast **#196** (85 files) drew a 3,993-character review and **#204** (46 files) drew 2,759.
The cliff is real and the silence on the far side is indistinguishable from approval in the GitHub
timeline, where `greptile-apps` appears as a commenter either way.

**Lines do not bind.** #225 was **50,511 insertions across 12 files** and was reviewed normally —
almost all of it generated mirror. #202 deleted 3,887 lines healthily. A line budget would have
misfired on both and would forbid a commit `CLAUDE.md` *requires* (the mirror must move with its
corpus).

| gate | value | how to check |
|---|---|---|
| **hard** | ≤ 100 changed files | `git diff --name-only origin/main...HEAD \| wc -l` |
| **soft warn** | ~35 files | same; above this a PR is usually a multi-arc bundle |
| **push trigger** | ~40 files | same; leaves headroom under the cliff |

Escape hatch, which Greptile itself prints: if a PR genuinely must exceed 100 files, comment
tagging `@greptile-apps` to force review, and **record in the PR body that you did**. Never open an
oversized PR and assume review happened.

**Generated artifacts are exempt from the size *judgement* but not from the *file count*** —
Greptile counts files before deciding. `docs/research_map.md` and `docs/research_map.json` are
generated. `docs/findings/research_map_corpus.json` is the **source** and counts fully.

---

## 3. Push cadence, which is the failure this ADR exists for

The 2026-08-04 branch reached **36 commits / 56 files / 11,329 insertions with no upstream at all**.
56 files is comfortably under the file cap, so the cap would not have caught it. This is a
*latency* failure, not a size failure, and it is worse than it looks:
`.github/workflows/tests.yml` fires only on `pull_request` and `push: branches: [main]`, so an
unpushed branch gets **zero CI, zero bot passes, and zero backup** — on a machine with nine live
worktrees and a recorded branch-volatility hazard.

**Push at ~40 changed files or when a finding lands, whichever comes first.** Use
`gh pr create --draft`: CI runs on drafts (the workflow's `pull_request:` trigger is unqualified),
a draft cannot be merged by accident, and the value bought is CI plus backup, not early review.

---

## 4. What a PR is

**One finding, plus the evidence artifacts it cites, its `research_map_corpus.json` row, and the
guard test pinning its number.** That is the same atom `CLAUDE.md` already defines at commit
granularity — lifted to branch granularity. A branch ends when its finding lands, not when the
session ends.

Infrastructure (provenance stamping, DB fixes, new graders) ships as its **own PR ahead of** the
findings that depend on it. A cluster job's result cannot be re-run later to disentangle it.

Split by **artifact class and verification gate**, not by "idea":

| class | gate |
|---|---|
| code / scripts | `pytest` green |
| findings prose | `research_map_db.py check` exit 0 |
| generated map | the mirror test |

Two hard exceptions: the **corpus → `research_map.md` → `research_map.json` triple must never split
across PRs**, and **two `exp(` commits must never be squashed together** — each records one cluster
job whose artifacts live off-repo and expire.

Because merges are non-squash, splitting costs no history.

---

## 5. Commits

**Atomic unit is the quadruple**, not "a finding plus the map":
`docs/findings/<dated>.md` + `research_map_corpus.json` + `research_map.md` + `research_map.json`.

This is currently violated ~79% of the time: since the corpus landed, **28 commits added a
`docs/findings/*.md` and only 6 touched `research_map_corpus.json`**. Regenerating
`research_map.json` alone is **not** sufficient and actively masks the gap — the export changes on
file presence alone, so the diff looks like the map was updated when the source was untouched.

**Opt out affirmatively, never by silence:** a commit adding a finding with genuinely no map impact
must carry a literal `MAP-IMPACT: NONE` line. Default is blocked. Today you cannot distinguish "no
impact" from "forgot".

**Never change a generator and its generated output in one commit.** When the mirror test fails
after such a commit, the failure cannot be attributed and there is no bisect point. Generator
first, regenerated output second — and accept that the intermediate commit may be red, because CI
grades the PR head, not each commit.

**Trailers, required only on `exp(` and `result(` commits** — `Run-dir:`, `Slurm-job:`,
`Gate: verify_run.py exit 0`, and `Pooler: geometric` wherever a `scav_rat` count is quoted. AICR
`/scratch` purges at 30 days, so **the commit is the only record that outlives the artifact**. Only
10 of 36 commits on the 2026-08-04 branch named a Slurm job at all, in free prose with inconsistent
case, so `git log --grep` cannot recover them.

**Retraction pointers must be structured**, not prose: `Retracts: ind352`,
`Supersedes: docs/findings/<dated>.md`. Across 144 finding files, 25 carrying a retraction banner,
`grep "RETRACTED BY"` returns **zero** — every pointer from a retraction to its replacement is
prose only, in a repo whose `SUPERSEDES` chain is already matched on normalised prose rather than
ids.

**Never `git merge main` on a work branch.** `git fetch origin && git rebase origin/main`. Six
stray merge commits are already permanent on main; the worst, `3da274b`, is a 133-file commit
corresponding to no unit of work, invisible at review time because GitHub reports the three-dot
diff.

**Scope prefixes stay open, not a fixed enum.** `exp`, `result`, `correct` and `prereg` are
first-class. 316 of the last 400 subjects already comply with no gate. Add no commit linter — a
Conventional-Commits allow-list would reject `prereg(amend):`, the most informative prefix in the
history.

---

## 6. What "version" means here

There is no released artifact, no API surface, no downstream consumer. So **semantic versioning is
meaningless and is not adopted.**

**A tag marks the state that produced a reported number**, so a finding can cite a SHA and a
manuscript figure resolves to a fixed corpus rather than "main at some point". This is not
cosmetic: `test_canonical_numbers.py` exists because the flagship `scav_rat` count drifted across
twelve documents and two audits then "corrected" the right value back to the wrong one.

Tag on: a manuscript figure freeze, and any commit whose number enters an external document.

---

## 7. Explicitly rejected

Recorded so they are not re-proposed: semantic versioning and release trains; GitFlow and
long-lived release branches; code owners, review rotas, and reviewer-attention budgets; the DCO /
`Signed-off-by`; Conventional Commits linting; size-XS..XXL auto-labels; the "200–400 LOC in 60–90
minutes yields 70–90% defect discovery" figure (unsourced marketing copy, not in the Cisco study it
is attributed to); Google's 100/1000-line guidance (median here is 4 files / 238 additions — already
inside it with no policy in force); and a 10-file cap derived from Google's 9M-change study (median
here is exactly 10, so it would bind on half of all PRs; their number was measured on code, and half
this repo's diff is prose and generated artifacts).

All were rejected for the same reason: their value comes from multi-developer coordination,
downstream version consumers, or a released API surface. This repo has none of those.

---

## 8. Enforcement, and the honest state of it

Every rule above is checkable in under a minute. The gaps, stated rather than assumed:

- `.git/hooks` contains **only samples** — there is no hook infrastructure at all, so during a long
  autonomous session nothing fires until ~36 commits after a defect is authored.
- Proposed pre-commit hook, deliberately just two things:
  `research_map_db.py check` and `pytest tests/test_research_map_integrity.py -q`. Both are
  pure-Python and fast. **Do not put the full suite in a hook** — a slow hook gets bypassed with
  `--no-verify` within a day, which is worse than no hook because it trains the bypass.
- Proposed `SessionEnd` hook mirroring the existing `SessionStart` one: warn at 10 unpushed
  commits, and always warn when there is no upstream. Warning, not block — a hard block at session
  end fires mid-arc and gets disabled.

**A gate that cannot fail is worse than no gate.** Four were found inert on 2026-08-04 alone: the
map DB searched truncated prose; the citation check tested disk existence rather than repo
membership; the mirror test compared the file against itself; and a job watcher read a failed `ssh`
as "complete". Each reported success while measuring nothing. **Every new gate must be
negative-controlled — run it against a case it should fail — and the control belongs in the test
suite, not in the author's memory.**
