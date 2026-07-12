# Track-2 emulator PoC — scored (cluster GPU, next-state vs persistence)

**Source:** Explorer array (job 8302950, T4; 500 epochs), `scripts/emulator_poc.py`. eqpac AOI
(21×51), tracers DIC/ALK/PIC/POC/FeT/Chl1, surface, 156–158 shared months (prog 158 / forc 156),
temporal hold-out (n_val_pairs=40). **Local-only — not committed to GitHub.** (Ran on T4 after the `cu128` PyTorch
build hit `no kernel image` on V100 — CC 7.0 unsupported; the tiny grid is launch-bound so GPU tier
is immaterial to the result.)

Headline metric = **skill over persistence** = 1 − MSE(model)/MSE(persistence) on held-out months,
ocean cells only, standardized units. >0 means the learned operator beats copying x(t). Persistence
is a **strong** baseline here (persistence skill vs climatology = +0.242 — it already captures
most of the month-to-month structure), so beating it is the real bar.

## Verdict: MAKE — FNO beats persistence across all prognostic seeds

- prognostic (no forcing): skill +0.1765 ± 0.0134 (n=3, 3 skill>0, range [+0.160,+0.193])
- forcing-augmented (SST/wind/MLD): skill +0.1920 ± 0.0296 (n=2, 2 skill>0, range [+0.162,+0.222])
- environmental forcing helps: **yes**

*Aggregation robustness:* the headline skill above is the persistence-error-weighted aggregate
(1 − Σ MSE_model / Σ MSE_persistence over z-scored channels). The **unweighted mean of the per-tracer
skills is +0.098** (still >0), and PIC/POC/FeT/Chl1 are each individually positive at 3/3 seeds — so
the "beats persistence" claim survives both aggregation choices and does not hinge on the weighting.

## Per-run

| config | seed | skill vs persistence | beats? | anomaly-R² vs clim | rollout stable | verdict |
|---|---|---|---|---|---|---|
| forc | 0 | +0.1623 | yes | +0.366 | yes | MAKE |
| forc | 1 | +0.2216 | yes | +0.410 | yes | MAKE |
| prog | 0 | +0.1605 | yes | +0.363 | yes | MAKE |
| prog | 1 | +0.1757 | yes | +0.375 | yes | MAKE |
| prog | 2 | +0.1933 | yes | +0.388 | yes | MAKE |

## Per-tracer skill (mean across prognostic seeds)

| tracer | skill vs persistence |
|---|---|
| DIC | -0.2451 ± 0.0444 (n=3, 0 skill>0, range [-0.295,-0.187]) |
| ALK | -0.0514 ± 0.0410 (n=3, 1 skill>0, range [-0.086,+0.006]) |
| PIC | +0.1855 ± 0.0039 (n=3, 3 skill>0, range [+0.180,+0.190]) |
| POC | +0.1734 ± 0.0139 (n=3, 3 skill>0, range [+0.156,+0.190]) |
| FeT | +0.1763 ± 0.0242 (n=3, 3 skill>0, range [+0.145,+0.204]) |
| Chl1 | +0.3498 ± 0.0125 (n=3, 3 skill>0, range [+0.332,+0.362]) |

## Reading this honestly

**The pass is real but bounded — one supporting guard, then two load-bearing caveats:**

**Guard — it beats climatology too, not just persistence** (anomaly-R² = +0.36–0.41, 3/3 seeds).
   This is the critical guard: persistence itself beats climatology by +0.24 here, so a model could
   "beat persistence" merely by predicting the seasonal mean. Beating *climatology* as well means the
   FNO is learning genuine month-to-month change, **not** a trivial seasonal-cycle artifact. This is
   what makes the +0.18 a real result.

**Caveat 1 — the skill is concentrated in the fast-varying tracers; the slow carbonate fields are
NOT beaten.** Chl1 +0.35, PIC +0.19, FeT +0.18, POC +0.17 (all 3/3 seeds), but **DIC −0.25 and
ALK −0.05** — the FNO is *worse than persistence* for the large-magnitude, slowly-varying
carbonate tracers (they barely change month-to-month, so persistence is near-unbeatable and the
FNO's small perturbations only hurt). So the emulator learns Darwin's fast-varying tracer fields (v05),
not the slow DIC/ALK — a residual/tendency formulation (predict Δ, not the full next state) is the
obvious next design change for those.

**Caveat 2 — 1-step skill is solid; the multi-step rollout is marginal.** All runs are rollout-*stable* (no
   blow-up; mass drift 0.17–0.41), but the 6-step autoregressive rollout degrades toward persistence
   (prog_s0 loses to persistence by the final step; other seeds win narrowly). A usable multi-decadal
   emulator needs the rollout to hold — this PoC clears the 1-step bar, not yet the rollout bar.

**Bottom line: the make-or-break PoC PASSES** — an FNO *can* learn v05 next-state and beat both
persistence and climatology, robustly across seeds. The emulator direction is **viable and worth the
B200 scale-up**, with a clear improvement path (residual formulation for the carbonate tracers;
rollout-aware training; more AOIs/data). This de-risks the emulator before any B200 spend.

*Why the skill is real (not an artifact):* the model predicts the **full next state**, not a
persistence residual — so it can't cheat by copying `x(t)` and adding a small correction; a positive
held-out skill therefore reflects genuinely learned month-to-month change. (The 4-audit adversarial
review confirmed all leakage axes clear; see `docs/findings/` commit history.)
