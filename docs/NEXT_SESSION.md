# DarwinDiff — next-session handoff prompt

Paste the block below as the **first message** of a fresh session. It is intentionally
detailed because long-context sessions lose detail — a new session should ground in
`STATUS.md` + auto-memory, not a compressed summary. Update this file + the STATUS.md
"Current best" / "Track 2" sections at the end of each substantial session.

---

Resume **DarwinDiff**. **Before acting, read `STATUS.md` (the "Current best" and "Track 2"
sections) and the auto-memory index in full**, then confirm the shape back to me — long-context
drift lost detail last session; ground in these files, not a running summary.

## Shape: two papers
- **Paper #1 (Track 1 identifiability study) is CLOSED** — a reference write-up at `docs/paper/main.tex`
  (local-only, gitignored; `cd docs/paper && latexmk -pdf main.tex`), shared with Jon Lauderdale (MIT)
  + the Explorer PI **as a write-up, not a submission** (frame it that way). Result: 0-D differentiable
  surrogate + per-cell DINN identifies the **demonstrated-observable trio {alpfe, scav_rat, R_PICPOC}**;
  per-cell load-bearing (7/10 n=10, 33/50 n=50, vs 0/50 global); honest **consistency check, not a discovery**.
- **Paper #2 = the Track-2 UDE (differentiable-Darwin), in progress.** It IS the independent-inversion
  validation Paper #1 lacked (#163).

## Merged (`main`, #177) — the UDE foundation
`integrators.py` (RK4/Euler + gradient checkpointing + **time-aware forcing `f(t,x)`** + `relative_mass_drift`);
`carroll6_ude_tendency` (pluggable neural `ffe`/`calcite` closures); `transport.py` (mass-conserving
batched-column vertical transport + dust/light forcing). Scripts: `ude_closure_identifiability_h200.py`
(arms A-H), `ude_forcing_design.py`, `ude_transport_stress_h200.py`; sbatch in `scripts/slurm/`.

## Key result (Night-1+2, SYNTHETIC self-twin — not real Darwin)
Closure equifinality is a **support problem**. Cure = **structural anchoring** (Monod backbone + bounded
NN correction, ~15x vs free MLP) **+ excitation designed offline** (CPU Fisher probe: light-driven drawdown,
not dust, wins; design lambda_min ↑330x). Excitation ladder (n=4, full-domain closure error):
`0.203 -> 0.173 -> 0.154 -> 0.116`. Free MLP NaN'd under strong forcing (structure buys stability).
Transport conserves ~5 ppm/68 yr; checkpointing ~100x memory. **Honesty guardrail: synthetic methods
result, NOT a real-data claim** — the E2 gate (held-out real-data R^2 > 0 with transport) is still unbuilt.

## Open thread — parameter learner <-> emulator
Three components: **DINN** (per-cell parameter learner), **FNO emulator** (`emulator.py`, scaffold, spatially
coupled, NOT parameter-aware, for long climate runs), and the mechanistic **UDE**. Seam: the parameter
learner's ceiling is the surrogate gap; the fix is a spatially-resolved differentiable forward model to
backprop through — the emulator IF **parameter-conditioned** (`FNO(state, Carroll-6 field) -> next`), or the
UDE. **Not yet built or researched.**

## Immediate next actions (in order)
1. **Research-first (cheap):** dive on *parameter-conditioned differentiable emulators for gradient-based
   calibration* (BINN, NeuralGCM, neural-operator conditioning, amortized / simulation-based inference).
2. **Build (autonomous, cluster/CPU):** (a) symbolic distillation of the trained Monod-anchored closure
   (STLSQ vs a Monod dictionary on the visited support = go/no-go); (b) real Phase-1 transport (batched
   **Thomas** vertical diffusion + **centered** advection per `docs/research_notes/2026-07-06_ude_phase1_design_brief.md`);
   (c) parameter-condition `emulator.py` + a DINN-backprop-through-emulator test.
3. **Prep for Jon (Paper #2-defining):** iron vs calcite closure target; what drives calcification (his call);
   offline transport scope OK; forcing realism (synthetic drawdown vs real seasonal cycle); what independent
   validation = discovery; fold in his two R_PICPOC points.

## Hard constraints
- **Local RTX 5090 is IN USE — cluster (Explorer H200, `ssh explorer`) or CPU only for compute.** Cluster repo:
  `/projects/schultz/qi.zim/ecco-darwindiff` + `.venv`; deploy via `scp`, run via sbatch (H200, or T4/A100 for light work).
- A caught CUDA OOM in a sweep poisons the context -> isolate OOM-probing from training.
- Commit conventions: scope-prefixed titles, **NO Co-Authored-By**, non-squash merges, `2imi9/` branches,
  explicit paths (shared checkout can switch branch / carry another session's untracked WIP — verify
  `git branch --show-current`; consider a `git worktree` for commits). `verify_run.py`-gate recovery numbers.
  **Research-first / cost-first.**

Start by reading `STATUS.md` + memory, confirm the shape, then begin with action 1.
