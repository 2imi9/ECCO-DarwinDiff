# Surrogate-vs-Darwin parameter-Jacobian validation — do we have the ground truth? (2026-07-23)

## The reviewer concern (correct, and unaddressed until now)

The manuscript's Fisher / CRLB identifiability array is computed by finite-differencing the
**0-D differentiable surrogate box** (`scripts/identifiability_sloppiness.py`, `--mode fisher_gn`).
That characterizes the *surrogate's* curvature, i.e. the identifiability of the **box**, not of
**ECCO-Darwin**. The transfer to the GCM is licensed **only if** the box's parameter Jacobian
`d(tracer)/d(param)` matches ECCO-Darwin's own sensitivities — in **sign**, in **relative magnitude**,
and above all in the **cross-parameter ranking** that the Fisher eigenstructure is built from.

Carroll/Menemenlis's Green's-functions (GF) calibration perturbs each parameter and runs a forward
ECCO-Darwin integration, so **those GF perturbation runs *are* the direct GCM sensitivities** — the
correct ground truth to validate the box against.

## TL;DR verdict

1. **We do not have the Darwin sensitivities.** An exhaustive search of the repo, the AICR cluster
   (`~/dd_data`, `/scratch/qi_zim_neu`), and the reference material turns up **no** GF perturbation
   runs, **no** saved `d(tracer)/d(param)` fields, and **no** Darwin `bin_average` output at perturbed
   parameters. Only the GF *endpoints* (initial → optimized values, from the Menemenlis 2019 deck) exist,
   and those are an inverse-problem solution, **not** a forward Jacobian.
2. **The box Jacobian was computed** (surrogate side of the comparison, this note, through the exact
   geo1 runner box the Fisher uses). Its **signs are correct — but guaranteed by construction**, because
   the box reuses Darwin's own functional forms; sign agreement is therefore **not** an independent
   validation. Its **magnitude and cross-parameter ranking are surrogate quantities** that remain
   unvalidated against the GCM.
3. **Net:** the Fisher/CRLB transfer to ECCO-Darwin is currently **assumed via the shared
   parameterization**, and the paper must carry an explicit scope caveat (verbatim text below).

---

## 1. What sensitivity data exists (the search)

### Repo
- `references/carroll_2020_ecco_darwin.pdf` (the JAMES paper) and the `references/README.md` bibliography
  (Carroll 2020/2022, Brix 2015, Menemenlis 2005) — all describe the GF *method* and report *optimized*
  values; **none** publishes the GF sensitivity kernels `G = d(obs)/d(param)`.
- `docs/ecco_darwin_parameter_inventory.md` — confirms the mechanism: "The Green's functions workflow
  literally edits these constants in source and recompiles per experiment." The perturbation runs were
  internal MITgcm experiments; only the 6 optimized scalars were retained.
