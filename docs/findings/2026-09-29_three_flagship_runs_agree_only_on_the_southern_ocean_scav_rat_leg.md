# Three runs of the flagship configuration: grades move off the Southern Ocean `scav_rat` leg

**Date:** 2026-09-29 · **Status:** measured · **New run:** local, laptop RTX 5090, 682 s ·
**Artifacts:** [`2026-09-29_flagship_percell_local/`](https://github.com/2imi9/ECCO-DarwinDiff/tree/main/docs/findings/2026-09-29_flagship_percell_local)
(the ten seed records, the per-cell fields and the run log)

## The three runs

All three use the flagship configuration and seeds 0–9. They differ in hardware, in code build and
in when they ran; none of them requested deterministic GPU kernels.

| run | where | code build | collapses recorded |
|---|---|---|---|
| **published** `n50e2k_percell_trio` | Explorer (2026-07-05) | not recorded | arithmetic only |
| **`collapse_n50`** | cluster, hardware not recorded (2026-07-29) | not recorded | all three |
| **local** (this note) | laptop RTX 5090 (2026-09-29) | `b7f2759`, runner unmodified | all three |

`collapse_n50` is the instrumented twin of the flagship *reproduction* `ctrl_n50`: bitwise identical
to `ctrl_n50` on all 50 seeds (`2026-08-04_pooler_audit_the_flagship_trio_halves.md`), **not** to
the published flagship. The local run was made to save the per-cell parameter fields
(`SAVE_PER_CELL_SEEDS=10`) for `docs/figures/fig_param_fields.png`; every recorded configuration key
agrees with the other two runs, and the keys only the newer runner records sit at the values those
runs used.

## Result

Per-region grades at the ±40% band, compared pairwise with `scripts/analysis/grade_flip_under_drift.py`
(arithmetic collapse, the only one all three runs carry) and `scripts/analysis/compare_run_bitwise.py`:

| pair | grade flips (of 180 seed-parameter-region units) | of them in the Southern Ocean | Southern Ocean `scav_rat` |
|---|---|---|---|
| published vs local | 8 | 3 | 0 |
| published vs `collapse_n50` | 10 | 3 | 0 |
| `collapse_n50` vs local | 6 | 0 | 0 |

No pair is bitwise identical (max relative difference 0.77–0.87). `verify_run.py` passes the local
run (exit 0; per-AOI `alpfe` 10/10, `scav_rat` 7/10, `R_PICPOC` 10/10; it has no untrained control).

**The trio** (per-AOI ≥2-of-3, arithmetic) on seeds 0–9 is **8** published, **9** `collapse_n50`,
**7** local. The local run gives the same trio verdict as the published flagship on 9 of 10 seeds
and as `collapse_n50` on 8 of 10. `alpfe` and `R_PICPOC` keep their ≥2-of-3 verdict on every seed in
every run; every trio difference is `scav_rat`. Between `collapse_n50` and local, where all three
collapses exist, 20 of 540 per-region verdicts flip (arithmetic 6, geometric 7, median 7) and the
trio moves 9 → 7, 5 → 3 and 5 → 3.

What moves:

- **Seed 5's equatorial-Pacific fit.** Its eqpac loss is 6.121 published, 6.696 `collapse_n50`, 6.114
  local, and four eqpac units change together (`alpfe`, `scav_rat`, `diatomgraz`, `Biggrow`). The
  local run reproduces the published flagship's seed-5 optimum; `collapse_n50` is the outlier.
- **Seeds 2 and 3 also changed their fit**, not just a grade: eqpac loss 6.747 / 5.665 / 6.545
  (seed 2) and 6.035 / 6.219 / 5.307 (seed 3), published / `collapse_n50` / local. Between
  `collapse_n50` and local their North Atlantic `scav_rat` legs cross the band under the geometric
  (seed 2) and median (seed 3) collapses.
- **Seeds 4 and 9 are band-edge cases**: their North Atlantic `scav_rat` legs sit within about 0.01
  of the band edge and land on different sides of it in different runs (seed 4: 0.603× Carroll in
  `collapse_n50`, 0.598× locally, against an edge at 0.600).
- **Southern Ocean legs of other parameters do flip** between the published flagship and either
  rerun: `Biggrow` (seed 2), `R_PICPOC` (seed 3) and `Smallgrow` (seed 7).

What does not: **the Southern Ocean `scav_rat` leg flips in no pair.** Across all 30 run-seed
records it lies between 0.84× and 1.02× Carroll, far inside the band. That is a statement about the
verdict, not the value: Southern Ocean values do move between runs (for example `R_PICPOC` seed 3,
1.83× → 1.54× between `collapse_n50` and local), and because these legs sit well inside the band a
count cannot see that movement, which is the blindness `CLAUDE.md` already describes.

## What this means

1. **It extends a settled row rather than contradicting it.** The 2026-08-02 check found 0 flips in
   60 units, for one pair of same-configuration runs with a stripped, eqpac-only loss, and scoped
   itself as "not the flagship". On the flagship, across three runs, grades do flip: 6–10 of 180
   units per pair under the arithmetic collapse.
2. **The movement is where the paper already calls the flagship fragile**: the multi-modal
   equatorial Pacific fit (seeds 7 and 9 sit at an eqpac loss near 22 in all three runs), and the
   North Atlantic `scav_rat` knife edge (`2026-08-03_the_pass_band_is_load_bearing.md`).
3. **The one leg the paper's `scav_rat` claim rests on, the Southern Ocean, keeps its verdict in all
   three runs.**

## Limits

Ten seeds, three runs. The pairs differ in hardware, in code build (the published and
`collapse_n50` records carry no code provenance, and 33 commits touched the runner or `src/`
between `c4323ae`, the day `collapse_n50` ran, and `b7f2759`) and in ordinary run-to-run
nondeterminism, which the runner never switches off; this comparison cannot separate the three. It shows that reruns of the flagship are
not grade-stable off the Southern Ocean `scav_rat` leg, not why.
