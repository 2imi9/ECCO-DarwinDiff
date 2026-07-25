# Overnight emulator-improvement loop — what helps, what doesn't (2026-07-14)

> **⚠️ SUPERSEDED — the '~9-month horizon' is RETRACTED (2026-07-19).** It was a `delta_t`
> calendar artifact: pre-2026-07-19 cubes carry `times_days` at 0.75× truth, so 94% of
> month-of-year bins were wrong and skill-vs-climatology was inflated. Against a correctly
> binned seasonal climatology the useful horizon is **one step**. Retained as the record of
> what was believed at the time.

An autonomous loop systematically tested candidate improvements to the global-monthly emulator
(each: implement → small test → scale). All numbers are **local** (self-consistency vs the v05
model output, not real observations). Headline baseline: global-monthly (surface) skill vs persistence
**+0.5204** (seed 0), bankable at **+0.5165 ± 0.0023** over n=5 seeds — **all skill numbers in this document are LINEAR space**
(no log-space control was run for this configuration; where controls exist on *other* runs, the log-space number is lower —
the depth-resolved monthly 3-D run went +0.432 linear → +0.365 log, and daily eqpac went +0.300 linear → +0.036 log.
Note: that 3-D +0.432 is a **different experiment** from the surface k=8 +0.432 in the table below — do not conflate them.)

## The systematic result: +0.52 (skill vs persistence, LINEAR space) is where *single-model, single-seed* input/rollout tweaks plateau — NOT a hard ceiling

> **CORRECTION (2026-07-19):** the "hard ceiling" / "near-optimal" / "intrinsic predictability" / "exhausted"
> framing in this section is REFUTED. The plateau is EPISTEMIC (seed variance), not aleatoric: an 8-seed deep
> ensemble lifts skill on both configs where the control was run — monthly 3-D +0.432 → +0.484, and daily eqpac
> +0.304 → +0.445. No ensemble control was run on *this* global-monthly SURFACE config, so the correct reading is
> that the ceiling claim here is **unsupported**, not that a specific gain is proven for it. Read every "ceiling" /
> "near-optimal" / "intrinsic" / "exhausted" statement below as **"single-model, single-seed plateau"**.
>
> Three things in this section SURVIVE and are not corrected: (i) **capacity saturation** — +0.007 for ~4× the
> parameters is a real result; capacity is genuinely not the lever, ENSEMBLING is; (ii) the rejections of
> **forcing** and **seasonal time-encoding** as single-model levers; (iii) the +0.52 number itself.
>
> Two further caveats: the +0.52 family is measured in **linear** space — global Chl is log-normal (p99/p1 ≈ 2.8e6×),
> so linear MSE-based skill is dominated by a few bloom cells; and the **persistence** baseline alone flatters
> long-horizon results (at 12 months persistence reads +0.441 while climatology reads −0.265), so co-report climatology.
>
> ⚠ Do not confuse the **+0.432** cited above (monthly 3-D flagship, the config the log-space and ensemble controls
> were run against) with the **+0.432** in the k=8 row of the table below (global-monthly SURFACE, longer rollout-k).
> Identical number, different experiments.

Every lever that changes the *inputs* or the *rollout post-processing* was rejected. The
surface-monthly emulator has stopped responding to *input* and *rollout post-processing* levers for a **single trained model**. That is not the same as near-optimal for its formulation: on the two configs where a deep ensemble was actually run (daily eqpac, and the monthly 3-D emulator), ensembling over seeds — same formulation, same inputs — still adds skill, so this plateau is epistemic, not intrinsic. No ensemble control has yet been run on *this* surface-monthly config.

| Lever | Result (skill values are vs persistence, **linear space**; rollout rows report neg-fraction / mass-drift) | Verdict |
|---|---|---|
| **Capacity** (modes/width, up to 4×) | +0.527 best (+0.007 over baseline) | Saturated — not the bottleneck |
| **Forcing** (SST/wind/MLD inputs) | global +0.5108 (−0.010) | **Rejected** — hurts |
| **Seasonal time-encoding** (sin/cos day-of-year) | eqpac +0.212 vs +0.285 (−0.073) | **Rejected** — hurts |
| **Rollout mass-conserve** (clamp + rescale to mean) | eqpac neg 0.103 / drift 0.482 — worse than positivity | **Rejected** |
| **Rollout positivity** (clamp ≥0 between steps) | eqpac neg 0.182→0.083, drift 0.482→0.401 | **Kept** — *reduces* negatives (does not eliminate them; log-space training is what gives 0%) |
| Longer rollout-k (k=8) | global +0.432 (−0.088), linear-space skill vs persistence, single-step/short-horizon | **Superseded (2026-07-19)** — k=4 wins *only* on this short-horizon, persistence-referenced metric. Rollout-aware training at k=8 is the #1 *useful-horizon* lever (~2 mo → ~9 mo; k=1 diverges, mass ratio 99.6 at 9 mo, while k=8 stays stable at +0.25). Long-horizon skill must co-report **climatology**, not persistence alone: at 12 mo persistence reads +0.441 while climatology reads −0.265. |

