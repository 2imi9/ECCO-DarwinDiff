# Coupling a physical ML model to DarwinDiff does not improve iron identifiability, and a prescribed source makes it worse

**Date:** 2026-08-12 · **Cost:** local, seconds · **Script:**
`scripts/analysis/prescribed_source_breaks_gauge.py`

## The question

Could the AI4Ocean physical ML products (MAESSTRO SST inpainting, NeurOST eddy/current maps, SSBI's
U-Net recovering vorticity/divergence/strain from SSH, SWOT SSH itself) be **coupled** to
DarwinDiff to improve parameter recovery?

"Coupled" has two distinct readings with different answers, and it is worth separating them because
one is already settled and the other was not.

## Reading 1 — feed the physical fields into the DINN as input channels. Settled NO.

Measured, and it is unambiguous: *"Do covariate input channels rescue `scav_rat`? **No.** `scav_rat`
stays 0/10 across all five arms"* (`2026-07-22_covariate_channels_result.md`). Covariates are also
actively harmful in specific pairs — wind, SSS, pCO₂ and CO₂-flux channels drive `R_PICPOC` to 0/10
(`ind254`).

The reason is structural, not empirical. `ded111` states the degeneracy is a multiplicative gauge
symmetry: a learned sink `S = r0·g_θ(x)` is homogeneous of degree one in `r0`, so
`(alpfe, r0) → (λ·alpfe, λ·r0)` leaves the predicted DFe field unchanged **"for ANY g and any
weights inside it."** Input channels are arguments to `g`. **A symmetry of the forward model cannot
be broken by changing the inputs to the parameter map.** More physics in the inputs cannot help.

## Reading 2 — use the physical model to supply a prescribed source term. Measured, and it is worse.

This is a genuinely different object and it is *not* covered by the gauge argument, because a
prescribed source does not co-scale with λ. The natural candidate is the vertical/eddy iron supply
that Uchida, Balwada et al. 2020 (`10.1038/s41467-020-14955-0`) measured as supporting Southern
Ocean production — exactly the kind of term a coupled eddy-resolving model would deliver.

The steady-state box makes it explicit:

```
FeT = (alpfe·D_sol + R − E) / (U + scav·f')
```

`R` is a prescribed source that does not scale with `alpfe`. Sweeping it, with a heterogeneous
24-cell field and DFe as the only observable, `E` pinned:

| R | prescribed-source fraction | \|ρ(alpfe, scav)\| | cond | CRLB log alpfe | CRLB log scav |
|---|---|---|---|---|---|
| 0.00 | 0.000 | **0.090** | 1.18e3 | **0.00154** | **0.0527** |
| 0.05 | 0.051 | 0.648 | 2.76e2 | 0.00547 | 0.0690 |
| 0.10 | 0.097 | 0.852 | 2.28e2 | 0.0128 | 0.100 |
| 0.20 | 0.177 | 0.919 | 2.32e2 | 0.0228 | 0.133 |
| 0.40 | 0.301 | 0.914 | 1.33e2 | 0.0287 | 0.129 |
| 0.80 | 0.462 | 0.875 | 5.40e1 | 0.0328 | 0.109 |
| 1.60 | 0.632 | 0.817 | 2.06e1 | 0.0394 | 0.0911 |

**Adding an independently-known iron source makes `alpfe` harder to identify, not easier.** The
correlation climbs from 0.09 to 0.92 and the CRLB on `log alpfe` degrades by **26×**.

### The mechanism, confirmed directly

Log-sensitivities of DFe at the truth:

| R | d ln FeT / d ln alpfe | d ln FeT / d ln scav |
|---|---|---|
| 0.00 | **1.4762** | −0.1667 |
| 0.20 | 1.1205 | −0.1667 |
| 0.80 | 0.6503 | −0.1667 |
| 1.60 | **0.4170** | −0.1667 |

`alpfe` enters **only** through `alpfe·D_sol` in the numerator. As `R` grows, the dust term is a
smaller share of the total source, so the DFe signal carrying `alpfe` is **diluted**, while the
`scav` sensitivity is untouched because it lives in the denominator. Better physics in the source
term means *less* of the observable is attributable to the parameter we are trying to recover.

### A useful by-product: the gauge symmetry, reproduced numerically

Setting `E = 0` and `U = 0` gives sensitivities of exactly **+1.0000** and **−1.0000**, summing to
**0.0000** — perfectly anti-parallel, i.e. rank-1. That is `ded111` reproduced from scratch, and it
also shows **what actually breaks the exact gauge in our box: `E` (export) and `U` (uptake), not
`R`.** With the defaults the sensitivities are +1.4762 and −0.1667, sum +1.3095 ≠ 0. This is the
quantitative face of `ded97`/`abd565` ("scavenging is ~79.7% of the surface sink, so the orbit is
NEARLY flat rather than flat").

## A correction worth recording

The first version of this test used a **single** DFe observation and reported `|ρ| = 1.000000` at
every `R`, which looked like the gauge symmetry surviving. It was not. A single scalar observation
gives `F = J Jᵀ / σ²`, which is rank-1 **by construction** for any two parameters — that is
underdetermination, not a symmetry. The gauge question only has content over a *field* of cells,
because the symmetry claims DFe is unchanged everywhere at once. The script now documents this so
the trap is not re-entered.

## What this means for the alliance products specifically

Their products are **SST, SSH, SSS, surface currents and surface eddy fields** — all surface. But
`abd529` measures that **`scav_rat` is identifiable from the VERTICAL STRUCTURE of dissolved iron,
not from its surface concentration** (`so_sub` 33/50 vs `so_surf` 14/50, Fisher P = 2.7e-04).

So the binding constraint on our one hard parameter is *subsurface*, and everything the alliance
offers is *surface*. Even setting aside both results above, their data does not touch the axis that
binds.

## Where physical coupling IS legitimate — a different goal

None of this argues against Track 2 (`#176`, differentiable BGC on prescribed 3-D transport). That
work targets the **dimensional surrogate gap** — the 0-D box homogenizes spatial structure — and a
better forward model is a real improvement in *fidelity*.

But fidelity and identifiability are different goals, and the repo already separates them:
`ded77` — *"No architecture can fix structural non-identifiability."* A coupled physical model would
make the forward model more right. It would not make the iron pair more observable, and by the
dilution mechanism above it could make one leg of it measurably less so.

## Limits

Idealized steady-state box in arbitrary units, one observable (DFe), `E` pinned, prescribed source
assumed known **exactly** (a real coupled model would carry its own error, which can only make this
worse). The CRLB magnitudes are not the repo's real ones and must not be quoted as such. What is
robust is the **sign and mechanism**: dust-share dilution is algebraic, not numerical, and it
follows from `alpfe` appearing only in the numerator.
