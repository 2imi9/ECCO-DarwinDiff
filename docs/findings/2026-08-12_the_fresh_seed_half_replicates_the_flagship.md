# The flagship replicates on 50 seeds that never appear in its lineage, and the repo was under-reporting it

**Date:** 2026-08-12 · **Cost: ZERO compute** — everything below is a re-grade of artifacts already
on disk · **Gate:** `pooler_audit.py` against the architecture-matched untrained null `wxe/w16_null`

## Why this was run

A proposed B200 replication of the flagship was screened before submission and the screen refuted
its premise: the flagship trio **already** has an out-of-sample replication, `wxe/w16e2k`
(job 258713, n=100, separate submission and separate code build), recorded at
`2026-08-04_pooler_audit_the_flagship_trio_halves.md` §5 and in STATUS.md.

But the screen surfaced something the repo had not exploited. **`w16e2k` ran seeds 0–99, while the
flagship, `logscale/ctrl_n50` and `collapse/collapse_n50` all ran seeds 0–49.** So seeds **50–99
have never appeared anywhere in the flagship lineage**. The repo reports only the pooled n=100
figure, which mixes fresh seeds with seed-index-overlapping ones and therefore *understates* the
cleanliness of the evidence.

This note grades the two halves separately. No new run was submitted.

## Method

`w16e2k`'s 100 seed JSONs were split by the `_seed(\d+)_` field into `seeds 0–49` and
`seeds 50–99` (verified disjoint, 50 files each, no overlap), and each half was graded with
`scripts/analysis/pooler_audit.py` against the same untrained baseline `wxe/w16_null` (n=50), which
was produced in the **same submission** as the trained arm. All three collapses are reported, per
the standing rule that `scav_rat` is never quoted under the arithmetic pooler alone.

## Result

Joint trio (`alpfe` + `scav_rat` + `R_PICPOC`), per-AOI ≥2-of-3, band 0.40:

| arm | seeds | n | arithmetic | geometric | median |
|---|---|---|---|---|---|
| flagship bitwise twin `collapse_n50` | 0–49 | 50 | **25/50** | **12/50** | 23/50 |
| `w16e2k`, seed-index-overlapping half | 0–49 | 50 | 21/50 | 7/50 | 20/50 |
| **`w16e2k`, FRESH half** | **50–99** | **50** | **24/50** | **10/50** | 17/50 |
| untrained null `w16_null` | — | 50 | **0/50** | **0/50** | **0/50** |

Per parameter on the fresh half, against that null:

| parameter | arithmetic | geometric | median |
|---|---|---|---|
| `alpfe` | 49/50 vs 10, P = 2.3e-33 | 49/50 vs 10 | 49/50 vs 10 |
| `R_PICPOC` | 49/50 vs 0, P = 6.3e-59 | 50/50 vs 0 | 50/50 vs 0 |
| `scav_rat` | 26/50 vs 0, P = 5e-19 | 11/50 vs 0, P = 1.5e-04 | 18/50 vs 0 |
| `diatomgraz` | 2/50 vs **32** | 1/50 vs 32 | 4/50 vs 32 |
| `Smallgrow` | 6/50 vs 6 | 1/50 vs 6 | 1/50 vs 6 |
| `Biggrow` | 4/50 vs 0, P = 0.35 | 4/50 vs 0 | 1/50 vs 0 |

## What this licenses

**The headline replicates on genuinely fresh seeds.** Arithmetic 24/50 against the published
25/50, geometric 10/50 against 12/50, with the null at 0/50 under every collapse. The manuscript
can now say "replicated out-of-sample on 50 seeds disjoint from the original" rather than citing a
pooled n=100 number, and that is a materially stronger sentence for the same evidence.

**`alpfe` and `R_PICPOC` are the stable legs**, at 49–50/50 in all three arms under all three
poolers. **`scav_rat` is the binding leg everywhere**, and the arithmetic-vs-geometric gap persists
in fresh seeds exactly as documented (paired McNemar on the fresh half: 15 arithmetic-only vs 0
geometric-only, P = 6.1e-05). The natl per-cell log-sd on the fresh half is **0.935**, flagged by
the audit as approaching the σ = 0.820 threshold at which the collapse alone can clear the ±40%
band — the same North Atlantic mechanism already on record.

## Honest caveats

1. **The median pooler is the weakest match**: 17/50 fresh vs 23/50 on the flagship twin. Arithmetic
   and geometric replicate tightly; the median does not, and that should be stated rather than
   averaged away.
2. **The two halves come from one job.** They are disjoint in *seeds*, which is what the
   replication question needs, but they share a submission, a code build and a node. This is
   stronger than a within-array split of one arm and weaker than a genuinely separate submission —
   and `w16e2k` itself already is that separate submission relative to the flagship, so the
   combination is what carries the claim.
3. **`alpfe`'s 49/50 remains bound-assisted** (see `2026-08-05_alpfe_rails_to_whatever_bound_it_is_given.md`;
   Lauderdale confirmed 2026-08-12 that the 1.0 ceiling is not physical). Replication does not
   repair that: it reproduces the same railing.
4. **`diatomgraz` scores 1–4/50 against an untrained 32/50** — far below its own null, consistent
   with the standing instruction to grade it per-leg at ≤0.10 rather than on the aggregate at 0.40.

## Consequence for the write-up

Replace the pooled n=100 replication sentence with the disjoint-seed split above. Cite the fresh
half as the out-of-sample evidence and the null as 0/50 under all three collapses.
