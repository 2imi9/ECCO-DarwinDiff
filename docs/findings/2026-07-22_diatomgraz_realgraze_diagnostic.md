# diatomgraz dilution-grazing-RATE diagnostic — result (2026-07-22)

**Bottom line: inconclusive, not a win. The grazing-RATE framing is the right idea (it breaks the
bSi biomass-tautology), but the 0-D box lacks the grazer structure to test it faithfully, and the
profile came back INVALID (unbracketed). Do NOT claim a `diatomgraz` identifiability improvement, and
do NOT ingest real Schmoker 2013 dilution data yet.** `diatomgraz` stays *not recovered on real data*
as of this diagnostic. (The *structural-vs-practical* question was still OPEN when this was written; it
was closed later the same day — the miss is **input-limited, not structural**. See the superseded note
at the end of this file.)

Artifacts: `docs/findings/graze_anchor/fim_diatomgraz_realgraze.json` (new RATE arm) and
`fim_diatomgraz_realbsi_synth.json` (bSi self-twin baseline). Both are profile-likelihood / Fisher
diagnostics (not recovery counts), so the `verify_run` gate does not apply; each carries its own
internal `valid` / `bracketed` / `converged` flags, cited below.

## The gate (grazing guard) — PASSED, but degenerately

The guard asks whether the large-vs-small size-fraction grazing-mortality **rate** isolates
`diatomgraz` (palatability) from grazer/biomass. Result (`grazing_guard`, `pass: true`):

| quantity | value | reading |
|---|---|---|
| ∂(specific rate)/∂diatomgraz | 0.30 | rate responds to palatability |
| ∂(specific rate)/∂biomass | **0.0** | rate does **not** depend on biomass — biomass cancels |
| rate: biomass-vs-diatomgraz frac | **0.0 %** | clean isolation in the *rate* |
| flux: biomass-vs-diatomgraz frac | **52.35×** | the *absolute flux* is biomass-dominated |

So the RATE isolates `diatomgraz` where the **flux (and therefore bSi) is biomass-tautological** —
that 52× is exactly why bSi-from-biomass is circular and the rate is the correct observable. But the
guard's own note is the catch:

> "Box has no grazer-biomass tracer and no small-PFT grazing term, so the raw specific rate already
> isolates diatomgraz (biomass cancels); the size-fraction contrast is unnecessary here. **NECESSARY**
> (rate breaks the bSi biomass-tautology) **but not SUFFICIENT** for the full Darwin
> grazer_biomass × response × palatability form."

The size-fraction contrast — the actual mechanism the anchor is supposed to exploit — is moot in this
box because the box has no grazer-biomass tracer to contrast against. The guard passes *trivially*,
not because the box reproduces the Darwin grazing structure.

## The profile — INVALID (unbracketed), so no curvature claim

`realgraze` arm (`fim_diatomgraz_realgraze.json`): θ\* = Carroll (diatomgraz 0.830), loss\* = 4.4e-13.
The profile grid `[0.05 … 1.0]` runs **monotonically downhill to the upper edge**:

| diatomgraz | 0.05 | 0.14 | 0.37 | 0.61 | **1.0** |
|---|---|---|---|---|---|
| min_loss | 0.883 | 0.700 | 0.309 | 0.072 | **0.042** |

- `bracketed: false` — argmin is grid point 6 (value = 1.0), the **upper edge**. The grid is too coarse
  to sample θ\*=0.83, so `profile_rel_span = 20.06` is a **lower bound only**.
- `valid: false`, verdict: *"INVALID → profile minimum is ON THE UPPER GRID EDGE; the optimum is not
  bracketed."*

**We cannot read curvature/identifiability off an unbracketed profile.** This does **not** deliver the
"curved `diatomgraz` profile" the handoff hoped for.

## Contradiction with the handoff framing — flagged

The handoff asked: *"is the `diatomgraz` profile CURVED (span > 0.5) vs the FLAT bSi baseline
(span 0.039)?"* The artifacts do **not** support that contrast:

1. The **`realgraze` profile is not cleanly curved — it is INVALID/unbracketed** (above).
2. The **bSi baseline here is itself CURVED, not flat**: `fim_diatomgraz_realbsi_synth.json` has
   `profile_rel_span = 103.4`, `valid: true`, `bracketed: true`, verdict *"CURVED → PRACTICAL
   non-identifiability (param IS constrained)."* This is a **synthetic self-twin** (loss_mode
   `realbsi_synth`, targets computed from the box at Carroll), so it shows the box *can* constrain
   `diatomgraz` given a clean bSi target — self-recovery, **not** real-data recovery.

The remembered "FLAT bSi span 0.039/0.118" is the **real-data** silicate_scope profile (a different
quantity), not this synthetic self-twin. So the intended "curved-rate vs flat-bSi" comparison is
apples-to-oranges as stated, and neither arm here establishes real-data identifiability.

## Verdict & next steps

**Do not over-read.** The RATE idea is sound in principle — the guard confirms the rate isolates
palatability (0 %) where flux/bSi is biomass-dominated (52×) — but two things block a claim:

1. **Structural:** the 0-D box has no grazer-biomass tracer / small-PFT grazing term, so it cannot
   faithfully test the Darwin `grazer_biomass × response × palatability` form (necessary, not sufficient).
2. **Numerical:** the profile is unbracketed (INVALID); no valid curvature was measured.

Two prerequisites before this path is worth real Schmoker 2013 dilution data:
- a **finer profile grid** that brackets θ\*=0.83 (current grid skips it), to get a *valid* span; and
- a **box with grazer structure** (a grazer-biomass tracer, or the full Darwin grazing term) so the
  size-fraction contrast becomes meaningful rather than trivially-satisfied.

This grazing-RATE diagnostic on its own changes no scoreboard number.

> **SUPERSEDED (2026-07-22 later the same day; extended 2026-07-23).** `diatomgraz` is **not** blocked as this doc's SST-only ~4/10
> (= chance) implies: adding an MLD input channel lifts it to 10/10 per-AOI, and at n=50 it reaches
> **35/50** with the biogenic-silica target off (`POSI_W=0`), constrained through chlorophyll + MLD
> (see [`2026-07-22_covariate_channels_result.md`](2026-07-22_covariate_channels_result.md) and
> [`2026-07-23_overnight_recovery_sweep_groupA.md`](2026-07-23_overnight_recovery_sweep_groupA.md)
> LEAD B). The honest framing is *recoverable from a non-circular model-internal observable, not
> recovered from independent real data*; the miss is input-limited, not structural
> ([#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152)).
