# Overnight session summary — 2026-07-24

Single coherent index of the 2026-07-23/24 overnight session's verified results. Links to the evidence docs;
does not duplicate them. Every number is `verify_run`-gated (exit 0) and cites its job + source doc.
**Canonical numbers live in [`2026-07-23_parameter_completion_matrix.md`](2026-07-23_parameter_completion_matrix.md).**

**Companion docs (this session):** [`research_refinement.md`](2026-07-24_research_refinement.md) (narrative arc
+ observation-design prescription + paper-readiness), [`reproducibility_methods_appendix.md`](2026-07-24_reproducibility_methods_appendix.md)
(configs/jobs/metrics + inverse-method baseline citations, #117), [`ghgcenter_positioning.md`](2026-07-24_ghgcenter_positioning.md)
(honest MRV motivation).

## 0. TL;DR
- **Two significant, verified improvements to the paper's central results:** (1) scav_rat is largely
  *optimization-limited* — trio 25/50 (2000ep) → **~41/50 (4000ep)**, scav_rat leg 26→41/50 (natl 19→40,
  eqpac 6), no new data; (2) diatomgraz has a **non-circular handle** — 35/50 from Chl+MLD with the bSi
  diagnostic off.
- **The 4-of-4 question is closed: it does not exist, and the trade-off is STRUCTURAL** (full+MLD+4000ep →
  diatomgraz 0/10). scav_rat needs the Darwin-pattern term; diatomgraz needs MLD; they conflict.
- Supporting, all verified: estimator-independence (EKI = backprop), per-AOI Fisher geometry, first-ever
  seasonal fit (#85, AOI-selective), and an honesty-scoped GHG-Center positioning.

## 1. Canonical results (→ [`parameter_completion_matrix.md`](2026-07-23_parameter_completion_matrix.md))
| param | best (n=50, verified) | note |
|---|---|---|
| alpfe | 49/50 | method-independent (DINN-free + Nelder-Mead + EKI) |
| R_PICPOC | 50/50 (anchor-off 6/50 epoch-matched; 4/50 at 1500 ep) | needs a real calcite anchor (Daniels) |
| scav_rat | 26/50 (2000ep) → **41/50 (4000ep)** | optimization-limited; eqpac 6/50 sole info-limited basin |
| diatomgraz | **35/50** (Chl+MLD, bSi OFF) | non-circular handle; structural trade-off with the trio |
| trio {alpfe,scav_rat,R_PICPOC} | 25/50 → ~41/50 | global-scalar control 0/50 (per-cell load-bearing) |
| Smallgrow / Biggrow | seasonal-only / never | growth pair; see §5 |

## 2. Recovery vs conditioning (→ [`overnight_recovery_sweep_groupA.md`](2026-07-23_overnight_recovery_sweep_groupA.md) §3/LEAD A; [`overnight_geometry_and_seasonal.md`](2026-07-23_overnight_geometry_and_seasonal.md) §1,5)
- Per-AOI iron 2×2 condition: **sopac 2.22 < eqpac 34.7 < natl 50.8** (PSD GN-Fisher, job 189403).
  Conditioning separates the well-conditioned SO from the two degenerate basins but does **not** rank eqpac
  vs natl. The **profile span** (eqpac 3.69 > natl 1.30 > sopac 1.12) tracks recovery order.
- Per-AOI iron sloppiness **5.19 / 5.99 / 4.99 decades** — now quotable (retires the earlier provisional 3.96).
- The aggregate "cond 3022→2.2 / ~1400×" from job 188077 is **Southern-Ocean-driven**; eqpac/natl stay
  ratio-degenerate even with subsurface iron.

## 3. scav_rat resolution (→ [`subiron_scav_rat_result.md`](2026-07-23_subiron_scav_rat_result.md) [S1 banner]; geometry §5)
- The n=10 "9/10" was **seed luck**: n=50 subW=1 = 26/50; subW=0 (surface-only) = 4/10; subW=1 replicate =
  6/10. Subsurface up-weighting *degrades* recovery (subW 1→3→8 → 9→5→1).
- 4000 epochs → **41/50** (job 190529): the weak leg is largely an optimization limit; eqpac is the sole
  residual information-limited basin.

## 4. Estimator independence — EKI (job 189754 → geometry §6)
Derivative-free EKI reaches the **same verdict as backprop**: alpfe 0.999 (Cal-grade), R_PICPOC 0.0364
(Cal-grade), scav_rat 2.09e-7 (Loose, biased low). Closes the "DINN+autograd artifact" attack. Posterior
**mean only** (EKI ensemble collapses; calibrated CI needs EKS — future).

## 5. First seasonal prototype #85 (job 189324 → geometry §4)
AOI-selective, sign tracks seasonality strength — **not a ceiling-break**: SO alpfe **+5**, natl Smallgrow
**+4**, natl alpfe **−4**, eqpac diatomgraz **−6**, eqpac Biggrow **−2**. Smallgrow openable in strong-bloom
basins (promising, prototype-level, unconfirmed); Biggrow never recovers.

## 6. No 4-of-4 — structural trade-off (job 192298 → groupA §"4-of-4 retry")
full-loss+MLD at 4000ep → diatomgraz **0/10** (both pattern=1 and 0.3 arms), and MLD degrades alpfe/scav_rat.
So {scav_rat (needs pattern), diatomgraz (needs MLD)} is a genuine loss-landscape conflict, not an
optimization limit. (Required `TORCH_COMPILE_BATCHED=0` — MLD 4000ep hangs torch.compile.)

## 7. Emulator / closure theory (→ [`bgc_operator_lineage_synthesis.md`](2026-07-24_bgc_operator_lineage_synthesis.md) §4-5; biblio → [`learned_closure_lineage.md`](../research_notes/2026-07-23_learned_closure_lineage.md))
1-month forward emulator has ~zero headroom over seasonal AR(1) (structural, a category error not a defect).
Value ranking: inversion-surrogate ≫ multi-month/scenario (unproven) ≫ 1-step (retired). Strongest framing =
learned closure on prescribed transport, with a concrete non-1-step test (rollout stability + invariants +
counterfactual forcing). Architecture shortlist: SFNO spherical geometry, Pangu depth-as-3D-axis, NeuralGCM
differentiable-core, ACE2 architectural conservation. **Whitespace correction: BG4Sea (2026) narrows it —
retire "first global BGC operator."**

## 8. GHG-Center positioning (→ [`ghgcenter_positioning.md`](2026-07-24_ghgcenter_positioning.md))
ECCO-Darwin CO₂ flux is a NASA-hosted, CC-BY carbon-MRV-relevant product whose worth is its calibration.
**Honest motivation:** the global sink is ~2% biology (Carroll 2022), so identifiability matters for
*regional/seasonal biological-pump credibility* (where the Carroll-6 were tuned), **not** the headline sink.
Explicitly flagged overclaims to avoid: quantifying a flux-error budget without an OSSE; attributing verified
OAE credits to the hosted product.

## 9. Documentation dispositions applied this session
- **Corrected:** N1 (backwards conditioning inequality in groupA §3); N3/N5/N6 (stale trio + provisional
  sloppiness); S1 (subiron "live lead" resolution banner); S4/S6/S7 (weak-leg pointer, Fields-Medals hedge,
  seasonal one-sidedness).
- **Consolidated:** closure-theory-questions **archived** (superseded by synthesis §5); learned-closure-lineage
  kept as the bibliography appendix; parameter_completion_matrix is the canonical numbers doc; this file is the
  index.
- **Flagged, not applied:** the AGU abstract's iron-mechanism + diatomgraz lines (now outdated by 4000ep) —
  banner added to the draft; awaiting your call (see §10).

## 10. OPEN — HOLD for your greenlight (touch manuscript CORE claims; not auto-applied)
- **H1.** Retire the "box tuning-exhausted / needs new observations, not more GPU" framing (STATUS banner +
  results_matrix verdict). 4000ep (compute, no new data) was the night's largest single gain — epochs was not
  an exhausted lever. Proposed reframe: recoverability gap = large *closeable optimization* component (natl
  scav_rat) + residual *information* component (eqpac).
- **H2.** Reclassify scav_rat "not point-identified (CV≈43%)" → "practical non-ID (curved profile), largely
  optimization-limited" (backed by the verified curved Hessian).
- **H3.** Soften "growth pair unobservable by construction" *for Smallgrow only* (seasonal recovers natl
  9/10) — keep Biggrow unobservable.
- **H4.** AGU abstract iron-mechanism + diatomgraz rewrites (§ banner in the draft).
- **H5.** Add the EKI estimator-independence result to STATUS's independent-validation section.
- **H6.** Qualify the iron-pair "95% (38/40)" headline against the honest per-AOI 26/50 + straddle finding.
- **Also pending your call (from earlier):** AGU abstract submission (deadline Aug 5); issue-tracker updates
  (#152, #187, #85, #188 advanced); the results_matrix.md refresh (S3, still on the 2026-07-05 verdict).