- `notebooks/06_carroll6_ml_vs_greens.ipynb` — the "Green's-functions class" is **emulated by a
  global-scalar autograd fit**, explicitly a *structural stand-in* ("a fair-or-better stand-in for what
  Green's-functions can do on the same data"), not a reconstruction from real GF sensitivities.
- `docs/findings/` — no prior box-vs-Darwin **sensitivity** comparison exists. The closest,
  `2026-06-26_rainratio_real_vs_darwin.md`, compares *R_PICPOC values*, not `d(tracer)/d(param)`.
- The Track-2 write-up (`docs/research_notes/2026-07-09_track2_identifiability_writeup.md`) and STATUS.md
  already name the underlying problem: **"the surrogate gap is dimensional"** — at uniform Carroll
  parameters the 0-D box relaxes to a near-uniform state (tracer CV ~1e-15 vs Darwin's O(1)), so
  box-vs-Darwin *pattern* correlations are not fidelity metrics. This note is the *sensitivity-space*
  statement of the same gap.

### Cluster (`ssh aicr`)
- `~/dd_data/ecco_darwin_v5/cache/` — three v05 **target** caches (`*_targets_*.pt`). These are Darwin
  output **at Carroll's optimized parameters only** — one point in parameter space, not a perturbation set.
- `~/dd_data/geotraces/` — GEOTRACES IDP2025 (a real-obs anchor, not a Darwin sensitivity).
- `/scratch/qi_zim_neu/` — training cubes, emulator outputs, physical fields. A `find` for
  `*green* / *pertur* / *sensitiv* / *jacobian* / *menemenlis* / *brix*` returns **nothing**.

**Conclusion of the search: no direct ECCO-Darwin parameter sensitivities are available anywhere we
control.** They live (if anywhere) in Carroll/Menemenlis's original GF experiment archive, which we do
not have.

## 2. The one Darwin-side quantity we do have — and why it is not a validation

The Menemenlis ECCO-Summer-School-2019 deck (Table S1, the ECCO-Darwin **v4** GF optimization; recorded
in project memory `reference_carroll6_param_values`) gives **initial → optimized** values:

| param | v4 initial | v4 optimized | move |
|---|---|---|---|
| alpfe | 1.0 | 0.927 | ↓ ~7% |
| scav_rat | 3 (raw) | 9.32 (raw) | ↑ ~3× |
| Smallgrow | 0.7 | 0.692 | ↓ ~1% |
| diatomgraz | 0.85 | 0.846 | ↓ ~0.5% |
| R_PICPOC | 0.04 | 0.0419 | ↑ ~5% |

**These moves are not `d(tracer)/d(param)`.** A GF-optimized displacement is
`Δp ≈ −(sensitivity) × (data–model mismatch)` folded through the full 13-GF covariance — it mixes the
forward sensitivity **sign** with the sign of the prior mismatch and with cross-parameter coupling. So the
direction Carroll's data pulled a parameter does **not** cleanly reveal the forward Jacobian sign, and
cannot be used to validate it. The deck also documents one perturbation *specification* ("Iron dust
solubility reduced by 20%") but **not its output** — we have the knob turn, not the response field.

## 3. The surrogate side, computed (box Jacobian at Carroll)

Computed this session through the **exact geo1 runner box** the Fisher is built from (reusing
`identifiability_sloppiness._import_runner`; `N_STEPS=200`, `DT=0.25`, Eppley-T; central finite difference
in log-parameter space, `eps=0.02`; ocean-mask mean, cell-weighted over the 3 AOIs). Entries are
dimensionless log-sensitivities `S = d ln⟨tracer⟩ / d ln(param)`:

| param ↓ / tracer → | DFe_surf | DFe_sub | diatom | PIC_surf | POC_surf |
|---|---|---|---|---|---|
| **alpfe** | **+0.607** | −0.245 | +1.901 | +0.526 | +0.526 |
| **scav_rat** | **−0.490** | −0.501 | −1.511 | −0.415 | −0.415 |
| **diatomgraz** | +0.021 | +0.018 | **−7.110** | −0.018 | −0.018 |
| **R_PICPOC** | 0.000 | 0.000 | 0.000 | **+1.000** | 0.000 |

Natural observable pairing and **surrogate ranking** (|log-sensitivity to the parameter's own observable|,
high = stiff):

1. **diatomgraz → diatom biomass: −7.11**
2. **R_PICPOC → PIC: +1.00**  (exactly unity; `dPIC = R_PICPOC·mort_total` → linear, and R_PICPOC is
   decoupled from every other tracer)
3. **alpfe → DFe_surf: +0.61**
4. **scav_rat → DFe_surf: −0.49**

### What the surrogate Jacobian shows
- **Signs are all mechanistically correct**: alpfe raises DFe (dust source ↑), scav_rat lowers DFe (sink ↑),
  diatomgraz lowers diatom biomass (grazing loss ↑), R_PICPOC raises PIC (calcite production ↑). It also
  reproduces the iron-fertilization coupling (alpfe → diatom +1.90) and the calcite/organic co-scaling.
- **The iron degeneracy is visible in the Jacobian itself**: alpfe (+0.61) and scav_rat (−0.49) act on the
  *same* observable (surface DFe) with **near-equal magnitude and opposite sign** — the source/sink
  compensation that makes the pair trade off along one combination. This matches the GN-Fisher result
  (the surface-only iron block is near-degenerate, conditional corr ≈ +0.999; with subsurface GEOTRACES it
  is largely separated, cond 2.2 — the "CRLB 68 vs 78" and "strong −0.77" readings are retracted, see
  [`2026-07-23_rigorous_identifiability_Q1Q2.md`](2026-07-23_rigorous_identifiability_Q1Q2.md) §Q2) and the
  published FeMIP degeneracy.
- **Raw sensitivity ≠ identifiability**: diatomgraz is by far the *stiffest* parameter in the box
  (|S|=7.11) yet is the manuscript's **data-blocked** parameter — the bSi/biomass observable routes
  through the model's own diatom biomass, which compensates, so a large `d(biomass)/d(param)` does not
  translate into an identifiable observable. This is a caution against reading the Jacobian magnitude as
  identifiability, and it is exactly why the Fisher (which folds in the observation footprint), not the raw
  Jacobian, is the right object — and why validating the *Fisher's* transfer, not just the Jacobian's,
  matters.

## 4. Why the box's sign agreement is not a validation

Sign agreement between the box and ECCO-Darwin is **guaranteed by construction**: `carroll6.py` reuses
Darwin's own parameterized terms — `alpfe·Φ_dust` (source), `scav_rat·DFe·POC` (sink),
`R_PICPOC·mort_total` (calcite), `diatomgraz·G0·P_large` (grazing). Any parameter that enters Darwin as a
source multiplier enters the box as one too, so the forward sign *must* match. That is expected and
reassuring, but it is not independent evidence about the GCM.

What is **not** guaranteed, and is what the Fisher transfer actually needs:
- **Magnitude.** Darwin is 3-D and spatially resolved with ~39 tracers, prognostic transport, depth
  remineralization, a variable sediment iron source, ligand chemistry, and particulate-weighted scavenging
  (`scav_POC_wgt`, `scav_PSi_wgt`, `scav_PIC_wgt`) — all collapsed in the 0-D, 2-layer, 5-effective-tracer
  box. The `|S|` magnitudes above are surrogate numbers.
- **Cross-parameter ranking.** Whether alpfe or scav_rat dominates the DFe response in Darwin depends on
  the full 3-D iron budget the box homogenizes; the surrogate ranking
  (diatomgraz ≫ R_PICPOC > alpfe > scav_rat) is a property of the box, and the Fisher eigenbasis —
  which the paper's sloppy/stiff directions and the EKI reparameterization are built on — inherits exactly
  that ranking. If Darwin's ranking differs, the sloppy direction differs.

## 5. What would validate it (the missing GCM runs)

A minimal, decisive validation needs a small one-at-a-time GF-style perturbation ensemble in ECCO-Darwin:

- For each observable parameter {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}: two v05 forward runs at
  `±10–20%` about the Carroll value (namelist edits: `data.darwin` for `alpfe`/`scav_rat`; `data.traits`
  `PALAT` / `a_R_PICPOC` for `diatomgraz`/`R_PICPOC`), plus the control at Carroll (the run we already have).
- Save the surface tracer fields (FeT, diatom biomass / bSi, PIC, POC), `bin_average`d onto the same 3 AOI
  footprints, and form `d ln⟨tracer⟩ / d ln(param)` by central difference — the **GCM rows** of the same
  matrix computed in §3.
- Compare to the box row-for-row: (a) sign (expected to pass by construction), (b) magnitude ratio per
  entry, (c) — the load-bearing test — whether the **ranking** of the four parameters by sensitivity to
  their own observable matches. Agreement in (c) is what licenses transferring the surrogate Fisher
  eigenstructure to ECCO-Darwin.

This is 8 short forward integrations (≈2 per parameter) — the cheapest possible version of the very GF
sweep the project set out to replace, run here only to *calibrate the surrogate*, not to optimize. It is a
data-staging / GCM-access task (needs the v05 build and run harness), out of scope for this repo's box.

## 6. Honest scope statement the paper must carry

> The reported Fisher information and Cramér–Rao bounds characterize the differentiable 0-D surrogate box.
> Their transfer to ECCO-Darwin is assumed via the shared parameterization — the box reuses Darwin's own
> source/sink functional forms, so the forward-sensitivity **signs** are identical by construction — and
> remains to be validated against direct GCM parameter perturbations. In particular the sensitivity
> **magnitudes** and the **cross-parameter ranking** that define the Fisher eigenstructure are surrogate
> quantities; a small one-at-a-time ECCO-Darwin perturbation ensemble about the Carroll optimum would be
> required to confirm the ranking transfers to the full model.

## Provenance / reproduction

- Surrogate Jacobian: reran the geo1 runner box via `identifiability_sloppiness._import_runner` on AICR
  (`~/dd_venv/bin/python`, `PYTHONPATH=src`, `GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces`,
  `DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5`). Central FD, `eps=0.02`, log-param space, cell-weighted
  ocean means over {eqpac, natlsubpolar, southernoceanpac}. Raw values in the table above; the probe
  script was a scratch file (not committed) and its cluster copies were removed after the run.
- No repo files other than this note were edited; no GCM runs were launched; nothing committed.
- Related: `STATUS.md` ("the surrogate gap is dimensional"; GN-Fisher 2026-07-23),
  `docs/research_notes/2026-07-21_manuscript_redteam.md` (the standing caveat backlog),
  `docs/ecco_darwin_parameter_inventory.md` (GF mechanism), `reference_carroll6_param_values` (deck Table S1).
