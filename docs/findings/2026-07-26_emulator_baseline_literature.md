# Is "−0.161 vs seasonal AR(1)" a fair bar? — literature check (2026-07-26)

**Question.** Our emulator shows no significant skill vs persistence (+0.055 ± 0.013) and is
significantly *worse* than a per-cell seasonal AR(1) baseline (−0.161 ± 0.013). Is that an
unusually harsh bar we imposed on ourselves, or the bar the field actually uses?

**Answer: it is the correct bar, and the leading 2026 marine-BGC emulator paper uses it too.**
The negative result is honestly measured. We cannot rescue it by arguing the baseline was unfair.

## What the literature does

[Deep learning model emulators for marine biogeochemistry forecasting from days to decades](https://arxiv.org/abs/2606.27168)
(arXiv 2606.27168, June 2026) — the closest published match to our problem — implements exactly
our baseline class:

- **Pure persistence** — future state equals the last observed value.
- **Anomaly persistence** — deseasonalise, persist the anomaly, add the climatological mean back.
  Stated purpose: *"removes trivial skill linked to the seasonal cycle."*
- **Damped anomaly persistence** — the anomaly is damped by a decorrelation timescale estimated
  from the temporal autocorrelation of the anomaly series.

Damped anomaly persistence **is** a seasonal AR(1) null. Our baseline is the field's baseline.

The same paper names the failure mode our metric is designed to catch: a deep emulator can
converge on *"purely the seasonal climatology"*, which *"could score well in terms of the loss
function, but is meaningless from the point of emulating the process-based simulator dynamics."*
Their remedy is ours — evaluate on deseasonalised anomalies.

## What this settles, and what it costs us

**Settles:** the deflation is real and correctly measured. "Beats persistence" was a weak claim not
because we were sloppy, but because persistence is a weak baseline *by construction* on a
seasonally-dominated field — which this literature states explicitly.

**Costs us:** the fallback framing — *"our negative result is a methodological contribution because
the field's baselines are too weak"* — **does not survive**. At least one 2026 BGC emulator paper
baselines correctly. We cannot claim the field is measuring wrong; we measured the same way and
got a worse number.

## Consequence for Track 2

The honest position is unchanged and now better supported: the emulator is a **clean negative
result** with a one-step useful horizon, and the reusable output is infrastructure (the ocean-BGC
Earth2Studio `PrognosticModel`, physics validators), not skill.

Worth noting: other results in this sweep report emulators that *do* beat persistence and
climatology ([Samudra 2](https://arxiv.org/html/2606.02610),
[correlation-aware loss](https://arxiv.org/pdf/2604.18727), a
[22-year-stable LSTM](https://arxiv.org/abs/2606.27168)). Those are ocean-physics or
single-variable-BGC problems, and none is a like-for-like comparison with a 6-tracer carbon-system
emulator scored on anomalies. **Do not cite them as "others succeeded where we failed" without
first matching baseline, metric space, and variable set** — that comparison is exactly the kind
this repo has been burned by.

## Open, not established

- Whether *any* published ocean-BGC emulator beats a seasonal-aware baseline **on anomalies, for
  carbon-system tracers**. Not answered here; the papers above were not read in full.
- Whether our −0.161 would improve with the Δt-scaled residual operator, which has not been
  rollout-tested.

## Method note

Two targeted web searches, deliberately not a large agent sweep. Findings are from search-result
abstracts and quoted text, **not** full-text reads. Treat as a directional answer with named
sources, not a completed literature review.
