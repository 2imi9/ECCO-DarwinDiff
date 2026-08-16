# The Southern Ocean `scav_rat` result replicates on fresh seeds

**Date:** 2026-08-12 · **Jobs:** 352450 (training, 10 tasks) + 352451 (grading, chained `afterany`)
· **Gate:** `verify_run.py` **exit 0**, 50/50 seeds · **Verdict: REPLICATES**

Pre-registered in [2026-08-12_prereg_so_only_replication.md](2026-08-12_prereg_so_only_replication.md),
committed **before** submission. Decision rule fixed in advance: REPLICATES if `scav_rat`'s
geometric count `k >= 43` and clears its null at P < 0.01; FAILS if `k <= 42`.

## Why it mattered

`so_only` is the project's **one established `scav_rat` claim** and the entire basis for
"regionally identifiable in the Southern Ocean". It had **no independent replication**: its
apparent replicate `so_only2` is bitwise identical on all 50 seeds, differing only in
`danielsW`/`posiW`, which are inert in a single-AOI Southern Ocean run. Meanwhile the 3-AOI
flagship has two replications. The weakest-evidenced headline was the one carrying the regional
claim.

Unlike the flagship trio — where detecting a difference needs a 44% relative collapse — the
reference here sits at 49/50, so the P < 0.05 boundary is a **14%** drop. **This run was powered
to fail.**

## Result

Fresh seeds **50–99**, disjoint from the original's 0–49. Trained arm and its architecture-matched
untrained null in the **same submission**.

| parameter | original `so_only2` (seeds 0–49) | **replication `so_rep` (seeds 50–99)** | untrained null |
|---|---|---|---|
| `scav_rat` **geometric** | 49/50 | **50/50** | 0/50 |
| `scav_rat` arithmetic | 30/50 | **30/50** | 0/50 |
| `scav_rat` median | 28/50 | 24/50 | 0/50 |
| `alpfe` (all poolers) | 50/50 | 50/50 | 11/50 |
| `diatomgraz` | 50/50 | 50/50 | 34–37/50 |
| `R_PICPOC` | 0/50 | 0/50 | 0/50 |

- **Primary:** geometric `k = 50`, against the pre-registered threshold of 43. Exact two-sided
  Fisher against the 49/50 reference: **P = 1.0000** — indistinguishable. Against the untrained
  null: **P = 8.1e-62**.
- The arithmetic count is **exactly identical** (30/50 both).
- Paired McNemar arithmetic vs geometric: 20 geometric-only vs **0** arithmetic-only,
  P = 1.9e-06 — the same direction and magnitude as the original (20 vs 1). The Southern Ocean
  remains the basin where the geometric collapse is *stronger*, the opposite of the North Atlantic.

## The pre-registered secondary reads, all of which pass

**1. Continuous accuracy, not just the count.** The count is demonstrably blind to accuracy (a
5.14× SO accuracy loss once showed as 9 seeds), so the pre-registration required the distribution:

| | median `scav_rat` / Carroll | IQR | range |
|---|---|---|---|
| original | 1.3919 | [1.3066, 1.4625] | [1.1738, 1.6078] |
| replication | 1.3619 | [1.3150, 1.4470] | [1.2407, 1.6517] |

Mann–Whitney two-sided: **U = 1266, P = 0.9149**. No detectable accuracy shift. The count
replicates *and* the underlying accuracy distribution replicates — the stronger of the two
statements.

**2. `alpfe` stayed 50/50** (median 0.99935 → 0.99911), so the run is not broken. It is still
railing to 99.9% of its 1.0 bound, which Lauderdale confirmed on 2026-08-12 is **not** a physical
ceiling — replication reproduces the railing rather than repairing it.

**3. `R_PICPOC` stayed 0/50** (median 0.788 → 0.745 against Carroll 0.04245). This is the positive
control for anchor gating: the basin has zero Daniels cells and, being single-AOI, nothing to
inherit from, so a non-zero value would have meant the gating was wrong. It collapsed exactly as
predicted.

**4. `diatomgraz` is not quoted** — its untrained null is 34–37/50, so a single-basin count carries
almost no discriminating power. Recorded, not interpreted.

## What this licenses

**"`scav_rat` is regionally identifiable in the Southern Ocean" now rests on two independent
submissions with disjoint seeds**, not one. The manuscript can state it as replicated. Given that
`scav_rat` is the sole binding leg of the flagship trio, this is the single most load-bearing
replication in the project.

## What it does not license

1. **It does not rescue `scav_rat` globally.** This is one basin. The trio is 0/50 here because
   `R_PICPOC` is 0/50 by construction — that is the design, not a failure.
2. **The value is biased high.** The recovered median is **1.36–1.39× Carroll**, inside the ±40%
   band but not centred. Replication reproduces the bias; it does not remove it.
3. **The median pooler is the weak leg** (28 → 24/50), the one place the two runs differ
   materially. Stated rather than averaged away.
4. **Same code build, different job.** The cluster checkout was fast-forwarded to `ca72abf` before
   submission and the forward model was shown bitwise identical across the intervening refactor
   ([2026-08-12_the_box_refactor_is_bitwise_neutral.md](2026-08-12_the_box_refactor_is_bitwise_neutral.md)),
   so code drift is excluded — but this is a fresh *submission*, not a fresh *implementation*.

## Process note

A 32-second smoke test (job 352406) caught two config errors before the real submission:
`AOI_W_SOUTHERNOCEANPAC` set to 1.0 when the original artifacts carry `w-southernoceanpac2.0`
(with a single AOI this scales the whole loss, so it scales gradients and is **not** inert), and a
directory mix-up in which `so_only/` is job 237913 — the run that *failed* `verify_run` with
exit 2 — rather than the reportable 238079. Either would have silently produced a false
non-replication.
