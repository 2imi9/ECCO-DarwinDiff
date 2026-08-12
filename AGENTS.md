# DarwinDiff — working agreement for Codex

This file is loaded into every Codex session on this repo. Keep it short; deep
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

**ENFORCED** — `check` exits 1 on any of these:

```
π_cl(σ_live(CLAIM))  ∩  π_old(SUPERSEDES)         = ∅   matched on normalised PROSE, not on ids
σ_mode=inductive ∧ numbers IS NULL (CLAIM)        = ∅   PRESENCE only — see the caveat below
σ_doc ∉ DOCUMENT (CLAIM)                          = ∅   cited file is in the REPO, not just on disk
σ_verdict=RESOLVES_MISMATCH (CITATION)            = ∅   no DOI points at the wrong paper
σ_verdict ∈ {DEAD, FABRICATED} (CITATION)         = ∅
σ_doc IS NULL (SETTLED)                           = ∅   a settled answer must say where it lives
σ_status IS NULL (CLAIM)                          = ∅
σ_prose ENDS WITH "…" (SETTLED ∪ CLAIM ∪ TRAP …)  = ∅   no markdown truncation leaked into the DB
```

**REPORTED, NOT ENFORCED** — `check` prints these and keeps exit 0. They are real properties with
real violations today; gating on them would fail every run and train you to ignore the gate, which
is the same reasoning that keeps STRADDLE advisory in `verify_run`:

```
σ_live(CLAIM) ⋈ σ_local_only(DOCUMENT), sole cite          2 rows   reader cannot open the source
CLAIM ⋈ SUPPORTS ⋈ σ_gate≠exit0(EVIDENCE) where live     39 rows   `dangerous` lists them
σ_live(CLAIM) ⋈ σ_retracted(DOCUMENT)                    26 rows   review each by hand
CLAIM − π_cl(SUPPORTS)                                  291 rows   claims with no evidence edge
```

**Three caveats, because a green `check` otherwise reads stronger than it is.** "Carries its
untrained null" is a presence check on the merged `n / null` column: the corpus has no separate
null field, so *no* constraint here can verify that a matched baseline exists. The citation
constraints run over the audit's **exception rows only, 1 of 130** — `check` prints its own
coverage line to say so. And `DOCUMENT` is built from `git ls-files` **plus** the seven declared
`LOCAL_ONLY_DOCS`, never from a disk walk: those notes are gitignored by name (`.gitignore:100-106`),
so a disk walk found them on the author's machine and nowhere else — the orphan constraint passed
locally and failed in CI, where **8 claims (2 live)** cite no document a fresh checkout contains.
Claims resting *only* on such a note are exempt from the gate and **counted by the advisory
above** — 2 today (`ded123`, `ind339`).

**Run `settled` before starting, and `check` before committing a finding.**

### Three artifacts, one source

| file | what it is for | do not |
|---|---|---|
| `docs/research_map.md` | reading as prose; the session-start index | hand-edit — regenerate it |
| `docs/research_map.json` | reading the whole relational model in one file read | hand-edit — export it |
| the in-memory DB | asking questions: joins, constraints, `settled` | expect it to persist |

**The markdown is TRUNCATED and the database is NOT.** `gen_research_map.cell()` cuts every cell
when it renders (settled answers at 240 characters, claim statements at 230, traps at 220) so the
tables stay readable. `research_map_db.py` parses that markdown and then **rehydrates every prose
column from the corpus JSON**, so queries and `settled` see the full text. Until 2026-08-04 they did
not: 87% of settled answers were cut and 35% of the corpus was unsearchable, and a missed search
printed *"This may be genuinely new work"* — a false negative that reads exactly like a true one.
So **quote numbers and detail from a query or the JSON, never from the rendered table**, which may
end mid-sentence. `check` enforces that no cut text reaches the database and prints a `text
coverage:` line saying how many rows were rehydrated.

Neither generated file is a second source of truth. The markdown is rendered from
`docs/findings/research_map_corpus.json` by `scripts/gen_research_map.py`; the JSON is exported from
the same in-memory database the SQL commands query, so a schema or constraint change propagates to
it automatically. Use SQL to **ask** (one command, joins, constraints) and JSON to **read in bulk**
(the entire structure without a shell round-trip per question).

```bash
python scripts/gen_research_map.py                   # corpus JSON -> research_map.md
python scripts/research_map_db.py export-json        # the DB       -> research_map.json
```

`test_research_map_json_mirror_is_current` fails when the committed JSON falls behind the build, so
"the mirror follows the SQL" is enforced rather than promised. **After changing the map, the schema
or the corpus, re-run both and commit all three together.**

## Issue tracker is the plan of record

