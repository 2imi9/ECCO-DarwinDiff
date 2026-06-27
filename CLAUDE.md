# DarwinDiff — working agreement for Claude Code

This file is loaded into every Claude Code session on this repo. Keep it short; deep
context lives in [STATUS.md](STATUS.md) (canonical results) and `docs/`.

## Issue tracker is the plan of record

The GitHub issue tracker (`2imi9/ECCO-DarwinDiff`) holds the forward plan for the
parameter-learner (Track 1) work, organized into spines **A–D** under index epic
[#124](https://github.com/2imi9/ECCO-DarwinDiff/issues/124):

- **A — land in-flight** · **B — seasonal + cluster gate** · **C — manuscript #1 hardening** · **D — R_PICPOC via real calcite anchor; identifiability frontier** *(the differentiable Darwin calcite port was tested and did not help — R_PICPOC recovers with a real calcite observation: Daniels CP:PP / MODIS PIC)*

**At session start (first repo access):** a `SessionStart` hook (`.claude/settings.json`)
prints the open issues. Orient the session against them before starting work; if the list
is missing (e.g. `gh` not authed), run `gh issue list --state open`.

**Before wrapping up a session:** review the open issues against what the session actually
changed, and update the tracker **if necessary** —
- check off acceptance-criteria boxes that the session completed;
- close issues whose work merged (reference the PR/commit);
- comment status on issues that advanced but aren't done;
- file a new issue (with full detail — acceptance criteria + blockers) for any substantial
  follow-up the session discovered.

"If necessary" means only when the session moved or invalidated tracker state — skip it for
pure discussion / read-only turns. Don't silently let the tracker drift from reality.

## Conventions (see CONTRIBUTING.md / project memory)

- Scope-prefixed PR titles; **no `Co-Authored-By` trailer** in commits; non-squash merges.
- After every push, fetch Greptile + Codex review comments via `gh` and address P1s before
  reporting done (when those bots are active on the repo).
- Recovery results: compare against Carroll's published Green's-functions optima, report
  n≥10 with seed variance, DINN baseline only by default. **Framing is a surrogate-to-model
  identifiability study, not a 6/6 chase**: the observable denominator is **4** {`alpfe`,
  `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is
  **unobservable by construction** (excluded, not failed). `R_PICPOC` is recoverable given a
  real calcite anchor (Daniels/MODIS); the best config holds {`alpfe`, `scav_rat`, `R_PICPOC`}
  jointly 8/10. The surrogate gap is dimensional (the 0-D box homogenizes spatial structure),
  so identifiability comes from real absolute anchors — see [STATUS.md](STATUS.md).
