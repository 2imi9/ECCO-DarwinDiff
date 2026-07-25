# Next research direction — R_PICPOC-protection grid (2026-07-22)

> Chosen via the `next-direction-research` workflow (internal frontier + external novelty + feasibility,
> 4 agents, 9 candidates scored). Launched immediately on B200 (jobs 183329 protection grid + 183299
> single-covariate sweep). This note captures the decision + plan; results appended when the jobs land.

Verified against the source: `MLD_CHANNEL`, `WIND_CHANNEL`, `SSS_CHANNEL`, `PCO2_CHANNEL`, `CO2FLUX_CHANNEL`, `AOI_ID_CHANNEL`, `DANIELS_RPICPOC_W`, and per-AOI `DANIELS_AOI_W_<AOI>` all exist as env flags in `scripts/run_v3.0_joint_multi_aoi.py` (lines 318, 326, 336-339, 454, 463). The covariate findings doc (`docs/findings/2026-07-22_covariate_channels_result.md`) confirms the baseline numbers and explicitly flags this experiment as open next-step #2. Decision below.

---

# THE DIRECTION: R_PICPOC-protection grid — lock the manuscript's production operating point

**Sharp question:** Is the MLD-vs-R_PICPOC covariate trade-off a fixable loss-weighting artifact or a real confound? Concretely: can an up-weighted real Daniels calcite anchor lift R_PICPOC from its marginal 5/10 to a defensible >=8/10 **while diatomgraz stays 10/10 and alpfe stays 10/10** — yielding the first jointly-robust {alpfe, R_PICPOC, diatomgraz} config the paper can ship as its recommended operating point? And does up-weighting rescue R_PICPOC even under wind (-> the wind break is DINN overfitting) or not (-> wind carries a genuine calcite confound)?

## (2) Why it beats the alternatives

The overnight covariate win is real but its recommended operating point ("geo1 + MLD only") currently ships R_PICPOC at **5/10 — a coin flip**, which is not a defensible "recovers." That is the single load-bearing soft spot between the current state and a clean 4-observable headline. This experiment converts it, and it is the one candidate that is simultaneously:

- **Directly manuscript-decisive** — defines the exact config the paper recommends, replacing the hand-waved "MLD only" with a numerically-defended operating point. Resolves the doc's own flagged caveat #2 verbatim.
- **Zero-code, launchable now** — pure env-var arms; every flag is verified present. The other high-scorers that would "upgrade the claim" (profile-likelihood on diatomgraz, real scav_rat sink anchor) both need ~half a day of harness code first (no `PIN_`/`FIX_PARAM` in run_v3.0; no `SCAV_ANCHOR_W` loss term). They are not tonight's launch.
- **Decisive either way** — a win gives the robust 4-observable config; a null ("Daniels can't hold R_PICPOC under wind at any weight") is itself a clean scientific statement (wind is a real calcite confound, MLD-only is a proven ceiling).

The pure covariate-matrix candidates (A / single-covariate) score high but are mostly *confirmatory table-filling* — they don't produce a new decisive result, they complete a figure. So I demote that to the cheaper parallel job (Section 5) where it belongs, and spend the primary decisive slot here.

## (3) Concrete, copy-pasteable experiment

**BASE_ENV (all arms):** the verified geo1 anchors-only config from job 178690 that reproduces the covariate doc bit-for-bit — GEOTRACES iron ON, POSi ON, `PINN_W=0`, `DUST_ANCHOR_W=0`, per-AOI DINN ON, `AOIS=eqpac,natlsubpolar,southernoceanpac`, `NB23_N_EPOCHS=2000`, `NB23_SEEDS=0,1,2,3,4,5,6,7,8,9`, `DANIELS_RPICPOC_W=1.0` as the reference weight. Only the vars below change per arm.

| arm | env delta vs BASE_ENV | decision it resolves |
|---|---|---|
| **A0** (ref) | `MLD_CHANNEL=1` | Reproduce the +MLD row (R_PICPOC ~5/10, diatomgraz 10/10, alpfe 10/10). Anchors the deltas. |
| **A1** | `MLD_CHANNEL=1 DANIELS_RPICPOC_W=3.0` | Does a 3x anchor lift R_PICPOC to >=8/10 with diatomgraz/alpfe held? |
| **A2** | `MLD_CHANNEL=1 DANIELS_RPICPOC_W=8.0` | Stronger anchor — watch for over-constraint tax bleeding into alpfe median or pushing R_PICPOC out the *high* side of the band. |
| **A3** | `MLD_CHANNEL=1 WIND_CHANNEL=1 DANIELS_RPICPOC_W=1.0` | Reproduce the 0/10 wind break so A4's delta is attributable. |
| **A4** (key mechanism) | `MLD_CHANNEL=1 WIND_CHANNEL=1 DANIELS_RPICPOC_W=8.0` | **Does the up-weight rescue R_PICPOC under wind?** In-band -> trade-off is a DINN loss-weighting artifact. Still 0/10 -> wind is a real calcite confound. |
| **A5** | `MLD_CHANNEL=1 DANIELS_RPICPOC_W=3.0 DANIELS_AOI_W_EQPAC=3.0` | Targeted per-AOI up-weight on the AOI carrying the calcite anchor — cheaper protection without a global tax? |

