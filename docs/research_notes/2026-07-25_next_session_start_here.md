# START HERE — next session prompt (2026-07-25)

Paste the block below to resume. Self-contained; captures the last session's decision that we can self-run
ECCO-Darwin v05 on Explorer for the #163 GCM validation (no Jon compute, no resource request needed).

---

Resume ECCO-DarwinDiff. Read these first, then confirm the shape back before acting:
1. docs/findings/2026-07-24_overnight_session_summary.md  (master index of verified results)
2. docs/findings/2026-07-24_research_refinement.md  (narrative + observation-design + paper-readiness)
3. docs/findings/2026-07-23_v05_perturbation_recipe.md  (traits-override-safe perturbation recipe)
4. STATUS.md
Plus the memory index and the SessionStart open-issues list.

STATE: the identifiability science is verified and solid — scav_rat 26→41/50 (optimization-limited; natl
19→40, eqpac 6/50), diatomgraz 35/50 (non-circular, Chl+MLD, bSi off), R_PICPOC 50/50 (with real Daniels
anchor; anchor-off 6/50 epoch-matched), alpfe 49/50, per-cell architecture load-bearing (global-scalar 0/50),
no robust 4-of-4 (structural trade-off), EKI estimator-independence = backprop verdict. The H-batch doc
reframes are largely applied (STATUS bottom-line two-component gap; AGU abstract iron/diatomgraz lines). The
ONE thing that lifts the whole study from "surrogate-conditional" to a GCM claim is #163: validate the
surrogate parameter-Jacobian against the real ECCO-Darwin v05.

DECISION (verified last session): we can self-run v05 on Explorer — no Jon compute, no resource request.
- Compute: Explorer `short` partition (232 nodes, ~2-day limit, thousands of cores), account c.schultz, user
  qi.zim. Covers the ~800-core llc270 run. (`ssh explorer`.)
- Build stack present: intel/compilers-2025.0.4, intel/mpi-2021.14, netcdf/4.9.3-intel, HDF5/1.14.6 (also
  OpenMPI/4.1.6, MPICH/4.3.0b1).
- Inputs PUBLIC (HTTP 200, no auth — same NAS we already wget from): iter42 input + ecco_darwin_v5 input on
  data.nas.nasa.gov; ECCO forcing (era_xx) public.
- Storage: HOME /home/qi.zim (111 TB free); /projects/schultz (124 TB free on a 3.3 PB fs).

PRIORITY — stand up ECCO-Darwin v05 on Explorer for the #163 perturbation validation:
1. BUILD (in a Slurm job, NOT the login node): git clone MITgcm-contrib/ecco_darwin + darwinproject/darwin3
   (git checkout 24885b71). Follow v05/llc270/readme.txt. genmake2 with code_darwin + code; adapt the optfile
   from linux_amd64_ifort+mpi_ice_nas to Explorer's Intel; make depend; make -j16.
2. STAGE inputs to /projects/schultz or home:
   - https://data.nas.nasa.gov/ecco/llc_270/iter42/input/
   - https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/input/
   - forcing: https://ecco.jpl.nasa.gov/drive/files/Version5/Alpha/era_xx and
     https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/era_xx_it42_v2 (public; if the JPL drive prompts, set
     up an Earthdata .netrc — free account).
3. RUN THE CONTROL from the provided v5 PICKUP (the assimilated state) as a SHORT segment (e.g. 1–3 yr) and
   confirm it is stable/sane. Do NOT re-simulate 1992–2023 — the pickup IS the state, so perturbation runs are
   short segments from it (cheap).
4. RUN THE PERTURBATIONS per docs/findings/2026-07-23_v05_perturbation_recipe.md: control + 4 params ×
   ÷1.2/÷1.1/×1.1/×1.2. Start with the MINIMAL 1 baseline + 1 perturbation to size wall-clock/IO, then scale.
   CRITICAL trait-override: alpfe + scav_rat in `data.darwin` `&DARWIN_PARAMS`; **R_PICPOC in `data.traits`
   R_PICPOC array (NOT `val_R_PICPOC` — overridden); diatomgraz in `data.traits` PALAT entries 36 & 43**.
   Verify each perturbed value loaded via the `STDOUT.0000` grep protocol in the recipe.
5. OUTPUT standard Darwin diagnostics at the 3 AOI footprints (eqpac/natlsubpolar/southernoceanpac):
   surface + subsurface DFe, PIC, POC, diatom Chl, biogenic silica (POSi), monthly-averaged over a fixed window.
6. GROUND TRUTH: compute the SURROGATE-side Jacobian d ln⟨tracer⟩/d ln param pushed through the SAME
   observation operators. The load-bearing test = does the cross-parameter sensitivity RANKING match
   (diatomgraz ≫ R_PICPOC > alpfe > scav_rat)? Only ranking agreement licenses transferring the surrogate
   Fisher to the GCM. Use central FD at ×÷1.1 and ×÷1.2 (nonlinearity check); v06 ≠ v05, stay on v05.

De-risk: BUILD + a minimal 1-baseline+1-perturbation run first, before the full ensemble.

SECONDARY (housekeeping): AGU abstract submit before Aug 5 (iron-focused → NG cross-list OS); refresh the stale
docs/results_matrix.md (2026-07-05 verdict); issue-tracker updates (#187/#152/#85/#188/#163) — ask before
posting. The Jon email is now OPTIONAL, a light courtesy ("reproducing v5 on Explorer for a perturbation
validation; any gotchas from the pickup?") — draft only, don't send.

GUARDRAILS: verify_run-gate every recovery number; docs/paper/main.tex is LOCAL-ONLY (show diffs, wait for my
OK, never git-track docs/paper/); commit only when I ask (no Co-Authored-By, non-squash); AICR (`ssh aicr`) for
surrogate recovery runs, Explorer (`ssh explorer`) for the GCM build; login nodes reset long ssh — grade/monitor
via server-side dependent Slurm jobs; simple warm style, no em dashes, no confidence percentages.

---
