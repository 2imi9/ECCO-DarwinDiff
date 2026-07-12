# Track-2 decision brief (2026-07-10)

Supersedes the 2026-07-07 questions brief. Since then the first real-data E2 ran and the
identifiability oracle landed, and they converge on one clear result — so the open questions
have narrowed to a small number of genuine decisions. This is the internal driver for the next
conversation; the shareable version is the write-up
([`2026-07-09_track2_identifiability_writeup.md`](2026-07-09_track2_identifiability_writeup.md)).

> **Role: decisions only.** The map's derivation and all identifiability numbers are **canonical in
> the write-up** (linked above) — this brief carries the *decisions*, not restated numbers. Cite the
> write-up for any figure.

## Provisional calls already made (2026-07-10, internal) — *distinct from the open D1–D3 below*

- **P1 — Both, in parallel.** The identifiability map is the baseline Track-2 deliverable; in
  parallel, hunt a positive E2 by trying the levers **one at a time**, cost-first (CPU
  transport-free floor + distillation oracle *before* any GPU E2), using best-judgment targets
  since the specific datasets are not yet documented.
- **P2 — Try levers one by one, best guess.** Order by tractability on data we can actually reach.
- **P3 — The map is the contribution.** Paper #2's validation claim is the honest identifiability
  bound (what real obs can/cannot constrain, and why), **not** contingent on an E2 pass. A
  positive E2, if one is found, is upside on top of the map.

## TL;DR — the one decision

Track-2's honest result is an **identifiability-limits map**: real observations do **not**
sharply constrain the Darwin closures we target, for **three distinct reasons** (below). The
machinery works; the observing system is the binding constraint. **The decision to make: is that
map the Track-2 contribution we write up, or do we spend cluster budget chasing a positive E2 on
a different observable?** Everything else is downstream of that call.

## What we found (the map)

| Darwin closure | observation targeted | verdict | why |
|---|---|---|---|
| calcite `R_PICPOC` | PIC:POC rain ratio (**≈ the parameter**) | not identifiable | **data/support-limited** |
| iron `scav_rat` | dissolved-Fe concentration (**≠ the parameter**) | not identifiable | **observability-limited** |
| growth `Smallgrow`/`Biggrow` | net primary production (aggregate) | not identifiable | **structurally unobservable** — total NPP gives only the biomass-weighted mean, so the pair stays degenerate (per-PFT production is the only lever; see D2) |

- **Calcite is Ω-support-limited.** The rain ratio essentially *is* the parameter, so if the
  environment drove it we could recover it. But three independent analyses agree it does not:
  the transport-UDE delta is within hold-out noise; the in-situ correlation is r ≈ 0.01
  (matching Marañón et al. 2016, tropical calcification Ω-independent); and the new
  distillation oracle shows *why* quantitatively — the **real Ω support is far too narrow**
  (0.08 dex per basin, 0.25 dex even pooling eqpac+natl; the fitted power-law exponent's 95 %
  CI includes zero). The data simply don't vary Ω enough, in these regions, to constrain an
  Ω-driven ratio.
- **Iron is observability-limited (an information wall).** Dissolved-Fe *concentration* is a
  low-information projection of the scavenging *rate* — many `scav_rat` values reproduce the
  same concentration field (Tagliabue 2016; Track-1 sloppiness). A closure fit to held-out DFe
  *looks* skillful (DFe is densely env-predictable), but that skill doesn't identify the rate.
  This is structural: more iron data would not close it.

Both are honest, novel, and publishable as a map of *what a differentiable-Darwin inversion can
and cannot constrain, and why* — the observing system, not the method, is the limit.

## The decisions you own

**D1 — Is the identifiability-limits map the Track-2 write-up, or do we chase a positive E2?**
The map is a complete, defensible result that needs no more compute. Chasing a positive E2 means
picking a closure/observable where transport genuinely helps *and* the observable constrains the
parameter — which, given the two walls above, needs a **new observable or dataset**, not a
re-run. (The pre-registered "pool basins + smaller closure" calcite rerun will not help — the
oracle shows Ω support, not sample size or closure size, is the binding constraint.)

