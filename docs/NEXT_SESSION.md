# DarwinDiff — next-session handoff prompt

Paste the block below as the **first message** of a fresh session. It is intentionally detailed —
long-context sessions lose detail, so a new session should ground in these files, not a running
summary. Update this file + `STATUS.md` at the end of each substantial session.

---

Resume **DarwinDiff**. **Before acting, do three things:** (1) say `resume` to load the
session-connector checkpoint (`D:\session-connector\ecco-darwindiff\HEAD.md` — the top two active
threads are `track2-emulator` and `realdata-validation`); (2) read `STATUS.md` (the "Track 2" section)
and the auto-memory index in full; (3) read the canonical result doc
`docs/research_notes/2026-07-09_track2_identifiability_writeup.md`. Then confirm the shape back to me
before starting — long-context drift lost detail before, so ground in these files.

## Shape: two papers, both now at a COLLABORATION gate (not a compute gate)

- **Paper #1 (Track-1 identifiability/recovery study) — submission-quality** since 2026-07-05.
  Local-only `docs/paper/main.tex` (gitignored; `cd docs/paper && latexmk -pdf main.tex`). Result:
  0-D differentiable surrogate + per-cell DINN identifies the demonstrated-observable trio
  {alpfe, scav_rat, R_PICPOC}; per-cell load-bearing (33/50 n=50 vs 0/50 global). Waiting on **Jon**
  (review / authorship / venue). Frame as a *write-up*, not a submission, in comms to collaborators.
- **Paper #2 (Track-2 differentiable-Darwin) — COMPLETE as an identifiability-limits map** (2026-07-10).
  The original "learn real closures from data" thesis is honestly bounded: transport does **not** close
  the gap on real data — not because the method fails but because the observations lack the signal.
  Waiting on **Jon** (direction decision: is the limits map the contribution?).

## Paper #2 = the identifiability-limits map (the finished result)

A **3-closure map** — none of Darwin's targetable BGC closures is constrainable by real obs, for three
distinct reasons (`docs/findings/figures/fig1_identifiability_map.png`):
- **iron `scav_rat` — observability wall** (structural): DFe concentration is a low-info projection of
  the rate. A "particulate:dissolved partitioning breaks the wall (~14×)" result this session was a
  **construction artifact** (pFe/DFe cancels algebraically) — caught by adversarial verification and
  **retracted**. Don't revive it without reading `docs/findings/2026-07-10_iron_partitioning_breaks_the_wall.md`.
- **calcite Ω-modulation of `R_PICPOC` — data/support-limited**: within-region Ω ≤0.16 dex everywhere.
  The **scalar R_PICPOC is itself recoverable** (Track-1); only its Ω-modulation is untestable. Null
  confirmed **four ways** — the in-sample distillation oracle; independent in-situ **GLODAPv3** Ω
  (838+1740 bottles; not the model cache); a driver test (SST/composition don't rescue it → not
  Ω-specific); and the **make-or-break out-of-sample transport E2** (learned closure does NOT beat a
  constant-through-transport null; default overfits −1.53, regularized −0.05, null +0.50, K_num flat;
  **hardened 2026-07-11 to a 10-seed ensemble — robust negative, every seed loses to null**; local
  `docs/findings/e2_seed_ensemble_scored.md`).
  Consistent with Marañón 2016. The pooled "0.38-dex" signal is a **Simpson artifact** (within-basin
  slopes positive, pooled negative via a between-biome intercept ordering) — never over-read it.
- **growth `Smallgrow`/`Biggrow` — structurally unobservable**: total NPP gives only the
  biomass-weighted mean → the pair stays degenerate.

New method artifact: the **symbolic-distillation identifiability oracle** (`scripts/symbolic_distill_probe.py`,
22 tests). Hardened by an 8-reviewer adversarial panel + a reproducibility appendix
(`2026-07-10_reproducibility_appendix.md`, with data checksums/DOIs + findings→commit) + 3 figures.
Verification is externally spot-checked: the Ω solver matches **PyCO2SYS** (log-Ω r = 1.0000). The
forward contribution is an **observing-system recommendation**: wider within-region Ω; a pure
scavenged-Fe observable; per-PFT production.

## The one binding next step: get both papers in front of Jon
- Paper #2: send `docs/research_notes/2026-07-10_track2_summary_for_discussion.md` + the 3 figures.
- Paper #1: send the local `main.tex` draft.

## If continuing autonomously (non-Jon work only)
1. ~~Merge branch → `main`~~ **DONE** (#180, 2026-07-10) and ~~regenerate/commit the iron
   env-predictability JSON~~ **DONE** (`21f238e`; R6-1 closed, GLOBAL-Ω +0.14 reproduced).
   2. A *positive* result now requires **new observing-system data** (the three levers above) —
   none is a re-run; needs Jon's steer. 3. Optionally promote the write-up to a full manuscript.

## Hard constraints
- **Local RTX 5090 is usually IN USE** — CPU (`CUDA_VISIBLE_DEVICES=-1`) for identifiability work;
  the 5090 was free for the E2 (a full E2 is ~15-20 min/run, launch-bound; kill n_steps=120, use ~60).
  Cluster (Explorer H200, `ssh explorer`) for anything heavy.
- Commit conventions: scope-prefixed titles, **NO Co-Authored-By**, non-squash merges, `2imi9/`
  branches, **explicit paths** (shared checkout can carry another session's untracked WIP — verify
  `git branch --show-current` before every commit). `verify_run.py`-gate any recovery number.
- Pre-existing untracked prior-session WIP in the tree (`ude_forcing_design.py`, hybrid_*, column_ude_*,
  a stray root `main.tex` — manuscript is local-only, do NOT commit it). Leave it alone.
- Adversarially verify any identifiability/numerics claim where the observable is *constructed from*
  the parameter — that's how the iron-partitioning artifact slipped past the tests.

Start by grounding (resume + STATUS + the write-up), confirm the shape, then — unless I say otherwise —
the next move is packaging for Jon or the branch merge.
