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
2. **Entangled with W_SINK and POC (not a clean relocated degeneracy).** The observable is
   `scav_rat·POC/W_SINK`, so `scav_rat` is confounded with the sinking rate `W_SINK` and the POC
   field. An earlier version of this note claimed `(scav_rat, W_SINK)` are *perfectly* degenerate (a
   "control A" that reported `0.00e+00` change under `(scav, W_SINK)→(2·scav, 2·W_SINK)`) — **that was
   wrong**: that control was an algebraic `(2x)/(2y)` identity on the **frozen** truth POC field, not a
   forward run. A **real forward experiment** (`scripts/iron_partitioning_forward_control.py` →
   `docs/findings/iron_partitioning_forward_control.json`) that actually varies `W_SINK` inside the
   rollout shows the pair is **not** degenerate: `W_SINK` governs POC (`dPOC = mort − W_SINK·POC`, so
   `W_SINK×2` drops POC to **0.32×**), so the equal-scaling `(2·scav, 2·W_SINK)` changes the observable
   by **69%** (not 0), and even the naive `(k², k)` invariant is not clean (`scav×4, W×2 → 0.60×`).
   `W_SINK` is therefore *partially self-identifying* through POC. The rate is still **not cleanly
   identifiable** — it is entangled with `W_SINK`/POC (and, below, with `alpfe`) — but the mechanism is
   **entanglement, not a perfect relocated degeneracy**.
3. **Not a transported tracer.** `pFe` is reconstructed algebraically from the rolled field, not
   advected/mixed/sunk as a real particulate tracer. So the prescribed transport is decorative
   here (a 0-D box would give the same well), and the "19× (transported DFe) vs ~1× (algebraic
   local) " comparison is not apples-to-apples.

## What legitimately survives

One narrow observability property: **the explicit dissolved-Fe source magnitude divides out of the
clean `pFe/DFe`** (the `alpfe·dust` term is not a direct prefactor of the observable). But "insensitive
to the iron *source*" is **too strong**: in the iron-limited box `alpfe` re-enters the *pure* observable
indirectly through POC (more iron → more growth → more POC), which the same forward control measures at
**+0.11 dex per 3× alpfe ≈ 25% of the sink sensitivity** (`scav×3 → +0.45 dex`). So partitioning removes
the *direct* source prefactor but not the source's indirect POC channel, and it does **not** identify the
rate (entangled with `W_SINK`/POC as above).

## Real-data contamination makes it worse (control B)

Real `Fe_TP` (and even labile `Fe_TPL`) is not pure scavenged Fe — it includes **biogenic** cellular
Fe (`Fe_CELL`, governed by growth/quota, not scav_rat) and **labile-lithogenic** Fe (dust coatings,
scaling with deposition ∝ `alpfe`). Adding a moderate contamination (50% biogenic + 50% lithogenic
of the scavenged pFe) to the twin numerator and re-profiling: the scav_rat band re-widens and an
**alpfe ridge returns** — the lithogenic term re-injects the source/sink dependence the clean
observable appeared to remove. (The specific magnitudes — band ~1×→2×, alpfe ridge ~1.5×→2.4× on the
coarse grid — are **illustrative only**: they are functions of the *assumed* 50/50 biogenic/lithogenic
split, not a measured `Fe_TP` composition, and the `alpfe` re-injection is definitional given that
contamination model, so it **corroborates rather than demonstrates**.) So `Fe_TPL` is **not** a clean
scavenged-Fe proxy (correcting an earlier claim in this note), and the real observable both dilutes the
signal and restores the alpfe dependence.

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
