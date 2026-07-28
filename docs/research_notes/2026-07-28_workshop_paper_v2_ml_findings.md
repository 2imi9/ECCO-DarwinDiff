# Workshop paper v2 — ML evaluation findings, holding ECCO-Darwin science back

**Date:** 2026-07-28 · **Target:** CCAI @ NeurIPS 2026, Papers track (4 pp) · **Deadline:** 29 Aug

> **Supersedes** `2026-07-28_workshop_paper_skeleton.md`, which proposed submitting the
> observation-design result. **Rejected on strategy:** ECCO-Darwin identifiability is the long-term
> flagship and belongs in a full conference/journal paper. A workshop should not spend it.
>
> **Process note.** The venue asks that its CFP and website materials not be passed through an LLM
> during paper-writing. Lucas owns format and scope by reading the CFP directly. Everything below
> comes from this repository's verified results only. **No venue material was used.**

## The pivot

Submit the **methods lessons from Track 2**, not the Track-1 science. These are findings about *how
geoscience ML emulators are built and evaluated*. They use ECCO-Darwin as a testbed but make no claim
about ocean biogeochemistry, so they cost the flagship nothing.

They also currently have **no home**: the emulator is a clean negative result and will not carry a
paper of its own. This is the natural venue for what it taught us.

## Proposed thesis

> Standard skill metrics certify emulators that are physically invalid, trained through a
> distribution-destroying transform, and measured against a baseline that cannot be lost to. Each
> failure is independently quantified here on the same model, and each is cheap to check.

## The three findings (all repo-verified)

**1. Skill is blind to physics.** The emulator scores **+0.43** (linear, vs persistence) while
producing **4.5% negative dissolved iron** — against a v05 control column at **1.89e-07**, i.e.
numerically zero. The model invents non-physical mass and the metric does not notice.

The contribution is that **physics validation needs no reference data**: positivity, mass ratio, and
carbonate closure are checkable on the prediction alone. That makes it a *third validator*
independent of both the target and the baseline. Provenance: `physics_3d.json`,
`docs/findings/2026-07-19_results_matrix.md` §4.

**2. Linear z-scoring destroys log-normal geophysical fields.** Chlorophyll spans p99/p1 ≈ 2.8 × 10⁶.
Z-scored linearly, the loss is dominated by the largest cells, the model collapses toward the mean,
and the inverse transform pushes low-value cells through zero.

| tracer | log-range retained | non-physical output |
|---|---|---|
| Chl1 | 0.359 → **0.891** | 30.41% → **0.00%** |
| PIC | 0.425 → **0.906** | 19.08% → **0.00%** |
| POC | 0.348 → **0.882** | 9.38% → **0.00%** |
| FeT | 0.882 → 0.940 | 7.27% → **0.00%** |

Predicted-vs-true fit slope **0.23 → 0.81**; the oligotrophic gyres, previously erased, reappear.
**And it buys no skill** — ocean fraction beating persistence 0.813 → 0.803. That is the interesting
part: the fix restores physical validity and dynamic range while leaving the headline metric flat, so
the metric was never measuring what mattered. Verified globally, AICR job 204877.

**3. "Beats persistence" is not a result.** Against a per-cell **seasonal AR(1)** baseline the
emulator is **−0.161 ± 0.015** across four seeds, CI entirely below zero, while
skill-vs-persistence is **+0.055 ± 0.013** with a CI straddling zero.

Persistence is weak by construction on a seasonally dominated field. We confirmed the correct bar is
already standard in this literature — [arXiv:2606.27168](https://arxiv.org/abs/2606.27168)
implements pure persistence, anomaly persistence and **damped anomaly persistence**, explicitly to
remove "trivial skill linked to the seasonal cycle." So we cannot claim the field baselines wrongly.
The contribution is narrower and still useful: a worked case where the weak-baseline claim was made,
retracted, and re-measured, with the delta quantified.

## Supporting material, if space allows

- **Capacity and diffusion are not levers; ensembling is.** Deep ensemble **+0.1415** (daily eqpac) /
  **+0.0515** (monthly 3-D); EDM diffusion **−0.020 / −0.026**; ~4× parameters **+0.007**. Diffusion
  improves calibration (spread/RMSE 0.375 vs 0.23–0.29) and adds no skill, at 256× the forward passes.
- **A calendar bug inflated skill-vs-climatology by +0.37 to +0.78.** `times_days` was built at 900 s
  against v05's true 1200 s, so 94% of month-of-year bins were wrong and the climatology baseline was
  too weak. Retracting the "~9-month horizon" it produced is the cautionary half of the paper.

## What is explicitly held back

- The Carroll-6 **identifiability study** and per-AOI recovery numbers.
- The **observation-design method** (Fisher ranking through the surrogate) — the strongest result and
  the flagship's centrepiece. `2026-07-28_workshop_paper_skeleton.md` retains that plan.
- The **GP15 coverage** result, which belongs with it.

## Honest risks

1. **This is a negative/methods paper** at a venue framed around *tackling* climate change. Frame as
   "what to check before trusting a climate emulator," not "our model failed."
2. **Finding 3 is partly known.** The literature already uses the right baseline. Do not overclaim
   novelty — the value is the quantified before/after on one model, not the discovery of the bar.
3. **Single testbed, single AOI for the deflation** (eqpac). Seed is ruled out; a different AOI could
   differ. State it.
4. **Findings 1 and 2 are the novel core.** If space forces a cut, cut 3 to a paragraph.

## Numbers that must NOT appear

κ(J) = 2930 (that is κ(F); κ(J) ≈ 54) · `scav_rat` 26/50 (flagship is 25/50) · −0.161 ± 0.013 (AR(1)
spread is ± 0.015) · "beats persistence" or "~9-month horizon" except as retracted.
`tests/test_canonical_numbers.py` (13 tests) guards these — **run it against the final text.**
