# Surrogate → GCM validation: advancing #163 (2026-07-25)

**Goal ([#163](https://github.com/2imi9/ECCO-DarwinDiff/issues/163)).** The manuscript's Fisher/CRLB
identifiability geometry is a property of the differentiable 0-D surrogate box. It transfers to ECCO-Darwin
**only if** the box's parameter-Jacobian matches the GCM's own sensitivities — above all in the
**cross-parameter ranking** the Fisher eigenstructure is built from. This note does the **surrogate side**
(executable) and **prepares the GCM side** (files + protocol + coordination draft) so the one test that
upgrades the study from *surrogate-conditional* to a *GCM claim* can run. Companion:
[`2026-07-23_v05_perturbation_recipe.md`](2026-07-23_v05_perturbation_recipe.md) (the verified recipe),
[`2026-07-23_surrogate_jacobian_validation.md`](2026-07-23_surrogate_jacobian_validation.md) (why this is the
missing ground truth).

---

## 1. Surrogate side — the log-sensitivity Jacobian through the obs operator

**Committed, reproducible tool:** [`scripts/analysis/surrogate_jacobian_obsop.py`](../../scripts/analysis/surrogate_jacobian_obsop.py).
It computes `S(p,T) = d ln <T>_obs / d ln p` for `p ∈ {alpfe, scav_rat, diatomgraz, R_PICPOC}`, where
`<T>_obs` is the **depth-resolved, AOI-footprint, observation-masked** mean the inverse-problem loss forms
its residuals against (surface DFe on the GEOTRACES surface footprint; subsurface DFe on the sub footprint;
surface PIC on the ocean footprint; the steady-state biogenic-silica diagnostic on the POSi footprint). AOIs
are aggregated by observation-cell count (the footprint/uncertainty weighting the loss uses). Because the
flagship targets are a 23-yr **time mean**, the operator's **phase** axis is degenerate (equilibrated mean) —
stated, not silently dropped. The derivative is a **central FD in log-parameter space at two geometric steps,
s = 1.1 and s = 1.2** — the *same* steps as the GCM recipe, so the two sides are directly comparable, and the
two magnitudes give the nonlinearity/convergence check.

This replaces the 2026-07-23 **scratch** probe (`surrogate_jacobian_validation.md` §3): that was uncommitted,
a single step size (`eps=0.02`), and a plain AOI-mean rather than the obs operator. The committed script is
deterministic (no training, no RNG beyond the fixed IC expansion), so it is `verify_run`-style re-derivable.

### Run status — data-blocked this session (reproduction command provided)

The geo1 box needs the v05 IC/forcing caches **and** GEOTRACES iron, which live on **AICR** (`~/dd_data`,
interactive-only via Duo 2FA). This session confirmed: nothing local (`DARWIN_DATA_ROOT`/`GEOTRACES_DATA_ROOT`
empty, no caches); **Explorer** is reachable but carries only the emulator/daily cubes
(`/scratch/qi.zim/{daily_v5,emulator_global}`), not the box caches or GEOTRACES. So the fresh, verify-gated
**two-step obs-operator** table awaits an AICR run:

```bash
PYTHONPATH=src \
DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5 \
GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces \
GEOTRACES_W=1 GEOTRACES_SUB_W=1 RATIO_MAX=2.0 \
AOIS=eqpac,natlsubpolar,southernoceanpac \
~/dd_venv/bin/python scripts/analysis/surrogate_jacobian_obsop.py \
  --out docs/findings/2026-07-25_surrogate_jacobian_obsop.json
```

### Provisional Jacobian (2026-07-23 scratch — NOT yet the committed two-step number)

From `surrogate_jacobian_validation.md` §3 (single-step `eps=0.02`, cell-weighted AOI mean). Indicative only;
the committed script supersedes it on the next AICR run.

| param ↓ / tracer → | DFe_surf | DFe_sub | diatom | PIC_surf | POC_surf |
|---|---|---|---|---|---|
| **alpfe** | **+0.607** | −0.245 | +1.901 | +0.526 | +0.526 |
| **scav_rat** | **−0.490** | −0.501 | −1.511 | −0.415 | −0.415 |
| **diatomgraz** | +0.021 | +0.018 | **−7.110** | −0.018 | −0.018 |
| **R_PICPOC** | 0.000 | 0.000 | 0.000 | **+1.000** | 0.000 |

Signs are all mechanistically correct (alpfe raises DFe, scav_rat lowers it, diatomgraz lowers diatom biomass,
R_PICPOC raises PIC) — **but guaranteed by construction** (the box reuses Darwin's own source/sink forms), so
sign agreement is *not* the independent test. Magnitude and ranking are the surrogate quantities to validate.

## 2. The load-bearing test — the sensitivity RANKING (item 4)

The Fisher transfer is licensed by the **cross-parameter ranking by sensitivity-to-own-observable**, not by
signs (which agree by construction) and not by any single magnitude. Natural own-observable pairing:

| rank | param → own observable | \|S_own\| (provisional §3) |
|---|---|---|
| 1 | **diatomgraz → diatom biomass** | **7.11** |
| 2 | **R_PICPOC → PIC** | **1.00** (exactly unity: `dPIC = R_PICPOC·mort`, linear + decoupled) |
| 3 | **alpfe → DFe_surf** | **0.61** |
| 4 | **scav_rat → DFe_surf** | **0.49** |

**Surrogate ranking: `diatomgraz ≫ R_PICPOC > alpfe > scav_rat`** — matches the expected ordering exactly
(the committed script asserts this and re-derives it at both step sizes). **Only if the GCM's ranking matches
this** does transferring the surrogate Fisher eigenstructure (sloppy/stiff directions, the EKI
reparameterization) to ECCO-Darwin become licensed.

- **Surrogate side: ranking ready** (provisional confirmed; committed two-step recompute pending the AICR run).
- **GCM side: pending** the perturbation ensemble prepared in §3.
- **Caution (from the recipe):** raw sensitivity ≠ identifiability. diatomgraz is the *stiffest* box parameter
  yet the manuscript's *data-blocked* one — the bSi/biomass observable routes through the model's own diatom
  biomass, which compensates. The ranking is what must transfer; the Fisher (which folds in the observation
  footprint), not the raw Jacobian, is the object of the claim.

## 3. GCM side — prepared, not launched

**Generator (tested):** [`scripts/perturbation/make_v05_oat_ensemble.py`](../../scripts/perturbation/make_v05_oat_ensemble.py)
writes the **17 decks** (control + 4 params × {÷1.2, ÷1.1, ×1.1, ×1.2}). It edits the file the model actually
reads (`data.darwin` ALPFE/SCAV_RAT; `data.traits` R_PICPOC array + PALAT entries 36 & 43), applies each edit
by literal token replacement scoped to the correct namelist line, and **aborts on any ambiguity** — it never
writes a deck it could not verify. Tested against a synthetic v05 fixture: all 17 edits land, and one-knob
isolation holds (a scav_rat deck's R_PICPOC stays at control).

**Load protocol (tested):** [`scripts/perturbation/verify_perturbation_loaded.sh`](../../scripts/perturbation/verify_perturbation_loaded.sh)
greps a run's `STDOUT.0000` for the override path (`opening data.traits`) and the **effective** `&DARWIN_*`
echo, and asserts the perturbed value loaded — **and, for R_PICPOC/diatomgraz, that the frozen original
(0.0418860) and the inert generation scalar (0.04245) are NOT what loaded.** Verified to catch the exact
silent-failure mode (a deck that edits the wrong file passes a naive file check but fails this one).

### The 17-deck manifest (exact values, computed from p0 — not transcribed)

| run | file | effective change |
|---|---|---|
| control | — | Carroll optimum (reuse the existing baseline) |
| alpfe_d1.2 / d1.1 / x1.1 / x1.2 | data.darwin | ALPFE = 0.773592 / **0.843918** / 1.021141 / 1.113972 |
| scav_rat_d1.2 / d1.1 / x1.1 / x1.2 | data.darwin | SCAV_RAT = 5.020853E-7 / 5.477294E-7 / 6.627525E-7 / 7.230028E-7 |
| R_PICPOC_d1.2 / d1.1 / x1.1 / x1.2 | data.traits | R_PICPOC(2:3) = 0.0349050 / 0.0380782 / 0.0460746 / 0.0502632 |
| diatomgraz_d1.2 / d1.1 / x1.1 / x1.2 | data.traits | PALAT(36,43) scaled: (0.140955,0.704775)/(0.153769,0.768845)/(0.186061,0.930303)/(0.202975,**1.014876**) |

**Two corrections to the recipe surfaced by computing from p0:**
1. **`alpfe ÷1.1` = 0.843918, not the recipe table's 0.844100** (0.92831/1.1 = 0.843918; the table entry was a
   transcription slip). The generator derives from p0, so it is correct; the recipe table should be fixed.
2. **`diatomgraz ×1.2` sends PALAT(43) to 1.014876 > 1.0.** Palatability is conventionally ≤ 1 — confirm Darwin
   does not clamp/renormalize (which would corrupt the FD), or cap that run at 1.0, or lean on the ±10% slope.
   The generator prints this warning.

## 3.5 Explorer self-run feasibility — VERIFIED 2026-07-25 (we do NOT need to request more)

Live read-only checks on Explorer (`ssh explorer`), correcting an earlier "needs NASA + Jon / compute-blocked"
assumption. The GCM ensemble can run on **Northeastern's Explorer**, resources in hand:

| resource | status | evidence (measured 2026-07-25) |
|---|---|---|
| Compute | ✅ in hand, no request | `short` partition: **231 CPU nodes, 20+ cores each, 2-day limit**; account **c.schultz** (normal QOS). An ~800-core llc270 run fits comfortably. |
| Build stack | ✅ present | `intel/compilers-2025.0.4`, `intel/mpi-2021.14`, `intel/mkl-2025.0`, `netcdf/4.9.3-intel`, `HDF5/1.14.6`. Needs an Explorer optfile adapted from the NAS `linux_amd64_ifort+mpi`. |
| Storage | ✅ ample on **/scratch** | `/scratch` = **1.9 PB, 810 TB free** (VAST) — stage inputs here. |
| Inputs | ✅ public + reachable | `data.nas.nasa.gov/ecco/eccodata/llc_270/` and `.../iter42/input/` return **HTTP 200 from Explorer**. No auth, no request. |

**Corrections to the optimistic earlier read (so nobody plans against wrong numbers):**
- `/projects/schultz` is **36 TB total, 8.2 TB free** — *not* "3.3 PB". The large filesystem is **/scratch (810 TB free)**; stage the TBs of ECCO input there, not /projects.
- "Home 111 TB free" is the *shared* `/home` filesystem free space (255 TB VAST), **not** a personal quota — do not rely on it for TB staging.

**Verdict: no new allocation or data request is needed.** Self-running the 17-run v05 ensemble on Explorer is
gated by our own setup effort (build an optfile → stage inputs to /scratch → reproduce + validate the baseline
from the v5 pickup → run the 17 short segments), not by permission or hardware. So Jon becomes an *optional*
courtesy + one real question (any gotchas reproducing the v5 baseline from the pickup), not a compute favor.

**Caveat to size at benchmark time:** the `short` partition mixes interconnects (10 GbE and InfiniBand). Before
scaling MPI to ~800 ranks, confirm the nodes carry InfiniBand and run **1 baseline + 1 perturbation first**.

> Note: this is the **GCM** feasibility. The *surrogate* Jacobian (§1) is a tiny torch job — Explorer CPU is
> far more than enough; it was only ever blocked on the geo1 `.pt` caches + GEOTRACES living on AICR, which can
> be rebuilt/staged on Explorer from the same public v05 + GEOTRACES sources, or run in one AICR Duo session.

## 4. Coordination — draft only (now optional)

[`2026-07-25_jon_gcm_ensemble_ask_DRAFT.md`](2026-07-25_jon_gcm_ensemble_ask_DRAFT.md) — **not sent.** Given §3.5,
the strongest framing gives Jon the *choice* (we can run it on Explorer, or he can), rather than handing him
work. It proposes benchmarking 1 baseline + 1 perturbation first, ≥2 symmetric FD steps, identical
checkpoints/forcing/averaging, convergence-with-integration-length, and central differences (adjoint returns
Jᵀr, not the Jacobian). Neutral and warm.

## 5. Guardrail — stay on v05

v06 ≠ v05: iron scavenging is reformulated (`SCAV_RAT` rate → `scav_tau` + per-particle-class weights), growth/
palatability/R_PICPOC become group-specific with a different array layout, and a **third iron source**
(hydrothermal vents) is added that could shift or break the alpfe/scav_rat degeneracy the story rests on. A v06
rerun is **not** a replication without an explicit physical mapping. Validate on v05; treat v06 as a monitored
moving target.

## Provenance / status
- Surrogate script + generator + protocol: **committed here**, compile-checked; generator and protocol
  **functionally tested** against synthetic fixtures (edit isolation + silent-failure detection both pass).
- Surrogate two-step obs-operator Jacobian: **run-blocked** on AICR data access this session; command above.
- Provisional Jacobian/ranking: 2026-07-23 scratch (`surrogate_jacobian_validation.md` §3), **not** verify-gated.
- No GCM runs launched; no message sent; nothing under `docs/paper/` touched.
