# Parameter accuracy + completion matrix (2026-07-23 overnight)

Per-parameter state after tonight's verified sweep. "Recovery" = per-AOI ≥2-of-3 Cal-grade+ (the honest
metric), verify_run-gated. Confidence is qualitative (no confidence percentages, per house style).
"Status" is how close each parameter is to paper-done, not a probability.

| param | best recovery (verified) | identifiability class | confidence | status to done | what remains |
|---|---|---|---|---|---|
| **alpfe** | **49/50** per-AOI (n=50) | point-identified; surface iron pins it; method-independent (DINN-free + Nelder-Mead) | verified-tight | **DONE** | nothing critical; per-AOI conditioning adds depth |
| **R_PICPOC** | **50/50** per-AOI (n=50) w/ real Daniels anchor | point-identified given a real calcite anchor; anchor-off → 6/50 epoch-matched (4/50 in the older 1500-epoch `n50_anchor_off`) (non-circular) | verified-tight | **DONE** | SO Daniels coverage gap noted; not a blocker |
| **scav_rat** | **41/50** at 4000ep (25/50 at 2000ep) — largely optimization-limited | basin-resolved: SO 48/50 & natl 40/50 recover with more compute; eqpac 6/50 stays info-limited (cond 35, flattest profile) | verified-tight (n=50 ×2 epoch levels + Fisher + curved profile + EKI) | **NEAR-DONE, upgraded** | eqpac needs a real 234Th scavenging-rate observable (future data); the rest is compute |
| **diatomgraz** | 10/10 with MLD via bSi / **35/50 with bSi OFF (Chl+MLD, n=50)** | has a NON-bSi handle (answers M11 circularity); still model-internal (Chl not independent data); structural-vs-practical closer to resolved | verified (n=50) | **OPEN → improving** | independent-real-data test (dilution-experiment grazing) is the remaining gap, not circularity |
| **Smallgrow** | real-unobservable / **NEW: seasonal 9/10 in natl** (+4 vs time-mean) | practical non-ID under time-mean; annual cycle carries growth-timing info in strong-bloom basins | provisional (seasonal prototype) | **OPEN, promising** | native interannual time-resolved fit (monthly_v5 staged) to confirm beyond the prototype |
| **Biggrow** | 0/N everywhere (real, synth-ID only, seasonal too) | not identified | verified-tight (fails-tight) | **EXCLUDED** | genuinely unobservable under current design (Spitz 1998); not a target |

## Trio {alpfe, scav_rat, R_PICPOC}
Joint per-AOI = **25/50 at 2000 epochs, rising to ~41/50 at 4000 epochs** (n=50, set by scav_rat's binding
count of 25/50; see LEAD A). alpfe 49/50 and R_PICPOC 50/50 both clear; scav_rat is the sole binding leg, and at 2000ep
it binds because eqpac/natl stay ratio-degenerate — but at 4000ep natl recovers (19→40/50), leaving eqpac the
sole info-limited basin. Global-scalar control: 0/50 (per-cell architecture load-bearing). **This is the
cleanest quantitative result and the manuscript headline — confirmed at n=50 tonight (the earlier n=10 "9/10"
was seed luck), with the 4000-epoch upgrade showing the gap is largely optimization-limited.**

## What tonight VERIFIED as significant (feed-back)
1. scav_rat 9/10 (n=10) → **25/50 (n=50)**: the lead was seed noise; the flagship scav_rat leg (**25/50**)
   holds, and the trio joint stays **25/50**. (Prevents an over-claim.)
2. **Per-AOI conditioning predicts per-AOI recovery** (SO 49/50 vs eqpac/natl 8–19/50) — a new, coherent,
   fully-verified chain: observation geometry → conditioning → recovery.
3. Per-AOI iron sloppiness firmed to ~5–6 decades (PSD GN-Fisher) — retires "provisional."
4. scav_rat eqpac profile is CURVED → practical (not structural) non-ID.
5. #85 seasonal: AOI-selective, sign tracks seasonality; SO alpfe +5 and natl Smallgrow +4, eqpac
   diatomgraz −6. Not a ceiling-break; a regime-dependent lever.

## Group A DONE (n=10, verified) — two significant leads now in n=50 confirmation
- **No robust 4-of-4** confirmed (pat030/050/010-mld all → diatomgraz 0/10 across the pattern-MLD crossover).
- **LEAD A — CONFIRMED at n=50: scav_rat 25/50 → 41/50 at 4000 epochs.** scav_rat is substantially
  OPTIMIZATION-limited (natl 19→40/50; eqpac stays 6/50). The trio rises 25/50 → ~41/50 with 2× compute, no
  new data. (job 190529, VERIFIED)
- **LEAD B — CONFIRMED at n=50: diatomgraz 35/50 with bSi/POSi OFF** (from Chl+MLD; median within 5% of
  Carroll). A non-bSi handle → answers M11 circularity. Caveat: Chl is Darwin-internal (consistency, not
  independent data). (job 190529, VERIFIED)
- **RESOLVED — NO 4-of-4; the trade-off is STRUCTURAL (job 192298, VERIFIED).** full-loss+MLD at 4000 epochs
  gives diatomgraz **0/10** (both pattern=1 and pattern=0.3 arms), and adding MLD even degrades alpfe (4/10)
  and scav_rat (6/10). So more optimization does NOT rescue diatomgraz when the pattern term is present:
  scav_rat needs the Darwin-pattern term (41/50 without MLD at 4000ep) and diatomgraz needs MLD (35/50 without
  pattern) — a genuine loss-landscape CONFLICT, not an optimization limit. The 3-of-4 frontier is real and
  structural. (torch.compile hang on the MLD 4000ep graph diagnosed + fixed via TORCH_COMPILE_BATCHED=0.)
- ~~EKI estimator-independence~~ **DONE**: same verdict as backprop (not a DINN artifact).
- ~~dg-realgraze-finegrid~~ **DONE**: CURVED, valid, bracketed (argmin θ=0.78 near Carroll 0.83) — closes the
  flagged INVALID grazing-profile artifact; diatomgraz's rate-based profile is a proper curved well.

## What we HOPE is there (and the honest odds)
- A single robust 4-of-4 config (pat030-mld): possible but the endpoints are known-negative, so the middle is
  the whole question — either a headline upgrade or a clean quantified trade-off. Both publishable.
- Seasonal breaking the growth-pair ceiling at native resolution: the prototype hints yes for Smallgrow, no
  for Biggrow — the native fit is the real test.
