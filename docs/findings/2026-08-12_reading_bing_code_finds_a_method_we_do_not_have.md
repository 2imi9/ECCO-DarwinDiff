# Reading BING's code (not its paper) finds a method we do not have: an information-criterion ladder

**Date:** 2026-08-12 · **Cost:** code read, no compute · **Prompted by:** a fair challenge that the
AI4Ocean deep-dive read papers rather than code.

## What the earlier scan actually did, stated plainly

The 38-member AI4Ocean scan and the 42-candidate evidence sweep were **publication-record work**:
homepages, Scholar/OpenAlex records, DOIs and abstracts. The only code touched was a **README-level**
enumeration of `github.com/ai-for-ocean` (4 repos: two workshop repos, the website source, and a
`projects` repo whose README is placeholder headings — no BGC code anywhere). Individual project
implementations (NeurOST, MAESSTRO) and all 38 members' repositories were **not** examined.

That was a real gap, and closing it on the single highest-value target changed something.

## The target

Prochaska & Frouin 2025 (`10.5194/bg-22-4705-2025`) is the alliance's closest methodological
analogue to our work: a **degeneracy/identifiability result for ocean-colour retrieval** (Rrs
depends on the ratio bb/a, so non-water IOPs cannot be retrieved independently). The paper states
the conclusion — *"multi-spectral satellite observations lack the statistical power to recover more
than three parameters describing non-water backscattering."*

The paper does not say **how** that number is obtained. The code does. It is **BING**, at
`github.com/ocean-colour/bing` (redirected from `AI-for-Ocean-Science/bing`).

## What the code shows

`bing/stats.py::calc_ICs` is the whole mechanism, and it is elementary:

```python
nparm = np.sum([model.nparam for model in models])
BICs  = nparm * np.log(model_Rrs.shape[1]) + chi2      # nwave = number of bands
AICs  = 2. * nparm + chi2
```

Combined with `bing/models/anw.py` and `bing/models/bbnw.py` — a library of interchangeable
absorption and backscattering parameterisations of differing complexity — and MCMC posteriors via
`emcee` (`bing/fitting/inference.py`), the method is:

> **fit a ladder of nested models of increasing parameter count, and let AIC/BIC identify where the
> observable stops supporting further parameters.**

"Three parameters" is not a claim about backscattering physics. It is where the BIC penalty
overtakes the χ² gain for that observation set.

## Why this matters to us

**We have no information-criterion analysis anywhere.** `settled` returns nothing for "information
criterion" across 550 rows / 292,189 characters, and `grep -riE "\bBIC\b|akaike|\bAIC\b"` over
`scripts/` and `src/` returns nothing. This is genuinely absent, not merely unrecorded.

It is a **different question from the one we ask**, and arguably a sharper one:

| | our framing | the IC framing |
|---|---|---|
| question | is parameter *X* recoverable? | how many parameters does this observable set support **at all**? |
| instrument | recovery counts vs matched untrained null; Fisher/CRLB; profile likelihood | ΔBIC across a nested-model ladder |
| output | per-parameter verdicts | a single supported-complexity number |

We currently assert a **4-observable denominator** and "two globally recovered, two regionally
identifiable". An IC ladder would produce an independent statement of the form *"these observables
support k free parameters"* — from a published method, in an adjacent ocean domain, by an author on
the alliance roster. That is exactly the shape of independent-method validation issue **#163** asks
for (the repo's stated #1 scientific gap).

There is also a suggestive connection to something already measured. `ded110`/`ded111` record a
**DOF ladder with an inverted U** — 6 free values → trio 0/50, 406 shared → 25/50, 1,218 per-AOI →
3/50, 17,106 free per-cell → 0/40. Underfit at one end, overfit at the other is precisely the
trade-off an information criterion formalises. An IC framing could convert that empirical curve into
a principled one.

## The obstacle, stated before anyone gets excited

**`nparm` is not 6 for us.** BING's models carry 3–5 physical parameters, so `nparm` is unambiguous.
Our parameters are *outputs of a per-cell DINN* with thousands of weights, so a naive BIC would be
dominated by network capacity rather than by the six quantities of interest. Any port has to first
answer "what is the effective parameter count of a per-cell network?" — which is the same question
issue **#209** asks (is the per-cell *network* load-bearing, or just the degrees of freedom?).

Two further caveats: BIC assumes a correctly specified likelihood with independent observations,
while our loss is a weighted sum of heterogeneous terms with per-cell spatial correlation; and
`calc_ICs` currently raises on the MCMC path (`"Not ready for MCMC yet"`), so even upstream it is
used with Levenberg–Marquardt fits, not posteriors.

**So this is a lead, not a result.** It is recorded as a lead.

## The honest generalisation

Reading the paper gave a **citation**. Reading the code gave a **method, its exact implementation,
and its limits**. For work this close to our own thesis, the code was worth more than the abstract —
and for the rest of the alliance (physical models we had already established are physics-only) it
would not have been. Targeted code reading, not blanket code reading.
