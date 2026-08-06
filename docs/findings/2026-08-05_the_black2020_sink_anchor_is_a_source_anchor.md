# The Black 2020 sink anchor is a source anchor, and mass conservation says so before any fit

**Date:** 2026-08-05 · **Compute:** none on the cluster; three 0-D box integrations locally ·
**Code:** `scripts/analysis/anchor_leverage_screen.py` (new), `tests/test_black2020_fe_flux_loader.py`
(new — the loader had none) · **Screened:** `src/darwindiff/black2020_fe_flux_loader.py`

**Verdict: the Black et al. (2020) upper-ocean Fe export compilation CANNOT identify `scav_rat`
in this box, and the reason is structural rather than observational. In a 0-D box at steady state
the total iron leaving the surface layer equals the iron entering it, so the total export flux —
exactly the quantity Black measures — is `alpfe · PHI_DUST` and is independent of `scav_rat` by
mass conservation. A 16x sweep of `scav_rat` moves it by 0.00%. At the 200-step operating window,
where the box is still in transient, a 4x sweep moves it by 5.2%, against an observation whose own
1σ is 412% of its value. The bulk-flux anchor is short by a factor of ~130. This was carried in the
repo as the designated SINK partner that would lift the alpfe↔`scav_rat` degeneracy; it is a
SOURCE anchor wearing a sink label.**

## 1. What was believed

`black2020_fe_flux_loader.py` has been in the repo with a clear premise, stated in its own
docstring: Black's iron EXPORT FLUX is "the dimensionally-new SINK rate: it is what a
scavenging/export closure produces, so it directly constrains `scav_rat`", and it pairs with the
Xu-Weber soluble-deposition SOURCE anchor as "the two legs that lift the rank-1 (alpfe ↔ scav_rat)
degeneracy into a bounded basin".

It had **zero importers and zero tests**. It has never been wired into a fit.

## 2. The structural result

The box loses dissolved iron by two routes, and gains it by one:

```
dDFe = alpfe·PHI_DUST  −  scav_rat_per_day·DFe·POC  −  Q_FE·(growth_s + growth_l)
        source              scavenged sink              biogenic sink
```

A ²³⁴Th- or sediment-trap-derived upper-ocean Fe export flux measures **particulate Fe leaving the
layer**, which is the SUM of the two sinks, not the scavenging term alone.

At steady state `dDFe = 0`, so:

```
scavenged + biogenic  =  alpfe · PHI_DUST
```

The total is pinned by the source. `scav_rat` sets **how** iron leaves — the split between the two
routes — never **how much**. Measured, integrating to steady state at Carroll's parameters:

| `scav_rat` | total Fe export (mmol Fe m⁻² yr⁻¹) |
|---|---|
| 0.25x Carroll | 0.8477 |
| 1.00x Carroll | 0.8477 |
| 4.00x Carroll | 0.8477 |

Equal to 6 significant figures, and equal to `alpfe·PHI_DUST·H·365.25` = 0.8477. This is pinned as
a regression test (`test_total_export_is_independent_of_scav_rat_at_steady_state`), because it is
the kind of invariant that a later refactor could quietly break.

This is the same shape as the 2026-07-30 gauge-symmetry result: an observable that looks new but
re-encodes a combination already fixed elsewhere. Here it is not even a subtle re-encoding — it is
mass conservation.

## 3. The result at the operating point, where it is weaker but not different

The flagship does not run to steady state: 200 steps at dt = 0.25 d is 50 days, and subsurface iron
is only 47.5% converged there. In transient the total export is not yet exactly the source, so
`scav_rat` retains a little leverage. How much:

`scripts/analysis/anchor_leverage_screen.py --param scav_rat --aoi natlsubpolar --obs-sigma-rel 4.12`

| observable | response to a 4x change in `scav_rat` | obs precision required | Black's actual precision |
|---|---|---|---|
| **total Fe export** | **5.15%** | 3.14% | **412%** |
| scavenged fraction | 4.67% | 2.85% | 412% |
| biogenic fraction | **44.41%** | 27.14% | 412% |

"Required precision" is what the observation must achieve to resolve a parameter change the size of
the Cal-grade band (±40%, a 2.33x span), scaling logarithmically from the measured response.

