# eqpac scored alone: information says "fixable", experiment says "worse" — the case for model error

**Date:** 2026-07-28 · **Artifact:** `docs/findings/observation_design_eqpac.json`
· **Run:** `AOIS=eqpac … scripts/analysis/observation_design.py`

## Result

Scoring the equatorial Pacific **on its own**, rather than as one of three AOIs:

    base F0 = surface dissolved Fe only
    iron 2x2 eigenvalues: sloppy 4.726e-05 · stiff 5.929e-01
    condition number 12545.4
    posterior corr(alpfe, scav_rat) = +1.000   DEGENERATE

| observable | var. reduction | cond after | alignment |
|---|---|---|---|
| **`dfe_sub`** (subsurface dissolved Fe) | **6426×** | **12545 → 2.1** | **0.98** |
| `scavflux_surf` (²³⁴Th/²¹⁰Po proxy) | 6192× | → 7.4 | 0.70 |
| `scavflux_sub` | 1106× | → 11.8 | 0.86 |
| `bsi_surf` | 7.4× | → 19745 (**worse**) | 0.00 |
| **`dfe_surf_2`** (a 2nd identical surface survey) | **2.00×** | **12545, unchanged** | 0.00 |
| `pic_surf` / `poc_surf` / `feupt_surf` | 1.6–1.7× | slightly worse | ~0.00 |

Two things stand out against the pooled 3-AOI figures we have been quoting:

1. **eqpac alone is far more degenerate than the pooled problem** — condition number **12545**, not
   2930, with `corr(alpfe, scav_rat) = +1.000` exactly. It is the degenerate basin, quantified.
2. **The winner for eqpac is subsurface dissolved Fe**, not the scavenging-flux observable. `dfe_sub`
   aligns 0.98 with the sloppy direction and collapses conditioning to **2.1** — effectively curing
   the degeneracy.

The "more of the same data does nothing" result reproduces exactly for this basin: a second identical
surface survey gives the trivial 2.00× and leaves the condition number untouched.

## The contradiction that matters

Information theory says eqpac is **fixable**, and names the fix: subsurface dissolved Fe.

But that data **already exists and is already loaded** — this very run reported
`GEOTRACES bins in-AOI: surface=26, subsurface=28`. And empirically, up-weighting it makes recovery
**worse**: `GEOTRACES_SUB_W` 1→3→8 degrades `scav_rat` **9/10 → 5/10 → 1/10** (`STATUS.md:335`).

So:

| line of evidence | says |
|---|---|
| Fisher / OED | subsurface Fe cures the eqpac degeneracy (cond → 2.1) |
| Actual experiment | adding weight to subsurface Fe **degrades** recovery |
| `tan φ` (measured today) | eqpac FeT residual ≥ ‖data‖, φ = 90° — the box cannot reproduce eqpac iron at all |
| Corrected κ arithmetic | eqpac is the one basin whose implied error **exceeds** the worst-case κ bound |

Four independent lines, one coherent reading: **eqpac's `scav_rat` wall is forward-model
misspecification, not an information limit.** Pushing more information through a wrong forward map
does not help and can hurt — which is exactly the observed sign.

This reframes the project's own conclusion. We have been reporting eqpac as *information-limited*
("the residual, needing new observations"). The evidence now points at *model-limited*, which needs a
better box, not a better cruise.

## What would falsify it

If eqpac iron were merely information-limited, an independent estimate of the equatorial dissolved-Fe
**field** should agree with Darwin's. TPOSE publishes dissolved Fe over this exact box at 1/3°
(`d59d1d0`). **Prediction: Darwin's equatorial iron will differ from TPOSE's.** If it agrees, this
reading is wrong and the information-limit framing survives.

That is a genuine prediction, made before looking, and it is testable with a download.

## Caveats

- Single seed (N=1), Carroll θ, `epochs=0` — this is a Fisher-geometry calculation at the published
  optimum, not a fit.
- OED scores are **local** at that θ; a strongly misspecified model makes local sensitivity a weaker
  guide, which is itself part of the argument.
- `dfe_sub` here means *subsurface dissolved iron*. GP15 Leg 2's dissolved phase is ²¹⁰Po/²¹⁰Pb —
  that maps to `scavflux`, ranked **2nd/3rd**, not to `dfe_sub`.
