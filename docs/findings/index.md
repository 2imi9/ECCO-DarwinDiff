# Findings

Per-version technical writeups behind the headline results. [Project Status](../status.md) is the canonical live summary; these pages are the underlying experimental record.

> **Current frame:** a *surrogate-to-model identifiability study* over **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction**. `R_PICPOC` is recoverable given a real calcite anchor (Daniels/MODIS) — the "6/6 wall / needs the Darwin port" framing in the older writeups below is **superseded**. The v2.x/v3.x pages are point-in-time records.

## Version milestones

- [v2.1 — GLODAP DIC/ALK hybrid](v2.1_phase1_glodap.md) — first real-observation target; `R_PICPOC` 360% → 74% off Carroll.
- [v2.2 — 5-PFT box](v2.2_phase2.md) — full 5-PFT box matching Darwin v05; project-first 4/6 calibration-grade.
- [v2.7 — 2-layer box scoping](v2.7_multilayer_box_scoping.md) — subsurface DFe anchoring alone does not unblock `scav_rat`.
- [v2.8 — Darwin ICs + POC loss](v2.8_darwin_ic_poc_sub.md) — project-first reproducible `scav_rat` recovery; bimodal degeneracy.
- [v2 Track 1 closeout](v2_track1_closeout.md) — carbonate-cycle arc summary.
- [v3.0 — multi-AOI scoping](v3.0_multi_aoi_scoping.md) — joint multi-AOI training; the 5/6 plateau (historical 'parameter conservation' framing — superseded; see lead note).
- [v3.1 — closeout](v3.1_closeout.md) — 3-AOI Basin C; 38/40 iron-pair recovery; two complementary 5/6 paths.
- [v3.2 — dense POSi + Eppley](posi_dense_diatomgraz.md) — first reproducible 5/6 at 3-AOI via forward-model fidelity *(valid prior result against Darwin's own silica field; the `/6` framing is superseded by the 4-observable frame, and `diatomgraz` does **not** recover in the real-data sweep — it is an iron-pair tradeoff)*.

## R_PICPOC recovery (real calcite anchor)

`R_PICPOC` is recoverable given a real calcite observation (Daniels CP:PP / MODIS PIC). Any ratio anchor recovers it (Darwin's own too, via `RATIO_MAX=2`) — the real anchor supplies **non-circularity**, not recoverability. The campaign below is point-in-time.

- [Ratio loss (structural)](rpicpoc_ratio_structural.md) — the PIC:POC ratio observable recovers `R_PICPOC` in eqpac without the iron-pair mutex. **SUPERSEDED:** the apparent ≥2-AOI "wall" was a *contaminated Southern-Ocean ratio target*, not forward-model fidelity — fixed by `RATIO_MAX=2` (`R_PICPOC` 10/10) and recoverable from a real calcite anchor.
- [ALK anchor mutex test](alk_anchor_rpicpoc_mutex.md) — pre-registered null; an apparent co-recovery falsified as a cell-weighted averaging artifact.

## Scaling & verification

- [Compute-time scaling](compute_time_scaling.md)
- [Memory scaling — eager (RTX 5090)](memory_scaling.md)
- [Memory scaling — compiled (Explorer H200)](memory_scaling_compiled.md) — measured 82.9 B/(cell·step), 4.3× below eager
- [Pre-scaleup verification](pre_scaleup_verification.md)
- [Stage-1 per-AOI gating (2-AOI)](stage1_per_aoi_gating_2aoi.md)

## Early daily logs

- [2026-05-02](2026_05_02.md) · [2026-05-08](2026_05_08.md) · [2026-05-09](2026_05_09.md) · [2026-05-10](2026_05_10.md)
- [v2.2 overnight summary](v2.2_overnight_summary.md)
