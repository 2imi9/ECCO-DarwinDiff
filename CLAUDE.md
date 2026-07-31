# DarwinDiff — working agreement for Claude Code

This file is loaded into every Claude Code session on this repo. Keep it short; deep
context lives in [STATUS.md](STATUS.md) (canonical results) and `docs/`.

## READ FIRST, EVERY SESSION: [docs/research_map.md](docs/research_map.md)

**Before proposing, designing, or launching anything, read the research map.** It is the index of
what is already known and how strongly, organised by inference mode (deductive / inductive /
abductive) over evidence, claims and open hypotheses.

Two sections are mandatory and take under a minute:

1. **§1 SETTLED — do not re-derive.** Questions already answered, with the answer and the file.
   If the thing you are about to work on is in that table, it is done. Say so and move on.
2. **§6 SUPERSEDES.** The retraction chain. A number that appears in an old doc may be retracted;
   this is where you find out before quoting it.

**This is not optional bookkeeping.** On 2026-07-30 one session re-derived work the repo already
contained **four separate times** (the GHG Center assessment twice, the rain-ratio precedence, the
1-D column study), one of them at a cost of 1.52M tokens. Every one would have been caught by §1.

When a session produces a durable result, a retraction, or answers a standing question, **update
the map in the same commit as the finding**, not later.

### The SQL harness — query the map, do not just read it

`scripts/research_map_db.py` parses the map's tables into an in-memory relational database and
ships the canonical queries. **SQL here is a guidance layer, not storage**: nothing is persisted,
the markdown stays the single source of truth, and the database is rebuilt on every invocation. If
a table stops parsing, the integrity test fails and you find out immediately.

```bash
python scripts/research_map_db.py settled daily      # BEFORE STARTING WORK: is this already answered?
python scripts/research_map_db.py superseded 0.408   # is this number retracted?
python scripts/research_map_db.py trace D1           # what a claim rests on, and what rests on it
python scripts/research_map_db.py param scav_rat     # everything known about one parameter
python scripts/research_map_db.py dangerous          # live claims on ungated or missing evidence
python scripts/research_map_db.py check              # all integrity constraints; exit 1 on violation
python scripts/research_map_db.py sql "SELECT ..."   # arbitrary read-only SQL
```

It assembles from four sources so nothing is maintained twice: the map's tables, the Carroll-N
registry in `src/darwindiff/carroll6.py`, `docs/findings/citation_audit.json`, and the presence and
retraction banners of every file under `docs/findings` and `docs/research_notes`.

The constraints it enforces are the map's rules written as relational algebra:

```
π_cl(σ_status=live(CLAIM))  ∩  π_old(SUPERSEDES)                  = ∅   no live claim is retracted
σ_mode=inductive ∧ null IS NULL (CLAIM)                           = ∅   every count carries its null
CLAIM ⋈ SUPPORTS ⋈ σ_gate≠exit0(EVIDENCE)  where live             = ∅   no live claim on ungated evidence
σ_doc ∉ DOCUMENT (CLAIM)                                          = ∅   every citation resolves
σ_verdict=RESOLVES_MISMATCH (CITATION)                            = ∅   no DOI points at the wrong paper
```

**Run `settled` before starting, and `check` before committing a finding.**

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
  **excluded, not failed** — `Biggrow` unobservable by construction, `Smallgrow` non-identifiable
  from *time-mean* observables only (a seasonal prototype recovers it natl 9/10, unconfirmed). `R_PICPOC` is recoverable given a
  real calcite anchor (Daniels/MODIS). The surrogate gap is dimensional (the 0-D box homogenizes
  spatial structure), so identifiability comes from real absolute anchors — see [STATUS.md](STATUS.md).
- **Grade on the per-AOI ≥2-of-3 metric, never the cell-weighted one** — cell-weighted counts
  *straddle* (per-AOI legs landing on opposite sides of Carroll) and overstate recovery, most
  severely for `scav_rat`. Flagship = `n50e2k_percell_trio` (n=50, 2000 epochs): `alpfe` **49/50**,
  `R_PICPOC` **50/50**, `scav_rat` **25/50**, trio **25/50** vs **0/50** global-scalar. The trio count
  *equals* `scav_rat`'s — it is the sole binding leg. At 4000 epochs (`ep4k_n50`) `scav_rat` and the
  trio both rise to **41/50** (natl 20→40, SO 49→48, eqpac 7→6).
- **Match the control to the epoch budget.** There are two anchor-off runs and both are real:
  `n50e2k_anchor_off` (2000 ep, the epoch-matched control for the flagship) gives `R_PICPOC` **6/50**;
  `n50_anchor_off` (1500 ep) gives **4/50**. Quote 6/50 against the 2000-epoch flagship.
- **The 3-of-4 frontier is structural — there are two operating points, not one.** No single
  config recovers all four observables: `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`}, while
  MLD-channel + heavy Daniels weight holds {`alpfe`, `diatomgraz`, `R_PICPOC`}. `scav_rat` needs
  the Darwin-pattern term; `diatomgraz` needs MLD; they conflict even at 4000 epochs.
