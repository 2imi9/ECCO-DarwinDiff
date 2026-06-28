# DarwinDiff — Project Status

Live status doc. Headlines reflect verified results at the current project version. Per-version technical detail lives in [`docs/findings/`](docs/findings/index.md) and individual PR threads.

## Current state — Track 1: surrogate-to-model identifiability study

DarwinDiff replaces ECCO-Darwin's Green's-functions Carroll-6 calibration with gradient descent through a differentiable 0-D box model, predicted by a per-cell neural network. The work is framed as a **surrogate-to-model identifiability study** — *which* of the six Carroll-6 parameters are identifiable from real ocean observations, *which* are not, and *why* — **not** a "6/6 recovery" chase. Active at 3-AOI joint training (Equatorial Pacific + N Atlantic Subpolar + Southern Ocean Pacific) on a single RTX 5090 32 GB, with the NU Explorer H200 cluster for sweeps.

**The honest target is four OBSERVABLE parameters** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}. The growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** — no real-world data constrains phytoplankton growth rates — so it is excluded from the identifiability target, not counted as a recovery miss.

**What is identifiable (verified real-data, all `verify_run.py` exit 0):**

- **The iron pair (`alpfe`, `scav_rat`)** from real GEOTRACES IDP2025 dissolved iron — reproducible **38/40** at the best 3-AOI config.
- **`R_PICPOC`** from real calcite-production data (Daniels CP:PP / MODIS PIC).
- **The best operating point `geo1` (`GEOTRACES_W=1`) holds {`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 7/10 seeds** — a **3/4 frontier**, statistically tied with `base`/`dan2` at n=10. (Cross-confirmed by a fresh identical-config re-run; the original hold-together sweep reported 8/10 at the same config — they differ by a single band-edge seed.) `docs/research_notes/2026-06-26_holdtogether_sweep_results.md`.

**`R_PICPOC` is recoverable — the earlier "6/6 wall / needs the differentiable Darwin calcite port + native resolution" conclusion is REFUTED.** The calcite port and native resolution were tested and did not help; the real gap was the absence of a *direct, real calcite observation* (now supplied: Daniels/MODIS) plus a contaminated Southern-Ocean ratio target (fixed by `RATIO_MAX`). Any ratio anchor recovers `R_PICPOC` — Darwin's own ratio does too — so the real anchor's value is **non-circularity**: real calcite data is *consistent with* Carroll's value, not a failure to recover it.

**`diatomgraz` is not recovered in the real-data sweep** (best 4/10 = chance). It is an **iron-pair tradeoff** — turning the sparse bSi proxy *off* raises it — not a sparse-proxy block; recoverable in principle via the dense Darwin POSi (`TRAC16`) target, which is **not yet staged on the cluster** (open, not solved). A profile-likelihood test (Raue 2009) confirms this is *structural* non-identifiability in the present data — the diatomgraz profile is **FLAT** in the full loss and only **SHALLOW** against the bSi observable alone — so a new observable is required, not reweighting (#152). v3.2 (below) recovered it against Darwin's *own* silica field, which is a different and weaker thing than the real-data + `R_PICPOC` operating point.

**The surrogate gap is dimensional — and it is the rigorous foundation of the whole approach.** At uniform Carroll parameters the 0-D box relaxes to a spatially near-uniform state (tracer CV ~4e-5 @200 steps → ~1e-15 @6400, vs Darwin's O(1) CV 0.6–2.4): it has no mechanism for the circulation-driven spatial structure Darwin gets from advection. So box-vs-Darwin spatial-pattern correlations are **not** meaningful fidelity metrics, and **identifiability comes from real, absolute, Darwin-independent observations, not pattern-matching against Darwin's own output.** This makes the per-cell DINN load-bearing, and a direct **per-cell-vs-global-scalar ablation confirms it on real data** (not just the homogenization argument): at `geo1`, per-cell holds the trio jointly **7/10 vs 0/10** for a single global Carroll-6 vector (`scav_rat` 8/0, `R_PICPOC` 9/0 require per-cell; Fisher p<0.01). Identifiability is *parameter-specific* — the global scalar instead recovers the growth/grazing params (which per-cell overfits, the synthetic-equifinality effect), but not the anchor-constrained trio. [PR #158](https://github.com/2imi9/ECCO-DarwinDiff/pull/158); `docs/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md`.

**Statistical honesty:** in the hold-together sweep only two effects are real at n=10 — the ratio anchor recovering `R_PICPOC` (3/10→10/10, Fisher p=0.003) and high iron weight collapsing `scav_rat` (8/10→0, p=7e-4); differences among the high cells (7–10/10) are sampling noise. The metric throughout is **per-AOI ≥2-AOI co-recovery** (avoids a cell-weighted straddle false-positive). FIM/profile diagnostics independently agree, and a per-AOI empirical Fisher map (#152) localizes it: the iron pair is jointly *sloppy* in eqpac/natl (the `alpfe`↔`scav_rat` trade-off), `R_PICPOC` is the *null* direction in the Southern Ocean (matching the contaminated-SO finding), and `diatomgraz` is structurally flat (profile-confirmed). Next stages: the per-parameter **identifiability map** (scoped, `docs/research_notes/2026-06-27_identifiability_map_GOAL.md`), the cluster seasonal/native work (gated), and the manuscript reframe (#116).

## Prior box-scale results (context — the "5/6 ceiling / 6/6 wall" framing here is SUPERSEDED by the identifiability reframe above)

**Verified results from the v3.1 sweep set** (856 seeds across 86 configs, outputs in `D:\runs\bcr_*\`):

- **Basin C iron-pair recovery is reproducible at n=40, 38/40 (95%).** Four independent 10-seed batches at the F2 Basin C config (POSI_W=1.0 + AOI_W_NATLSUBPOLAR=2.0 + AOI_W_SOUTHERNOCEANPAC=2.0 + CHL1_W_EXTRA=3.0). Per-batch iron-pair counts: 10/10, 10/10, 10/10, 8/10.
- **Two 5/6 Cal-grade single-seed events** out of 856 seeds (0.23% break rate, both unreproduced at scale):
  - `w2e_peraoi_lam0.1` seed 3: PER_AOI_DINN + CONSISTENCY_LAMBDA=0.1 at Basin C base. Recovers alpfe (Excellent) + scav_rat + Smallgrow + Biggrow + diatomgraz; R_PICPOC drifts. Wave 5 dose-response (CONSISTENCY_LAMBDA ∈ {0.05, 0.15, 0.20, 0.30}) and n=20 extension (seeds 10-19 at the same config) produced 0 additional 5/6.
  - `c_chl40_posi15` seed 9: CHL1_W_EXTRA=4.0 + POSI_W=1.5 at Basin C base. Recovers alpfe + scav_rat (Excellent) + Smallgrow + Biggrow + R_PICPOC; diatomgraz drifts. n=20 retest at seeds 10-19 produced 0 additional 5/6 (combined: 1/20 at 5/6).
- **Composition test of the two 5/6 recipes fails (Wave 6).** Combining PER_AOI_DINN + CONSISTENCY_LAMBDA=0.1 + CHL1_W_EXTRA=4.0 + POSI_W=1.5 at Basin C 3-AOI base yields 0/10 at 5/6, 0/10 at 4/6, mean_cal 2.00 — worse than either parent (2.40 / 2.70). Iron pair survives (9/10) but R_PICPOC and diatomgraz both drift; small-cell phyto params (Smallgrow, Biggrow) also regress. The two intervention families interfere.
- **Binary mutex confirmed at low PIC dose.** Any nonzero `PIC_ABS_W` (tested down to 0.02) wipes iron-pair recovery → 0/10, regardless of POC pair. `POC_ABS_W` alone also kills iron pair, with different downstream basin geometry.

The structural 5/6 ceiling holds at 2/856 across all v3.1 work. Five independent pieces of evidence now support parameter conservation as the binding limit: (1) 0 at 6/6 across 856 seeds and 86 configs of single-lever 3-AOI variation, (2) `w2e_peraoi_lam0.1` n=20 → 1/20 at 5/6, (3) `c_chl40_posi15` n=20 → 1/20 at 5/6 (both 5/6 events unreproduced), (4) the composition test of the two complementary 5/6 lever families produces 0/10 at 5/6, (5) the v3.1.1 AOI ablation (n=200) produces 0/80 at 5/6 in the best-mean-cal 2-AOI `eqp+natl` configuration despite 19/80 at 4/6 via a recovery route v3.1 never observed (R_PICPOC + diatomgraz both Cal+, iron pair drops). The 5/6 ceiling is the headline finding; AOI mix decides WHICH 4--5 params recover but never lifts the cap to 6.

**v3.1.1 — AOI ablation** (PR #89 / paper §4.7, 200 fresh seeds). At the F2 Basin C lever set, four AOI configurations:

| Config | n | iron-pair | diatomgraz | R_PICPOC | k≥4/n | mean_cal |
|---|---|---|---|---|---|---|
| 1-AOI eqpac | 40 | 0% | 100% | 8% | 0% | 2.08 |
| 2-AOI eqp+natl (no SO) | 80 | 1% | 85% | 20% | **24%** | **3.20** |
| 2-AOI eqp+SO (no natl) | 40 | 75% | 15% | 0% | 12% | 2.30 |
| 3-AOI baseline (matched n=40) | 40 | 95% | 0% | 0% | 5% | 2.52 |

Per-AOI attribution: eqpac carries `alpfe` + `diatomgraz`; natl carries `Biggrow` + `R_PICPOC`; SO carries `scav_rat`. The 3-AOI configuration is one of several Pareto-equivalent points; it trades `diatomgraz` + `R_PICPOC` recovery for `scav_rat` recovery. 16/80 seeds in `eqp+natl` recover R_PICPOC + diatomgraz Cal+ simultaneously --- a basin v3.1's 856-seed sweep never produced.

**v3.2 — forward-model fidelity: Eppley temperature + dense POSi** (box scale, 3-AOI F2 Basin C, on main; `docs/findings/posi_dense_diatomgraz.md`). Two laptop-feasible forward-model edits from the 2026-06-11 utilization audit, behind default-OFF flags: (i) a **dense Darwin `POSi` (`TRAC16`) target** for `diatomgraz` (`POSI_DARWIN_W`, replacing the sparse GEOTRACES-bottle bSi proxy); (ii) **Eppley temperature limitation** of growth (`USE_EPPLEY_T`; the box previously had no `f(T)`, `LIGHT=1.0`). Result (n=20, seeds 0--19, reproducible by split-half 3.90/3.80):

| param | `alpfe` | `scav_rat` | `Smallgrow` | `Biggrow` | `diatomgraz` | `R_PICPOC` |
|---|---|---|---|---|---|---|
| Cal+ | 18/20 | 20/20 | 15/20 | 4/20 | 20/20 | 0/20 |

**mean 3.85/6 · ≥4/6 in 14/20 (70%) · 5/6 in 4/20 (20%, reproducible) · 6/6 in 0/20.** This is the **best multi-AOI recovery in the project** and the first *reproducible* 5/6 at 3-AOI (the two v3.1 5/6 events were 1/20 flukes). Mechanism: Eppley gives diatom biomass an SST handle independent of iron, so the dense-silica target no longer commandeers the iron budget --- breaking the `alpfe`↔silica mutex (dense POSi alone collapses `alpfe` 10/10→2/10) and letting the **iron pair *and* `diatomgraz` recover together**, which the v3.1.1 ablation had shown were mutually exclusive across regions. **`R_PICPOC` is now the entire 6/6 wall**: 0/20 and the sole miss in all four 5/6 seeds. Two box-scale cracks both fail by the same mutex: separate calcite sinking (`W_SINK_PIC`) did not move it (0/10); a PIC magnitude anchor on Eppley (`PIC_ABS_W ∈ {0.02, 0.1}`) *does* recover it (8/10) but wipes the iron pair (18→0, 20→0) **and** `diatomgraz` (20→1), net mean 3.85→2.5 — i.e. the binary PIC-anchor mutex is robust even to the temperature physics that broke the *other* mutex. This refines "parameter conservation": forward-model fidelity *raises* the effective recovered count (2.0→3.85) rather than reshuffling a fixed budget. **[SUPERSEDED 2026-06-27:** the "`R_PICPOC` ⊕ iron-pair is a genuine binary degeneracy / 6/6 is foreclosed, cluster-gated on native resolution" framing is refuted. `R_PICPOC` recovers alongside the iron pair once a *real* calcite anchor (Daniels/MODIS) is added and the contaminated SO ratio target is sanitized (`RATIO_MAX`) — `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`} jointly 7/10. The honest target is 4 observable params, not 6; the growth pair is unobservable. See the Current-state section.]**

## Headline results

| Version | AOI | Config | Best result | Source |
|---|---|---|---|---|
| **spine D (real-data identifiability)** | 3-AOI | `geo1` (`GEOTRACES_W=1`) + Daniels R_PICPOC anchor | **{`alpfe`, `scav_rat`, `R_PICPOC`} recover jointly in 7/10 seeds** (3/4-observable frontier; tied w/ base/dan2 at n=10); `diatomgraz` not recovered (iron-pair tradeoff, open) | docs/research_notes/2026-06-26_holdtogether_sweep_results.md |
| v3.2 (Eppley + dense POSi) | 3-AOI Basin C | `USE_EPPLEY_T` + `POSI_DARWIN_W=0.5` | mean 3.85/6; 14/20 at 4/6 (70%); 4/20 at 5/6 (reproducible); iron pair + diatomgraz recover together; R_PICPOC the sole 6/6 wall (0/20) | docs/findings/posi_dense_diatomgraz.md |
| v3.1.1 (AOI ablation, PR #89) | 2-AOI eqp+natl | F2 base, no SO | 19/80 at 4/6 (24%, best 4+ rate in project); 16/80 with R_PICPOC + diatomgraz Cal+ together (v3.1 had 0 of 856) | bcr_5pft_eqp_natl_20260523_1058/ |
| v3.1.1 (AOI ablation, PR #89) | 1-AOI eqpac | F2 base | 40/40 alpfe Cal+ (7 Excellent); 40/40 diatomgraz Cal+; iron pair 0/40 | bcr_eqp5_20260523_0242/ |
| v3.1 (Wave 2) | 3-AOI | `w2e_peraoi_lam0.1` | 1/10 seeds at 5/6; alpfe Excellent + scav_rat + Smallgrow + Biggrow + diatomgraz Cal | bcr_w2_/w2e_peraoi_lam0.1/ |
| v3.1 (Wave 3) | 3-AOI | `c_chl40_posi15` | 1/10 seeds at 5/6; alpfe + scav_rat Excellent + Smallgrow + Biggrow + R_PICPOC Cal | bcr_w3_/c_chl40_posi15/ |
| v3.1 (n=40 extension) | 3-AOI | F2 Basin C base | 38/40 iron-pair Cal+ across four 10-seed batches | bcr_*/arc6_basinC_seeds10-19/, /w2f_basinC_seeds20-29/, /e_basinC_seeds30-39/ |
| v3.0 baseline (PR #57) | 2-AOI | AOI ID + GEO POC=0.5 + hd=32 + NAtl_W=2.0 | 7/15 seeds at 5/6 Cal-grade; mean_cal=3.93 | nb32 |
| v2.8 | Eq Pac | Darwin v5 ICs + L2 POC z-score | 7/10 Cal-grade scav_rat (4/10 Excellent); aggregate 6/10 at 4/6 | docs/findings/v2.8_darwin_ic_poc_sub.md |
| v2.6 | Eq Pac | GEOTRACES_W=0.3 + PINN drift w=3.0 | 4/6 Cal-grade reproducible across n=10; Smallgrow 9/10 Cal+ | PR #40 |
| v2.4 | Eq Pac | 5-PFT + PINN drift w=3.0 | 4/6 Cal-grade — project-first | nb29 |
| v2.1 Phase 1 | Eq Pac | GLODAP DIC + ALK hybrid | R_PICPOC 360% → 74% off Carroll | PR #41 (nb22) |
| v2.0 | Eq Pac | 7-tracer carbonate joint loss | Iron pair to 1.1% (alpfe) / 40% (scav_rat) off Carroll | nb20-21 |

## Version chronology

- **v0.x → v1.8** (nb 05–19): synthetic-truth methodology validation, real-data demos on GLODAP and Darwin Chl, cross-basin verification (Mid-Atl + N Pacific), iron-pair recovery via Darwin FeT in HNLC, multi-tracer joint loss partial collapse of parameter degeneracy.
- **v2.0** (nb 20–21): carbonate cycle (`carbonate.py` Follows-2006 solver + Wanninkhof 2014 air-sea flux); 7-tracer joint loss moves iron pair to 1.1% / 40% off Carroll. Robust across DINN baseline + DINNDeep.
- **v2.1 Phase 1** (nb 22, PR #41): GLODAPv2.2016b real-obs DIC + ALK hybrid; R_PICPOC dramatic improvement, iron pair degraded under obs swap.
- **v2.2** (nb 23–29, PR #37): full 5-PFT box matching Darwin v05; 22 experiments; v2.4 PINN drift w=3.0 reaches 4/6 calibration-grade. `alpfe` confirmed structurally stuck under z-scored loss without absolute iron observations.
- **v2.5** (PR #39): GEOTRACES IDP2025 loader scaffold validated against real NetCDF schema.
- **v2.6** (PR #40): GEOTRACES dissolved-iron absolute-units MSE loss; 4/6 Cal-grade reproducibly across n=10; Smallgrow at 9/10 Cal+. Reframes v2.2's "alpfe + Smallgrow are structurally stuck" claim.
- **v2.7** (PR #42): 2-layer (0–50 m + 50–1000 m) box with sinking-POC iron + Kz + subsurface remineralisation. Subsurface DFe anchoring alone does NOT unblock scav_rat.
- **v2.8** (PR #45): Darwin v5 pickup ICs + L2 POC z-score loss. Project-first reproducible scav_rat recovery (7/10 Cal-grade, 4/10 Excellent). Reveals bimodal degeneracy in (alpfe, scav_rat) selected by `POC_SUB_W`.
- **v3.0** (PRs #46–#59): joint multi-AOI training across Eq Pac + N Atl Subpolar with a shared Carroll-6. Establishes the 5/6 plateau across 50+ seeds. Architectural (PR #58: per-AOI DINNs falsified at 2-AOI) and observational-anchor (PR #59: PIC_ABS + POC_ABS paired anchors underperform baseline) break attempts all empirically falsified. 5/6 ceiling characterized as **parameter conservation**: the observations support ~5 effective constraints on 6 parameters; the 6th is always the residual sink, and loss weighting decides which.
- **v3.1** (PR #64+): Southern Ocean Pacific added as 3rd AOI; Basin C iron-pair 38/40 at n=40; two complementary 5/6 paths via PER_AOI_DINN at low CONSISTENCY_LAMBDA and via CHL1_W + POSI_W combo tuning. PER_AOI_DINN was falsified at 2-AOI; 3-AOI behavior is new and material.
- **v3.1.1** (PR #89): AOI ablation (4 configs × n=40-80 = n=200) decomposes the v3.1 recoverability gradient into per-AOI attribution. Dropping SO recovers `diatomgraz` (0→85%) and `R_PICPOC` (0→20%) at the cost of `scav_rat` (95→1%). Architecture-level Carroll-6 tradeoff: no single AOI mix reaches 6/6. Paper §4.7 in the same PR. 5/6 ceiling holds (0/80 at 5+ in `eqp+natl`).
- **v3.2** (forward-model fidelity, box scale, on main): dense Darwin `POSi` (`TRAC16`) target + Eppley temperature limitation of growth, both from the 2026-06-11 utilization audit. Eppley breaks the `alpfe`↔silica mutex and recovers the iron pair + `diatomgraz` together — mean 2.0→3.85/6, 70% of seeds ≥4/6, first *reproducible* 5/6 at 3-AOI (n=20). `R_PICPOC` localized as the entire 6/6 wall (0/20). First gain via forward-model physics rather than loss-weight/architecture/IC levers. `docs/findings/posi_dense_diatomgraz.md`.
- **v3.2 ALK anchor — R_PICPOC mutex test (2026-06-15, on main, default-OFF `ALK_ABS_W`/`ALK_ABS_SOURCE`): NULL, mutex holds.** Tested whether a real-GLODAP absolute-alkalinity anchor (calcite ⇒ 2:1 ALK signature) breaks `R_PICPOC ⊕ {iron pair}` without the iron-pair collapse the PIC anchor causes. Pre-registered (`docs/findings/alk_anchor_rpicpoc_mutex.md`); paired n=20 + split-half + 5-lens adversarial panel. An *apparent* co-recovery (a100: R_PICPOC joint 14/20, iron 14/20, co-rec 13/20 [split 6+7], 6/6 3/20) **passed the reproducibility gate but was falsified as a cell-weighted averaging artifact**: per-AOI decomposition shows `R_PICPOC` recovered in **no single AOI** (eqpac driven →0, natl/SO too-high, joint mean straddles Carroll; only 2/13 co-rec seeds have any AOI Cal). Confirmed generic (not real-obs) by the Darwin-ALK-source control (a100d reproduces the straddle) and dose (a300 deepens deflation, erodes iron pair). The iron pair / diatomgraz remain per-AOI genuine, so the metric is sound where parameters are identified — `R_PICPOC` is the lone per-AOI-unidentified parameter and thus the only one vulnerable to the straddle. **A 7th independent box-scale exclusion of `R_PICPOC`** (now: loss weight, AOI mix, architecture, IC, Eppley physics, PIC anchor, ALK anchor) — reinforces cluster-gated / AICR. Methodological note: report `R_PICPOC` per-AOI, not only joint cell-weighted.
- **v3.2 R_PICPOC structural campaign (2026-06-15 night, on main, default-OFF `RATIO_W`): the wall is calcite forward-model fidelity, not the estimator/info/seasonal axis.** Adversarial code audit showed R_PICPOC's level is a provable null-space degeneracy of the z-scored loss (not a bug). A new **PIC:POC ratio loss** (mort_total cancels at steady state → orthogonal to the iron pair) **breaks the mutex**: recovers R_PICPOC in eqpac **10/10 without collapsing the iron pair** (dose-robust r0.5–r30) — the first lever to recover R_PICPOC and keep the iron pair. But it lands only in eqpac (Darwin realized PIC/POC ≈ Carroll there); natl/SO realized ratios are ~0.9/1.4 (coccolithophore blooms), which the box's rigid `PIC/POC=R_PICPOC` calcite can't match at a single value. **Exhaustive structural exclusion: 25 arms (ratio×dose×coccolith×W_SINK_PIC, paired PIC+POC per-AOI, gating, PER_AOI_DINN), 0/10 co-recovery in ≥2 AOIs**; every magnitude anchor still wipes the iron pair; coccolith-only backfires. A **1° seasonal fit is also excluded** (theory+probe: box has no seasonal biology — Eppley mean-neutralized, LIGHT constant — and PIC is phase-locked to mort). **Conclusion (SUPERSEDED 2026-06-27): R_PICPOC needs richer calcite physics (the differentiable Darwin port) + native resolution.** This is **refuted**: the calcite port and native resolution were tested and did not help. The real blockers were (a) the absence of a *direct, real calcite observation* — now supplied (Daniels CP:PP / MODIS PIC) — and (b) a contaminated Southern-Ocean ratio-loss target, fixed by `RATIO_MAX=2`. With both addressed, `R_PICPOC` recovers ≈Carroll alongside the iron pair (`geo1` jointly 7/10). The defensible structural point survives: a single *global-constant* `R_PICPOC` is mis-specified when Darwin's realized rain ratio is regionally variable. `docs/findings/rpicpoc_ratio_structural.md`; superseding evidence in `docs/research_notes/2026-06-26_holdtogether_sweep_results.md`.
- **v3.3** (seasonal / native bridge — infrastructure; #115 / #126 / #127 merged, #131 in review): the transient-seasonal integrator (`carroll6_5pft_2layer_integrate_seasonal`) and `scripts/run_seasonal_recovery.py` are now **seed-batched + `torch.compile`-ready** (the per-cell seed axis folds into the spatial dims, proven seed-independent) and **emit `verify_run.py`-gateable per-seed JSON** — the AICR-readiness layer so the first H200/B200 seasonal fit saturates the GPU and is verifiable rather than idle-reaped. `#119` `--compile` flag added to the memory/wall-clock harnesses (compiled measurement pending a WSL run). No new science: seasonal *recovery results* stay cluster-gated (the 1° box has no seasonal biology — native resolution is the test).
- **spine D — real-data identifiability (2026-06, the current frame).** Reframed the project from a "6/6 recovery" chase to a *surrogate-to-model identifiability study* over **4 observable params**. Real-data anchors identify the iron pair (GEOTRACES) and `R_PICPOC` (Daniels CP:PP / MODIS PIC); the best config `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`} jointly 7/10 (hold-together sweep, 8×n=10, all `verify_run` exit 0). Refuted the "R_PICPOC needs the differentiable Darwin port + native resolution" claim (both tested, neither helped). Established that the 0-D box homogenizes spatial structure (the surrogate gap is dimensional), so identifiability comes from real absolute anchors and the per-cell DINN is load-bearing. `diatomgraz` is an open iron-pair tradeoff (needs dense Darwin POSi/TRAC16, not staged); the growth pair is unobservable by construction. Next: the per-parameter identifiability map (`docs/research_notes/2026-06-27_identifiability_map_GOAL.md`). Findings in `docs/research_notes/2026-06-2[67]_*.md`.
- **Cluster-gated**: native-resolution recovery, time-resolved multi-year fitting, Track 2 emulator, forward Darwin validation. (Note: these remain legitimate cluster goals; they are **not** gated on `R_PICPOC` or "6/6", which are resolved/reframed at 1° box scale.) See [docs/cluster_setup.md](docs/cluster_setup.md).

