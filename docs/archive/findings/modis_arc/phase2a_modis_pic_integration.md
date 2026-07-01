# Phase 2.A — MODIS-Aqua PIC integration: design + diagnostic

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data stands, framing corrected by [STATUS.md](../../../STATUS.md). The project is a surrogate-to-model identifiability study over **4 observable params**; the growth pair is unobservable by construction. **R_PICPOC is recoverable** with a real calcite anchor (the '6/6 wall / 5/6 ceiling / needs the Darwin port' framing is refuted). The dimensional surrogate gap (box homogenizes) — not calcite physics — is the real limit.


**Status:** Loader + cache built and validated. Integration patch prepared (Section 4 below), pending application after the v3.0 max-lever overnight sweep finishes.

## TL;DR

1. **MODIS-Aqua observes 20× more PIC than Darwin v05 reports in eqpac** (per-cell median ratio 20.7×, mean 52.8×). In natlsubpolar the gap shrinks to 2.8× median. This is a systematic, regime-dependent bias in Darwin v05's PIC field.
2. PR #63's paired-anchor sweep used Darwin v05 PIC as its absolute-magnitude target — fundamentally circular against Carroll-6, and it was pulling R_PICPOC toward Darwin's WRONG magnitude. Cost: alpfe + diatomgraz drifted out of basin A.
3. **MODIS-Aqua L3m PIC v2022.0 is the independent observation that breaks the circularity.** Same Balch-Gordon algorithm Carroll's Green's functions implicitly target, calibrated for coccolithophore assemblages, 2017-2019 climatology aligned exactly with Carroll 2022's calibration window.
4. **Spatial PIC ratio (natl/eqpac):** Darwin v05 = 14.95×; MODIS = 11.12×. The 2-basin diagnostic gradient direction is preserved, but Darwin overstates magnitude by 34%. Combined with the 20× per-cell absolute-magnitude error in eqpac, this gives a quantitative explanation for why PR #63 had to trade alpfe/diatomgraz to get R_PICPOC.

## 1. What was done in Phase 2.A

