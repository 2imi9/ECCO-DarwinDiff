# Changelog

All notable changes to the DarwinDiff **parameter learner (Track 1)** are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/); the project is pre-1.0 and under active research.

## [Unreleased] — proposed **v0.1.0** (first coherent parameter-learner release)

Framed as a **surrogate-to-model identifiability study**: which of ECCO-Darwin's six Carroll-6
biogeochemistry parameters are identifiable from real ocean observations, which are not, and why.
Replaces Green's-functions calibration with gradient descent through a differentiable box model.

### Added
- Differentiable 0-D box model of ECCO-Darwin v05 biogeochemistry (`carroll6_5pft_2layer`, 15-tracer
  2-layer) with carbonate chemistry (Follows 2006 + Wanninkhof 2014).
- Per-cell `DINN` (env → 6 Carroll-6 parameters) trained by autograd through the box.
- Real-data loaders: GEOTRACES IDP2025 (dissolved iron, biogenic silica), GLODAP (DIC/ALK),
  Daniels 2018 CP:PP + MODIS-Aqua (calcite / rain ratio).
- Verified-experiment loop (`scripts/verify_run.py`): every recovery number re-derived from raw and
  gated (exit 0 = trustworthy).
- Diagnostics: self-twin method-proof (`scripts/self_twin_recovery.py`), box-vs-Darwin fidelity
  (`scripts/box_vs_darwin_fidelity.py`), FIM/profile sloppiness (`scripts/identifiability_sloppiness.py`),
  per-AOI co-recovery aggregator (`scripts/aggregate_daniels_recovery.py`).
- ADRs (`docs/adr/`): Track-2 emulator scope (0002); differentiable Darwin calcite port (0001 — retained
  as a *rejected* decision record).

### Results (verified, `verify_run.py`-gated)
- **Iron pair** (`alpfe`, `scav_rat`) recovers **38/40 (95%)** at the best 3-AOI config, from real
  GEOTRACES dissolved iron.
- **`R_PICPOC`** recovers against a real calcite anchor (Daniels CP:PP / MODIS PIC); the best config
  (`geo1`) holds **{`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 8/10 seeds** — a 3-of-4-observable frontier.
- The **surrogate gap is dimensional**: the 0-D box homogenizes spatial structure (tracer CV → ~1e-15),
  so identifiability comes from real *absolute* anchors and the per-cell DINN is load-bearing.

### Scope / honest limits
- Honest target = **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth
  pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real growth-rate data).
- `diatomgraz` is not recovered in the real-data sweep (iron-pair tradeoff; needs dense Darwin
  POSi/TRAC16, not yet staged).
- 1° box-model proxy; 23-year climatology, not time-resolved; single-method (no forward-Darwin held-out
  validation yet); single-GPU prototype.

### Changed / corrected
- Reframed from a "6/6 recovery chase" to the identifiability study. **Refuted** the earlier
  "`R_PICPOC` needs the differentiable Darwin calcite port + native resolution" conclusion (both tested,
  neither helped). Repo-wide documentation accuracy pass (#151) and open-PR consolidation (#153).

---

*Earlier internal milestones (v2.x–v3.x box-science, the "5/6 ceiling" framing now superseded) are
recorded per-version in [`docs/findings/`](docs/findings/index.md) and [`STATUS.md`](STATUS.md).*