**The bulk-flux anchor is short by a factor of 131.** Longer windows make it worse, not better: at
3200 steps the total response falls to 0.4% as the box approaches the steady state where it is
exactly zero.

## 4. The coverage problem, which is the smaller problem

Even setting leverage aside, the staged Table 1 does not reach the basins:

| AOI | programs, of 20 |
|---|---|
| eqpac | **0** |
| natlsubpolar | **1** (GA01 GEOVIDE, `coord_kind = transect`) |
| southernoceanpac | **0** |
| npac | 0 |
| npsg | 1 (VERTIGO / ALOHA, `point`) |

One program across all three flagship AOIs, and it is a `transect` row — the fidelity class the
loader's own docstring warns "badly under-represents" the program, since a basin-crossing transect
is reduced to a single representative coordinate. Its province scalar is
**3.056 ± 12.601 mmol Fe m⁻² yr⁻¹**, σ/value = 4.12, and with n = 1 there is no between-program
scatter, so that σ is one program's own min–max half-range.

Worth being clear about the ordering: **coverage is the fixable problem and leverage is not.** If
the bot-blocked per-station Supporting Information (Table S1) were obtained tomorrow, it would
improve the first table and leave §2 and §3 untouched.

## 5. What this says to do instead

The screen does not only refute; it points. The **partition** carries an order of magnitude more
signal than the total: the biogenic share of Fe export moves **44%** for the same 4x change in
`scav_rat` that moves the total by 5%. That is the discriminating quantity.

So the observable class that could anchor `scav_rat` is **particulate Fe speciation** — scavenged
(lithogenic/authigenic) versus biogenic Fe in sinking particles — not bulk Fe export.

This is consistent with, and independently re-derives, the standing ranking that a particulate-Fe
**scavenging-rate** observable is the best new measurement for the degeneracy. The Cochran GP15
²¹⁰Po/²¹⁰Pb loader already in the repo measures scavenging specifically rather than total export,
which puts it in the right class where Black is not — though its own staged coverage is
two stations, and that is a separate gate it still has to pass.

## 6. What was built, and what was deliberately not

**Built:**
- `scripts/analysis/anchor_leverage_screen.py` — a reusable design-time screen. Given a parameter,
  a factor span and the run window, it returns the fractional response of each candidate observable
  and the observation precision needed to grade the parameter at the Cal band. Registry and box
  arithmetic, no fitted model, one 0-D integration. The anchor-side sibling of
  `contract.rescale_is_admissible` and `contract.bound_proximity_risk`.
- `tests/test_black2020_fe_flux_loader.py` — 14 tests. The loader had none. They pin the parse, the
  geometric-mean point estimate, the per-AOI coverage counts, and the mass-conservation invariant.

**Not built: the loss term.** A `BLACK_FE_EXPORT_W` lever wired to the total export flux would be a
weight on a quantity that is provably independent of the parameter it was introduced to constrain.
`verify_run.inert_terms()` would not catch it either — natlsubpolar is nonzero, so the term would
report as live while carrying no information about `scav_rat`. Wiring it would produce a runnable,
gate-passing, meaningless anchor. The screen exists so that this decision gets made before the
cluster night rather than after it.

If the anchor is wanted anyway as an **`alpfe` / source-side consistency check** — which is what it
actually is — that is a coherent use and a different proposal, and it should be graded against
`alpfe`, not `scav_rat`.

## 7. Caveats

- The areal conversion uses `H_MLD = 50 m`. Every flux number is linear in it, so a different layer
  thickness rescales the modelled fluxes — but **not** the leverage percentages or the steady-state
  invariant, which are ratios.
- Black's export horizon is 0–300 m while the box layer is ~50 m. That mismatch makes the absolute
  comparison in §3 approximate. It does not touch §2: mass conservation holds at any layer depth.
- The 0-D box homogenises spatial structure, and all three AOIs converge to the same steady state
  precisely because of that. The transient numbers in §3 do differ by AOI (natlsubpolar 5.15%,
  southernoceanpac 6.55%) and both are far short.
- Single-parameter sweep at Carroll's values for everything else. A full Fisher treatment could
  differ in detail; it cannot repair a zero.