| Step | Result |
|---|---|
| `pip install earthaccess` | Successful (v0.17.0). Auth via `EARTHDATA_TOKEN` env var works. |
| Search `MODISA_L3m_PIC v2022.0` | Found 23 monthly granules in 2017-2019 at 9km global. |
| Download 2017-2019 monthly 9km | 107 MB total, downloaded in 7 seconds via S3 parallel streams to `D:\modis_aqua_pic\`. |
| Build `src/darwindiff/modis_pic_loader.py` | Mirrors `geotraces_loader` + `ecco_darwin_loader` conventions. Public API: `open_modis_pic`, `open_climatology`, `subset_aoi_modis`, `bin_to_1deg`, `build_aoi_climatology`, `save_aoi_cache`. |
| Build AOI climatology cache | `D:\modis_aqua_pic\modis_pic_clim_2017_2019.npz` — eqpac shape (21, 51) 100% finite, natlsubpolar shape (16, 31) 99.2% finite. **Grid convention matches Darwin v05 exactly** (integer-degree cell centers inclusive of both endpoints, edges at ±0.5°). |
| `scripts/compare_modis_vs_darwin_pic.py` | Quantitative head-to-head against Darwin v05's binned PIC field (read from `D:\ecco_darwin_v5\cache\eqpac_targets_*.pt`). |

## 2. Quantitative findings

All units in mmol C/m³ after MODIS conversion (`mol m⁻³ × 1000 = mmol m⁻³`; one mol calcite is one mol C).

### Per-AOI absolute-magnitude comparison

| AOI | Darwin v05 mean | MODIS mean | Darwin median | MODIS median |
|---|---:|---:|---:|---:|
| **eqpac** | 4.023e-3 | 6.292e-2 | 3.317e-3 | 6.421e-2 |
| **natlsubpolar** | 6.012e-2 | 6.995e-1 | 5.488e-2 | 1.573e-1 |

### Per-cell MODIS / Darwin ratio (where both finite, both positive)

| AOI | n cells | mean ratio | median ratio | p5 | p95 |
|---|---:|---:|---:|---:|---:|
| **eqpac** | 1071 | **52.83×** | **20.67×** | 3.17× | 236.04× |
| **natlsubpolar** | 486 | **10.33×** | **2.82×** | 1.03× | 19.69× |

### The 2-basin spatial diagnostic

| Source | natlsubpolar mean | eqpac mean | natl / eqpac |
|---|---:|---:|---:|
| Darwin v05 | 6.012e-2 | 4.023e-3 | **14.95×** |
| MODIS-Aqua | 6.995e-1 | 6.292e-2 | **11.12×** |

Darwin v05's spatial gradient overshoots MODIS by 34% (= 14.95 / 11.12 - 1). Both agree on direction (natl > eqpac) and both put eqpac in the "low PIC" tail.

## 3. Why this matters for the 5/6 ceiling

PR #63's diagnosis: **paired PIC_ABS + POC_ABS anchors recover R_PICPOC at 5/5 Cal-grade, but at the cost of alpfe + diatomgraz dropping to Drifted.** The mutex was attributed to a 2-basin observation lock-in.

The MODIS comparison reframes this:

1. **The "PIC anchor" PR #63 used wasn't really an anchor against truth — it was an anchor against Darwin v05's particular biases.** Darwin v05 PIC in eqpac is 20× too low vs satellite observation.
2. **R_PICPOC ≈ obs(PIC) / obs(POC) per cell.** If Darwin v05's PIC is too low by 20× in eqpac, the implicit R_PICPOC target is also 20× too low in eqpac. Recovery thus pulled R_PICPOC toward a wrong magnitude — and to do that, the optimizer had to deform alpfe + diatomgraz to compensate.
3. **MODIS-Aqua PIC anchor predicts a 20× larger R_PICPOC target in eqpac.** That's still below Carroll's 0.04245, but much closer to it than the Darwin v05 anchor implied. The alpfe / diatomgraz tradeoff should shrink correspondingly.

This is testable: rerun the PR #63 paired-anchor configuration with MODIS PIC as the target, see if alpfe + diatomgraz survive the recovery basin. That's the Phase 2.A integration sweep (Section 4).

## 4. Integration patch (to apply after the current overnight sweep finishes)

The patch adds `MODIS_PIC_ABS_W` as a parallel knob to `PIC_ABS_W`. Both can be enabled simultaneously, but the intended use is **MODIS_PIC_ABS_W replaces PIC_ABS_W for the next R_PICPOC unlock attempt**.

### 4.1 Changes to `scripts/run_v3.0_joint_multi_aoi.py`

**A. Env-var declaration (near line 270 alongside `PIC_ABS_W`):**

```python
# MODIS-Aqua observed PIC absolute-units MSE loss weight. Uses the cache built
# by src/darwindiff/modis_pic_loader (D:\modis_aqua_pic\modis_pic_clim_2017_2019.npz)
# instead of Darwin v05's internal PIC. The 2017-2019 climatology aligns with
# Carroll 2022's calibration window. See docs/findings/modis_arc/phase2a_modis_pic_integration.md
# for the rationale: Darwin v05 PIC is 20x lower than MODIS-Aqua observed PIC
# in eqpac, making the existing PIC_ABS_W anchor circular against Carroll's
# Green's-functions calibration.
MODIS_PIC_ABS_W = float(os.environ.get("MODIS_PIC_ABS_W", "0.0"))
MODIS_PIC_CACHE_PATH = Path(os.environ.get(
    "MODIS_PIC_CACHE_PATH",
    r"D:\modis_aqua_pic\modis_pic_clim_2017_2019.npz",
))
```

**B. Cache load + per-AOI lookup (in `load_aoi_bundle`, after the existing pic_binned block ~line 450):**

```python
# MODIS-Aqua PIC anchor (independent observation, 2017-2019 climatology).
# Loaded from the precomputed AOI cache; conversion mol/m^3 -> mmol C/m^3.
if MODIS_PIC_ABS_W > 0:
    modis_cache = np.load(MODIS_PIC_CACHE_PATH)
    pic_key = f"pic_{aoi_key}"
    if pic_key not in modis_cache.files:
        raise KeyError(
            f"MODIS PIC cache has no entry for AOI '{aoi_key}'; "
            f"available: {list(modis_cache.files)}"
        )
    modis_pic_mmol_c = modis_cache[pic_key] * 1000.0  # mol/m^3 -> mmol C/m^3
    modis_pic_mask_np = (
        ocean_mask
        & modis_cache[f"mask_{aoi_key}"]
        & np.isfinite(modis_pic_mmol_c)
        & (modis_pic_mmol_c > 0)
    )
    modis_pic_target_np = np.where(modis_pic_mask_np, modis_pic_mmol_c, 0.0).astype(np.float32)
    modis_pic_target_t = torch.tensor(modis_pic_target_np).to(device)
    modis_pic_mask_t = torch.tensor(modis_pic_mask_np, dtype=torch.bool).to(device)
    modis_pic_mask_f = modis_pic_mask_t.to(torch.float32)
    n_modis_pic = int(modis_pic_mask_np.sum())
    n_modis_pic_f = modis_pic_mask_f.sum().clamp(min=1.0)
    print(
        f"  MODIS-Aqua PIC target: {n_modis_pic} cells, "
        f"mean={float(modis_pic_target_t[modis_pic_mask_t].mean()):.4f} mmol C/m^3"
    )
else:
    modis_pic_target_t = torch.zeros_like(pic_abs_target_t)
    modis_pic_mask_t = torch.zeros_like(pic_abs_mask_t)
    modis_pic_mask_f = torch.zeros_like(pic_abs_mask_f)
    n_modis_pic = 0
    n_modis_pic_f = torch.tensor(1.0, device=device)
