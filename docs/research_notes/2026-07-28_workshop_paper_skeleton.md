# Workshop paper skeleton — observation design through a differentiable surrogate

> ## ⚠ NOT the workshop submission — superseded 2026-07-28
>
> Superseded by `2026-07-28_workshop_paper_v2_ml_findings.md` **on strategy, not on content.**
> ECCO-Darwin identifiability and observation design are the long-term flagship and belong in a full
> conference/journal paper. A 4-page workshop should not spend them.
>
> **This plan is retained as the outline for that flagship paper.** The argument, the numbers and the
> GP15 coverage turn all stand — they are simply aimed at a different venue.

**Date:** 2026-07-28 · **Target:** ~~CCAI workshop~~ → **flagship conference/journal paper**

> **Process note.** The venue asks that its CFP and website materials not be passed through an LLM
> during paper-writing. So Lucas owns format, scope and section-length decisions by reading the CFP
> directly. Everything below is assembled from this repository's own verified results only.
> **No venue material was used to produce it.**

## The pitch in one sentence

Rank candidate ocean observations by their Fisher-information contribution *through a differentiable
biogeochemistry surrogate*, so cruises can be compared before they are funded — and show the method
rejecting a top-ranked observable on grounds the ranking alone would miss.

## Why this is the right result to submit

It is the one finding that survived a full adversarial review. Two neighbouring claims did not, and
must stay out of the paper:

- the emulator's skill story (a clean negative result; different paper, different venue),
- the float32/conditioning hypothesis (my κ units error, corrected — see
  `2026-07-27_conditioning_precision_hypothesis.md`).

## Argument

**1. Setup.** ECCO-Darwin calibrates biogeochemistry by Green's functions: one full forward run per
parameter, so few parameters get tuned. Menemenlis's ECCO Summer School 2019 Table S1 gives the cost
per observation for all 14 simulations. Decomposing it: the *first-guess → baseline* step accounts
for 0.23520 of the total 0.23919 improvement, and the Green's-functions parameter fit for **0.00399**
— about **1.7%**. With **n = 4,038,777** observational constraints. *(Menemenlis's own slide
annotates this as 93%; our arithmetic gives 98.3%. Reconcile or quote the raw costs and show the
subtraction — do not inherit a number we cannot reproduce.)*

So the parameters are weakly constrained *by a comprehensive observing system*. That is the hook: the
binding constraint is **which** observations exist, not how many.

**2. Method.** Reimplement the biogeochemistry differentiably; the per-cell parameter network gives
gradients for every parameter in one backward pass. For each candidate observable, form its Fisher
contribution `F_o` and score `F0 + F_o` against the base:
variance reduction along the degenerate direction, condition number after, smallest-eigenvalue lift,
D-optimality gain, and the alignment of `F_o`'s top eigenvector with the sloppy direction.

**3. Results (all repo-verified).**

| finding | number | why it matters |
|---|---|---|
| base iron 2×2 Fisher eigenvalues | 1.08e-3 / 3.18 → κ(F) = **2930** | the alpfe/scav_rat degeneracy, quantified |
| a ²¹⁰Po/²¹⁰Pb-type scavenging-rate observable | κ(F) **2930 → ~7**, sloppy-direction variance ÷ **1400** | rate observables break it |
| subsurface [DFe] | ~1260× | depth breaks the source/sink symmetry (alpfe injects only at the surface) |
| **a second identical surface-[DFe] survey** | variance ÷ **2.00**, κ **unchanged at 2930** | **more of the same data does nothing** |

That last row is the paper's sharpest sentence.

**4. The honest turn — and the reason a reviewer should believe the rest.** The top-ranked rate
observable is realised by GP15 (Cochran ²¹⁰Po/²¹⁰Pb). Testing coverage against our three study
basins:

```
eqpac 0 · natlsubpolar 0 · southernoceanpac 0 · npac 50 · npsg 25
```

GP15 is a single Pacific meridional transect near 152°W. **It has zero samples in the two basins
where scav_rat actually fails** (eqpac 7/50, natl 20/50). An information ranking that ignores where
the ship sailed would have funded the wrong cruise. Observation design must be **joint over
information content and spatial support** — that is a method contribution, not a caveat.

**5. Impact.** Ocean cruises cost millions and are planned years ahead. A surrogate that ranks
candidate measurements *before* funding, and can rule one out on coverage, is a concrete decision
tool.

## Numbers that must NOT appear

- κ(J) = 2930 — that is κ(F) = κ(J)²; κ(J) ≈ 54. Corrected 2026-07-27.
- "beats persistence" / "~9-month horizon" — retracted.
- `scav_rat` 26/50 — the flagship is **25/50**; 26/50 is the subW=1 arm.
- `−0.161 ± 0.013` — the AR(1) spread is **± 0.015**; ±0.013 belongs to persistence.

`tests/test_canonical_numbers.py` (13 tests) guards these. **Run it against the final text.**

## Gaps to close before writing

1. **`tan φ` is unmeasured** and load-bearing in the design doc — one forward pass per block.
2. **Reconcile 93% vs 98.3%** on the Table S1 decomposition, or quote raw costs only.
3. **The other four unwired loaders have no tests.** Only `cochran` is now covered
   (`tests/test_cochran_gp15_po_pb_loader.py`, 13 tests). If the paper claims a ranking over
   candidate observables, the loaders behind those candidates should be exercised.
4. **Is there ANY ²³⁴Th or Po/Pb dataset with equatorial Pacific coverage?** If no: the eqpac wall is
   an observing-system fact statable with unusual confidence, and that is a stronger result than the
   ranking itself. If yes: it is the next experiment. **This is the highest-value open question.**

## What stays out

The identifiability study proper is domain-shaped and belongs at AGU or in manuscript #1, where
reviewers know ECCO-Darwin. The AGU draft (`docs/agu26_abstract_draft.md`) is finished and still
valid for a future cycle — do not delete it.