**D2 — If we chase a positive result, which lever?** Each is a data/observable question:
- *Calcite lever — now partly tested, and it did not flip.* The denser high-latitude Marsh 2025
  compilation adds Southern-Ocean coverage (Ω down to ~2.3), pushing the pooled Ω support above
  the identifiability threshold (0.38 dex, n = 79) — and the exponent comes back **consistent
  with zero** (CI [−1.16, +0.16]), i.e. a *tested* null, not merely an under-excited one. So more
  Ω range from the existing compilations does **not** produce a positive. The remaining calcite
  lever is narrower than before: either an *independent* in-situ carbonate Ω (to rule out a
  cache-Ω artifact) or a fundamentally different, even-wider-Ω calcite record. Is either worth
  pursuing, or does the tested null settle the calcite closure?
- *Iron lever — tested, FAILED verification (not a positive).* A particulate:dissolved partitioning
  observable initially looked like a dramatic pass, but a 5-skeptic adversarial verification showed
  it was largely a construction artifact: `pFe/DFe` reduces to `scav_rat·POC/W_SINK` (DFe cancels),
  so the "sharp well" is tautological, `(scav_rat, W_SINK)` are perfectly degenerate, and a real
  contaminated `Fe_TP` (biogenic + `alpfe`-scaling lithogenic) re-injects the source degeneracy.
  Only the *alpfe* confounder legitimately cancels — the rate stays unidentifiable. So partitioning
  reinforces the wall from a second angle rather than breaking it. Fe isotopes / ligands remain
  untested fallbacks, but the bar is now higher (need a *pure* scavenged-Fe observable + independent
  `POC`/`W_SINK`).
- *The growth closure's per-PFT lever (D2), scouted (growth via primary production).* Best candidate: the growth
  closure (`Smallgrow`/`Biggrow`) via specific production `NPP/biomass = μ·f_fe·LIGHT` — the structural
  twin of the iron trick (a flux/stock ratio cancels the loss terms that make standing-stock biomass
  unobservable). Verification verdict: **feasible but not a clean positive.** It inherits the same
  algebraic tautology (NPP computed from the candidate μ); *total* NPP — the only real observable —
  gives only the biomass-weighted **mean** of `μ_s, μ_l`, so the `{Smallgrow, Biggrow}` **pair stays a
  ridge** (Track-1's growth-pair ceiling, from a new angle), and per-PFT production (which would break
  it) is unmeasured; satellite NPP is Chl-derived (partly circular), only sparse 14C is independent. So
  growth becomes *aggregate*-observable-in-principle, not a positive E2. A ready self-twin scout design
  exists (`scripts/growth_npp_scout.py`, unbuilt) to confirm the aggregate-vs-pair split concretely.

**D3 — What counts as "independent validation = discovery"?** Track-1 was a consistency check
against Carroll's (under-constrained) values. If we clear an E2 on some observable, is held-out
real-data R² > 0 through transport the bar you'd accept as independent validation, and what is a
legitimately held-out target (v05 vs GLODAP; which region/period)?

## Smaller confirmations (carry-forward, don't gate the decision)

- **Stoichiometry / budget:** confirm DIC(−1)/ALK(−2) per mole PIC and boundary-flux signs
  (dust in, export/burial out, air–sea CO₂) so one `PIC_prod` feeds `dPIC`/`dDIC`/`dALK` and the
  budget closes; and whether freezing PIC dissolution/sinking (learning **production only**) is
  acceptable for Phase 1. (The steady-state sinking identity `W_SINK_PIC == W_SINK` is verified
  in the box; flagged in case the field version needs a cocco-PFT correction.)
- **Rain-ratio target:** the two load-bearing points stand — Carroll's `R_PICPOC` is itself
  under-constrained, and a single global constant is mis-specified against a regionally-variable
  ratio (real eqpac ≈ 0.039, ~1.6× the global mean). If we do target calcite, target the regional
  field, not a global constant.

## Already decided (no meeting time needed)

Route B (mechanistic UDE) over the black-box emulator and SBI — both need an unaffordable
perturbed-parameter Darwin ensemble; re-confirmed 2026-07-09 against the newest sources
(NeuralOGCM, differentiable VEROS, DIFNO), which independently corroborate parameter-specific
identifiability. Transport numerics (div-free `w`-from-continuity, Thomas vertical diffusion,
centered advection), windowed-BPTT + checkpointing, the distillation go/no-go gate, and DB-1/DB-2
data staging are all built, verified, and local-gated. v05 velocity is on disk; a
perturbed-parameter ensemble is assumed ≈ 0 (confirm only if that changed).