```

**C. Bundle entries (in the dict around line 742):**

```python
"modis_pic_target_t": modis_pic_target_t,
"modis_pic_mask_t": modis_pic_mask_t,
"modis_pic_mask_f": modis_pic_mask_f,
"n_modis_pic": n_modis_pic,
"n_modis_pic_f": n_modis_pic_f,
```

**D. Loss term in `aoi_loss()` (after the existing PIC_ABS_W block around line 989):**

```python
if MODIS_PIC_ABS_W > 0 and bundle["n_modis_pic"] > 0:
    residual = (pic - bundle["modis_pic_target_t"][None]) * bundle["modis_pic_mask_f"][None]
    scale = (
        bundle["modis_pic_target_t"][bundle["modis_pic_mask_t"]] ** 2
    ).mean().clamp(min=1e-30)
    l = (residual ** 2).sum() / (bundle["n_modis_pic_f"] * scale)
    z = z + MODIS_PIC_ABS_W * l
```

**E. Filename tag (around line 1253):**

```python
modis_pic_tag = f"_modispicW{MODIS_PIC_ABS_W}" if MODIS_PIC_ABS_W > 0 else ""
```

Add `{modis_pic_tag}` to the `out` filename build around line 1276.

**F. Result-row dict (around line 1204):**

```python
"modis_pic_abs_w": MODIS_PIC_ABS_W,
```

### 4.2 Smoke test (after patch is in)

```powershell
$env:MODIS_PIC_ABS_W = "1.0"
$env:PIC_ABS_W = "0.0"       # turn OFF the Darwin v05 PIC anchor
$env:POC_ABS_W = "0.0"       # turn OFF the paired POC anchor for the smoke
$env:POSI_W = "1.0"
$env:NB23_SEEDS = "0"
$env:OUTPUT_DIR = "D:\runs\smoke_modis_pic"
python scripts/run_v3.0_joint_multi_aoi.py
```

Expected wall-clock: ~5 min. Pass criteria: training completes, JSON writes, recovery printout shows the per-parameter joint bands.

### 4.3 First MODIS-anchored sweep

```powershell
$env:MODIS_PIC_ABS_W = "1.0"
$env:POC_ABS_W = "0.25"      # keep POC anchor for the paired-anchor R_PICPOC unlock
$env:POSI_W = "1.0"
$env:NB23_SEEDS = "0,1,2,3,4,5,6,7,8,9"
$env:OUTPUT_DIR = "D:\runs\modis_paired_n10"
python scripts/run_v3.0_joint_multi_aoi.py
```

**Hypothesis:** with MODIS PIC replacing Darwin v05 PIC, R_PICPOC still lands Cal-grade (because the spatial gradient direction is preserved) BUT alpfe + diatomgraz are no longer pulled out (because the per-cell magnitude is now correct). Best case: 5/6 or 6/6 with R_PICPOC + alpfe + diatomgraz all Cal-grade.

If the hypothesis holds, this is the project's first 6/6 path that doesn't require unreleased PACE PIC.

## 5. Risks + open questions

1. **MODIS PIC retrieval uncertainty.** The Balch-Gordon algorithm is known to overestimate PIC in cyanobacteria-dominated regions (eqpac is high-cyanobacteria — Pro + Syn). The 20× MODIS-vs-Darwin ratio in eqpac may partly reflect cyanobacteria-induced backscatter artifacts rather than real coccolithophore PIC. Cross-check with literature would be useful before committing to MODIS as the "truth" anchor.

2. **POC anchor still Darwin v05.** PR #63 paired PIC and POC. If only PIC switches to MODIS but POC stays on Darwin v05, the R_PICPOC = obs(PIC) / obs(POC) anchor is half-circular. Phase 2.A.2 should add a MODIS-Aqua POC anchor (the same v2022.0 collection has POC). 

3. **Time-alignment.** MODIS PIC is 2017-2019 mean. Darwin v05 cache is presumably a different climatology window. The integrator doesn't see "time" — it works on the time-mean field — so this is only a concern if Darwin v05's mean window differs systematically from 2017-2019.

4. **Grid alignment.** Confirmed exact match against Darwin v05's `pic_binned` cache shapes: (21, 51) eqpac, (16, 31) natlsubpolar. ✓

## 6. References

- MODIS-Aqua L3m PIC v2022.0 catalog: <https://www.earthdata.nasa.gov/data/catalog/ob-modis-aqua-l3m-pic-2022.0>
- Balch-Gordon PIC algorithm ATBD: <https://oceancolor.gsfc.nasa.gov/resources/atbd/pic/>
- PR #63 (R_PICPOC paired-anchor unlock + 2-basin diagnosis): in main, commit `014723f`
- `scripts/compare_modis_vs_darwin_pic.py` (this analysis)
- `src/darwindiff/modis_pic_loader.py` (the loader)
- `D:\modis_aqua_pic\modis_pic_clim_2017_2019.npz` (the cache)
