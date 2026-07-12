# Track-2 — results summary for discussion (2026-07-10)

*A short, shareable summary of where the differentiable-Darwin (Track-2) work landed — results in
write-up form, for a decision on direction, not a submission. Full detail:
[`2026-07-09_track2_identifiability_writeup.md`](2026-07-09_track2_identifiability_writeup.md);
reproducibility: [`2026-07-10_reproducibility_appendix.md`](2026-07-10_reproducibility_appendix.md).*

> **Role: 1-page abstract.** Headlines only — the **canonical** map/E2 numbers live in the write-up
> above. State results qualitatively here and cite the write-up, so any number is updated in **one**
> place (this de-duplication is what let the n=10 E2 update drift before).

## The result in one line

Track-2 asked whether adding prescribed spatial transport lets real observations constrain
ECCO-Darwin's uncertain BGC closures where the 0-D box could not. The answer, across the three
closures we can target with real, Darwin-independent data, is a clean **identifiability-limits
map**: none of them is constrainable, and — usefully — they fail for **three distinct reasons**.
*The method is ready; the observing system is the binding constraint.*
(Figure: `docs/findings/figures/fig1_identifiability_map.png`.)

| closure | verdict | why |
|---|---|---|
| **iron** `scav_rat` | observability wall | dissolved-Fe *concentration* is a low-information projection of the *rate*; a particulate:dissolved observable does not rescue it (structural) |
| **calcite** Ω-modulation of `R_PICPOC` (the scalar itself *is* recoverable) | support-limited | within-region Ω range ≤0.16 dex in every region — too small to fit a curve |
| **growth** `Smallgrow`/`Biggrow` | unobservable | total NPP gives only the biomass-weighted mean → the two-rate pair stays degenerate |

## What makes the calcite verdict solid (four independent lines)

`docs/findings/figures/fig2_calcite_support.png` tells it: Ω barely varies *within* any region
(0.08–0.19 dex, all below the ~0.30-dex identifiability threshold), and the only "wide" support comes
from *pooling* biomes — a between-biome contrast whose slope is a **Simpson artifact** (each basin's
slope is positive; the pooled slope flips negative only because the basins sit at different Ω *and*
different mean ratio). The null is confirmed four ways: the in-sample distillation oracle, independent
**in-situ GLODAPv3** Ω (838+1740 bottles — so it does not depend on model-derived Ω), a driver test
showing **SST and community composition don't rescue it either** (the limit is not Ω-specific), and
the make-or-break out-of-sample transport E2 (below). It is consistent with Marañón et al. (2016).

## The make-or-break test — run, decisive negative

`docs/findings/figures/fig3_e2_result.png`: a learned calcite closure fit through prescribed
transport and scored on held-out cells **does not beat a constant-through-transport null**, with a
**non-discriminating K_num control**. Notably a *constant* ratio advected through transport already
captures the held-out structure — the learned environmental modulation adds nothing. So transport
does not close the gap for the calcite closure; the identifiability limit holds **out-of-sample**,
not just in-sample.

**Hardened (2026-07-11):** this negative was replicated across a **10-seed ensemble** (Explorer H200)
— the learned closure loses to the null in **every** seed, robust to random init (the single-seed
default closure overfits far worse than the regularized one). Full per-seed numbers live in the
local-only `docs/findings/e2_seed_ensemble_scored.md`. *(Number kept out of this shareable summary per
the local-only policy — cite the scored doc.)*

## Honesty guardrails

Not a "transport closes the gap" pass, not a recovered closure, not "learned real biology." An early
"particulate observable breaks the iron wall" result was an artifact and was retracted after
adversarial verification. Small n throughout (calcite 26–34 cells/region), and a cleanly *powered*
within-region E2 is structurally impossible here (the Ω-band hold-out becomes a between-biome
extrapolation when pooled). An 8-reviewer adversarial panel hardened the write-up.

## The decision, and the forward contribution

**Is this identifiability-limits map the Track-2 contribution?** It reframes the original "learn real
closures" aim into an honest study of *what is observable and why* — which is itself novel, and which
turns into a concrete, actionable message for the observing community:

- **calcite** — need a dataset with real *within-region* Ω variation (high-latitude / seasonal
  co-located production + carbonate), not more tropical points;
- **iron** — need an observable closer to the scavenging *rate* (pure scavenged/authigenic Fe), not
  more dissolved concentration;
- **growth** — need per-PFT production, which no instrument currently provides.

**Open questions for the discussion:** (1) is the map the write-up we pursue, or do we chase a
positive on new data along one of the three levers? (2) which closure's observing-system gap is worth
advocating for? (3) what would count as an independent-validation "discovery" if new data arrive?
