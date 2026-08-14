# `R_PICPOC`'s anchor-conditionality replicates out-of-sample, and the straddle says why

**Date:** 2026-08-14 · **Jobs:** 358528 (3 arms × n=100) + 358529 (grading, chained `afterany`)
· **Gate:** `verify_run` **exit 0** on both trained arms, 100/100 seeds each

Out-of-sample replication of the 2026-08-13 result that the flagship's `R_PICPOC` 50/50 is specific
to the Daniels compilation. **Fresh seeds 50–149**, disjoint from the original's 0–49, at **n=100**
per arm rather than n=50 — per ADR-0003, which rules n=50 indefensible for this class of claim.

## The effect replicates, and is slightly larger

Per-AOI ≥2-of-3, Daniels (control) vs Marsh:

| parameter | original n=50 | Fisher | **replication n=100** | **Fisher** |
|---|---|---|---|---|
| **`R_PICPOC`** | 50/50 → 30/50 | 1.8e-07 | **98/100 → 50/100** | **2.7e-16** |
| `scav_rat` | 26/50 → 18/50 | 0.158 | 49/100 → 36/100 | 0.086 |
| `alpfe` | 49/50 → 48/50 | 1.000 | 99/100 → 97/100 | 0.621 |
| `diatomgraz` | 2/50 → 4/50 | 0.678 | 2/100 → 3/100 | 1.000 |

The drop is **40 pp originally, 48 pp on replication**. This satisfies clause 1 of the three-check
rule — a genuinely fresh submission, disjoint seeds, its own null in-job — which the 2026-08-13
finding explicitly lacked.

**`scav_rat` still does not clear significance** (P = 0.086 at n=100, having been P = 0.158 at
n=50). The direction is consistent across both jobs and matches the single-AOI cost result, but it
must continue to be reported as **not significant**, not as a trend that "almost" made it.

**`alpfe` is untouched in both jobs**, as expected — it does not read the calcite anchor.

## The straddle is the mechanism, and only n=100 exposed it

`verify_run` flags a *straddle* when a seed's cell-weighted verdict disagrees with its per-AOI
verdict, i.e. when the per-region legs land on opposite sides of the target:

| arm | `R_PICPOC` seeds straddling |
|---|---|
| Daniels | **1/100** |
| Marsh | **42/100** |

Fisher: **P = 5.1e-14**.

Under Daniels the three basins agree about the rain ratio almost perfectly. Under Marsh — which
adds 7 North Atlantic cells and 12 Southern Ocean cells where Daniels has none — **the basins
disagree in 42% of seeds**. The cell-weighted count still reads 91/100 while the per-AOI count is
50/100, which is exactly the overstatement the per-AOI rule exists to prevent.

This is the regional mis-specification signature, measured directly: a single global `R_PICPOC`
can satisfy Daniels' coverage, and cannot simultaneously satisfy the expanded coverage. It is
independent support for `ind247`/`ded86` from a controlled A/B rather than a cached comparison.

## What changes, and what does not

**Changes.** The manuscript must report `R_PICPOC` 50/50 as **Daniels-conditional**, now on two
independent submissions rather than one. The claim "recovered globally" needs the qualifier that it
holds against the anchor used, and that the successor compilation halves it.

**Does not change.** No published number is retracted. Every reported `R_PICPOC` result used
Daniels, and the Daniels arm here reproduces it (98/100 at n=100, against 50/50 at n=50). The
Daniels result is real; its *generality* is what is now bounded.

**Still open.** Whether Marsh is the better anchor is not settled by this. Where coverage is
identical (eqpac, 34 cells in both) Marsh agreed with Carroll far better on 2026-08-13 (1.04× vs
1.25×), which argues for it; where it adds coverage the basins disagree. Distinguishing "Marsh is
better data" from "the rain ratio is genuinely regional" needs a per-basin analysis this run did
not do.

## Provenance

Both arms `verify_run` exit 0 at 100/100 seeds, one shared untrained null in the same submission
(admissible here because the arms differ only in a loss-side lever — see the 2026-08-12 amendment;
a null at `lr = 0` never trains, so the anchor cannot influence it). Code `636b5a4`, recorded in
every artifact.
