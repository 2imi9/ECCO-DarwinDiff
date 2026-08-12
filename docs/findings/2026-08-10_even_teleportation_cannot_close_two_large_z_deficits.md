# Even teleportation cannot close two frozen-path large-Z deficits

**Finding, 2026-08-10. One deterministic frozen-trajectory upper bound; no
transport run, modified dynamics, optimizer, replication, or B200.**

## Result

The preregistered hypothesis is falsified. Letting the large predator teleport
to the best wet cell at every quarter-day step still does not accumulate the
source mortality integral `12.2` in EqPac or the Southern Ocean:

| AOI | best fixed cell | monthly teleport | stepwise teleport | stepwise / mortality |
|---|---:|---:|---:|---:|
| eqpac | 11.060 | 11.455 | 11.463 | 0.9396 |
| natlsubpolar | 11.160 | 12.161 | 12.210 | 1.0008 |
| southernoceanpac | 11.574 | 11.890 | 11.904 | 0.9757 |

The stepwise margins are `-0.7375 / +0.00970 / -0.2961` for EqPac / North
Atlantic / Southern Ocean. Thus relocation through the **unchanged frozen prey
field** is energetically ruled out in two AOIs. North Atlantic is not a robust
positive: the unrestricted stepwise oracle clears by only `0.08%`, while the
already-unphysical monthly relocation envelope remains `0.0394` below
mortality.

## Temporal structure

EqPac has no instantaneous refuge: in `0/1,464` saved steps does any wet cell's
large-predator gain rate reach `1/30 d^-1`. North Atlantic and Southern Ocean
have at least one instantaneous refuge in `51.43%` and `54.03%` of steps, but
only the North Atlantic's per-step maxima sum above annual mortality.

The envelope is intentionally more permissive than transport. Its maximizing
cell switches `20 / 36 / 26` times and makes jumps as large as `60 / 28 / 88`
Manhattan grid cells in one quarter-day. The monthly envelope selects `5 / 6 /
9` distinct cells and requires maximum month-to-month jumps of `70 / 22 / 89`
grid cells. These are diagnostics of how loose the bound is, not inferred
velocities.

## Integrity

The runner reconstructed all `1,464` large-predator gain steps from the saved
large/small prey pools and assimilation numerators using the literal source
Holling-II constants. The reconstructed upstream gain fields agree with the
source-floor-corrected energy artifact to maximum absolute errors:

| AOI | monthly field | annual field |
|---|---:|---:|
| eqpac | 4.56e-8 | 3.81e-7 |
| natlsubpolar | 6.20e-8 | 3.66e-7 |
| southernoceanpac | 6.07e-8 | 3.69e-7 |

The independent verifier reproduced the complete oracle and decision from
`16,765,728` support-tensor cells, checked the source hash chain, and rejected
tampered gains, prey support, source hashes, and compute authorization.

## What this does not say

This does **not** show that real transport is irrelevant. Actual transport can
change the prey trajectory, import material across the AOI boundary, couple
depths, and alter predator-prey colocation; none of those mechanisms is present
in a frozen-path relocation envelope. The result only says that moving the
predator through the already-visited prey field cannot supply enough annual
energy in EqPac or the Southern Ocean, even when continuity and travel time are
discarded.

The existing transport implementation also remains blocked by issue #192's
horizontal-diffusivity unit error. No direct transport result was produced.
EqPac diatom seasonality and the global `diatomgraz` handle remain independent
Stage-0 failures. The seasonal target therefore remains `stage0-failed-stop`;
this audit neither chooses endpoint versus time mean nor authorizes B200.

## Artifacts

- preregistration:
  `docs/findings/2026-08-10_prereg_large_zooplankton_transport_oracle.md`
- runner and report:
  `scripts/analysis/explicit_zooplankton_transport_oracle_audit.py` and
  `docs/findings/2026-08-10_explicit_zooplankton_transport_oracle_audit.json`
- verifier and receipt:
  `scripts/analysis/verify_explicit_zooplankton_transport_oracle_audit.py` and
  `docs/findings/2026-08-10_explicit_zooplankton_transport_oracle_audit_verification.json`

