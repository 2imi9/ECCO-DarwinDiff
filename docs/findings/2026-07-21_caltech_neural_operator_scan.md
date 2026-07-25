# Caltech (Anandkumar-lab) neural-operator scan — what actually helps us (2026-07-21)

A 14-agent adversarial workflow (`caltech-neural-operator-scan`, 7 methods × research + hostile verify,
918K tokens) mapped Anandkumar-lab neural-operator methods onto our project and challenged each against
our measured constraints (structural 1-step ceiling, dimensional surrogate gap, diffusion-adds-no-skill,
~110 monthly pairs, rank-1 iron degeneracy). Every verdict is grounded, several in our own code.

## Ranked verdict

| method | impact | the one-line reason |
|---|---|---|
| **GINO** (geometry-informed) | **MEDIUM** | *Might* clean coastal/seam artifacts in the 2-D emulator — but run the cheap geometry diagnostic first; same "richer operator, no new info" class as capacity (+0.007) and diffusion (~0). |
| CoDA-NO (codomain attention) | LOW | Wrong instrument: the emulator trains on a **binned regular lat-lon array** (`bin_native_tracer_to_1deg`), so the real gap is *non-periodic boundary + land mask in a regular grid*, not unstructured mesh. |
| SFNO (spherical) | LOW | Only matters if error is geometry-limited; decide with `emulator_err_geometry.py`, not the paper. |
| Markov/dissipative NO | LOW | Targets state-norm blow-up under composition; our ceiling is information-limited, and the UDE's "mass conservation open" may be soft-constraint slack, not blow-up. |
| PINO (physics-informed) | DEAD-END | PINO's contribution is FFT-based spectral derivatives on **periodic** grids — the exact thing that doesn't apply to non-periodic LLC270. |
| FunDPS (guided diffusion) | DEAD-END | A posterior sampler cannot manufacture information a **rank-1** likelihood lacks — it cannot break the alpfe/scav_rat null direction. |
| Generative/score NO (DDO) | DEAD-END | Our EDM null is the signature of a near-deterministic target (deep ensemble +0.14 captures the spread; diffusion ~0). |

## The convergent finding — one cheap test decides four of these

GINO, SFNO, CoDA-NO and the geometry theme all reduce to a **single, zero-new-data question**: *does the
emulator's 1-step error concentrate at coastlines / cube-face seams / high |lat|, or is it spatially
flat?*

- **Flat** → the 1-step ceiling is genuinely information-limited; GINO/SFNO/CoDA-NO are dead-ends. Close
  them with evidence.
- **Concentrated at boundaries** → part of what we call the "structural ceiling" is a discretization
  artifact, **and — the load-bearing consequence — the N-Atlantic ~5×-low chlorophyll bias (a headline
  result) may be partly artifactual** if the bloom region sits within 1–2 cells of a seam/coast. That is
  a correction worth making *before* it goes in a write-up.

**RESULT (job `8524645`, done): SPATIALLY-FLAT in all four regions.** corr(err, coastal proximity) is
~0 everywhere (natlsubpolar −0.033, npac −0.008, sopac +0.018, midatl −0.008); coastal and near-coastal
cells carry identical error. Detail: `docs/findings/2026-07-21_emulator_geometry_flat.md`. Consequences:
(a) the 1-step ceiling is **information-limited, confirmed** — GINO/SFNO/CoDA-NO drop to
**dead-end-by-evidence** for the regional emulators; (b) because the distance metric includes the domain
edge, this **also refutes the cheap pad+mask FFT fix** (the periodicity artifact costs no measurable
error); (c) the **N-Atlantic chl bias is genuine, not a coastal artifact** (highest error, but flat in
coastal proximity) — the headline stands. Untested: deep interior (tiles too small) and cube-face seams
(global cube only).

## My out-of-box read (beyond the workflow)

1. **The uniform LOW/DEAD-END is itself the answer: our problem is not architecture-shaped.** Six of
   seven fancy operators do nothing here because our bottlenecks are *data* (110 monthly pairs) and
   *information* (a correct 1-step operator buys no horizon; a rank-1 inverse degeneracy). Chasing a
   better operator is the wrong axis. The scan is a decisive negative result — publishable as "we tested
   the SOTA operator zoo against a real ocean-BGC emulation task and the ceiling is information-limited,
   not architecture-limited."

2. **The cheapest real improvement isn't GINO — it's two lines in `SpectralConv2d`.** The CoDA-NO
   verifier read our code: the FFT runs `rfft2/irfft2` with **no padding, no mask**, on a bounded ocean
   basin. Before any geometry operator, test the ~1-day fix: **zero/reflect-pad the box before the FFT +
   add a static land-mask input channel.** If that recovers most of the boundary error, the entire
   geometry-operator question is moot and we saved months. I rate this the single highest-EV emulator
   experiment on the board, and it should run right after the geometry diagnostic confirms the artifact
   exists.

3. **Track-1 is untouched by all of this, correctly.** Every agent that looked at parameter recovery
   concluded the same thing we did: the FeMIP degeneracy is a rank-1 *information* problem, so no operator
   / no diffusion sampler helps. The real Track-1 lever is *observations that break the degeneracy* (the
   GEOTRACES section gradient, not the global mean) + the EKI/CES posterior we already built
   (`eki_core.py`). The scan independently validates #187.

4. **What I would actually build next, in order:** (a) the geometry diagnostic [running]; (b) if positive,
   the pad+mask FFT fix (cheap) before GINO (expensive); (c) reframe the chlorophyll result if the bias is
   partly artifactual; (d) leave PINO/FunDPS/DDO closed. Do **not** start an SFNO/GINO port on faith.

Provenance: workflow `wf_32b3ff01-77e` (journal at
`…/subagents/workflows/wf_32b3ff01-77e/journal.jsonl`); per-method research + verdict objects retained.
