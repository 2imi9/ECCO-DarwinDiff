# Two-anchor iron inversion — living execution plan (auto-updated)

Autonomous mode (set 2026-07-22): as each background result lands, analyze → update this plan → launch the next
step via workflow/agent, without pausing. Stop only for genuine blockers: a large file the user must stage, a
registration-gated dataset, a collaborator ask, a git commit, or a real scientific fork.

## Thesis
Diagnose the structural alpfe↔scav_rat degeneracy, then identify + verify the two-anchor observing-system design
that BREAKS it in direction and BOUNDS each parameter to a factor of a few (not point-ID). alpfe = strong leg
(dust source anchor); scav_rat = bounding leg (234Th flux + export partition).

## Phase status
| phase | what | status |
|---|---|---|
| **P0** | alpfe dust anchor (Xu & Weber Al-inverse → alpfe prior) | **DONE** — B200 n=10 A/B (job 177483, both `verify_run` exit 0): alpfe **10/10 both, now principled**; scav_rat **0/10 both** (source can't move sink); **R_PICPOC uptick was SEED NOISE** (6/10→8/10, Fisher p≈0.63, identical medians ~0.058; joint grade 7/10 for both). See dust_anchor_ab_b200.md |
| **P1** | pull open sink+remin datasets + build loaders (Black flux, Cochran Po/Pb, Rufas POC, Gledhill Fe′) | **DONE** — 4 loaders built+smoke-tested; scav_rat now double-sourced (Cochran source-free + Black bounding); Rufas=remin; Gledhill=operator-only |
| **P2** | sink anchor: 234Th flux + export partition (living-biomass + particle-class Fe:Th). scav_rat BOUNDING | **UNBLOCKED (P0 done); GEOMETRY GATE PASSED.** Real-box self-twin (job 179387) confirms the two-anchor design breaks `|ρ(alpfe,scav)|` 0.472→0.061 in the real box (dust→0.195 ≈ OSSE 0.20), **conditional on the partition** (both_pinned 0.061 vs both_free 0.131) — see 2026-07-22_realbox_geometry_result.md. Loaders ready: `cochran_gp15_po_pb_loader.scavenging_1deg_grid` (source-free J_Po), `black2020_fe_flux_loader.fe_export_province` (bounding Fe export), `rufas2024_poc_flux_loader` (POC/Teff = uptake leg). Partition still needs ATP/particle-class → scav_rat BOUNDING (factor ~2), not point-ID. Self-twin ≠ real recovery (still 0/10 on real data) |
| **P-novelty** | **diatomgraz dilution-grazing anchor** (real grazing RATE, not circular bSi) — could make the trio a QUARTET | **DONE — INCONCLUSIVE (negative).** Guard passed *degenerately* (box has no grazer-biomass tracer → rate trivially isolates diatomgraz; NECESSARY not SUFFICIENT); realgraze profile INVALID/unbracketed (argmin on upper edge). No identifiability win; do NOT ingest Schmoker yet. See 2026-07-22_diatomgraz_realgraze_diagnostic.md |
| **P3** | manuscript #1 reframe (observing-design thesis) | can start in parallel |
| **P-cross** | #152 multi-start array; B200 staging; collaborator asks (Jon: ensemble, remin diag, GA03 contact) | queued |

## Verified results feeding the plan (findings notes)
- 2026-07-22_two_anchor_osse_verified.md — geometry breaks (export pinned)
- 2026-07-22_two_anchor_redteam.md — honest bounds: break-in-direction, factor-of-few; δ56Fe no-go; diatomgraz combo-only
- 2026-07-22_dust_anchor_phase0.md — alpfe≈1.15 from independent Al-inverse in the Sahara
- 2026-07-22_anchors_only_n50_verified.md — alpfe 50/50 (anchor-driven), scav_rat 0/50 (pattern/rate-driven)
- data_acquisition_roadmap.md — independence-clean acquisition order (scav_rat ~6-7 independent lines)

## Blockers requiring the user / collaborator (not auto-resolvable)
- Fox 2024 POC (~9.9 GB) → user stages on D:\
- GA03 soluble aerosol (BODC, registration) — the sole alpfe-solubility anchor → Jon ask
- SeaBASS EXPORTS/NAAMES/BIO-GO-SHIP (registration) → user one-time
- Jon asks: perturbed-parameter ensemble; v05 internal remin diagnostic

## Log (newest first)
- 2026-07-22 (overnight): **FLAGSHIP — covariate DINN channels recover `diatomgraz` 10/10** (from 3/10 SST-only)
  by adding MLD as a per-cell DINN input (fixes the Southern Ocean AOI); input-limited not structural; wind/full
  wreck R_PICPOC, scav_rat unmoved (still needs Phase-2 sink anchor). All `verify_run` exit 0. See
  `docs/findings/2026-07-22_covariate_channels_result.md`. Also: v06 research done (unreleased; vent-iron is the
  one change that matters); emulator 2D-globe built (a render of a real run; the `+0.664` was scored against
  **persistence**, a baseline since retired — against a per-cell seasonal AR(1) the emulator shows no significant
  skill, its useful horizon is one step, and in log space Chl scores negative vs persistence at every level, so the
  earlier MAKE verdict does not stand); Architecture figure v2
  (OlmoEarth-style, delivered). Real-box self-twin re-running (179387; 5090 too slow + noisy, B200 1h timeout —
  now n=20/600, 2.5h). Compute all on B200 (H200/Explorer open but unprovisioned; no 5090 — user asleep).
- 2026-07-22 (pm): **P0 CLOSED** — B200 n=10 A/B graded + `verify_run` exit 0 both. The n=5 R_PICPOC uptick did
  NOT survive (seed noise); alpfe principled 10/10; scav_rat 0/10 → Phase-2 sink anchor is the only path.
  **P-novelty (diatomgraz) closed negative** (unbracketed profile; box lacks grazer structure).
  Real-box self-twin lost its JSON (agent forgot `--out`); CPU rerun too slow → **re-submitted to B200 (job 178456)**.
  Figure: showcase hero rebuilt (robust sibling-node badges) + covariate fix (velocity dropped — not a Track-1 forcing).
- 2026-07-22 (am): P0 real-data diagnostic done (alpfe≈1.15); P0 H200 A/B launched; P1 loaders workflow launched.