The GitHub issue tracker (`2imi9/ECCO-DarwinDiff`) holds the forward plan for the
parameter-learner (Track 1) work, organized into spines **A–D** under index epic
[#124](https://github.com/2imi9/ECCO-DarwinDiff/issues/124):

- **A — land in-flight** · **B — seasonal + cluster gate** · **C — manuscript #1 hardening** · **D — R_PICPOC via real calcite anchor; identifiability frontier** *(the differentiable Darwin calcite port was tested and did not help — R_PICPOC recovers with a real calcite observation: Daniels CP:PP / MODIS PIC)*

**At session start (first repo access):** a `SessionStart` hook (`.codex/hooks.json`)
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
  `scav_rat`, `diatomgraz`, `R_PICPOC`} — but only **three** of those four have ever cleared
  their own untrained null at an uncontaminated band; `diatomgraz` stays *in* the denominator
  and is reported as not established, never quietly dropped to flatter the ratio. The growth
  pair {`Smallgrow`, `Biggrow`} is
  **excluded, not failed** — `Biggrow` unobservable by construction, `Smallgrow` non-identifiable
  from *time-mean* observables only (a seasonal prototype recovers it natl 9/10, unconfirmed). `R_PICPOC` is recoverable given a
  real calcite anchor (Daniels/MODIS). The surrogate gap is dimensional (the 0-D box homogenizes
  spatial structure), so identifiability comes from real absolute anchors — see [STATUS.md](STATUS.md).
- **`scav_rat` MUST be reported under the geometric pooler (or all three), never the arithmetic
  one alone.** Run `python scripts/analysis/pooler_audit.py RUN_DIR [--null NULL_DIR] [--legs]`.
  It grades all three collapses from the same fit, pairs them with McNemar, and prints
  `per_aoi_log_sd`. **The collapse choice affects `scav_rat` and nothing else** — `alpfe` and
  `R_PICPOC` are exactly invariant in every run measured (`log_sd` ≤ 0.21 against a decisive
  threshold of σ = √(2 ln 1.4) = 0.820).
  **The flagship trio is 25/50 arithmetic and 12/50 geometric** (`scav_rat` 26 → 13), measured on
  `collapse/collapse_n50`, which is bitwise identical to the flagship reproduction `ctrl_n50` on
  50/50 seeds. The whole difference is the **North Atlantic** leg, 19 → 5.
  **The bias is NOT one-directional.** arithmetic = geometric × exp(σ²/2), so the direction is
  decided by where the geometric centre sits in the ±40% band: *below* it the inflation
  manufactures passes (natl 0.43× → 0.58× Carroll), *inside* it the inflation destroys them
  (single-AOI Southern Ocean 0.73× → 1.39×, so `scav_rat` reads **30/50 arithmetic but 49/50
  geometric**, P = 6.3e-59). The arithmetic pooler has been *understating* the one basin where
  `scav_rat` is established. Under the geometric collapse `scav_rat` is systematically biased
  **low** everywhere (0.43×–0.89× Carroll).
  **⚠️ The keys only exist from 2026-07-29 (`c4323ae`).** 119 of 211 run dirs — including the
  published flagship, both anchor-off controls, `ep4k_n50`, `ctrl_n50`, `abl_global`/`abl_percell`
  — carry none of them and **cannot be pooler-checked at all**. `pooler_audit.py` prints
  `<absent>` and exits 2; that is a gate, never a fallback to the arithmetic number.
  See [docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md](docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md)
  and [docs/findings/2026-08-03_the_arithmetic_pooler_manufactures_scav_rat_recovery.md](docs/findings/2026-08-03_the_arithmetic_pooler_manufactures_scav_rat_recovery.md).
- **Every reported effect must pass THREE checks — each necessary, none sufficient.** The
  2026-08-03 width claim passed the first two and was still an artifact.
  (1) **Out-of-sample replication — and splitting ONE array in half is NOT that.** A genuinely
  fresh submission is required: the per-parameter effect died exactly this way (45/50 vs 34/50
  became **38/50 vs 38/50** on seeds run in a *later job*). Within a single array the halves are
  an arbitrary partition of one sample, and a permutation test over 10,000 re-splits of the width
  arms puts **P(both halves significant) = 0.926** — near-automatic given a significant aggregate,
  so it carries almost no information. Cite a separate job, or state that you have no replication.
  (2) **Band sensitivity** — re-count at ±0.05 around the pass band; an effect that *peaks* at the
  reported threshold is threshold geometry, not accuracy.
  (3) **Pooler invariance** for `scav_rat` — see the bullet above.
  All three run on artifacts already on disk and cost one query each.
