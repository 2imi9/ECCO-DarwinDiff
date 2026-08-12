# The constant-forcing self-twin validates the harness, then returns a double null

**Date:** 2026-08-09 | **Status:** measured, one submission, not replicated, not settled |
**Jobs:** 320993 (15 arms x 50 artifacts) and 320994 (grader) |
**Pre-registration:** `2026-08-08_prereg_loss_comparison_self_twin.md`

## Result in one sentence

In verified equatorial-Pacific and North-Atlantic cells, the two matched controls recover
`scav_rat` under all three poolers at the pre-registered `<=0.20` band, while both losses return
0/50 under all three poolers at every tested band against the quasi-steady long target. This
validates the self-twin harness and shows that the constant-forcing long target cannot decide the
endpoint-versus-time-mean question. It does **not** choose a loss for seasonally forced Darwin.

## 1. Submission and grading boundary

Job 320993 completed all 75 array tasks. Every one of the 15 arms contains exactly 50 JSON
artifacts; grader 320994 completed with exit 0. The experiment is nevertheless only **one
submission**. There is no disjoint-seed replication and no settled claim.

The grader reports arithmetic / geometric / median poolers in that order. `scav_rat` is never
reported from the arithmetic pooler alone.

### Complete dimensional matrix

The presentation's compact tables are backed by a tidy fact table rather than hand-selected
cells:

- `docs/findings/2026-08-09_loss_twin_dimensional_matrix.json` retains arm metadata, parameter
  roles, coverage, verifier state, medians, nulls, and the reporting rules;
- `docs/findings/2026-08-09_loss_twin_dimensional_matrix.csv` contains one row per arm x parameter
  x pooler x tolerance-band cell;
- `scripts/analysis/build_loss_twin_dimensional_matrix.py` regenerates both from the 750 source
  artifacts and runs `verify_run` on every arm;
- `scripts/analysis/verify_loss_twin_dimensional_matrix.py` independently verifies the complete
  Cartesian relation and writes
  `docs/findings/2026-08-09_loss_twin_dimensional_matrix_verification.json`, including SHA-256
  receipts for both matrix files.

The relation has **1,080 cells**: 15 arms x 6 parameters x 3 poolers x 4 bands. Exactly 360
numeric cells are retained, 360 parameter-excluded cells remain present with blank values and a
reason, and 360 Southern Ocean cells remain verifier-gated with blank values. Thus the matrix is
complete without converting a gated or excluded artifact into a quoted result.

## 2. The matched controls pass in the two verified basins

These cells compare identical target and loss objects. Their purpose is to falsify the harness
before the decisive cells are read.

| basin | matched cell | `scav_rat` at `<=0.20` | untrained null | geometric median / truth |
|---|---|---:|---:|---:|
| eqpac | `target=end`, endpoint loss | **50/50/50** | 0/0/0 | 1.028x |
| eqpac | `target=mean`, time-mean loss | **50/50/50** | 0/0/0 | 1.024x |
| natlsubpolar | `target=end`, endpoint loss | **50/50/50** | 0/0/0 | 1.105x |
| natlsubpolar | `target=mean`, time-mean loss | **50/50/50** | 0/0/0 | 1.066x |

At the tighter `<=0.10` band the counts are 47/47/47, 50/50/50, 22/22/24, and 47/47/48,
respectively. The `<=0.20` statement is therefore not an arithmetic-only or 0.40-band artifact.

## 3. The quasi-steady long target gives the same null under both losses

The decisive cells use the Carroll-truth box state after 4,000 steps under constant forcing. At
every tested band (`0.10`, `0.20`, `0.30`, and `0.40`), `scav_rat` is 0/50 under arithmetic,
geometric, and median pooling:

| basin | endpoint loss | time-mean loss | geometric median / truth, endpoint | geometric median / truth, mean |
|---|---:|---:|---:|---:|
| eqpac | **0/0/0** | **0/0/0** | 2.454x | 2.454x |
| natlsubpolar | **0/0/0** | **0/0/0** | 3.299x | 4.977x |

The matched controls rule out a broken twin harness in these basins. The long-target result is a
double null: neither comparison recovers `scav_rat` from this target.