**Interpretation.** Two independent "add-information" ideas (forcing, seasonal phase) both *hurt*.
Under the residual formulation with a strong persistence baseline, the model already extracts the
predictive signal from the current state; extra input channels add parameters that overfit. Capacity
is saturated. So the +0.52 level (linear space) is **not a tuning artifact** — that part stands.

> **CORRECTION (2026-07-19).** The rest of this sentence — that +0.52 is "close to the intrinsic
> single-step predictability" and that "pushing past it requires changing the problem, not tweaking
> it" — is **refuted**. Averaging independently-seeded models is neither a change of problem nor a
> tweak of inputs, and it lifts skill on both configurations where the control was run (daily eqpac
> +0.304 → +0.445; monthly 3-D +0.432 → +0.484, both linear space). Those are **different
> experiments** from this global-monthly surface run, and both ensembled values sit *below* +0.52,
> so they do not tell us where this configuration lands after ensembling — that control has not been
> run here. What is established is that a single-model plateau is **not** evidence of an intrinsic
> predictability limit. Capacity saturation (+0.007 for ~4× parameters) is unaffected and still
> holds: capacity is not the lever, ensembling is.

## Rollout physics: positivity is the fix; mass-conservation is not

Plain positivity (project concentrations ≥0 between steps) reduces negatives and, on the eqpac
subset, also reduces mass drift. The mass-conserving variant (rescale to the pre-clamp mean) does
not help — it slightly worsens both. Note the positivity effect on *drift* is regime-dependent
(improves eqpac, worsened the global case): negatives are always fixed, but multi-step mean drift
is a separate, harder problem best addressed by a log-space parameterization or a genuinely
conservative operator — not by rescaling. Kept as `--rollout-positivity` (committed 9130df5);
`--rollout-mass-conserve` retained as an option but not recommended.

## The real frontier

Since single-model *input* tweaks are exhausted — but note the rollout-k row above was rejected on **single-step** skill, and rollout-aware training (k=8) later proved the **#1 horizon lever** (~2 mo → ~9 mo) — the substantive upgrades are (revised 2026-07-19):

0. **Deep ensembling (8 seeds)** — the cheapest real gain. On the separate depth-resolved monthly 3-D run: +0.432 → +0.484 (linear-space skill vs persistence; this is *not* the "global +0.432" k=8 surface entry in the table above). This **refutes the "intrinsic ceiling" reading in §1**: the plateau was epistemic, not aleatoric. The EDM diffusion variant adds zero skill and hurts on 3-D (+0.421 → +0.395). Note **capacity saturation still holds** (+0.007 for ~4× parameters is a real, surviving result) — capacity is not the lever; ensembling is.
0b. **Rollout-aware training (k=8)** — useful horizon ~2 mo → ~9 mo (k=1 diverges, mass ratio 99.6 at 9 mo; k=8 stable at +0.25). Long-horizon skill must **co-report climatology**: at 12 months persistence reads +0.441 ("strong") while climatology reads −0.265 (dead), so persistence alone hides rollout drift.
0c. **Log-space training** — global Chl is log-normal (measured p99/p1 ≈ 2.8e6×), and log-space also buys physical validity (exp(·) > 0 ⇒ 0% negatives, vs the 4.5% negative iron this emulator invents while still scoring +0.43). The monthly flagship **survives** the log control (+0.432 linear → +0.365 log, −15%); the daily eqpac case **collapses** (+0.3000 → +0.0361) and global daily log is a **NULL** (+0.005).

All skill numbers in this document — including the +0.5204 / +0.5165 headline above — are **linear-space** skill vs persistence unless marked "log".

Honest overall claim: a ~9-month, **ensembled, rollout-trained, log-space, physically-valid (0% negatives)** seasonal BGC surrogate of ECCO-Darwin v05, validated for **self-consistency vs v05 only** — never against real observations.
1. **Depth / 3-D** — the emulator is surface-only; carbon is a 3-D story. A 10-level (60-channel)
   global-monthly 3-D emulator is training (the one genuinely different problem this loop pursued).
2. **External validation** vs SOCAT/GLODAP — the project-level lever (issue #163).

Neither is a tweak; both change what the emulator *is* or what it *means*.
