# Findings

Per-version technical writeups behind the headline results. [Project Status](../status.md) is the canonical live summary; these pages are the underlying experimental record.

## Version milestones

- [v2.1 — GLODAP DIC/ALK hybrid](v2.1_phase1_glodap.md) — first real-observation target; `R_PICPOC` 360% → 74% off Carroll.
- [v2.2 — 5-PFT box](v2.2_phase2.md) — full 5-PFT box matching Darwin v05; project-first 4/6 calibration-grade.
- [v2.7 — 2-layer box scoping](v2.7_multilayer_box_scoping.md) — subsurface DFe anchoring alone does not unblock `scav_rat`.
- [v2.8 — Darwin ICs + POC loss](v2.8_darwin_ic_poc_sub.md) — project-first reproducible `scav_rat` recovery; bimodal degeneracy.
- [v2 Track 1 closeout](v2_track1_closeout.md) — carbonate-cycle arc summary.
- [v3.0 — multi-AOI scoping](v3.0_multi_aoi_scoping.md) — joint multi-AOI training; the 5/6 plateau as parameter conservation.
- [v3.1 — closeout](v3.1_closeout.md) — 3-AOI Basin C; 38/40 iron-pair recovery; two complementary 5/6 paths.
- [v3.2 — dense POSi + Eppley](posi_dense_diatomgraz.md) — first reproducible 5/6 at 3-AOI via forward-model fidelity.

## Real-data validation + identifiability (2026-06) — current frontier

- [Daniels CP:PP — first real-data R_PICPOC recovery](2026-06-26_daniels_realdata_rpicpoc_recovery.md) — graded against the Darwin-independent Daniels 2018 CP:PP anchor (not Darwin's own PIC): `R_PICPOC` ≥2-AOI co-recovery **50/50, Wilson 95% CI [0.93, 1.00]**, `verify_run.py` exit 0. Breaks the circularity. Honest scope: drops `alpfe` + `diatomgraz` (not a 6/6).
- [FIM/profile identifiability spine](2026-06-26_fim_alpfe_contrast.md) — `alpfe` 0.103 (full loss) vs 0.9997 (real GEOTRACES iron); the iron-pair "collapse" is loss-weighting, not structural.
- [Rain ratio: real vs Darwin](2026-06-26_rainratio_real_vs_darwin.md) — ECCO-Darwin's `R_PICPOC` global constant is consistent with real surface calcite but mis-specified as a single global value (the real rain ratio is regional).
- Self-twin diagnostic (`scripts/self_twin_recovery.py`, PR #148) — with zero surrogate gap the method recovers θ to loss 5e-10, isolating method-correctness from surrogate fidelity.

## R_PICPOC structural campaign (Darwin-graded history — superseded by the real-data validation above)

- [Ratio loss (structural)](rpicpoc_ratio_structural.md) — the PIC:POC ratio observable recovers `R_PICPOC` in eqpac without the iron-pair mutex. *(The "≥2-AOI wall is calcite forward-model fidelity / needs the calcite port" conclusion is superseded: the calcite port was refuted at box scale, and `R_PICPOC` now recovers ≥2-AOI via real Daniels data.)*
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