## Architecture

DarwinDiff is a per-cell neural network `env → 6 Carroll-6 params` trained by gradient descent through a differentiable box model. Architecture details in [docs/dinn_design.md](docs/dinn_design.md).

- **Networks**: `DINN` (~454 weights, SST-only, baseline for structural argument), `DINNDeep` (~9.4K weights, 4-channel, saturates on biomass tracers), `DINNRegional` (legacy, superseded).
- **Box model**: 5-PFT 2-layer integrator (`src/darwindiff/carroll6_5pft_2layer.py`) extending the original 5-tracer proxy. Includes carbonate chemistry (`src/darwindiff/carbonate.py`, Follows 2006 solver + Wanninkhof 2014 air-sea flux).
- **Multi-AOI joint training (v3.0+)**: shared DINN with optional per-AOI identity channel (`AOI_ID_CHANNEL=1`), per-AOI loss weights (`AOI_W_<KEY>`), optional per-AOI DINN architecture (`PER_AOI_DINN=1` + `CONSISTENCY_LAMBDA=λ`).
- **Loss components**: z-scored MSE per-AOI per-tracer (`GEOTRACES_W`, `POC_SUB_W`, `NB23_PINN_WEIGHT`, `NB23_FET_WEIGHT`), absolute-units anchors (`PIC_ABS_W`, `POC_ABS_W`, `F_CO2_ABS_W`), biogenic silica MSE against GEOTRACES IDP2025 bSi observations (`POSI_W`, via the steady-state diagnostic in `src/darwindiff/silica.py`), extra diatom-chl weight (`CHL1_W_EXTRA`).
- **Optimization**: Adam at lr=5e-3, 1500 epochs (extendable via `NB23_N_EPOCHS`). Forward-Euler integrator (`DT=0.25`, `N_STEPS=200`).
- **Recovery scoring** (canonical `diagnostics.band_of`): Excellent if `|recovered − Carroll| / Carroll ≤ 0.05`; Cal-grade if `≤ 0.40`; Loose if `≤ 0.80`; Drifted otherwise. Six Carroll-6 params: `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC`. Carroll's published values bit-identical between v04 (JAMES) and v05 (GBC).

