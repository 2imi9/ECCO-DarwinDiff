# B-SOSE `TRAC06` is total dissolved iron, so the Darwin comparison is not definitional

**Date:** 2026-07-30 · **Method:** documentation and source lookup, no compute ·
**Verdict: the pool is the same in both models. The 21% offset carries information and the
comparison can be reported as a difference in the modelled field.**

`2026-07-29_bsose_extent_and_first_iron_field_comparison.md` measured Darwin 0.197 nM against
B-SOSE 0.165 nM over 21,120 matched surface cells in `southernoceanpac`, ratio 1.21, log10 r 0.68.
That note correctly withheld the bias reading, because if B-SOSE's `TRAC06` were the free
(unbound) iron pool while Darwin's `FeT` is total dissolved iron, a 21% gap would be a definition
rather than a result. Per `2026-07-28_bling_comparability.md`, BLING partitions free iron against
a ligand while Darwin uses a total-DFe bilinear, so the concern was well founded.

It is resolved. **Both are the total dissolved pool.**

## First, a name collision worth recording

`TRAC06` is not a B-SOSE-specific name. It is the generic MITgcm ptracer slot number, and it means
different things in the two models purely because both list iron sixth:

| | model | tracer 6 | our mapping |
|---|---|---|---|
| ECCO-Darwin v05 | Darwin | `FeT`, "Total iron", mmol Fe / m^3 | `src/darwindiff/llc270_loader.py:66,103` |
| B-SOSE iter105 | MITgcm + N-BLING | `Fe` | distributed file ships as `TRAC06` |

`MITgcm/pkg/bling/bling_description.txt` fixes the BLING ordering: N-BLING "includes 8 tracers:
DIC, ALK, O2, NO3, PO4, Fe, DON, DOP (in that order in data.ptracers)". Iron is sixth, so
`TRAC06` = `Fe`. The B-SOSE iteration-105 solution page lists exactly those eight, which confirms
B-SOSE runs N-BLING rather than the 6-tracer `USE_BLING_V1` variant (whose order is DIC, ALK, O2,
PO4, Fe, DOP, where iron is *fifth*). Had B-SOSE used BLING v1, `TRAC06` would have been DOP.

So the earlier framing "is B-SOSE TRAC06 total or free iron" contained a hidden assumption that
`TRAC06` was a B-SOSE label. It is a slot index, and it happens to land on iron in both models.

## The answer, from the code B-SOSE actually runs

`MITgcm/pkg/bling/bling_bio.F` computes the speciation inline. The prognostic tracer array is
`PTR_FE` (declared at line 66, described at line 62 as "iron concentration"). The relevant block
begins at line 706 with the comment that the calculation determines ligand-bound and free iron,
that both forms are available for biology, and that only free iron is scavenged onto particles.

The mechanics settle it:

- `FreeFe` is a scalar local (`_RL FreeFe`, line 189), solved at line 719 from a quadratic in
  `kFe_eq_lig`, `ligand` and `PTR_FE`. It is **computed from** the prognostic tracer.
- `FreeFe` is never advected, never registered as a ptracer, and never written out.
- Scavenging uses `FreeFe` (lines 736 and 745). Biological uptake uses the total: line 414 has
  `FetoP_up = FetoP_max*PTR_FE/(k_Fe+PTR_FE)`, matching the comment that both forms feed biology.
- Under anoxia `FreeFe` is forced to zero (line 729) while `PTR_FE` is untouched, which is only
  coherent if `PTR_FE` is the conserved total.

`FreeFe <= PTR_FE` always. **`PTR_FE` = ligand-bound + free = total dissolved iron**, the same
conceptual quantity as Darwin's `FeT`.

### On the solution page's wording

The iteration-105 page describes `Fe` as "Dissolved Inorganic Iron [mol Fe/m^3]". That reads as if
it might exclude organically complexed iron, which would contradict the above. It does not:
"inorganic" there distinguishes the dissolved nutrient pool from iron held in organic matter and
biomass, not bound from unbound. Where a page label and the integrated source disagree about what
is in the array, the source is authoritative, and the source is unambiguous.

## What this does and does not license

**Licensed.** The 21% offset is a difference between two models' total dissolved iron fields. It is
not a units or definition artifact, so it can be reported as a model-model difference.

**Still not licensed.** Calling it a *bias* in Darwin. Two independent estimates disagreeing by 21%
says one of them is high relative to the other, and B-SOSE is not truth. Establishing direction
needs the observational anchor, not the second model. The comparability caveat from
`2026-07-28_bling_comparability.md` also survives in a narrower form: the pools match, but the
*dynamics* differ, because BLING scavenges the free fraction against a ligand with a
light-dependent stability constant while Darwin scavenges total DFe bilinearly. That affects how
each model arrives at its field, and it is a reason the fields differ, not a reason the numbers are
incomparable.

**Unchanged.** B-SOSE iter105 spans 29.79S to 78S and has no equatorial data, so it can only ever
test `southernoceanpac`.

## Sources

- `MITgcm/pkg/bling/bling_description.txt` and `bling_bio.F` (github.com/MITgcm/MITgcm), the
  package B-SOSE integrates.
- B-SOSE iteration-105 solution page, sose.ucsd.edu/bsose_solution_Iter105.html, for the
  distributed variable list.
- Galbraith, Gnanadesikan, Dunne and Hiscock 2010, Biogeosciences 7, 1043-1064, the BLING v0
  reference cited by the package.
