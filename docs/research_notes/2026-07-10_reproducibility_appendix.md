# Reproducibility appendix — Track-2 identifiability-limits map (2026-07-10)

Companion to [`2026-07-09_track2_identifiability_writeup.md`](2026-07-09_track2_identifiability_writeup.md).
Pins the exact data, code, and software behind every number in the map, so each result is
third-party rebuildable. Addresses issue [#117](https://github.com/2imi9/ECCO-DarwinDiff/issues/117)
and the reviewer panel's R6 (reproducibility) objections.

**Code state.** Branch `2imi9/status-handoff-2026-07-07`, HEAD `697c0cf` (this appendix pins results
to the commit that produced each). The branch is **not yet merged to `main`** — a known
reproducibility gap; merge before submission.

**Software.** Python 3.11.9; torch 2.11.0+cu128, numpy 2.3.5, scipy 1.16.0, scikit-learn 1.7.0,
pandas 2.2.3. All identifiability numbers here run **CPU-only** (`CUDA_VISIBLE_DEVICES=-1`); no GPU
or cluster is needed to reproduce the map (the transport-UDE E2, which did not contribute to any
verdict, is the only GPU piece).

## Input datasets (all gitignored — too large / redistribution-restricted)

| dataset | version / accession | DOI or source | local path | size | sha256[:16] |
|---|---|---|---|---|---|
| GLODAP bottle carbonate (in-situ Ω) | GLODAPv3, NCEI **0315582** (2026) | 10.25921/m6tp-mj50 · [data dir](https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0315582/) | `D:\glodap\GLODAPv3_Pacific_Ocean.csv` | 380 MB | `c09ff030f84f98ee` |
| " (Atlantic) | " | " | `D:\glodap\GLODAPv3_Atlantic_Ocean.csv` | 351 MB | `25d30703ed865326` |
| GLODAPv3 QC / adjustment method (provenance) | Humphreys et al. 2026 | 10.5194/egusphere-2026-3063 | — (citation only) | — | — |
| Calcite rain ratio (Daniels) | Daniels et al. 2018 | PANGAEA **888182** | `data/daniels/Daniels_etal_2018_PANGAEA_888182.tab` | <1 MB | `bc36ee8141deea22` |
| Calcite rain ratio (Marsh, denser high-lat) | Marsh et al. 2025 | (Poulton/Daniels successor) | `data/marsh/Marsh_etal_2025_coccolith_calcification.tab` | <1 MB | `7c3fd3a47dd803d8` |
| Dissolved / particulate iron | GEOTRACES **IDP2025** | idp2025 seawater | `D:\geotraces\GEOTRACES_IDP2025_Seawater.nc` | 62 MB | `9dc525e02c74d12f` |
| ECCO-Darwin v05 env cache (DIC/ALK/T/S/POC/PIC/Chl per PFT) | v05, per-AOI 1° | NAS ECCO portal | `D:\ecco_darwin_v5\cache\eqpac_targets_*.pt` | ~1 MB ea | `c6b1c6b1024f9c47` (eqpac) |
| v05 soluble-iron dust forcing (DB-1) | Mahowald 2009, LLC270 | NAS `input/darwin_forcing/` | `D:\ecco_darwin_v5\input\llc270_Mahowald_2009_soluble_iron_dust.bin` | 46 MB | (see DB-1 note) |
| v05 velocity (DB-2) | v05 `uVel_C`/`vVel_C` | NAS `output/monthly/` | `D:\ecco_darwin_v5\...` | (native) | — |

External literature corroboration (citation only): Marañón et al. 2016 (L&O 61:1345; tropical
calcification ≈ Ω-independent); Tagliabue et al. 2016 (iron concentration under-determines the
scavenging rate).

## Findings → producing script → commit

| result | findings artifact | script | commit |
|---|---|---|---|
| calcite null, independent in-situ Ω | `docs/findings/calcite_omega_glodap_marsh.json` | `scripts/glodap_omega_calcite.py` | `3e5455e` |
| calcite null, cache Ω (Daniels + Marsh) | `docs/findings/calcite_omega_identifiability_real*.json` | `scripts/calcite_omega_identifiability_real.py` | `a7a1634` / `798451f` |
| calcite: no driver (SST/composition) rescues it | `docs/findings/calcite_driver_scout_marsh.json` | `scripts/calcite_driver_scout.py` | `f8b9654` |
| iron partitioning is a construction artifact (corrected) | `docs/findings/2026-07-10_iron_partitioning_breaks_the_wall.md` | `scripts/iron_partitioning_scout.py` + `iron_partitioning_controls.py` | `f99a470` / `8d9b0c2` |
| iron scav_rat unidentifiable from DFe (32× wall) | (printed; bundle-driven) | `scripts/iron_scav_rat_profile.py` | (pre-branch) |
| growth pair not split by total NPP | (printed) | `scripts/growth_npp_scout.py` | `04e43e4` |
| make-or-break transport E2 → negative (calcite) | `docs/findings/2026-07-10_e2_powered_result.md` | `scripts/e2_real_calcite_eqpac.py` | `aa0cc1b` |
| symbolic-distillation oracle (method + tests) | 22 tests | `scripts/symbolic_distill_probe.py`, `tests/test_symbolic_distill.py` | `c12fbf7` / `c4b8508` |

**Known artifact gap (R6-1):** the supporting iron statement "DFe concentration is env-predictable
(global Ω hold-out +0.14, p≈0)" was produced pre-branch by `scripts/geotraces_glodap_identifiability.py`
against the **GLODAPv2.2016b mapped** OmegaC climatology, which is no longer staged (superseded here by
GLODAPv3 bottle data). Its JSON is not committed. This number is *supporting* (it shows concentration
carries env signal), **not** load-bearing for the wall itself (the wall is the 32× flat scav_rat
profile from `iron_scav_rat_profile.py`). To restore it, either re-stage GLODAPv2.2016b or adapt the
script to GLODAPv3; until then it should be cited as "prior-analysis, pending regeneration."

## Reproduce the headline results (CPU, from staged data)

```bash
# calcite null on independent in-situ Omega (GLODAPv3)
CUDA_VISIBLE_DEVICES=-1 python scripts/glodap_omega_calcite.py --source marsh
# calcite null is not Omega-specific (SST / composition tested)
CUDA_VISIBLE_DEVICES=-1 python scripts/calcite_driver_scout.py --source marsh
# calcite cache-Omega oracle (Daniels + Marsh)
CUDA_VISIBLE_DEVICES=-1 python scripts/calcite_omega_identifiability_real.py --source marsh
# growth pair not split by total NPP  (needs the iron bundle; see iron_scav_rat_profile --build-bundle)
CUDA_VISIBLE_DEVICES=-1 python scripts/growth_npp_scout.py --bundle <bundle.pt>
# the distillation oracle itself (self-tests, no data)
CUDA_VISIBLE_DEVICES=-1 python -m pytest tests/test_symbolic_distill.py -q
```

The `iron_*` and `growth_npp` scouts read a small AOI input **bundle**
(`python scripts/iron_scav_rat_profile.py --build-bundle <path>`, built once on CPU from the native
data) so the sweeps never touch the ~TB native tree — the data-discipline pattern.

## Open reproducibility items (before submission)

1. Merge `2imi9/status-handoff-2026-07-07` → `main` (code currently on an unmerged branch).
2. Regenerate + commit the iron env-predictability JSON (GLODAPv3-adapted), or drop the +0.14 claim.
3. The make-or-break **out-of-sample transport E2 was run** for calcite (commit `aa0cc1b`) and
   returns a decisive negative (learned closure does not beat the constant-through-transport null;
   K_num non-discriminating). It has *not* been run for iron/growth (argued from their own
   diagnostics). A cleanly *powered* within-region E2 is structurally impossible (the Ω-band hold-out
   becomes a between-biome extrapolation when pooled), so the calcite E2 is a decisive negative at
   n_val = 6, not a high-n rejection.
