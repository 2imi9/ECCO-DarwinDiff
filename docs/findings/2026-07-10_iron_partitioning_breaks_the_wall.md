# Iron partitioning and the scavenging-rate wall — a corrected (mostly-negative) result

*Self-twin probe, 2026-07-10, local CPU. E2-hunt lever 1 (iron). **This finding was
adversarially verified (5 skeptics) and substantially walked back** — the original headline
("partitioning breaks the wall, scav_rat identifiable, ~14× tighter") was largely a construction
artifact. This note records the corrected verdict; the verification transcript is in the
workflow journal for run `wf_380272f4-652`.*

## Corrected verdict

**QUALIFIED / mostly artifact.** A particulate:dissolved partitioning observable does **not** make
the scavenging *rate* identifiable. What is true is narrower and weaker than first claimed: a
*pure scavenged-Fe* partitioning observable removes the **alpfe** confounder *in principle* — but
the rate stays degenerate with `POC·W_SINK`, the self-twin's apparent sharpness is tautological,
and a real (contaminated) `Fe_TP` re-injects the alpfe degeneracy. This is **not** a realizable
positive E2.

## Why the original claim was wrong

The scout computes the observable as `pFe/DFe` where `pFe := scav_rat·DFe·POC/W_SINK`. Algebraically
**DFe cancels exactly**, so the scored observable is

    pFe/DFe  =  scav_rat · POC / W_SINK

— the swept parameter times a near-fixed factor. Three consequences, all numerically confirmed by
[`scripts/iron_partitioning_controls.py`](../../scripts/iron_partitioning_controls.py):

1. **Tautology.** The observable is proportional to `scav_rat` by construction, so fitting it
   recovers `scav_rat` trivially (fit `c·scav` to `c·scav0`). The "sharp well" is a definitional
   log-parabola, not earned identifiability. The reported "~1× band / 14× tighter" is a **grid +
   threshold artifact** — the well half-width is smaller than one grid step, and the `+0.02` band
   on a coarse grid manufactures the "1×."
2. **Relocated degeneracy (decisive).** Because the observable is `scav_rat·POC/W_SINK`, the pair
   `(scav_rat, W_SINK)` is **perfectly degenerate**: scaling both by any `k` leaves the observable
   unchanged (control A: change = `0.00e+00` under `(scav, W_SINK)→(2·scav, 2·W_SINK)`). The
   self-twin only reads a sharp `scav_rat` because `W_SINK` (a fixed constant) and `POC` are held
   at truth. The wall was "concentration constrains `alpfe/scav`, not the rate"; partitioning
   trades that for "`scav·POC/W_SINK`, not the rate" — the degeneracy is **relocated, not removed**.
3. **Not a transported tracer.** `pFe` is reconstructed algebraically from the rolled field, not
   advected/mixed/sunk as a real particulate tracer. So the prescribed transport is decorative
   here (a 0-D box would give the same well), and the "19× (transported DFe) vs ~1× (algebraic
   local) " comparison is not apples-to-apples.

## What legitimately survives

One real observability property: **alpfe cancels from the clean `pFe/DFe`.** So a *pure* scavenged
particulate:dissolved observable is insensitive to the iron *source* while retaining sensitivity to
the *sink* — it removes the alpfe confounder that half of the dissolved-only wall. That is a genuine
(if modest) structural fact. It does **not** identify the rate, because of the relocated
`scav·POC/W_SINK` degeneracy above.

## Real-data contamination makes it worse (control B)

Real `Fe_TP` (and even labile `Fe_TPL`) is not pure scavenged Fe — it includes **biogenic** cellular
Fe (`Fe_CELL`, governed by growth/quota, not scav_rat) and **labile-lithogenic** Fe (dust coatings,
scaling with deposition ∝ `alpfe`). Adding a moderate contamination (50% biogenic + 50% lithogenic
of the scavenged pFe) to the twin numerator and re-profiling: the scav_rat band re-widens
(1× → 2× on the coarse grid) and an **alpfe ridge returns** (1.5× → 2.4×) — the lithogenic term
re-injects the source/sink degeneracy the clean observable appeared to remove. So `Fe_TPL` is
**not** a clean scavenged-Fe proxy (correcting an earlier claim in this note), and the real
observable both dilutes the signal and restores the alpfe dependence.

## Coverage, for completeness

Even setting the above aside, the co-located data are sparse: `Fe_D` dense (23,912) but surface
co-located `Fe_TP`+`Fe_D` only ~94 global / 4 on eqpac; `Fe_TPL`+`Fe_D` 150 global surface. Where
measured, the ratio spans a wide 2.59 dex.

## Honest place in the map

Lever 1 does **not** yield a positive E2. It reinforces the map's theme from a new angle: the
scavenging *rate* is not identifiable from concentration (the wall) **nor** from a realistic
particulate:dissolved observable (tautology + relocated `POC·W_SINK` degeneracy + contamination).
The only thing that would help is a **pure authigenic/scavenged Fe** measurement co-modeled with
independent `POC` and `W_SINK` — an observing-system + model-structure requirement, not a lever we
can pull now.

## Method lesson

This is exactly the failure mode the project has hit before (a sign-flip once survived every unit
test): a numerical identifiability claim that passes because the observable was *constructed from*
the parameter. The adversarial-verification workflow caught it where the tests could not — run it on
any new identifiability/numerics claim before building on it.
