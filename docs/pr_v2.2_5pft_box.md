# PR description draft — v2.2-5pft-box branch

> **⚠ SUPERSEDED FRAMING (2026-06-28).** Point-in-time record; data stands, framing corrected by [STATUS.md](../STATUS.md). The project is a surrogate-to-model identifiability study over **4 observable params**; the growth pair is unobservable by construction (`Biggrow`; `Smallgrow` is non-identifiable from time-mean observables only). **R_PICPOC is recoverable** with a real calcite anchor (the '5/6 ceiling / 6/6 wall / needs the Darwin port + native resolution' framing is refuted). The per-cell predictor is load-bearing for the target trio (ablation 7/10 vs 0/10, PR #158).


**Suggested title (per CONTRIBUTING.md scope-prefix):**
`Track 1 v2.2 closeout: 5-PFT box + v2.4 PINN drift (4/6 calibration-grade)`

**Suggested body (paste into `gh pr create --body` when ready):**

---

## Summary

Extends the Carroll-6 box-model recovery work from the 2-PFT proxy used in v2.0 to the full 5-PFT setup matching Darwin 3 v05, and explores three methodology axes (loss balance, raw-FeT magnitude, PINN physical coupling) for restoring identifiability of the parameters that drifted in v2.0.

**Headline result:** `notebooks/29_v2_4_pinn_drift_eqpac_w3.0.ipynb` recovers **4 of 6 Carroll-6 parameters at calibration-grade (≤ 40% off Carroll's published Green's-functions optima)** — `scav_rat`, `Biggrow`, `diatomgraz`, `R_PICPOC`. This is the project's first 4/6 result.

| Param | Recovered | Carroll publ. | |Δ|/Carroll | Band |
|---|---|---|---|---|
| alpfe | 0.105 | 0.928 | 0.888 | Loose (structurally limited) |
| scav_rat | 3.95e-7 | 6.03e-7 | 0.345 | ✓ Cal-grade |
| Smallgrow | 1.485 | 0.661 | 1.251 | Drifted (PFT-mapping mismatch with Carroll) |
| Biggrow | 0.567 | 0.431 | 0.314 | ✓ Cal-grade |
| diatomgraz | 0.583 | 0.830 | 0.299 | ✓ Cal-grade |
| R_PICPOC | 0.058 | 0.042 | 0.358 | ✓ Cal-grade |

## What's in this PR

**Code (`src/darwindiff/`):**
- `carroll6_5pft.py` — 10-tracer / 5-PFT box module with optional per-PFT K_FE
- `glodap_loader.py` — cherry-picked from PR #36 for the v2.1 Phase 1 hybrid experiment
- (Note: `glodap_loader.py` is duplicated with PR #36 by design — when PR #36 merges, the files are byte-identical)

**Tests (`tests/`):**
- `test_carroll6_5pft.py` — 9 tests covering smoke, autograd flow, per-PFT mapping validation, per-PFT K_Fe behavior
- Full suite: 158 passed, 5 skipped (opt-in real-data tests)

**Notebooks (20 executed):**
- `23_5pft_box_eqpac.ipynb` + 4 multi-seed variants (`_seed1..4.ipynb`) — v2.2 baseline + robustness
- `24_5pft_box_glodap_hybrid_eqpac.ipynb` — Phase 2 + Phase 1 combo (rejected: 1/6)
- `25_5pft_box_perfe_eqpac.ipynb` — v2.2.1 per-PFT K_FE (rejected: 2/6)
- `26_v2_2_2_lossweighted_fet3.0x.ipynb` — v2.2.2 FET-weighted z-score (2/6)
- `27_v2_3_raw_fet_eqpac_w{0.01,0.05,0.1,0.3,0.5,1.0,3.0}.ipynb` — v2.3 raw-FeT weight sweep
- `28_v2_4_pinn_balance_eqpac_w{0.3,1.0}.ipynb` — v2.4 PINN strict balance
- `29_v2_4_pinn_drift_eqpac_w{0.05,3.0}.ipynb` — **v2.4 PINN drift (winner at w=3.0)**
- `29_v2_4_pinn_drift_eqpac_w{0.3,1.0}_rawfet0.05.ipynb` — v2.5 combo (raw-FeT + PINN)

**Build infrastructure (`scripts/`):**
- `build_nb23.py` — Single configurable builder via env vars (`NB23_SEED`, `NB23_FET_WEIGHT`, `NB23_RAW_FET_WEIGHT`, `NB23_PINN_WEIGHT`, `NB23_PINN_TYPE`); routes to nb23/26/27/28/29 by config
- `phase2_p4_p5_check.py` — reproducible P4 (Eq Pac PFT abundance) + P5 (VRAM budget) prereq diagnostics
- `overnight_run.ps1` + `overnight_wave2.ps1` — sequential experiment-queue runners (Windows + single-GPU + no-multi-process-CUDA constraint documented in repo memory)
- `overnight_summary.py` — idempotent aggregator producing `docs/findings/v2.2_overnight_summary.{md,csv}`

**Docs:**
- `CONTRIBUTING.md` — branch convention + commit/PR title format + no Co-Authored-By rule (lands here if not in PR #36 first)
- `docs/findings/v2.2_phase2.md` — full v2.2 / v2.3 / v2.4 narrative with goal-check tables for each notebook
- `docs/findings/v2.2_overnight_summary.{md,csv}` — sorted comparison of all 20 executed notebooks
- `STATUS.md` — updated through finding #21 with the v2.4 winner + alpfe structural ceiling

## Confirmed structural finding: alpfe is stuck

Across all 20 overnight experiments — z-scored loss, FeT pattern upweighting, raw-FeT magnitude terms (7 weights 0.01–3.0), PINN balance (2 weights), PINN drift (4 weights), GLODAP-hybrid carbonate, per-PFT K_FE, raw-FeT+PINN combos — **alpfe sat at 0.80–0.94 off Carroll**. The multi-seed runs (seeds 0–4) show alpfe at 0.841–0.891 off with std ≈ 0.020 — robustly reproducible across seeds.

The single exception was `raw_fet w=0.01` which moved alpfe to 0.392 but broke scav_rat to 2.556 off (iron-pair tradeoff swapped roles).

**Conclusion:** alpfe is structurally non-identifiable under the current observation set. Remaining options requiring data we don't have:
- Carroll's Experiment #18 initial-condition fields (asked Jonathan)
- GEOTRACES IDP2025 real-iron observations
- Longer integration window for true steady-state behavior

## Test plan

- [x] `pytest -q tests/` — 158 passed, 5 skipped
- [x] All 20 notebooks executed end-to-end on RTX 5090 Laptop
- [x] `python scripts/phase2_p4_p5_check.py` — empirical PFT abundance + VRAM budget reproducible
- [x] `python scripts/overnight_summary.py` — idempotent aggregator regenerates summary from disk
- [x] Per-PFT mapping verified via empirical Eq Pacific Chl1–Chl5 abundance check
- [ ] Block CV — deferred (not yet implemented; closeout item 2 for v2.3.x or later)
- [ ] Cross-basin (Mid-Atl, N Pac) — deferred (closeout item 3)
- [ ] Forward Darwin validation of recovered `scav_rat` — cluster-gated (Phase 3, ORCD)

## Known issues / honesty notes

- **alpfe + Smallgrow remain Loose / Drifted** — see structural-ceiling section above
- **Smallgrow's recovery target is contested** — Carroll 2020 SI Table S1 confirms "Small phytoplankton growth rate" is a group-level parameter for {Syn + Pro-LL + Pro-HL}; our v2.2 mapped it to Pro-HL specifically. The "right" Smallgrow value when restricted to Pro-HL is likely not Carroll's 0.661 (which was a group average). Pending clarification from Jonathan.
- **Two bugs encountered + fixed during the overnight runs**, commits `45ae539` (PINN scope error) and `23f8061` (combo filename collision). Both are documented in `STATUS.md` finding #21 and `docs/findings/v2.2_phase2.md`. No silent fabrication.
- **`glodap_loader.py` duplication with PR #36** — intentional cherry-pick before #36 merged. When #36 lands first, the files are byte-identical and will merge cleanly.

## Branch state

- ~25 commits ahead of `main`
- All checks pass locally (pytest 158 passed, 5 skipped)
- Greptile + Codex re-review expected on push (the v2.4 PINN block has the bug-fix from `45ae539` baked in)
