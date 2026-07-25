# Prognostic dissolved-SiO2 in the 0-D box — feasibility + diatomgraz identifiability prototype (2026-07-23)

**Trigger.** A domain expert corrected a DarwinDiff claim: our statement that "`diatomgraz` is only
observable through a circular biogenic-silica steady-state diagnostic" is a **surrogate artifact**.
ECCO-Darwin v05 already carries prognostic dissolved SiO2 with Si-limited diatoms; our reduced 0-D box
(`carroll6_5pft_2layer`) **dropped that tracer** and replaced it with an algebraic back-solve
(`silica.diagnostic_bsi_steady`). The claim under test: adding prognostic SiO2 + Si-limitation would
remove the artificial rank deficiency for `diatomgraz`.

**Scope.** Feasibility + a self-contained prototype. Nothing in production was modified. Deliverables
are this doc and `scripts/analysis/box_silica_prototype.py` (a throwaway standalone box; imports only
the *background constants* from production, changes no default behaviour). No scoreboard change from
this prototype: `diatomgraz` is unchanged by it; separately it now recovers **35/50 per-AOI with the bSi
target off** (chlorophyll + MLD), i.e. from a non-circular but still *model-internal* observable, not
from independent real data (issue #152).

---

## Bottom line (the 4-sentence answer)

1. **The box silica fix is straightforward-but-not-free (~2-3 days + revalidation):** the diatom Si
   uptake, a Michaelis-Menten `f_Si` on diatom growth, and a bSi→SiO2 dissolution return are ~40 lines
   in a new 17-tracer step function, and the initial condition is *already in the same Darwin pickup*
   (SiO2 = record 6, POSi = record 15) — but it invalidates every 15-tracer `darwin_ic_cache_*.npz` and
   turns every prior 2-layer recovery number into "a different model's number," so it is a follow-on, not
   a flag flip.
2. **Prognostic Si does NOT, by itself, fix `diatomgraz` identifiability:** in the prototype, the Si
   observables *alone* (dissolved SiO2 + prognostic bSi, no biomass) constrain `diatomgraz` only through
   the diatom **turnover flux**, which is confounded with diatom **growth** — the profile well is ~16×
   shallower than when biomass is co-observed, and the best-fit growth rate slides monotonically with
   `diatomgraz` (the growth-grazing ridge).
3. **Given the biomass channel we already have, prognostic Si is at PARITY with the circular bSi
   diagnostic** — identical profile curvature and identical growth-grazing ridge (rel_span 3.36 vs 3.31)
   — so the honest gain is *qualitative* (a genuine, independently-measurable tracer instead of a
   back-solve from the model's own biomass) plus access to ~630× more real observations (6,968 in-AOI
   GLODAP silicate bottles vs 11 bSi), **not** a better-conditioned `diatomgraz` profile.
4. **This is exactly caveat 4:** even with prognostic SiO2, the steady SiO2/bSi balance confounds
   uptake / growth / grazing / sinking / dissolution, so it does not identify `diatomgraz` *alone* — it
   identifies it only in combination with the biomass (Chl) observable and fixed dissolution/supply, the
   same combination the current diagnostic already relies on.

---

## 1. How the current box handles silica

### 1.1 The 15-tracer state vector (`carroll6_5pft_2layer.py:104-124`)

Two layers, biology in L1 only:

```
L1 (surface, 0-50 m):   [0]DFe_1 [1]P_diatom [2]P_lge [3]P_syn [4]P_proLL [5]P_proHL
                        [6]POC_1 [7]PIC_1 [8]DIC_1 [9]ALK_1
L2 (subsurface, 50-1000 m): [10]DFe_2 [11]POC_2 [12]PIC_2 [13]DIC_2 [14]ALK_2
N_TRACERS_2LAYER = 15
```

**There is no dissolved-SiO2 state and no particulate bSi state.** Silica exists only as a *diagnostic*.

### 1.2 The diatom growth term (`carroll6_5pft_2layer.py:389`)

```python
growth_diatom = MU_DEFAULT_DIATOM * f_fe * LIGHT * gamma_T * P_diatom
#   f_fe = DFe_1/(DFe_1+K_FE)   (iron limitation, shared K_FE)
#   gamma_T = optional Eppley multiplier (USE_EPPLEY_T)
#   MU_DEFAULT_DIATOM = 0.43148 (FIXED; diatoms have no learned growth rate)
```

There is **no Si-limitation factor**. Diatoms are limited only by iron and light. `diatomgraz` enters
the diatom budget *only* through the grazing loss `graze_diatom = g_diatom * G0_GRAZE * P_diatom`
(`:405`, `:458`). This is the single point where a `f_Si` factor would be inserted (min-law), and Si
uptake/return terms would be added to the tendency block.

### 1.3 The current silica "observable" is a circular diagnostic (`silica.py:78-109`)

`diagnostic_bsi_steady` **algebraically back-solves** bSi from the model's own diatom biomass:

```
bSi_1 = R_SI_C * (mort_diatom + graze_diatom) / W_SINK
      = R_SI_C * (M_LIN·P + M_QUAD·P² + diatomgraz·G0·P) / W_SINK
```

`silica.py:10-17` documents this as a deliberate cost decision (a 15→17 tracer extension would
invalidate every IC cache). The consequence: **`diatomgraz` enters the observation operator itself**,
not an independent tracer — the constraint is partly *definitional* rather than *dynamical*. The runner
(`run_v3.0_joint_multi_aoi.py:227,496,503`) drives two losses off this diagnostic: `POSI_W` (sparse
GEOTRACES bSi bottles) and `POSI_DARWIN_W` (Darwin's own dense POSi/TRAC16 field). Our own reviewer
panel (M11) and the 2026-07-19 audit both flagged this as circular; that is the real issue this
prototype addresses.

---

## 2. What a prognostic-Si extension requires (specific code changes)

The physics to add: (a) a dissolved-SiO2 tracer, (b) a Michaelis-Menten `f_Si = SiO2/(SiO2+K_SI)`
folded into diatom growth by a Liebig **min-law** with the existing Fe/light limitation, (c) a bSi pool
that is produced by diatom mortality+grazing, sinks, and dissolves back to SiO2.

| # | Change | Location | Cost | Risk |
|---|---|---|---|---|
| 1 | New tracers `SiO2_1, bSi_1` (L1) + `SiO2_2` (L2); `N_TRACERS_2LAYER` 15→17 (or 18 w/ `bSi_2`). New index constants. | `carroll6_5pft_2layer.py:104-124` | ~0.5 d | Changes state length everywhere |
| 2 | `f_si = SiO2_1/(SiO2_1+K_SI)`; `growth_diatom = MU_DEFAULT_DIATOM * min(f_fe, f_si) * LIGHT * gamma_T * P_diatom` (diatom ONLY; other 4 PFTs unchanged) | `:389` | ~1 line | **Changes the forward model** → all prior recovery numbers are a different model's |
| 3 | New tendencies: `dSiO2_1 = supply(SiO2_2−SiO2_1) − R_SI_C·growth_diatom + R_SI_DISSOL·bSi_1`; `dbSi_1 = R_SI_C·(mort_diatom+graze_diatom) − R_SI_DISSOL·bSi_1 − W_SINK·bSi_1`; L2 return term. Reuse the existing `Kz` eddy-diffusion path for the SiO2 supply. `R_SI_C, R_SI_DISSOL` already exist in `silica.py`. | `:410-530` | ~0.5 d | Adds a new supply constant `SIO2_DEEP`/`K_SI` to pin |
| 4 | Add the 2-3 tracers to the `torch.stack` in `_step` and thread through `_integrate` / `_integrate_seasonal` signatures | `:532-717` | ~0.5 d | Low |
| 5 | Gate the whole thing behind a **separate step function / box module** selected by an env flag (like `USE_EPPLEY_T`), so the 15-tracer default path stays **bitwise identical**. A flag that changes the state length is cleaner as a sibling module than an in-place branch. | new `carroll6_5pft_2layer_si.py` | ~0.5 d | Preserves the SST-only default |
| 6 | IC cache: add `"SiO2": 6` and `"POSi": 15` to `INORGANIC_TRACERS` — **the data is already in the same pickup** (`pTr07`=SiO2, `pTr16`=POSi). Build new 17-tracer caches (do NOT overwrite the 15-tracer ones). | `build_darwin_ic_cache.py:62-68` | ~2 lines + rebuild | **Invalidates 15-tracer `darwin_ic_cache_*.npz`** |
| 7 | Target caches + a new `SIO2_W` loss vs the *prognostic* dissolved SiO2 (real GLODAP bottles); keep `POSI_W`/`POSI_DARWIN_W` but point them at the real `state[I_BSI_1]` tracer instead of the diagnostic | `run_v3.0_joint_multi_aoi.py:488-503,1150-1165` | ~0.5 d | Low |
| 8 | GLODAPv3 **bottle** silicate loader (currently only the gridded climatology is read; the map `"Si"→"silicate"` already exists). 6,968 in-AOI ≤50 m QC-good bottles verified present. | new in `glodap_loader.py` | ~0.5 d | Low (data verified) |
| 9 | Extend tests for the 17-tracer path; assert the 15-tracer path is bitwise unchanged. Downstream 15-hardcodes (`seasonal.py`, `e2s/`, emulator channels, ~30 files ref tracer counts) need conditional handling. | `tests/`, `seasonal.py`, `e2s/` | ~0.5 d | Medium (blast radius) |

**Total ≈ 2-3 days of forward-model work + cache rebuild + a real-data loader, then full revalidation of
every 2-layer recovery number** (item 2 changes the model). Matches the earlier 2026-07-19 scoping
estimate. It is a scientific scope change, not a flag flip — but the single most reassuring fact is #6:
the reduced box *dropped* SiO2/POSi that are sitting in the same pickup, so the IC comes free.

---

## 3. Prototype + results (`scripts/analysis/box_silica_prototype.py`)

A self-contained 0-D box `[DFe, P_diatom, P_small, POC, SiO2, bSi]` with a `prognostic_si` switch:
`True` = Si-limited diatoms + prognostic SiO2/bSi tracers; `False` = LEGACY (no Si-limitation, bSi is
the algebraic `diagnostic_bsi_steady` form). Synthetic self-recovery, forward-only grid search (the
parameter space is 1-2 D, so this avoids the profile/θ\* optimiser artifact that contaminated the
2026-07-19 real-data runs). Truth: `diatomgraz = 0.830` (Carroll), diatom growth `mu_d = 0.80` set in a
**diatom-favorable regime** (Carroll's `mu_d = 0.431` puts a single global-mean box at the diatom
extinction edge, `P_diatom ≈ 0.05`, which makes the biomass hypersensitive; the conclusions are
unchanged at `mu_d` 0.65 and 0.90). At truth: `SiO2 = 4.43`, `f_si = 0.689 < f_fe = 0.730` → **Si is the
active limitation**, `P_diatom = 0.504` (healthy).

**Exp A — feasibility + self-recovery (diatom growth FIXED, as in the prod box).** 1-D profile
`L(diatomgraz)`, argmin should land on truth.

| arm | argmin (true 0.830) | rel_span | verdict |
|---|---|---|---|
| LEGACY (biomass + circular bSi diagnostic) | 0.829 | 3.51 | RECOVERED |
| PROGNOSTIC (biomass + SiO2 + prognostic bSi) | 0.829 | 3.43 | RECOVERED |

→ The prognostic-Si box **works and is not worse** than the diagnostic. Feasibility confirmed.

**Exp B — caveat 4: does the Si observable ALONE identify `diatomgraz`?** Profile `diatomgraz` with the
diatom **growth** rate `mu_d` marginalised (min over a nuisance grid). Report the well depth (max grid
loss) and the best-fit `mu_d` at each grid point.

| observable set | argmin | well depth (max loss) | best-fit `mu_d` across grid |
|---|---|---|---|
| Si **only** (SiO2 + prognostic bSi, NO biomass) | 0.83 | **0.0046** | 0.60 → 0.85 (rises with diatomgraz) |
| Si **+ biomass** (SiO2 + bSi + P_diatom/POC) | 0.83 | **0.0732** (~16× deeper) | 0.55 → 0.85 |

→ Si observables alone put the minimum nominally at truth, **but the well is ~16× shallower** than with
biomass — a shallow constraint that real noise/sparsity would wash out. The monotone best-`mu_d` slide
(0.60→0.85) is the **growth-grazing compensation ridge**: assume more grazing, need more growth to hold
the same steady flux. The identifying power is carried by the **biomass** channel, not by Si.

**Exp C — head-to-head with biomass, growth marginalised (the real config's comparison).**

| arm | rel_span | well depth (max loss) | best-fit `mu_d` ridge |
|---|---|---|---|
| LEGACY (biomass + circular bSi diagnostic) | 3.31 | 0.0653 | 0.55 → 0.85 |
| PROGNOSTIC (biomass + SiO2 + prognostic bSi) | 3.36 | 0.0732 | 0.55 → 0.85 |

→ **Parity.** Given the biomass observable we already use, the circular diagnostic and the genuine
prognostic tracers produce essentially the same profile and the same ridge. Prognostic Si is not a
curvature win here; it is a *defensibility* win.

---

## 4. Honest caveat + verdict

**Why Si does not identify `diatomgraz` alone (caveat 4, confirmed).** All three Si observables — the
diagnostic bSi, the prognostic bSi, and dissolved SiO2 — are set by the diatom **turnover flux**
(`mort_diatom + graze_diatom`, which equals `growth_diatom` at steady state). At fixed biomass this flux
minus the known mortality pins `graze_diatom`, hence `diatomgraz` — that is why the box *can* self-recover
it. But the flux is equally a function of the growth rate, the Si:C ratio `R_SI_C`, the dissolution rate
`R_SI_DISSOL`, and the SiO2 supply; once growth is free, `diatomgraz` and `mu_d` trade off along a ridge,
and the standing SiO2/bSi confounds uptake / growth / grazing / sinking / dissolution exactly as stated.
Prognostic Si re-expresses the same flux constraint as a *genuine, independently measurable* tracer
(removing the "back-solved from the model's own biomass" circularity and unlocking ~630× more real
observations), but it adds **no constraint on `diatomgraz` orthogonal to biomass + turnover**.

**Verdict.** The box silica fix is a tractable ~2-3-day forward-model change with a free IC, and it is
worth doing to retire the circularity criticism and ingest real GLODAP silicate — **but it should not be
sold as the fix for `diatomgraz` identifiability**. On its own it does not separate `diatomgraz` from
diatom growth; the identifiability still comes from co-observing biomass (Chl) with the Si turnover, the
same combination the current diagnostic already exploits. `diatomgraz` is nonetheless recoverable without
any bSi target — 35/50 per-AOI at n=50 with `POSI_W=0`, through chlorophyll + MLD
([`2026-07-23_overnight_recovery_sweep_groupA.md`](2026-07-23_overnight_recovery_sweep_groupA.md) LEAD B) —
so the honest statement is *recoverable from a non-circular model-internal observable, not recovered from
independent real data*. The SST-only ~4/10 is the no-MLD baseline, not a ceiling; structural-vs-practical
is closer to resolved (#152).

---

## Reproduce

```bash
# CPU, ~3 min, no cluster (0-D box). Nothing in production is touched.
python scripts/analysis/box_silica_prototype.py --json /tmp/box_silica_results.json
```

Constants (`box_silica_prototype.py`): `K_SI=2.0`, `SIO2_DEEP=6.0`, `KAPPA_SI=0.02`; `R_SI_C=0.13`,
`R_SI_DISSOL=0.015` (from `silica.py`); truth `diatomgraz=0.830`, `mu_d=0.80`. Real silicate inventory
(6,968 in-AOI ≤50 m bottles vs 11 bSi) is counted in
`docs/findings/2026-07-19_silicate_observable_scope.md` §4.1.
