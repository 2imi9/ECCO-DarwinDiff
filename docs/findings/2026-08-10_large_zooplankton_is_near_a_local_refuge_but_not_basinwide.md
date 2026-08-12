# Large zooplankton is near a local refuge, not basin-wide support

**Finding, 2026-08-10. One deterministic frozen-trajectory diagnostic; no
modified dynamics, optimizer, replication, or B200.**

## Result

The preregistered local-refuge hypothesis is supported in the narrow sense it
defined. On the independently verified source-floor-corrected cycle-13 path,
the best cell in every AOI reaches the source large-zooplankton mortality
integral after multiplying all five prey by no more than `1.25`:

| AOI | minimum all-prey multiplier | median | p95 | maximum | fraction <=1.25 |
|---|---:|---:|---:|---:|---:|
| eqpac | 1.114 | 1.158 | 1.241 | 1.285 | 96.45% |
| natlsubpolar | 1.104 | 1.321 | 1.602 | 1.898 | 32.31% |
| southernoceanpac | 1.061 | 1.322 | 1.592 | 1.616 | 37.58% |

All `2,856` ocean cells are bracketed below `64x`, and every all-prey root is
below `2x`. The important qualification is spatial: a nearby refuge is almost
basin-wide in EqPac but covers only about one third of the other two AOIs at the
frozen `1.25x` threshold. "Near a local refuge" must not be shortened to
"the predator is nearly viable basin-wide."

## Large prey alone costs more

Scaling only `{diatom, large eukaryote}` while leaving the three small prey
unchanged raises the required support:

| AOI | minimum large-prey-only multiplier | median | p95 | maximum | fraction <=1.25 |
|---|---:|---:|---:|---:|---:|
| eqpac | 1.165 | 1.234 | 1.368 | 1.446 | 58.54% |
| natlsubpolar | 1.152 | 1.518 | 2.131 | 2.736 | 13.50% |
| southernoceanpac | 1.086 | 1.520 | 2.106 | 2.166 | 20.68% |

The minimum large-prey-only root is `1.046 / 1.043 / 1.024` times the minimum
all-prey root. This says only that small-prey support contributes under the
source palatability and assimilation algebra. It does not select a missing prey
route or imply that a source trait should be changed.

## Equivalent subsidy scale

The frozen-path external per-capita subsidy needed to offset the shortfall is:

| AOI | minimum d^-1 | median d^-1 | p95 d^-1 | median fraction of mortality |
|---|---:|---:|---:|---:|
| eqpac | 0.00311 | 0.00417 | 0.00594 | 12.50% |
| natlsubpolar | 0.00284 | 0.00730 | 0.01125 | 21.89% |
| southernoceanpac | 0.00171 | 0.00731 | 0.01117 | 21.94% |

This is a dimensional diagnostic against the source mortality `1/30 d^-1`,
not a proposed restoring or transport term.

## Integrity

The runner replayed the canonical cycle from the corrected cycle-12 endpoint
and saved stepwise weighted prey pools and assimilation numerators. Before any
root was interpreted, those tensors reproduced:

- every monthly large-predator gain field to maximum absolute error
  `6.20e-8`;
- every annual gain field to maximum absolute error `3.81e-7`;
- the prior cycle-13 zooplankton endpoint exactly (`relative L2 = 0`).

The independent verifier recomputed both 48-iteration bisections, bound the
large- and small-prey monthly gain components to the upstream energy artifact,
and checked the censored summaries, SHA-256 chain, and final decision from
**16,780,043 raw tensor cells**. Tamper tests reject changed prey support,
roots, source hashes, and compute authorization.

## What this does not say

The audit held the state trajectory fixed. It did not integrate a system with
more prey or an external subsidy, so it cannot establish stable coexistence or
initialization robustness. It does not identify transport, vertical niche,
DOC, multi-element stoichiometry, mortality, assimilation, or zooplankton
restoring as the missing process. The frozen Darwin-1 source inventory already
contains the same five prey and two predators as this projection, so a missing
PFT is not the explanation for this particular source setup.

Two independent Stage-0 blockers also remain untouched: EqPac diatom
seasonality is below the frozen threshold and the cross-AOI `diatomgraz`
response remains only 2-3%. The seasonal target therefore remains
`stage0-failed-stop`; this finding does not choose endpoint versus time mean and
does not authorize B200.

## Artifacts

- preregistration:
  `docs/findings/2026-08-10_prereg_large_zooplankton_support_threshold_audit.md`
- runner:
  `scripts/analysis/explicit_zooplankton_support_threshold_audit.py`
- report and raw bundle:
  `docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.{json,pt.gz}`
- verifier:
  `scripts/analysis/verify_explicit_zooplankton_support_threshold_audit.py`
- receipt:
  `docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit_verification.json`
