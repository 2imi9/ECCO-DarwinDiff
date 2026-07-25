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
- **Iron pair** (`alpfe`, `scav_rat`) recovers from real GEOTRACES dissolved iron, carried by `alpfe`
  (**49/50** per-AOI at n=50); `scav_rat` is basin-fragile (**26/50** per-AOI at 2000 epochs → **41/50** at
  4000 epochs, with the equatorial Pacific leg stuck at 6/50). The earlier **38/40 (95 %)** headline is an
  n=40 count that predates the per-AOI reconciliation and reads too optimistically.
- **`R_PICPOC`** recovers against a real calcite anchor (Daniels CP:PP / MODIS PIC); the best config
  (`geo1`) recovers `R_PICPOC` **50/50 per-AOI** in the n=50 flagship (`n50e2k_percell_trio`, 2000 epochs), and the
  real anchor is what drives it (anchor-off control, 1500 epochs `n50_anchor_off` → **4/50**; the epoch-matched 2000-epoch control `n50e2k_anchor_off` → **6/50**). The same config holds
  **{`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 25/50 seeds** under the honest per-AOI ≥2-of-3 metric
  (33/50 cell-weighted — that metric straddles and must not be quoted as recovery), versus **0/50** for the
  global-scalar control — a 3-of-4-observable frontier whose binding leg is `scav_rat` (26/50 at 2000 epochs,
  41/50 at 4000). The earlier n=10 sweep (7/10; 8/10 in the original run) is the precursor, not the headline.
  Recovery lands at real ~0.05, consistent with Carroll within the wide Cal band; the load-bearing finding is
  that Carroll's *global* `R_PICPOC` is itself under-constrained and mis-specified vs a regionally-variable rain ratio.
- The **surrogate gap is dimensional**: the 0-D box homogenizes spatial structure (tracer CV → ~1e-15),
  so identifiability comes from real *absolute* anchors and the per-cell DINN is load-bearing.

### Scope / honest limits
- Honest target = **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth
  pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real growth-rate data).
- `diatomgraz` is **input-limited, not data-blocked**: SST-only DINN sits at chance (~4/10), but adding an
  MLD input channel takes it to 10/10, and with the biogenic-silica diagnostic off (`POSI_W=0`) it still
  reaches **35/50 per-AOI** through chlorophyll + MLD — so it is not a bSi tautology. The Chl target is
  Darwin's own output, so the honest claim is "recoverable from a non-circular model-internal observable",
  not "recovered from independent real data". The 3-of-4 frontier is **structural**: `geo1` holds
  {`alpfe`, `scav_rat`, `R_PICPOC`} and the MLD-channel + heavy-Daniels config holds
  {`alpfe`, `diatomgraz`, `R_PICPOC`}; `scav_rat` needs the Darwin-pattern term, `diatomgraz` needs MLD,
  and they conflict even at 4000 epochs.
- 1° box-model proxy; 23-year climatology, not time-resolved; single-method (no forward-Darwin held-out
  validation yet); single-GPU prototype.

### Changed / corrected
- Reframed from a "6/6 recovery chase" to the identifiability study. **Refuted** the earlier
  "`R_PICPOC` needs the differentiable Darwin calcite port + native resolution" conclusion (both tested,
  neither helped). Repo-wide documentation accuracy pass (#151) and open-PR consolidation (#153).

---

## Version history (research chronology)

> The per-version box-science record. The "5/6 ceiling / parameter conservation / 6/6 wall" framing
> below is **superseded** by the identifiability reframe in [Unreleased] — read it as a record of what
> was concluded at each step. Per-config detail: [Config / Results Matrix](docs/results_matrix.md);
> full writeups: [archive](docs/archive/index.md).

- **v0.x → v1.8** (nb 05–19): synthetic-truth methodology validation; real-data demos on GLODAP and
  Darwin Chl; cross-basin verification; iron-pair recovery via Darwin FeT in HNLC; multi-tracer joint
  loss partially collapses the parameter degeneracy.
- **v2.0** (nb 20–21): carbonate cycle (`carbonate.py`, Follows 2006 + Wanninkhof 2014); 7-tracer joint
  loss moves the iron pair to 1.1 % / 40 % off Carroll.
- **v2.1** (nb 22, PR #41): GLODAPv2.2016b real-obs DIC + ALK hybrid; `R_PICPOC` 360 % → 74 % off Carroll.
- **v2.2** (nb 23–29, PR #37): full 5-PFT box matching Darwin v05; v2.4 PINN-drift reaches 4/6 Cal-grade.
- **v2.5** (PR #39): GEOTRACES IDP2025 loader scaffold validated against the real NetCDF schema.
- **v2.6** (PR #40): GEOTRACES absolute-iron MSE loss; 4/6 Cal-grade reproducibly across n=10.
- **v2.7** (PR #42): 2-layer box; subsurface DFe anchoring alone does **not** unblock `scav_rat`.
- **v2.8** (PR #45): Darwin v5 pickup ICs + L2 POC z-score; project-first reproducible `scav_rat`
  (7/10 Cal, 4/10 Excellent); bimodal (`alpfe`, `scav_rat`) degeneracy selected by `POC_SUB_W`.
- **v3.0** (PRs #46–#59): shared-Carroll-6 joint multi-AOI training (Eq Pac + N Atl Subpolar);
  the 5/6 plateau across 50+ seeds; per-AOI DINN falsified at 2-AOI.
- **v3.1** (PR #64+): Southern Ocean Pacific added as 3rd AOI; iron pair 38/40 at n=40; two
  complementary single-seed 5/6 paths; 5/6 ceiling holds at 2/856.
- **v3.1.1** (PR #89): AOI ablation (4 configs, n=200) — AOI mix decides *which* 4–5 params recover;
  no mix reaches 6/6.
- **v3.2** (on main): dense Darwin `POSi` (TRAC16) target + Eppley temperature limitation; breaks the
  `alpfe`↔silica mutex and recovers the iron pair + `diatomgraz` together (mean 2.0 → 3.85/6, first
  *reproducible* 5/6 at 3-AOI, n=20). `R_PICPOC` localized as the lone remaining box-scale miss.
  *(Against Darwin's own silica field — a different, weaker thing than the real-data operating point.)*
- **v3.3** (#115 / #126 / #127 / #131): seasonal/native infrastructure — the transient-seasonal
  integrator is seed-batched + `torch.compile`-ready and emits `verify_run.py`-gateable per-seed JSON.
  No new science (seasonal recovery stays cluster-gated).
- **spine D — real-data identifiability (2026-06, current frame):** reframed to a surrogate-to-model
  identifiability study over 4 observable params. Real anchors identify the iron pair (GEOTRACES) and
  `R_PICPOC` (Daniels CP:PP / MODIS); `geo1` holds the trio 7/10 at n=10, superseded by **25/50 per-AOI**
  in the n=50 flagship (see [Unreleased] above). Refuted the "needs the Darwin port + native resolution"
  claim. Established the dimensional surrogate gap and the load-bearing per-cell DINN.

*Underlying writeups: [archive](docs/archive/index.md). Current truth: [STATUS.md](STATUS.md).*
