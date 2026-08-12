# Explicit zooplankton rescues diatoms but fails the seasonal target gate

> **PRE-CORRECTION RESULT - SUPERSEDED FOR QUOTATION.** This run omitted
> Darwin-1's literal `phygrazmin=1.2e-8 C` response. The corrected, independently
> verified chain preserves every gate classification and supersedes this model
> specification; use
> `2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md`.

**As of 2026-08-09: independently verified Stage-0 stopping result. No
optimizer was run, no B200 was used, and no recovery claim is authorized.**

## Question

Does replacing the box's biomass-independent linear diatom grazing term with
the source-defined Carroll/Darwin-1 two-zooplankton closure produce a stable,
initialization-robust, seasonally forced self-twin target while retaining a
measurable `diatomgraz` handle?

The answer for the frozen projection is **no**. The change does rescue diatom
persistence in all three AOIs, but one predator is competitively excluded and
the `diatomgraz` response remains below the preregistered sensitivity gate.

## Frozen test

The preregistration is
[`2026-08-09_prereg_seasonal_twin_explicit_zooplankton_gate.md`](2026-08-09_prereg_seasonal_twin_explicit_zooplankton_gate.md).
The implementation mirrors Carroll's shared-prey Holling-II closure with two
surface zooplankton states:

- `Gmax = 0.625 d-1`, `K_graze = 10.2 mmol C m-3`, and predator mortality
  `1/30 d-1`;
- five prey-specific palatabilities and source assimilation efficiencies;
- `diatomgraz` multiplies only the two diatom-palatability entries;
- unassimilated prey and predator mortality enter POC because the projection
  has no DOC state;
- astronomical monthly light, 12 cycles, chemical-only restoring at
  `tau=365.25 d`, and no phytoplankton or zooplankton restoring;
- three predator initializations (`0.01`, `0.10`, `0.50` times initial total
  prey per predator) and frozen `diatomgraz` perturbations (`0.9x`, `1.1x`).

The raw bundle contains **4,681,005 checked tensor cells**. The independent
verifier reconstructs every gate and the source prey-to-predator carbon
partition; maximum partition residual is **1.041e-17**.

## Result

| AOI | diatom cycle-12 / initial | diatom monthly CV | small-Z / initial | large-Z / initial | cycle 11->12 max rel-L2 | max IC-flank rel-L2 | `log[D(1.1g)/D(0.9g)]` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Eq Pacific | **1.026** | 0.034 | 26.26 | **3.62e-7** | **0.706** | **0.844** | -0.0301 |
| N Atlantic subpolar | **0.869** | 0.556 | 15.21 | **2.27e-7** | **0.664** | **0.799** | -0.0206 |
| Southern Ocean Pacific | **0.866** | 0.550 | 15.04 | **1.25e-5** | **0.494** | **0.741** | -0.0203 |

The frozen thresholds were `<=0.01` for cycle stability, `<=0.05` for
initial-condition robustness, and `abs(log response) >= log(1.05)=0.04879`
in at least two AOIs. None passes. The response sign is nevertheless
consistent: increasing `diatomgraz` from `0.9x` to `1.1x` lowers diatom
inventory by **2.97% / 2.04% / 2.01%** in Eq Pacific / North Atlantic /
Southern Ocean.

All numerical, chemical-closure, and DFe-structure gates pass in all three
AOIs:

- zero raw-negative biology events and zero clamp correction;
- exact zero phytoplankton and zooplankton restoring;
- chemical closure shares and turnover remain within the frozen limits;
- the preregistered DFe2 contrast minima and cycle-to-cycle contrast gates
  pass.

The failed initialization-robustness metric is localized to `Z_large`.
Across both flanks, the other six plankton states differ from the central
cycle-12 mean only at float-scale in Eq Pacific; the large predator remains a
decaying near-zero mode. The preregistration required both source predators to
retain at least 1%, so that mode cannot be silently dropped after seeing the
result.

## Interpretation

The positive mechanistic result is durable: the earlier diatom extinction was
not an inevitable consequence of astronomical forcing. It was caused by the
box's constant diatom-specific mortality floor. Once realized grazing depends
on predator biomass and prey competition, diatoms persist without direct
biomass restoring in all three basins.

That does **not** make this a valid target. The 0-D surface projection supplies
no spatial transport, vertical grazer niche, or DOC pathway, and one of the
two source predators is excluded everywhere. A relative stability metric is
large because that state continues to decay from tiny to tinier values, while
the retained small predator becomes 52-64% of plankton carbon. Calling the
remaining six-state attractor a successful two-grazer Darwin target would be a
post-hoc model reduction.

The sensitivity result is independently disqualifying. Even after diatoms are
rescued, a 22.2% span between the two `diatomgraz` perturbations produces only
a 2.0-3.0% inventory response. The construction therefore does not establish
an adequate recovery handle.

## Limits

- This is one deterministic Stage-0 construction matrix, not out-of-sample
  replication and not a parameter-recovery experiment.
- The result rejects the declared 17-state projection, not explicit
  zooplankton in the full transported Darwin model.
- Routing all non-assimilated carbon to POC is a declared consequence of the
  missing DOC state.
- The Eq-Pacific monthly-CV failure (`0.034 < 0.05`) is additional but not
  needed for the stopping decision.
- No Southern Ocean *loss-twin recovery count* is inferred here; this target
  construction uses verified ocean cells and is separate from job 320993's
  excluded Southern Ocean grading arm.

## Decision

`stage0-failed-stop`: no optimizer, no B200, no n=50 submission. The next
scientific fork must be preregistered as a different model-reduction question;
the failed large-grazer state and weak parameter handle may not simply be
removed from this result.

## Artifacts

- runner: `scripts/analysis/seasonal_twin_explicit_zooplankton_gate.py`
- source projection: `src/darwindiff/explicit_zooplankton.py`
- report: `docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json`
- raw bundle: `docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz`
- verifier: `scripts/analysis/verify_seasonal_twin_explicit_zooplankton_gate.py`
- verification receipt: `docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_verification.json`