Run as one n=10 array job (~1.3h/arm, ~8 GPU-h, under the 32-GPU QOS cap; array backfills). **Grade each arm with `scripts/verify_run.py --expect-seeds 10` (exit 0 required)**, per-AOI >=2-of-3 Cal+ (<=40% off Carroll: alpfe 0.928, R_PICPOC 0.0425, diatomgraz 0.830), and **watch the RPICPOC_STRADDLE flag** (guards against the median drifting out the high side under over-anchoring).

**DECISIVE WIN:** any of A1/A2/A5 gives R_PICPOC >=8/10 AND diatomgraz 10/10 AND alpfe 10/10, no straddle flag -> ship that as the recommended operating point (robust {alpfe, R_PICPOC, diatomgraz}; scav_rat the sole wall).
**DECISIVE MECHANISM:** A4 vs A3 resolves overfitting-vs-confound for the wind break.

## (4) Honest null scenario and what it still teaches

Plausible nulls, all publishable:
- **Over-anchoring tax:** up-weight drags R_PICPOC out the *high* side (straddle flag trips) or pulls alpfe's median out-of-band -> establishes MLD-only@1.0 as a proven ceiling and quantifies the anchor-weight/other-param trade cost. The operating point stays "MLD only, R_PICPOC ~5/10" but now *characterized*, not hand-waved.
- **A4 stays 0/10 at any weight** -> wind carries a genuine confound with the calcite field, a clean scientific statement that justifies excluding wind from the shipped config on mechanistic (not tuning) grounds.
- **R_PICPOC only reaches ~7/10** -> "better but soft"; still a decisive, honest number for the paper.

The only true waste is if all arms sit inside seed noise — unlikely given the 6->0/10 wind signal and the R_PICPOC/anchor coupling are both large. scav_rat stays 0/10 throughout (expected; not this experiment's job).

## (5) Cheaper parallel job if B200 slots allow: single-covariate matrix

Fills the holes in the manuscript covariate x parameter figure. The prior 5-arm run never *isolated* SSS, pCO2atm, or CO2flux — so it cannot say whether the R_PICPOC break is wind-specific or generic to any carbonate/location channel. Zero code, ~8 GPU-h, and the SST-only baseline reproduces bit-for-bit as a built-in sanity check.

Same BASE_ENV, each arm flips exactly one channel vs the SST-only baseline (n=10, seeds 0-9, 2000 epochs, 3 AOIs):

`arm0` = (no channel, SST-only baseline) · `arm1` = `SSS_CHANNEL=1` · `arm2` = `PCO2_CHANNEL=1` · `arm3` = `CO2FLUX_CHANNEL=1`

(MLD and WIND columns already exist from job 178690 — don't re-run them.) Grade with `verify_run.py --expect-seeds 10`; tabulate per-AOI recovery for all 4 params + medians + rho(alpfe,scav). Resolves: is the R_PICPOC collapse generic carbonate-covariate overfitting (all break it -> MLD uniquely safe) or wind-specific, and a clean yes/no on any single channel nudging scav_rat. Most likely confirmatory, but it is exactly the completeness the manuscript covariate table needs and it runs alongside the primary grid for free.

**Launch both as a single backfilling array job (10 arms total, ~16 GPU-h).**

Key files: `scripts/run_v3.0_joint_multi_aoi.py` (env-flag driven config), `scripts/verify_run.py` (grading gate), `docs/findings/2026-07-22_covariate_channels_result.md` (verified baseline + flagged this as next-step #2).
---

## RESULT (2026-07-23) — DECISIVE WIN

Both arrays finished (verify_run exit 0). **The trade-off was a loss-weighting artifact; wind is a real confound.**
- Weight ladder (MLD channel): R_PICPOC per-AOI DAN=1 **5/10** → DAN=3 **9/10** → DAN=8 **10/10** (clean, no straddle), with diatomgraz 10/10 + alpfe 10/10 held. **Shippable operating point: geo1 + MLD + DANIELS_RPICPOC_W=8 → {alpfe, R_PICPOC, diatomgraz} = 10/10 each.**
- Wind mechanism: mld_wind R_PICPOC 0/10 at DAN=1/3/8 (median stuck 0.21) → wind carries a GENUINE calcite confound, not overfitting.
- Single-covariate matrix: SSS/pCO2/CO2flux all break R_PICPOC too → the confound is generic to carbonate/salinity channels; MLD (mixing) is uniquely safe.

Full write-up: docs/findings/2026-07-23_rpicpoc_protection_result.md. STATUS updated with the operating point.
