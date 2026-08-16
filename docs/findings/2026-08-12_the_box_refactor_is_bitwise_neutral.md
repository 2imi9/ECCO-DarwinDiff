# The 2026-08 box-model refactor is bitwise neutral, so HEAD may carry the flagship's numbers

**Date:** 2026-08-12, re-measured 2026-08-16 · **Cost:** local CPU, ~2 minutes, no cluster ·
**Verdict: PASS, and it is a prerequisite the repo had never checked.**

> **Correction (2026-08-16, from Codex review of PR #242).** The original 2026-08-12 measurement
> built its test state in the wrong tracer order: the initializer assumed `state[1] = DFe_2`,
> but the model's layout is `state[1] = P_diatom` and `state[10] = DFe_2`, so the state it
> integrated had DFe_2 ≈ 2.0 (≈2000× plausible) and DIC_2 ≈ 0.01 — a scrambled, implausible
> regime. The verdict was re-measured at the documented plausible layout, extended to both
> precisions and gradients in the banked harness, and **is unchanged: bitwise equivalent**.
> The hash table below is the 2026-08-16 re-measurement; the original scrambled-state hashes
> (`70e7fa7b7bdc0320` etc.) are superseded and reproduce only with the pre-fix harness.
> The originally named post-refactor endpoint `b731f75` was also rebased away and is reachable
> from no branch; the re-measurement names endpoints a fresh clone can check out.

## Why this was run

The AICR production checkout sits at `dd83710` (reachable from `origin/main`). Between it and
the post-refactor tree (`82abbd5`, whose `src/darwindiff/carroll6_5pft_2layer.py` was last
touched by `487d451`)
`src/darwindiff/carroll6_5pft_2layer.py` changed by **259 lines** and
`scripts/run_v3.0_joint_multi_aoi.py` by **88**. The box diff is not purely additive: 42 lines
were removed or rewritten, and among them the core growth computation

```python
growth_diatom = MU_DEFAULT_DIATOM * f_fe * LIGHT * gamma_T * P_diatom
growth_lge    = mu_lge            * f_fe * LIGHT * gamma_T * P_lge
...
```

was restructured (extracted into a new `phytoplankton_process_rates` helper added for the
seasonal-twin work).

**That is the flagship's forward model.** Every published headline (`alpfe` 49/50, `R_PICPOC`
50/50, `scav_rat` 25/50, trio 25/50) was produced *before* the refactor, and the manuscript is
written from HEAD. Nobody had checked that the refactor is numerically neutral, so strictly the
paper's numbers were attributable to code that no longer exists in that form. Issue #226 states
runs are not bitwise reproducible and nothing ever asked them to be, so "it's just a refactor"
was not a safe assumption.

## Method

Two checkouts, identical deterministic inputs, no data files: the current tree (`82abbd5`) and a
`git worktree` at `dd83710`. Carroll truth for all six parameters read by name from the registry,
a 15-tracer state in the model's **documented tracer order** at plausible per-tracer magnitudes,
over **37 cells** (a field, not a scalar, so any broadcast/reduction change would surface),
seeded forcing (T, S, wind), **200 steps at dt = 0.25 d** — the flagship's own window (50 days).

Two things are compared, because forward agreement alone is insufficient: recovery is driven by
`d(loss)/d(params)` **through** the box, so the autograd graph must match too. And training runs
in **float32**, where re-associating identical algebra can change the result even when float64
agrees.

Script: `scripts/analysis/forward_model_equivalence.py` (banked; deterministic, CPU-only). It is
a **gate, not a report**: with `--baseline` it exits 1 on any hash mismatch, verified against a
deliberately doctored baseline (negative control), so a future refactor that moves the model
fails loudly instead of writing a JSON and exiting 0.

```bash
python scripts/analysis/forward_model_equivalence.py --repo <worktree-at-dd83710> --out pre.json
python scripts/analysis/forward_model_equivalence.py --repo . --out post.json --baseline pre.json
```

## Result — identical in every cell of the matrix (re-measured 2026-08-16)

| | dd83710 (pre-refactor) | 82abbd5 (post-refactor) | match |
|---|---|---|---|
| float64 trajectory hash | `997511609141603f` | `997511609141603f` | ✅ bitwise |
| float64 gradient hash | `8e392f0e579cac6a` | `8e392f0e579cac6a` | ✅ bitwise |
| float32 trajectory hash | `0c25270abb43fb06` | `0c25270abb43fb06` | ✅ bitwise |
| float32 gradient hash | `e6c0cee9bc7d1fee` | `e6c0cee9bc7d1fee` | ✅ bitwise |
| float64 final state sum | 664.6807654089816 | 664.6807654089816 | ✅ exact |
| float32 final state sum | 664.6807250976562 | 664.6807250976562 | ✅ exact |
| `phytoplankton_process_rates` present | **False** | **True** | (confirms the two checkouts really differ) |

The last row is the positive control: the API genuinely changed, so the identical hashes are not
an artifact of accidentally importing the same module twice.

## What this licenses, and what it does not

**Licensed.** The flagship's forward model and its parameter gradients survive the refactor
bit-for-bit, in the precision training actually uses. HEAD may therefore be described as the code
that produces the published forward dynamics, and the AICR checkout being two commits behind is
**not** a numerical problem for the box. This removes one standing objection to running a fresh
replication on the current tree.

**Not licensed.** This tests `carroll6_5pft_2layer_step` and its gradient, not the whole pipeline.
The runner (`run_v3.0_joint_multi_aoi.py`, 88 lines changed, 15 removed/rewritten — mostly warning
strings and twin-specific code) and `verify_run.py` (46 lines) are **not** covered here. It also
says nothing about run-to-run reproducibility on GPU (issue #226), which is a separate property:
this is a *code-version* equivalence at fixed inputs, not a determinism claim.

**It does not by itself replicate anything.** The flagship's counts remain, as of today, without
an independent out-of-sample replication in a fresh job. This finding only removes the code-drift
confound that would have made such a replication uninterpretable.

## Follow-ups

1. Extend the same equivalence harness to the runner's loss assembly, so the whole graded path is
   covered rather than the box alone.
2. Pin the AICR checkout to a commit and record it in every run artifact (issue #218).
3. ~~Bank the two scripts into `scripts/analysis/`~~ **Done 2026-08-16**:
   `scripts/analysis/forward_model_equivalence.py` covers both precisions, values and gradients,
   and gates via `--baseline` (exit 1 on mismatch, negative-control verified).
