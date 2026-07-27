# Is part of the "information limit" actually float32 roundoff? — hypothesis + decisive test

**Date:** 2026-07-27 · **Status:** hypothesis, NOT tested · **Cost to settle:** one config change

## The measured facts (all already in-repo)

| quantity | value | source |
|---|---|---|
| iron-block condition number, surface [DFe] only | **2930** | `2026-07-23_observation_design.md:15` |
| … after adding a surface particulate-Fe scavenging-flux observable | **≈7** | same, `:15` |
| … after a *second identical* surface [DFe] survey | **2930, unchanged** | same, `:24` |
| per-AOI iron conditioning, Southern Ocean | **cond 2.2** | `STATUS.md:307,347` |
| per-AOI iron conditioning, eqpac / natl | **cond 35–51** | `STATUS.md:309,348` |
| box integration dtype | **float32** | `carroll6_5pft_2layer.py:490` |

Recovery tracks conditioning almost monotonically: `scav_rat` is **49/50** where cond = 2.2, and
**7/50 (eqpac) / 20/50 (natl)** where cond = 35–51.

## The amplification arithmetic

For a linear least-squares inverse problem the relative parameter error is bounded by the relative
data error times the condition number of the Jacobian:

```
‖δθ‖/‖θ‖  ≲  κ(J) · ‖δd‖/‖d‖
```

Near the optimum the loss curvature is the Gauss-Newton Hessian `H ≈ JᵀJ`, and

```
κ(JᵀJ) = κ(J)²
```

That squaring is the "small noise blows up" mechanism. Working it through, and asking how many
significant decimal digits survive in each precision:

| regime | κ(J) | κ(JᵀJ) | digits left, float32 | float64 |
|---|---|---|---|---|
| iron block, surface-only | 2930 | 8.6 × 10⁶ | **0.29** | 9.02 |
| eqpac / natl ratio | 50 | 2 500 | 3.82 | 12.55 |
| Southern Ocean | 2.2 | 4.8 | 6.54 | 15.27 |
| iron block + scav-flux obs | 7 | 49 | 5.53 | 14.26 |

(float32 carries ~7.22 decimal digits, float64 ~15.95.)

## The hypothesis

**In float32, the sloppy direction of the surface-only iron block sits at or below the roundoff
floor.** 0.29 surviving digits means the curvature along that direction is numerically
indistinguishable from noise. The box integrates **200 forward-Euler steps** before the loss is
formed, so roundoff accumulates along the way, and the sloppy-direction signal is ~2930× smaller
than the stiff-direction signal it is competing with.

If true, some part of what we currently report as an *information* limit in eqpac/natl is really a
*numerical* limit — and it is fixable, cheaply, without new observations.

**This would also explain the epoch behaviour.** `scav_rat` rises 25→41/50 between 2000 and 4000
epochs (`ep4k_n50`), which is the signature of grinding slowly along a high-curvature-ratio
direction. But eqpac stays ~6/50 even at 4000 epochs. Under this hypothesis those are two different
things: natl is optimisation-limited (slow but above the floor), eqpac is at the floor.

## The decisive test

Run the flagship config with the box in **float64**, changing nothing else.

- **eqpac `scav_rat` improves materially** → part of the "information limit" was precision. The
  claim in STATUS.md and the manuscript needs revising, and the fix is a dtype, not a cruise.
- **eqpac stays ~7/50** → the information-limit claim is *confirmed and strengthened*, because we
  will have eliminated the most obvious numerical confound. That is a better paper either way.

Cost: one dtype change plus a rerun; roughly 2× memory and ~2× time on the box. Cheap relative to
what it settles. Use n=10 seeds first as a screen, and only go to n=50 if the screen moves.

## Why this matters for the hierarchy question

The observation-design finding already contains the structural answer, and it is worth stating
plainly: **a second identical surface-[DFe] survey leaves the condition number unchanged at 2930**
and buys the trivial √2 variance drop. More of the same data does nothing.

So the hierarchy should not be organised by data *volume* but by **which observable breaks which
degenerate direction**. Measured, per the same file: a particulate-Fe scavenging flux collapses the
iron block 2930 → 7; a subsurface [DFe] is nearly as strong, because `alpfe` injects iron only at
the surface, so depth resolution is what breaks the source/sink symmetry.

That is the concrete form of "each parameter needs its own data part."

## Caveats — read before acting

- Training is first-order (Adam); we never form `JᵀJ` explicitly. The κ² figure describes the *loss
  curvature ratio* and the achievable accuracy, not a matrix we invert. The claim is about the
  signal-to-roundoff ratio along the sloppy direction, not about a literal normal-equations solve.
- The condition numbers above come from the Fisher analysis of the **iron block**, and it is not yet
  verified that the same κ governs the full multi-anchor loss actually used in the flagship.
- `float32` at `carroll6_5pft_2layer.py:490` is one confirmed site; the end-to-end training dtype
  has **not** been fully audited. Do that before running the test, or the test is meaningless.
- Digit counts assume worst-case error growth. Real accumulation is usually better than the bound.
