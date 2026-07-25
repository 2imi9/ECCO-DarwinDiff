# Two-anchor real-box self-twin — geometry result (2026-07-22, B200)

**Bottom line: the two-anchor {dust source + scav sink} design breaks the `alpfe`↔`scav_rat` degeneracy
GEOMETRY in the real differentiable box — `|ρ(alpfe,scav)|` drops 0.472 → 0.061 as the anchors are added,
and the break is CONDITIONAL on pinning the export/uptake partition (the "partition tax"). This validates
the identifiability *geometry* the analytic OSSE predicted (`|ρ| 1→0.20`), NOT real-data recovery.**

This promotes `scripts/analysis/two_anchor_osse.py` (analytic) into the real Darwin 0-D box via
`scripts/analysis/two_anchor_realbox.py`. The two anchors are **synthetic self-twin** (computed FROM the box
at Carroll, so self-consistent). Job 179387, n=20 random-init seeds, 600 Adam steps, geo1 anchors-only recipe.
Artifact: `docs/findings/two_anchor_realbox.json`.

## Geometry at the config optimum

| config | anchors | \|ρ(alpfe,scav)\| | CRLB_rel(scav) | sloppiness (dec) |
|---|---|---|---|---|
| baseline | anchors-only | **0.472** | 0.770 | 2.84 |
| dust | + source | **0.195** | 0.698 | 3.34 |
| scav_pinned | + sink (partition removed) | **0.089** | 0.713 | 3.51 |
| **both_pinned** | source + sink, partition removed | **0.061** | 0.706 | 3.70 |
| **both_free** | source + sink, **partition NOT removed** | **0.131** | 0.707 | — |

Two things the table shows:

1. **The two anchors progressively break the degeneracy geometry.** `|ρ|` falls 0.472 → 0.195 (dust source) →
   0.089 (scav sink) → 0.061 (both). The dust-source value **0.195 matches the analytic OSSE's `|ρ| 1→0.20`**
   — the real box has the response-surface geometry the OSSE predicted.
2. **The partition tax is real and quantified.** `both_pinned` (export partition removed, i.e. a ²³⁴Th flux
   with the biological export already subtracted) reaches `|ρ|=0.061`; `both_free` (raw flux, partition NOT
   removed, so `scav_rat` trades against the free growth params) only reaches `|ρ|=0.131` — ~2× looser. So the
   geometric break is **conditional on pinning the export/uptake partition**, exactly as the Phase-2 plan
   requires (assimilate the scavenging flux with the partition removed, not the raw flux).

## The honest caveat (script's own verdict: "NO CLEAN BREAK")

`scav_rat` recovers **20/20 in EVERY config, including baseline** — because in the self-twin the anchors are
self-consistent, so there is no recovery degeneracy to break (the box can always fit its own targets). The
anchors therefore tighten the **geometry** (`|ρ|`, CRLB) without changing the already-perfect self-twin
recovery count. That is why the script's verdict is *"NO CLEAN BREAK in the real box"* in the **recovery**
sense — and it is the correct, honest read: **this validates the identifiability GEOMETRY of the two-anchor
design, not real-data recovery of `scav_rat`.** Real-data recovery still requires real ²³⁴Th / ²¹⁰Po flux data
with the export partition (Phase 2); on real data `scav_rat` is 0/10 in this anchors-only recipe (25/50
per-AOI in the flagship geo1 config, 41/50 at 4000 epochs), and this self-twin says nothing to the
contrary.

## What it does and does not license

- **Does:** confirm that a {source row + sink row} makes `scav_rat` geometrically identifiable in the real box
  (|ρ| 0.47→0.06), conditional on the partition — the OSSE geometry holds in the full differentiable model.
  Motivates Phase 2 (build the real sink anchor with the partition; present `scav_rat` as BOUNDING, factor ~2).
- **Does NOT:** demonstrate that real observations recover `scav_rat` (self-twin ≠ real data), and does not
  move the STATUS scoreboard (`scav_rat` stays the frontier's fragile leg — basin-dependent, with only the
  equatorial Pacific leg information-limited — awaiting the real sink anchor).

Reproduces the OSSE (`docs/findings/2026-07-22_two_anchor_osse_verified.md`) and the red-team bounds
(`docs/findings/2026-07-22_two_anchor_redteam.md`) in the real box. `verify_run` N/A (this is a geometry
diagnostic, not a recovery run; its own convergence/geometry checks pass).