## 5/6 ceiling — structural diagnosis (SUPERSEDED FRAMING)

> **[SUPERSEDED 2026-06-27]** The "5/6 ceiling / parameter conservation" framing in this section is a historical box-scale diagnosis. It is reframed by the identifiability study: the binding limit is that the **growth pair {`Smallgrow`, `Biggrow`} is unobservable by construction** (no real data constrains growth rates), so the honest target is **4 observable params**. `R_PICPOC` is recoverable with a real calcite anchor (not a "wall"), and the iron-pair⊕R_PICPOC "binary mutex" below is specific to the **PIC magnitude anchor** (`PIC_ABS_W`) — the *ratio* anchor (Daniels/`RATIO_MAX`) recovers `R_PICPOC` while keeping the iron pair (`geo1` jointly 7/10). Read the diagnosis below as a record of the magnitude-anchor regime.

Across 856 seeds in v3.1, only 2 broke the 5/6 ceiling. Different interventions shift WHICH parameter is the dominant 5/6 miss:

| Family | Dominant 5/6 miss | Mechanism |
|---|---|---|
| Baseline (PR #57, 2-AOI) | `diatomgraz` | Chl1 z-score under-constrains diatom-specific growth |
| Per-AOI DINN (PR #58, 2-AOI) | `R_PICPOC` | Shared-MLP regularization removed; basin selection collapses |
| PIC alone (PR #59) | `alpfe + scav_rat` | Magnitude anchor on PIC competes with iron budget |
| Paired POC+PIC (PR #59) | `alpfe + scav_rat` | Both anchors disturb iron budget |
| PER_AOI + low λ at 3-AOI (v3.1 w2e) | `R_PICPOC` | Same family as PR #58 but the 3rd AOI breaks the basin lock |
| CHL1 + POSI combo at 3-AOI (v3.1 c_chl40_posi15) | `diatomgraz` | Loss reweighting lands R_PICPOC while losing diatomgraz |
| 2-AOI eqp+natl ablation (v3.1.1) | `scav_rat` + `Smallgrow` | Dropping SO recovers diatomgraz + R_PICPOC + Biggrow but iron pair collapses (no surface↔subsurface DFe contrast) |

The two v3.1 5/6 paths recover complementary param subsets (one lands diatomgraz, the other lands R_PICPOC). Combining their interventions in a single config is the obvious next test for a 6/6 candidate.

The mutex between iron-pair recovery and R_PICPOC recovery is binary in PIC anchor presence (not magnitude): any nonzero `PIC_ABS_W` wipes iron pair regardless of dose. The PER_AOI architectural lever produces 5/6 without invoking that mutex — orthogonal axis.

## Methodology rules

- **Compare against Carroll's published Green's-functions optima**, not against prior notebooks. The headline is "did the parameter learner catch the goal?", not "did this version beat the previous one." Inter-version deltas are supplementary methodology context.
- **Train DINN baseline only by default from v2.2.x onward.** DINNDeep saturates trivially on biomass tracers (r → 1.0) and recovers fewer calibration-grade Carroll-6 params than the baseline; halves wall-clock per fit. The dual-architecture framing remains useful for the v2.0 saturation-ceiling argument.
- **Recovery analyses report n=10 minimum and disclose seed variance** in any headline claim. Avoid single-seed framing; n=5 medians can hide bimodality.

## Cluster path

Three clusters across **two institutions** — do not conflate (full table in [docs/cluster_setup.md](docs/cluster_setup.md)):

- **Explorer** (Northeastern RC, H200 144 GB ×32) — **active near-term path**, access granted June 2026 (Cristina-sponsored). The first native-resolution prototype runs here.
- **AICR** (Northeastern RC, B200) — future path via a PI **project proposal** (in prep); target for the global-native / seasonal sweep. (Earlier notes mis-framed AICR as an MIT-ORCD follow-on to Engaging — it is Northeastern's.)
- **Engaging** (MIT ORCD) — Jon-side option, open to MIT users.

Detailed setup, partitions, storage, and SLURM templates in [docs/cluster_setup.md](docs/cluster_setup.md).

The cluster path unlocks: native LLC270-resolution recovery (vs the 1° box-model proxy), time-resolved multi-year fitting, n=20–50 multi-seed ensembles, full-ocean parameter recovery sweeps, and Track 2 emulator development.

## Known limitations

- **Box model is a 5-tracer proxy** of full Darwin 3. The 5-PFT + 2-layer extensions close part of the gap; cluster-scale native-resolution recovery is the planned next reduction.
- **DINN is per-cell, not spatially coupled.** Advection / diffusion between cells is ignored — appropriate for parameter recovery but not for the Track 2 emulator.
- **The surrogate gap is dimensional.** At uniform Carroll params the 0-D box relaxes to a spatially near-uniform state (tracer CV ~4e-5 @200 steps → ~1e-15 @6400, vs Darwin's O(1) CV 0.6–2.4): it cannot reproduce the circulation-driven spatial structure of Darwin. Box-vs-Darwin spatial-pattern correlations are therefore *not* fidelity metrics; identifiability rests on real, absolute, Darwin-independent anchors (GEOTRACES iron, Daniels/MODIS calcite). This is why the per-cell DINN is load-bearing. `docs/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md`.
- **DINNDeep does not extrapolate spatially.** Block CV gives held-out r=0.301 vs in-distribution r=1.000 on FeT. Use DINN baseline for cross-AOI extrapolation claims.
- **Climatology, not time-resolved.** All current fits use 23-year time-mean Darwin output.
- **Windows MAX_PATH=260.** Long config-name + filename combinations crash JSON writes after training succeeds. `scripts/recover_failed_config_log.py` reconstructs from `.log` files; sweep orchestration uses short OUTPUT_DIR prefixes (`D:\runs\bcr_<stamp>\`) to stay under the limit.
- **Laptop sleep on Windows** suspends background Python processes during overnight runs. Use `powercfg /change standby-timeout-ac 0` for unattended runs.

## Cross-references

- [README](README.md) — project overview
- [docs/dinn_design.md](docs/dinn_design.md) — DINN architecture, training loop, structural argument
- [docs/cluster_setup.md](docs/cluster_setup.md) — Northeastern Explorer / AICR + MIT ORCD Engaging setup
- [data/README.md](data/README.md) — dataset provenance and download mechanics
- [.claude/skills/README.md](.claude/skills/README.md) — project-scoped Claude Code skill bundle
- [docs/findings/](docs/findings/index.md) — per-version technical writeups
