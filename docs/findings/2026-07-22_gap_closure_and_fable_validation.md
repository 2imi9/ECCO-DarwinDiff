# Gap-closure by design + Fable validation (2026-07-22)

A systematic pass to "fill every gap by design and test coordinated on the cluster." Every candidate
improvement from prior sessions was enumerated into **12 gaps**, each **designed** (sonnet, grounded in
the real repo) and **adversarially vetted for decisiveness** (opus) — kill the null-by-construction ones
before they earn compute — then the contested KILLs were **independently validated by Fable** (the deepest
call: what to permanently discard). Workflows `wf_26a77fbb-751` (design+vet) and `wf_70c52987-421` (Fable).

## Triage (12 gaps)

| verdict | gaps |
|---|---|
| **GO / GO-AFTER-CODE** | G1 sign-flip n≥50, G2 integrator stationarity, G3 anchors-only n=50 + PINN-off, G4 W=0.3 alpfe regime, G8 diffusion-recompute (scoped to committing the fix) |
| **DEFER** | G5 per-AOI saddle, G6 EKI-CI (subsumed by the trio-EKI below) |
| **KILL — null-by-construction** | G7 per-cell Fisher map, G9 cube-seam, G10 UDE forcing (as posed), G11 field-conservation (as posed), G12 discovery route-A |

Most "improvements" are foregone numbers or structurally pre-determined — itself the finding: the project
is near its real identifiability limits. The kills are code-grounded, not lazy.

## Fable validation of the contested kills

- **G7 per-cell Fisher — DROP (kill upheld).** Per-cell Fisher of a mask-multiplied anchor term is nonzero
  ~only on the anchor mask, so "info tracks anchor location" is a near-identity. Confirmed against code.
- **G9 cube-seam — DROP (kill upheld).** `emulator_poc.py:352-366` regrids native (face,j,i) onto a flat
  lat/lon array (`binned_statistic_2d`) **before** the FNO, so the facet-seam topology is discarded for
  every cube we build — the named artifact is structurally unobservable. (Fable even verified the
  antimeridian seam-fold arithmetic is correct.) Close-out = the doc note in
  `docs/findings/2026-07-21_emulator_geometry_flat.md`.
- **G6/G12 → BUILD-NOW: full-box EKI as a whole-TRIO method-independence check.** The as-posed versions
  were null (the 6-D align metric lands on the decoupled R_PICPOC/growth axis; R_PICPOC-alone just
  re-shows the anchor pins it). The coherent, decisive version — built as `scripts/analysis/eki_fullbox_trio.py`
  — runs the unit-tested `eki_core.eki` through the **real geo1 box + real anchors** {GEOTRACES surf/sub
  DFe, Daniels CP:PP} over the trio, growth held at Carroll. Success (either direction is positive):
  alpfe + R_PICPOC posterior means land Cal-grade == backprop (two independent estimators agree → closes
  the "single-method / DINN+autograd artifact" reviewer attack), and scav_rat stays wide on the sloppy
  ridge (estimator-independent confirmation of the binding leg). It is **method-independence, not
  discovery** (grades against Carroll, adds no information). CPU-local. *[running]*
- **G11 field-conservation — kill upheld, but it surfaced a REAL BUG → issue #192.** Conservation is
  machine-precision by construction (flux-form + no-flux BC), so it cannot informatively fail. BUT
  `kh=50` in `e2_real_calcite_eqpac.py:145` / `iron_scav_rat_profile.py:109` is a **units bug** — m²/s
  copied from `kz` into an m²/day framework, ~7 orders below the stability floor 0.5|u|dx ≈ 1.9e9 m²/day.
  This **voids the E2 K_num control** and makes the pre-registration's "physical kh" label wrong. It does
  **not** overturn the E2 negative: correcting kh upward adds smoothing → reinforces the null.

## Three surprise findings (all fixed/filed)

1. **`kh=kz` units bug** → issue #192.
2. **`eki_core.eki` is an EKI *optimizer*, not a sampler** — its ensemble collapses, so its spread is not
   a calibrated posterior. `eki_prototype.py` labeled it "posterior"; the manuscript's published numbers
   use point recovery + CRLB + seed variance (not the EKI ensemble), so nothing published is affected, but
   any future EKI *credible interval* would need the EKS/CES sample stage. Caveat added to `eki_core.py`.
3. **False docstring** — `eki_core.py:4` claimed `identifiability_sloppiness.py` was a "full-box
   promotion" importing the core; it does not (only Fisher/profile). Corrected to point at the real
   importer (`eki_fullbox_trio.py`).

## Coordinated cluster + local runs launched

- **Local (validate-by-doing):** G1 sign-flip n=50 (both loss kinds); G10-stage1 forcing Fisher probe
  (done — `drawdown_pulse` wins, `antiphase` widest coverage); the full-box EKI trio check.
- **Cluster (job `8536393`, coordinated GPU array):** G3 anchors-only n=50 in PINN-on and PINN-off arms
  (isolates the pure real-anchor contribution) + G4 W=0.3 default regime for the alpfe weight-conditional
  table.

## Meta-conclusion

The design-then-vet-then-Fable pipeline did exactly its job: it **killed 6 foregone experiments before
they burned compute**, launched the ~5 genuinely-decisive ones coordinated, and **surfaced a real bug in
a load-bearing result** (the E2 K_num control). The single most valuable output was not a new recovery
number but the discovery that the project's remaining "gaps" are mostly limits, not to-dos — with two
exceptions worth building: the estimator-independence EKI check (a real reviewer-attack closer) and the
kh fix (a correctness fix to Track-2's make-or-break control).