The target diagnostic measured before fitting explains why this null is plausible. From the
200-step endpoint to the constant-forcing long state, DFe2 relative spatial contrast falls from
0.0845 to 0.0001 in eqpac and from 0.1323 to 0.0026 in natlsubpolar, reductions of about 845x and
51x. DFe2 is the field carrying the `scav_rat` signal. A nearly uniform z-scored pattern target
contains almost no level information for that parameter.

## 4. What the result does and does not say

The result supports only this bounded statement:

> A constant-forcing quasi-steady self-twin does not distinguish endpoint from time-mean loss for
> `scav_rat`; both fail after their matched controls pass.

It does **not** establish any of the following:

- that endpoint loss is correct for Darwin;
- that time-mean loss is correct for Darwin;
- that the two losses are equivalent under seasonal forcing;
- that Darwin's climatological target is information-free for `scav_rat`;
- that the result is replicated;
- any accuracy statement from `alpfe` touching a parameter bound.

The box is forced constantly and approaches a fixed point. Darwin is seasonally forced and its
climatology averages a recurring trajectory rather than a fixed point. Issue #239's seasonally
forced self-twin is therefore the next experiment. Another constant-steady factorial is not the
next step.

## 5. Southern Ocean coverage diagnosis: resolved cause, still excluded result

The Southern Ocean arms and null all return `verify_run=2`: `DANIELS_RPICPOC_W=1` and `POSI_W=1`
were declared, but both terms had zero active cells. Following the 2026-07-30 precedent, no fitted
Southern Ocean count or median is reported here.

A read-only audit of job 320993 distinguishes geographic absence from source staging failure:

| check | observation |
|---|---:|
| Southern Ocean task logs audited | 25/25 |
| log says no Daniels coverage in AOI | 25/25 |
| Daniels load failure | **0/25** |
| GEOTRACES bSi active-cell count is zero | 25/25 |
| task completion marker `rc=0` | 25/25 |
| sibling eqpac coverage in the same submission | 34 Daniels cells / 123 samples; 7 bSi cells |
| sibling natl coverage in the same submission | 26 Daniels cells / 116 samples; 4 bSi cells |

The staged files also exist on the submission host:

| source | size |
|---|---:|
| `data/daniels/Daniels_etal_2018_PANGAEA_888182.tab` | 473,302 bytes |
| `GEOTRACES_IDP2025_Seawater.nc` | 64,566,461 bytes |

This audit is reproducible rather than prose-only:
`scripts/analysis/audit_loss_twin_so_coverage.py` re-reads all 75 immutable Slurm logs and the
two staged sources over SSH. Its exit-0 receipt is
`docs/findings/2026-08-09_loss_twin_so_coverage_verification.json`; it includes every log's
SHA-256 digest and a digest of the complete ordered log set.

Thus the current job's zeros are **expected geographic coverage zeros, not a missing-source
staging failure**. That resolves the cause but does not waive the gate. The historical JSONs do
not carry source-load provenance, and their declared-on terms still contributed nothing. They
remain excluded under the standing rule that the artifact must honestly describe the live loss.

The runner and verifier are hardened for future work:

- active Daniels and GEOTRACES-bSi sources now fail before training if they cannot load;
- artifacts record source status and per-AOI coverage status;
- `verify_run` distinguishes certified expected-zero coverage from unknown staging state;
- expected-zero coverage remains a discrepancy until the inactive weight is declared zero.

No constant-steady rerun is scheduled to repair the Southern Ocean declaration. The next science
submission is the seasonally forced twin in #239, whose arm declarations must match coverage from
the start.

## 6. Research-map decision

The recovery finding is deliberately **not added to SETTLED**. It is one unreplicated submission
and it does not answer the Darwin loss-choice question, so it enters the map only as a semantic-ID
claim with `pending-replication` status. The narrower job-provenance question is settled: job
320993's Southern Ocean zero-active-cell state is expected geographic absence rather than source
staging failure. That settled cause does not waive `verify_run=2` or make any Southern Ocean
result reportable. The loss-choice question remains open until a seasonally forced twin supplies
evidence that can actually address it.
