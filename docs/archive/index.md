# Archive — research provenance

These are the **verified, point-in-time research writeups** behind the headline results.
They are kept as provenance (every number was `verify_run.py`-gated when written) but are
**out of the onboarding path** — start at [Project Status](../status.md) and the
[Config / Results Matrix](../results_matrix.md), which state the current truth once.

!!! warning "These pages are historical"
    Framings here may be **superseded**. In particular the "6/6 wall / 5/6 ceiling /
    parameter conservation / needs the differentiable Darwin port" language predates the
    [identifiability reframe](../status.md): the honest target is **4 observable params**,
    the growth pair is unobservable by construction, and `R_PICPOC` is recoverable given a
    real calcite anchor. Read each page as a record of what was true when it was written.

## Findings — per-version technical record

The box-scale parameter-recovery writeups, v2.1 → v3.2 (and the `R_PICPOC` campaign).
Full list: **[findings index](findings/index.md)**. Highlights:

- [v2.1 — GLODAP DIC/ALK hybrid](findings/v2.1_phase1_glodap.md)
- [v2.2 — 5-PFT box](findings/v2.2_phase2.md) · [v2.7 — 2-layer scoping](findings/v2.7_multilayer_box_scoping.md) · [v2.8 — Darwin ICs + POC loss](findings/v2.8_darwin_ic_poc_sub.md)
- [v3.0 — multi-AOI scoping](findings/v3.0_multi_aoi_scoping.md) · [v3.1 — closeout](findings/v3.1_closeout.md) · [v3.2 — dense POSi + Eppley](findings/posi_dense_diatomgraz.md)
- `R_PICPOC`: [ratio loss (structural)](findings/rpicpoc_ratio_structural.md) · [ALK anchor mutex test](findings/alk_anchor_rpicpoc_mutex.md)
- Track-2 feasibility: [spatial UDE](findings/2026-06-30_spatial_ude.md)
- Scaling / verification: [compute-time](findings/compute_time_scaling.md) · [memory (eager)](findings/memory_scaling.md) · [memory (compiled)](findings/memory_scaling_compiled.md) · [pre-scaleup verification](findings/pre_scaleup_verification.md)

## Research notes — deeper investigations & decision records

Identifiability theory, sweeps, manuscript red-teams, and compute budgets:

- **Surrogate gap / homogenization:** [box homogenization (definitive)](research_notes/2026-06-27_box_homogenization_DEFINITIVE.md) · [box convergence](research_notes/2026-06-27_box_convergence_finding.md) · [surrogate gap quantified](research_notes/2026-06-26_surrogate_gap_quantified.md)
- **Identifiability:** [per-cell vs global ablation](research_notes/2026-06-27_percell_vs_global_ablation.md) · [identifiability map goal](research_notes/2026-06-27_identifiability_map_GOAL.md) · [synthetic equifinality demo](research_notes/2026-06-27_synthetic_equifinality_demo.md) · [growth-pair deep research](research_notes/2026-06-25_growth_pair_identifiability_deep_research.md) · [R_PICPOC observability deep research](research_notes/2026-06-24_rpicpoc_observability_deep_research.md)
- **Hold-together sweep (current-best `geo1`):** [results](research_notes/2026-06-26_holdtogether_sweep_results.md) · [pre-registration](research_notes/2026-06-26_sweep_holdtogether_prereg.md)
- **Track-2 hybrid feasibility:** [differentiable-BGC feasibility note](research_notes/2026-06-29_hybrid_differentiable_bgc_feasibility.md)
- **Manuscript:** [spine](research_notes/2026-06-27_manuscript_spine.md) · [red-team](research_notes/2026-06-27_manuscript_redteam.md) · [reviewer panel (ultra)](research_notes/2026-06-19_reviewer_panel_ultra.md) · [scientific revision report](research_notes/2026-06-10_scientific_revision_report.md) · [paper refinement report](research_notes/2026-06-10_paper_refinement_report.md)
- **Compute / cluster:** [full compute budget](research_notes/2026-06-21_full_compute_budget.md) · [AICR memory budget](research_notes/2026-06-19_aicr_memory_budget.md) · [B200 roadmap review](research_notes/2026-06-26_review_b200_roadmap.md) · [Darwin utilization audit](research_notes/2026-06-11_darwin_utilization_audit.md)

> Daily logs and overnight sweep dumps (`2026_05_*.md`, `basinC_refine_sweep`, `modis_arc/`,
> `v3.0_arc/`) live in the same folders and are reachable from the
> [findings index](findings/index.md). They are raw session records, not curated docs.
