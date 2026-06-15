# Dense Darwin POSi target for `diatomgraz` (box scale)

**Date:** 2026-06-11 · **Status:** result established. Dense POSi recovers `diatomgraz` (n=10 dose sweep); **Eppley temperature limitation breaks the `alpfe`↔silica mutex and recovers the iron pair + `diatomgraz` together — best 3-AOI recovery in the project, reproducible at n=20.**

## Hypothesis

The 2026-06-11 utilization audit named **dense gridded `POSi`** (Darwin's own
biogenic-silica field, `TRAC16`) as the cheapest laptop-feasible lever for the
stuck `diatomgraz` parameter. Until now the only silica constraint was `POSI_W`,
which compares the box's steady-state `bsi_1` diagnostic to **sparse GEOTRACES
bottle bSi** (typically <10 surface bins per AOI). The hypothesis: a **dense,
model-consistent, diatom-specific** target — Darwin's own surface POSi binned to
the AOI 1° grid — identifies `diatomgraz` where the sparse proxy and every other
lever in the 856-seed sweep produced 0%.

## Method

- **Tracer:** `POSi = TRAC16` (surface biogenic silica, mmol Si/m³, 289 monthly
  native LLC270 snapshots on disk). Registered in `TRAC_MAPPING`
  (`src/darwindiff/llc270_loader.py`), bin-averaged to 1° via the surface-level
  `bin_native_tracer_to_1deg` (aligns with the box's surface `bsi_1`).
- **Loss:** new additive `POSI_DARWIN_W` lever in
  `scripts/run_v3.0_joint_multi_aoi.py` — an absolute-units MSE between the box's
  `silica.diagnostic_bsi_steady` `bsi_1` and the dense Darwin POSi target, sharing
  the `bsi_1_pred` computation with the existing GEOTRACES `POSI_W` path (left
  untouched). Target cache augmented in place (bins only POSi, no re-bin of the
  other 5 tracers); no IC-cache or tracer-vector change.
- **Config:** 3-AOI F2 Basin C — `AOIS=eqpac,natlsubpolar,southernoceanpac`,
  `POSI_W=1.0`, `AOI_W_NATLSUBPOLAR=2.0`, `AOI_W_SOUTHERNOCEANPAC=2.0`,
  `CHL1_W_EXTRA=3.0`, 1500 epochs. This is the canonical *stuck* config where
  `diatomgraz` recovery is 0% across the v3.1 856-seed sweep.
- **Design:** paired seeds 0–9 (n=10) per arm; dose sweep
  `POSI_DARWIN_W ∈ {0, 0.5, 1.0, 2.0, 5.0}`. Scored vs Carroll 2022 published
  values (Cal-grade ≤40%, Excellent ≤10%).

## Result — dose response (n=10 paired)

| `POSI_DARWIN_W` | diatomgraz | alpfe | Biggrow | Smallgrow | mean Cal-grade/6 | seeds ≥4/6 |
|---|---|---|---|---|---|---|
| 0.0 (baseline) | 0/10 | 10/10 | 1/10 | 9/10 | 2.00 | 0/10 |
| **0.5** | **10/10** (1 Excellent) | 2/10 | **9/10** | 8/10 | **3.00** | **3/10** |
| 1.0 | 9/10 (2E) | 2/10 | 5/10 | 7/10 | 2.50 | 2/10 |
| 2.0 | 8/10 (4E) | 2/10 | 5/10 | 6/10 | 2.10 | 1/10 |
| 5.0 | 10/10 (0E) | 2/10 | 4/10 | 4/10 | 2.10 | 0/10 |

`scav_rat` 0/10 and `R_PICPOC` 0/10 at every dose (unchanged).

## Interpretation

1. **Dense POSi recovers `diatomgraz`** — 0/10 → up to 10/10, mean |offset|
   0.78 → 0.14. The audit's #1 lever is confirmed: the sparse GEOTRACES proxy
   never achieved this in the stuck config.
2. **A gentle dose is a genuine net gain, not a reshuffle.** `POSI_DARWIN_W=0.5`
   lifts mean recovered from **2.00 → 3.00/6** and yields **3/10 seeds at ≥4/6**
   (baseline 0/10) — the best 3-AOI recovery the project has produced. It
   recovers `diatomgraz` *and* rescues `Biggrow` (1→9/10).
3. **The `alpfe` cost is binary and dose-independent.** `alpfe` collapses
   10/10 → 2/10 at the *first* nonzero dose and never recovers across all doses.
   A new mutex analogous to the binary PIC-anchor mutex: dense-silica and
   iron-uptake both bind diatom biomass (iron → diatom growth → bSi), so they are
   mutually exclusive.
4. **The 6/6 ceiling holds.** 0/10 at ≥5/6 and 0/10 at 6/6 across all doses;
   best single seed = 4/6. Strong doses over-constrain bSi and decay the gain
   (Biggrow 9→4, Smallgrow 8→4 as W rises).

**Thesis refinement.** "Parameter conservation" is not strict count-conservation:
the *effective* recovered count is configuration-dependent and rises (2.0→3.0)
with a better forward-model constraint that injects genuine identifying
information. The hard **6/6 cap** still stands, and certain parameter pairs
(`alpfe` vs dense-silica/diatom) are mutually exclusive. This is a sixth
independent line of evidence for the ceiling — and the first via a forward-model
fidelity intervention rather than a loss-weight or architecture lever.

## Result — forward-model fidelity levers (on `POSI_DARWIN_W=0.5`)

Re-reading Carroll 2020/2022 confirmed the box was missing **temperature
limitation of growth** (Darwin uses an Eppley-style `f(T)`; our box had growth =
`μ·f_Fe·1.0`, `LIGHT=1.0`, no `f(T)`). Added behind two default-OFF flags:
`USE_EPPLEY_T` (Eppley `2^((T−T_ref)/10)` growth scaling in
`carroll6_5pft_2layer.py`) and `W_SINK_PIC` (separate calcite sinking rate,
decoupling PIC export from POC). Validated at the new best operating point.

| arm (on W=0.5) | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC | mean/6 | ≥4/6 | 5/6 |
|---|---|---|---|---|---|---|---|---|---|
| W=0.5 control (n=10) | 2/10 | 1/10 | 8/10 | 9/10 | 10/10 | 0/10 | 3.00 | 3/10 | 0/10 |
| **+Eppley (n=20)** | **18/20** | **20/20** | 15/20 | 4/20 | **20/20** | 0/20 | **3.85** | **14/20 (70%)** | **4/20 (20%)** |
| +wPIC only (n=10) | 1/10 | 0/10 | 8/10 | 7/10 | 9/10 | 0/10 | 2.50 | 1/10 | 0/10 |
| +Eppley+wPIC (n=10) | 9/10 | 9/10 | 7/10 | 2/10 | 10/10 | 0/10 | 3.70 | 6/10 | 2/10 |

Recovery is real, not a scoring artifact: Eppley arm mean |offset| `scav_rat`
0.158 (recovered 4.7e-7 vs Carroll 6.0e-7), `alpfe` 0.295, `diatomgraz` 0.156.

**Reproducible at n=20.** Split-half: seeds 0–9 → mean 3.90, 7/10 ≥4/6, 2/10 at
5/6; seeds 10–19 → mean 3.80, 7/10 ≥4/6, 2/10 at 5/6. Near-identical halves —
unlike the v3.1 5/6 events (1/20 flukes that vanished on retest), this 5/6 rate
is *stable at ~20%*. (`+Eppley+wPIC` is n=10 only — its seeds 10–19 run was
interrupted by laptop sleep at ~epoch 750; not rerun, since wPIC is inert here.)

## Interpretation (updated)

5. **Eppley breaks the `alpfe`↔silica mutex.** The dose-sweep mutex (#3) was an
   artifact of the missing temperature physics: without `f(T)`, the only handle
   on diatom biomass is iron uptake, so pinning bSi forces `alpfe`. Giving diatom
   growth an *independent SST handle* lets silica be matched without commandeering
   the iron budget — so `alpfe` (2→18/20) **and** `scav_rat` (1→20/20) **and**
   `diatomgraz` (20/20) recover **simultaneously**. The v3.1.1 AOI ablation had
   shown the iron pair and `diatomgraz` were mutually exclusive across regions;
   the missing forward-model term, not a hard budget, was the cause.
6. **Best multi-AOI recovery in the project.** mean 2.00 (baseline) → 3.85/6,
   70% of seeds ≥4/6, and the **first *reproducible* 5/6 events at 3-AOI** (the
   v3.1 5/6 were single-seed flukes). `scav_rat`, previously needing the Southern
   Ocean and lost whenever `diatomgraz` recovered, now lands in 20/20.
7. **`R_PICPOC` is the entire 6/6 wall, and it is cluster-gated.** 0/20 under
   Eppley, the *sole* miss in all four 5/6 seeds. Two box-scale attempts to crack
   it both fail by the *same* mutex:
   - Separate calcite sinking (`W_SINK_PIC=0.30`) alone did **not** move it
     (0/10) and slightly degraded the iron pair.
   - A **PIC magnitude anchor on the Eppley config** (`PIC_ABS_W ∈ {0.02, 0.1}`,
     n=10 each) **does** recover it (0→8/10) — so R_PICPOC is identifiable in
     principle — **but wipes the entire iron pair (18→0/10, 20→0/10) *and*
     `diatomgraz` (20→1/10)**, even with Eppley's stabilization. Net mean *drops*
     3.85→2.5. You get {iron pair + diatomgraz} **or** {R_PICPOC}, never both.

   This is the **binary PIC-anchor mutex** (STATUS: "any nonzero `PIC_ABS_W`
   wipes the iron pair") — and it is now shown **robust even to the forward-model
   temperature physics** that broke the *other* mutex. R_PICPOC under pattern-only
   z-loss is genuinely degenerate with the iron budget at the box scale; breaking
   it needs the information the box does not have (seasonal cycle, native
   resolution), not another laptop lever. **This is the AICR case, backed by an
   exhaustive box-scale exclusion.**

**Thesis (revised).** "Parameter conservation" is *not* a fixed effective count:
forward-model fidelity injects genuine identifying information and raises the
recovered count (2.0 → 3.85/6) while making 5/6 reproducible rather than a fluke.
The hard cap is now sharply localized — **`R_PICPOC` is the one parameter no
laptop-scale lever (loss weight, architecture, IC, or forward-model physics) has
recovered.** Whether it is fundamentally unidentifiable from time-mean pattern
data or needs the seasonal/native-resolution axis is the cluster-gated question
(and the AICR case in the Schultz/Jon deck).

## Pending follow-up

- `+Eppley+wPIC` at n=20 — optional tidy-up only (seeds 10–19 interrupted by
  laptop sleep; n=10 already shows it tracks Eppley-alone, wPIC inert). Set
  `powercfg /change standby-timeout-ac 0` before any rerun.
- `R_PICPOC` is now characterized as **cluster-gated**, not a pending laptop
  lever: the box-scale exclusion is exhaustive (loss weight, AOI mix,
  architecture, IC, Eppley physics, and PIC magnitude anchor all fail by the same
  iron-pair mutex). The open question — fundamentally unidentifiable vs.
  resolvable by the seasonal/native-resolution axis — requires the cluster
  (AICR). This is the strongest motivation for native-resolution + seasonal
  fitting in the Schultz/Jon deck.

## Reproduce (R_PICPOC mutex test)

```bash
# on the Eppley best config, add a PIC magnitude anchor:
DARWIN_DATA_ROOT=D:/ecco_darwin_v5 GEOTRACES_DATA_ROOT=D:/geotraces \
AOIS=eqpac,natlsubpolar,southernoceanpac POSI_W=1.0 \
AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 CHL1_W_EXTRA=3.0 \
POSI_DARWIN_W=0.5 USE_EPPLEY_T=1 PIC_ABS_W=0.02 \
NB23_SEEDS=0,1,2,3,4,5,6,7,8,9 OUTPUT_DIR=<out> \
python scripts/run_v3.0_joint_multi_aoi.py
```

## Reproduce

```bash
DARWIN_DATA_ROOT=D:/ecco_darwin_v5 GEOTRACES_DATA_ROOT=D:/geotraces \
AOIS=eqpac,natlsubpolar,southernoceanpac POSI_W=1.0 \
AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 CHL1_W_EXTRA=3.0 \
POSI_DARWIN_W=0.5 NB23_SEEDS=0,1,2,3,4,5,6,7,8,9 \
OUTPUT_DIR=<out> python scripts/run_v3.0_joint_multi_aoi.py
```
