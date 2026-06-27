# Identifiability map — Phase-0 feasibility (#152, 2026-06-27)

**Question (the binding feasibility gate from the goal doc):** the box STATE homogenizes at uniform
Carroll params (tracer CV → ~1e-15), so does the per-cell *sensitivity* `dx*/dθ` still carry spatial
structure — or does the map collapse to flat?

**Method:** integrate eqpac to the converged steady state (1600 steps), then for 30 ocean cells spanning
the SST range compute the steady-state sensitivity `S = pinv(I−J)·B` (implicit function theorem; pinv
handles the 2 conserved modes). Report the per-parameter relative sensitivity of the surface observables
and its **CV across cells** (`/c/Users/Frank/dd_agg/identifiability_map_phase0.py`).

## Result

| param | mean rel-sens | **CV across cells** |
|---|---|---|
| alpfe | 2.46e-6 | **0.26** |
| scav_rat | 1.97e-6 | **0.26** |
| R_PICPOC | 2.61 | 0.18 |
| diatomgraz | 1.97e-8 | 0.01 |
| Smallgrow | 0.737 | **0.00** |
| Biggrow | 0.303 | **0.00** |

Max spatial CV = **0.26**.

## Conclusion

- **FEASIBILITY: PASS.** The converged per-cell sensitivity varies spatially (CV up to 0.26) despite the
  state homogenizing — the spatial signal comes from the **forcing-modulated Jacobian**, confirming the
  goal-doc premise that a map is feasible (signal = forcing + observation placement, not box-state pattern).
- **Caveat (do not over-read the ranking).** The naive sensitivity *values* are NOT the identifiability
  map: this uses the box's surface observables with **no observation-noise model Σ**. The ranking
  (R_PICPOC dominant, iron pair ~2e-6, diatomgraz ~0) is the same artifact flagged in `box_linearization`
  — it does not match the real-data identifiability (iron pair ← real GEOTRACES iron; R_PICPOC ← real
  calcite). The growth pair's **CV=0.00** is a partial H3 signal (flat everywhere = unidentifiable), but
  its large *mean* is the artifact: with no real growth-rate observation, Σ→∞ ⇒ FIM=0.

## Next (Phase 1+, per the goal doc)
Build the FIM `= Jᵀ Σ⁻¹ J` with the **real observable set + Σ** (Σ→∞ where no data: growth rates have
none; iron only where GEOTRACES; calcite only where Daniels/MODIS). The map's spatial structure will be
dominated by **observation coverage** (Σ), modulated by the forcing-driven J (CV ~0.26). Then run the
decisive H2 validation: does the map reproduce the v3.1.1 hand-ablation attribution?
