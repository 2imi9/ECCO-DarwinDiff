# DarwinDiff — Start Here (onboarding basement)

*A cold-read orientation for a new collaborator. Read this before STATUS.md. It tells you what the
project is, what it deliberately is **not**, and the handful of ideas you must hold in your head to
follow any result. Live numbers live in [STATUS.md](../STATUS.md) (verify_run-gated, they move); this
page is boundaries and vocabulary, which do not.*

## 1. The one-paragraph scope statement (read this twice)

ECCO-Darwin calibrates its ocean biogeochemistry (BGC) with **Green's functions** — a method that needs
a fresh full model run per parameter, so the published calibration tunes only **6** of the model's ~100
tunable BGC knobs. DarwinDiff replaces *that 6-parameter calibration step* with gradient descent through
a small **differentiable box model**, predicting the six values **per grid cell** from the local
environment instead of one global scalar each. That is the entire contribution surface.

**What this project does NOT do, stated plainly so you do not over-read it:**

- It does **not** re-implement or replace ECCO-Darwin. It touches only the biogeochemistry
  **source-minus-sink (SMS) kernel** (`darwin_plankton.F` in Darwin) as a differentiable proxy. Physics,
  transport, mixing, and dust/river forcing are all **inherited from v05 as-is** and never learned.
- It addresses **6 of ~103** independent tunable Darwin scalars (~5.8%). The other ~94% sit at
  literature defaults, held fixed. This is a *slice*, not the model.
- It is a **surrogate 0-D box** (5 tracers), not the full 39-tracer GCM. See the surrogate gap (§4).
- It is a **consistency check against Carroll's own published values**, **not** a cross-validated
  discovery. Held-out real-data R² is negative (§4). Do not describe it as "learning real biology" or
  "replacing Green's functions" without the "consistency-check" qualifier.

If you can restate those four bullets in your own words, you understand the scope.

## 2. The Carroll-6 parameters and the observable/unobservable split

The six parameters are declared once in `src/darwindiff/carroll6.py` (the `PARAMS` registry — read them
by name via `P.<name>`, never by position; the order is load-bearing):

| # | Name | Role | Carroll value | Observable? |
|---|---|---|---|---|
| 1 | `alpfe` | scalar on already-soluble Fe flux (≈1; **NOT a solubility**) | 0.92831 | ✅ observable |
| 2 | `scav_rat` | iron scavenging rate (s⁻¹) | 6.025e-7 | ✅ observable (the binding leg) |
| 3 | `Smallgrow` | small-phyto growth rate (d⁻¹) | 0.66098 | ❌ unobservable* |
| 4 | `Biggrow` | large-phyto growth rate (d⁻¹) | 0.43148 | ❌ unobservable |
| 5 | `diatomgraz` | diatom palatability (–) | 0.83003 | ✅ observable (input-limited) |
| 6 | `R_PICPOC` | PIC/POC production ratio (–) | 0.04245 | ✅ observable (needs a real calcite anchor) |

**The honest denominator is 4, not 6.** The growth pair {`Smallgrow`, `Biggrow`} is **excluded by
construction** — no time-mean observable constrains phytoplankton growth rates (total NPP gives only the
biomass-weighted mean, leaving the pair degenerate). This is *not* a failed recovery; it is a correct
identifiability statement. **"6/6" is the wrong frame** and the project deliberately does not chase it.
(*Nuance: a seasonal prototype recovers `Smallgrow` in strong-bloom basins — North Atlantic 9/10,
unconfirmed; `Biggrow` never recovers.)

## 3. The box surrogate (what actually runs)

A per-cell network `env → 6 Carroll-6 params`, trained by backprop through a differentiable box:

```
per-cell env (SST[, MLD, wind, lat]) ─▶ DINN ─▶ 6 raw ─▶ sigmoid bounds ─▶ Carroll-6 per cell
                                                                                   │
                                     differentiable 5-tracer box (carroll6 step)   ▼
                                     [DFe, P_small, P_large, POC, PIC] (+DIC, ALK carbonate ext.)
                                                                                   │
                                        predicted fields ── compare ── v05 target / real obs ── loss
                                                                                   │
                                        backprop through the box ─────────────────▶ DINN weights
```

- **Box**: 5-tracer 0-D reaction network (`carroll6.py`), optionally 7-tracer with carbonate chemistry
  (Follows-2006 + Wanninkhof-2014). A 2-layer 5-PFT integrator exists for seasonal fits.
