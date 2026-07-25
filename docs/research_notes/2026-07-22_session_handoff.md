# Session handoff — 2026-07-22 (two-anchor iron inversion + showcase figure)

Detailed resume prompt for the next session. This session verified the two-anchor design that breaks the core
`alpfe`↔`scav_rat` degeneracy, built + real-data-validated the `alpfe` dust anchor, staged the sink/remin data,
and started a showcase Architecture-&-Method figure. Living plan: `docs/two_anchor_execution_plan.md`.

## FIRST — collect what is still running / just finished (gate everything through verify_run)
1. **B200 job `177483` — the n=10 dust-anchor A/B (STILL RUNNING on AICR at handoff).**
   - `ssh aicr` (cert auth, no Duo). Check: `sacct -j 177483 --format=JobID,State,Elapsed -X`.
   - JSONs land at `/scratch/qi_zim_neu/dust_ab/n10/{A_dustW0,B_dustW5}/` (seeds 0-9, both configs).
   - Grade **per-AOI ≥2-of-3** (`band_of` Cal+ ≤40%) for alpfe / scav_rat / R_PICPOC / diatomgraz; medians;
     alpfe↔scav_rat correlation across the 10 seeds. **The specific question:** is the n=5 `R_PICPOC` uptick
     (3/5 → 5/5 under the dust anchor) REAL or seed noise? Expect alpfe stays ~10/10 (now *principled*),
     scav_rat stays ~0 (source anchor can't move the sink leg — that's the honest prediction).
   - Result note started at `docs/findings/2026-07-22_dust_anchor_ab_b200.md` (n=5 recorded); append n=10.
2. **diatomgraz dilution-grazing diagnostic** (agent finished mid-run). Check `scripts/analysis/` for a
   `realgraze` arm + a JSON in scratchpad. The GATE was: does the large-vs-small size-fraction grazing-mortality
   CONTRAST isolate `diatomgraz` (palatability) from grazer/biomass? If guard passed, is the `diatomgraz` profile
   CURVED (span >0.5) vs the FLAT bSi baseline (span 0.039)? If curved → ingest real Schmoker 2013 dilution data.
3. **Real-box geometry validation** (5090, agent finished). Check for a per-config table (two_anchor_realbox.py).
   Self-twin → validates identifiability GEOMETRY, not real-data recovery.

## THE STATE (scoreboard)
- **`alpfe`** — recoverable (50/50 anchors-only) AND corroborated out-of-band: the Xu & Weber 2021 ocean-Al
  inverse deposition (BCO-DMO 922468, cached `data/xu_weber_2021/`, loader `src/darwindiff/xu_weber_loader.py`)
  implies `alpfe`≈1.15 in the Saharan N. Atlantic ≈ Carroll 0.93. Wired into `run_v3.0` as a Gaussian prior
  (env levers `DUST_ANCHOR_W`/`_MU`=1.15/`_SIGMA`=0.7; no-op at W=0).
- **`R_PICPOC`** — recoverable (Daniels calcite anchor, 50/50). Possible dust-anchor bonus (see item 1).
- **`scav_rat`** — the binding leg (0/50 anchors-only). Two-anchor OSSE breaks it (|ρ| 1→0.20) *conditional on
  the export partition*; red-team bounds it to a factor ~2 (NOT point-ID). Sink data loaders built:
  Cochran ²¹⁰Po/²¹⁰Pb (source-free) + Black ²³⁴Th flux + Rufas POC + Gledhill Fe′ (operator only). Phase-2 =
  build the sink anchor WITH the uptake/export partition (living-biomass + particle-class Fe:Th) — assimilate the
  FLUX not τ; present scav_rat as BOUNDING.
- **`diatomgraz`** — recoverable once MLD is a DINN input channel; with the bSi diagnostic OFF (`POSI_W=0`) it
  still reaches **35/50** per-AOI via chlorophyll + MLD, so it is NOT a bSi tautology. The Chl target is Darwin's
  own output, so this is model-internal consistency, not independent real-data validation — the dilution
  grazing-RATE anchor is still the path to an independent anchor (item 2).
- **growth pair** — unobservable by construction (honestly excluded). δ56Fe = NO-GO (fixed ligand). Emulator↔UDE
  coupling + field-reconstruction = dead by evidence.
- **External landscape** — niche intact (Neural-BGC does DO/NO3 only; M2LINES zero-BGC); information-wall thesis
  triangulated. Manuscript reframe: from "limits" → "observing-system design that BREAKS the degeneracy."

Key findings notes (all `docs/findings/2026-07-22_*`): two_anchor_osse_verified, two_anchor_redteam,
dust_anchor_phase0, dust_anchor_ab_b200, anchors_only_n50_verified, column_osse_result,
iron_bottleneck_solution_map, neuralbgc_m2lines_landscape. Data plan: `docs/data_acquisition_roadmap.md`.

## THE FIGURE TASK (user-requested, in progress)
Make the **"ECCO-DarwinDiff · Architecture & Method"** figure genuinely SHOWCASE-attractive — the current one is
"too simple and normal." Use the newly-installed **`tikz` skill** (`.claude/skills/tikz/`, renders TikZ→SVG with
instant browser preview — faster than the pdflatex loop) and the TikZ tutorial the user gave:
`https://mkofinas.github.io/tikz_tutorial.pdf`.
- Current files: `docs/figures/tikz/architecture_method.tex` (clean, detailed, compiles rc=0) and
  `architecture_method_hero.tex` (showcase WIP — cards+shadows+dashboard, needs a robustness pass on the nested
  disc nodes / node-naming). Style pkg: `docs/figures/tikz/darwindiff-tikz.sty`. Verdicts must match
  `param_identifiability.tex` (alpfe ident 49/50, scav_rat basin-fragile 26/50 per-AOI and the trio's binding leg,
  R_PICPOC ident 50/50, diatomgraz recoverable 35/50 per-AOI from a non-circular model-internal Chl+MLD observable,
  growth unobservable; the global-scalar control holds the trio **0/50**).
- **USER FIX TO APPLY:** the `environment` node lists only "SST · wind · MLD" — too few. Add the fuller covariate
  set the DINN/box actually use: **SST · wind · MLD · SSS · pCO2_atm · CO2 flux · iron-dust forcing (+ velocity)**
  (verify against the AOI caches `eqpac_targets_*.pt` keys and `run_v3.0`/DINN inputs before finalizing).
- Aim: soft-shadowed cards, colored accents/icons, zoned bands, a hero backward-pass loop, dashboard result row —
  but keep it legible and paper-usable. Then offer to wire into `main.tex` via `\includestandalone{...}`.

## WORKING AGREEMENTS (unchanged)
Gate every recovery number through `scripts/verify_run.py` (exit 0); never report unverified. Manuscript is
LOCAL-ONLY (`docs/paper/` gitignored) — never git-track it; call it a "write-up" to Jon/Schultz. Commit only when
asked; scope-prefixed titles; NO `Co-Authored-By`; non-squash merges; verify branch before every commit.
**Compute: use the Explorer H200 or AICR B200, NOT the local 5090** (H200 queue can be ~30h — B200 `b200-batch`
was free and immediate; `ssh aicr`, `--account=p2026_0089_neu --gres=gpu:b200:1`, env `~/dd_venv`). FIM/identifiability
jobs can run CPU-short. Report contradictions loudly (this session: corrected "verified break" → "breaks in
direction, bounds to factor-of-few"; corrected the R_PICPOC/scav_rat over-reads). At session end update the issue
tracker + memory.