- **The per-AOI ≥2-of-3 rule is close to degenerate for `scav_rat`; do not call it a three-basin
  test.** Measured on the width arms: `southernoceanpac` passes **99–100/100** in every arm, a
  free vote, and there is **not one seed** in either arm where natl passes and the parameter
  fails. So ≥2-of-3 collapses to **≥1-of-{eqpac, natl}** — and eqpac fires at an identical 12/100
  in both arms on largely *different* seeds (overlap 2 of 12), i.e. seed noise. The headline is
  effectively a one-basin test wearing a three-basin label.
  **`scav_rat` is a knife edge (22/100 at 0.35, 45 at 0.40, 81 at 0.45) and it is the sole
  binding leg, so the joint trio headline inherits that** — but note **that knife edge is itself
  partly an arithmetic-collapse artifact**: in the Southern Ocean the geometric collapse reads
  48/49/50 at the same three bands, i.e. at ceiling and threshold-robust. `alpfe` (98/100 flat
  from 0.20 to 0.60) and `R_PICPOC` are threshold-robust — quote `alpfe` at **≤0.30**, where its
  untrained null is 0/100 rather than the 20/100 it carries at 0.40. See
  [docs/findings/2026-08-03_the_pass_band_is_load_bearing.md](docs/findings/2026-08-03_the_pass_band_is_load_bearing.md).
- **Compare within a job, never across.** Cross-job comparison of nominally identical configs
  cannot be defended here: older artifacts leave the deciding keys `<absent>`, not equal, and
  *absent is unknown*. Any new arm needs its control in the same submission.
- **Grade on the per-AOI ≥2-of-3 metric, never the cell-weighted one** — cell-weighted counts
  *straddle* (per-AOI legs landing on opposite sides of Carroll) and overstate recovery, most
  severely for `scav_rat`. Flagship = `n50e2k_percell_trio` (n=50, 2000 epochs): `alpfe` **49/50**,
  `R_PICPOC` **50/50**, `scav_rat` **25/50**, trio **25/50** vs **0/50** global-scalar — all
  **arithmetic**; the trio is **12/50 geometric** (see the pooler bullet above). The trio count
  *equals* `scav_rat`'s — it is the sole binding leg. At 4000 epochs (`ep4k_n50`) `scav_rat` and the
  trio both rise to **41/50** (natl 20→40, SO 49→48, eqpac 7→6) — but `ep4k_n50` predates the
  collapse instrumentation, so that 41/50 is **arithmetic-only and unauditable**.
  **⚠️ Do NOT cite that 4000-epoch rise as evidence `scav_rat` is optimisation-limited.** A 2×2
  (width × epochs, n=100/cell, one job 258713) shows the epoch lever is a **bad trade**: it buys a
  **pooler-dependent** natl gain (better under arithmetic and geometric, *worse* under median) and
  pays with a **pooler-invariant** Southern Ocean loss of **1.4–1.75×** at 4000 epochs alone
  (P = 1.6e-09 geometric), rising to **2.7–5.1×** with width added. The SO is the **one** basin
  where `scav_rat` is established (30/50 vs untrained 0/50, P = 3.15e-24). The reported count is
  blind to it: a 5× accuracy loss shows as 9 seeds, because the SO sits far inside a 40% band —
  that "SO 49→48" is one seed hiding a 1.75× degradation. **Keep the flagship at width 16 /
  2000 epochs**; it is the best cell in the 2×2 for the SO under all three poolers. Affects
  `ind342`, `ind345`, `ind353`, `ind354`. See
  [docs/findings/2026-08-04_more_optimisation_damages_the_one_basin_that_works.md](docs/findings/2026-08-04_more_optimisation_damages_the_one_basin_that_works.md).
- **Match the control to the epoch budget.** There are two anchor-off runs and both are real:
  `n50e2k_anchor_off` (2000 ep, the epoch-matched control for the flagship) gives `R_PICPOC` **6/50**;
  `n50_anchor_off` (1500 ep) gives **4/50**. Quote 6/50 against the 2000-epoch flagship.
- **Do not write "the 3-of-4 frontier", and do not claim two operating points.** Both are stated
  in an aggregate ≥2-of-3 count at a 0.40 band, and 2026-08-03 showed that count conveys neither
  half of what is actually there. **`diatomgraz` is REGIONALLY IDENTIFIABLE in the equatorial
  Pacific** — its eqpac leg is **40/100 at ≤10% and 20/100 at ≤5% against an untrained 0/50**
  (P = 5.5e-09 and 2.0e-04) — **and anti-recovered in the other two**, where training pushes the
  median from 0.38 out to 0.79 and 0.86 and both legs fall *below* their own nulls. The 0.40 band
  is blind to all of this because `diatomgraz`'s prior midpoint (rel **0.367**) already sits
  inside it, so its untrained null passes 33/50 there and P = 0.254.
  **Grade `diatomgraz` per-leg at ≤0.10, never on the aggregate at 0.40.** This settles `ded1`
  affirmatively: "carries no observational signal" is not merely unsupported, it is **false**.
  The mirror of `scav_rat`, which is locally identifiable in the **Southern Ocean**.
  Honest framing: **two globally recovered (`alpfe`, `R_PICPOC`), two regionally identifiable in
  different basins (`scav_rat`, `diatomgraz`), two excluded by construction.**
  See [docs/findings/2026-08-03_the_pass_band_is_load_bearing.md](docs/findings/2026-08-03_the_pass_band_is_load_bearing.md).