- **Network**: `DINN` (~454 weights, SST-only — the clean baseline for the structural argument);
  `DINNDeep` (~9.4K weights, saturates — not default). Sigmoid bounds map NN outputs into Carroll's
  published physical ranges.
- **The differentiable box is the load-bearing piece.** Without it, gradients cannot flow from the
  observation loss to the network, and the method collapses to either pure-NN emulation (no parameter
  recovery) or back to Green's functions (no per-cell variation).

## 4. The surrogate gap — the single most important idea to internalize

The box is **0-D**: it has no spatial coupling. At uniform Carroll parameters it relaxes to a
near-uniform state (tracer coefficient-of-variation ~1e-15, vs Darwin's O(1) spatial structure). Two
consequences you must never forget:

1. **Box-vs-Darwin pattern correlations are NOT fidelity metrics.** A high spatial-pattern r means
   nothing here. Identifiability comes only from **real, absolute anchors** (GEOTRACES iron
   concentration, Daniels calcite ratio), not from matching Darwin's patterns.
2. **Held-out real-data validation is structurally blocked.** A held-out GEOTRACES cross-validation
   returns **negative R²** — the box has no spatial structure to predict *which cell* has how much iron.
   The recovery pins iron *magnitude*, not the spatial field. This is exactly why the work is a
   **consistency check**, not a discovery, and exactly what a spatial model (Track 2) would need to fix.

The corollary — the **central verified result** — is that the **per-cell architecture is load-bearing**:
a per-cell DINN holds the target trio {`alpfe`, `scav_rat`, `R_PICPOC`} while a single global-scalar
vector holds ~0 (disjoint confidence intervals; 7/10 vs 0/10 at n=10, 25/50 vs 0/50 at n=50). That
contrast *is* the paper-#1 result.

## 5. identifiability ≠ recoverability

A parameter can carry Fisher information yet still not recover, because recovery is downstream of
optimization and coverage. `scav_rat` is the worked example: with subsurface GEOTRACES iron it is
*well-conditioned* (the source/loss ratio degeneracy breaks ~1400×), yet its recovery is largely
**optimization-limited** — 25→41/50 per-AOI just by training to 4000 epochs instead of 2000, with the
equatorial Pacific (6/50) the residual *information*-limited basin. When you read a recovery count, ask
which of three it is: information-limited, optimization-limited, or a metric straddle (per-AOI legs on
opposite sides of Carroll — the cell-weighted count can lie).

## 6. The two tracks

- **Track 1 — parameter learner (paper #1, complete as a study).** Everything above. A
  surrogate-to-model identifiability study: which of the four observable Carroll params are identifiable
  from real observations, which are not, and why.
- **Track 2 — identifiability-limits map (paper #2, complete) + forward emulator.** Adds *prescribed*
  transport and asks which BGC closures real observations can constrain. Answer for all three targetable
  closures (iron, calcite Ω-modulation, growth): they cannot be sharply constrained — the binding
  constraint is the **observing system, not the method**. The forward emulator is a physically-valid v05
  surrogate with a **1-step useful horizon and no significant skill over a seasonal AR(1)** — a complete,
  well-traced **negative result** plus reusable infrastructure (the first ocean-BGC Earth2Studio
  `PrognosticModel`). Its real iron-cycle value lives in adjacent, observation-grounded findings (the
  v05-vs-MODIS chlorophyll regime split and the equatorial ENSO phase discrepancy), not in the emulator
  "beating" anything. Honesty guardrail: box/UDE Track-2 probes are synthetic self-twin — do **not** say
  "made Darwin differentiable" or "learned real biology."

## 7. The verify_run discipline (the trust gate)

Every headline number passes `scripts/verify_run.py` (exit 0). It never trusts a stored number: it
re-derives each recovery band from the raw per-seed `joint_recovered` vs the canonical
`carroll6.CARROLL_VALUES`, counts seeds, and flags any mismatch. **A nonzero exit means "no trustworthy
result" — never headline a number this script did not bless.** When you read a claim in this repo, check
whether it is verify_run-gated (trustworthy) or a note/hypothesis (not yet). Compare recoveries against
**Carroll's published Green's-functions optima**, not prior notebooks; report **n≥10 with seed
variance**; DINN baseline only by default.

Recovery scoring (`diagnostics.band_of`): *Excellent* ≤5% off Carroll, *Cal-grade* ≤40%, *Loose* ≤80%.

## 8. Where the data lives

All data is **gitignored and fetched separately**; loaders resolve paths via env vars
(`DARWIN_DATA_ROOT`, `GLODAP_DATA_ROOT`, `GEOTRACES_DATA_ROOT`). See [data/README.md](../data/README.md)
for URLs, auth, and loaders.

| Dataset | What | Loader module |
|---|---|---|
| ECCO-Darwin v05 1° bin_average | surface fields, ~1.7 GB NetCDF (the everyday target) | `ecco_darwin_loader` |
| ECCO-Darwin v05 native LLC270 | depth-resolved tracers, ~1.9 TB (native fits) | `llc270_loader` |
| GEOTRACES IDP2025 | real dissolved iron (drives `alpfe`/`scav_rat`) | `geotraces_loader` |
| Daniels 2018 CP:PP | real calcite rain-ratio anchor (drives `R_PICPOC`) | `daniels_loader` |
| GLODAPv2 | mapped DIC/ALK/nutrients | `glodap_loader` |

## 9. Run it, then plug in

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync && uv run pytest -q                        # smoke test (data-dependent tests self-skip)
```

Then, in order: the synthetic recovery demo in `notebooks/demo_colab.ipynb` (laptop / Colab T4, no data
download needed) shows the whole loop end-to-end; the real-data recovery runners live in `scripts/`
(the 3-AOI joint trainer is `scripts/run_v3.0_joint_multi_aoi.py`, env-var driven); and every run is
graded by `scripts/verify_run.py <run_dir>` (exit 0 == trustworthy). Read a runner's `--help` / the
top-of-file docstring for its exact levers before launching.

**Genuinely handoff-able open sub-problems** (self-contained pieces a new contributor can pick up):

- **diatomgraz: structural vs practical.** Current read is input-limited (SST-only ~4/10 → 10/10 with an
  MLD input channel), but the profile-likelihood-with-MLD confirmation is pending — the multi-start
  identifiability array ([#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152)) is running to
  settle it. *State it as: recoverable from a non-circular **model-internal** observable (chlorophyll +
  MLD), not recovered from independent real data — the SST-only ~4/10 is the no-MLD baseline, not a
  ceiling. The remaining gap is an independent real diatom observable, not circularity.*
- **Track-2 Phase-1 minimal real-data transport UDE** (regional 2-D on Darwin's own velocities). The
  make-or-break gate (held-out real-data R² > 0 once transport is present) was **run and came back
  negative** (`docs/findings/2026-07-10_e2_powered_result.md`, #180): the learned closure cannot beat a
  constant-through-transport null out of sample, so transport does not close the surrogate gap on real
  data. What is genuinely open is the *regional* build itself and the observing-system question it
  exposes, not the gate ([#176](https://github.com/2imi9/ECCO-DarwinDiff/issues/176)).
- **Calibrated credible intervals.** The derivative-free EKI reaches the same verdict as backprop but
  gives a posterior **mean only** (the ensemble collapses); an EKS/CES sampling stage is future work
  ([#187](https://github.com/2imi9/ECCO-DarwinDiff/issues/187)).
- **Seasonal `Smallgrow` confirmation** — the North-Atlantic 9/10 prototype needs a native interannual
  fit (current version uses a constant-IC/forcing approximation).
- **Equatorial-Pacific `scav_rat`** — the 6/50 information-limited residual, the most degenerate basin;
  needs a real scavenging-rate observable (²³⁴Th), not more epochs.
- **The surrogate→GCM ranking check** — a small ECCO-Darwin v05 perturbation ensemble to confirm the
  surrogate Fisher ranking transfers ([#163](https://github.com/2imi9/ECCO-DarwinDiff/issues/163);
  decks + protocol staged in `scripts/perturbation/`).

## Read next

[STATUS.md](../STATUS.md) (canonical current-best, verify_run-gated) · [Config/Results Matrix](results_matrix.md)
(single source of truth per config) · [ECCO-Darwin relationship](ecco_darwin_relationship.md) (which piece
of Darwin we touch) · [parameter inventory](ecco_darwin_parameter_inventory.md) (the 6-of-~103 audit) ·
[DINN design](dinn_design.md) (architecture + the structural-ceiling argument).
