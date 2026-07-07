# DarwinDiff — next-session handoff prompt

Paste the block below as the **first message** of a fresh session. It is intentionally
detailed because long-context sessions lose detail — a new session should ground in
`STATUS.md` + auto-memory, not a compressed summary. Keep this file updated at the end of
each substantial session (it and the "Current state (2026-07-07)" section of `STATUS.md`
are the two durable state stores).

---

Resume **DarwinDiff**. **Before doing anything, read `STATUS.md` (the "Current state (2026-07-07) — the project is now TWO papers" section) and the auto-memory index in full**, then confirm the shape back to me. Long-context drift lost detail last session — ground in these files, not assumptions or a running summary.

## Where we are
The project is **two papers**:
- **Paper #1 (Track 1 identifiability study) is CLOSED** — a reference write-up at `docs/paper/main.tex` (local-only, gitignored; `cd docs/paper && latexmk -pdf main.tex`), shared with Jon Lauderdale (MIT) + the Explorer PI **as a write-up, not a submission** (frame it that way to them). Result: a 0-D differentiable surrogate + per-cell DINN identifies the **demonstrated-observable trio {alpfe, scav_rat, R_PICPOC}**; per-cell is load-bearing (7/10 n=10, 33/50 n=50, vs 0/50 global); honest **consistency check, not a discovery**; characterizes the *surrogate gap*.
- **Paper #2 = the Track-2 UDE (differentiable-Darwin), in progress.** It IS the independent-inversion validation Paper #1 lacked (#163).

## What's merged (`main`, PR #177) — the UDE foundation
- `src/darwindiff/integrators.py` — RK4/Euler + gradient checkpointing + **time-aware forcing `f(t,x)`** (RK4 fractional-stage; back-compat shim wraps legacy 1-arg tendencies) + `relative_mass_drift`.
- `src/darwindiff/carroll6.py` — `carroll6_tendency`, `carroll6_ude_tendency` (pluggable neural `ffe_closure`/`calcite_closure`), `carroll6_integrate(method="rk4")` (Euler default byte-identical).
- `src/darwindiff/transport.py` — mass-conserving batched-column vertical transport (diffusion + upwind advection) + vectorized BGC + dust/light forcing.
- Scripts: `ude_closure_identifiability_h200.py` (arms A–H = {single, multi-IC, regime, forced} × {free MLP, Monod-anchored}), `ude_forcing_design.py` (offline Fisher forcing design), `ude_transport_stress_h200.py`; sbatch in `scripts/slurm/`.

## The key result (Night-1+2)
Closure equifinality is a **support problem** (a neural closure fits the trajectory but recovers the true function only where the state visits). The cure is **structural anchoring** (Monod backbone + bounded NN correction, ≈15× better than a free MLP) **+ excitation you design offline** — a ~2-min CPU Fisher probe found the lever is **light-driven drawdown, not dust** (winner `drawdown_pulse`, design λ_min ↑330×). Excitation ladder (n=4, full-domain closure error): `0.203 → 0.173 → 0.154 → 0.116`. Free MLP NaN'd under strong forcing (structure buys stability). Transport conserves ~5 ppm/68 yr; checkpointing ~100× memory.

## The open thread — parameter learner ↔ emulator
Three components: **DINN** (per-cell parameter learner), **FNO emulator** (`emulator.py`, scaffold, spatially coupled, **NOT parameter-aware**, for long climate runs), and the mechanistic **UDE**. The **seam**: the parameter learner's ceiling is the surrogate gap; the fix is a spatially-resolved differentiable forward model to backprop through — the emulator IF **parameter-conditioned** (`FNO(state, Carroll-6 field) → next`), or the UDE. **Not yet built or researched.**

## Immediate next actions (in order)
1. **Research-first (cheap):** deep-research dive on *parameter-conditioned differentiable emulators for gradient-based calibration* (BINN, NeuralGCM, neural-operator conditioning, amortized / simulation-based inference; when the FNO's extrapolation risk forces the mechanistic UDE). Save to `docs/research_notes/`.
2. **Build (autonomous, cluster/CPU):** (a) symbolic distillation — save the trained Monod-anchored closure, distill to a formula (STLSQ vs a Monod dictionary on the *visited* support) = the go/no-go; (b) real Phase-1 transport — batched **Thomas** vertical diffusion + **centered** flux-form advection per `docs/research_notes/2026-07-06_ude_phase1_design_brief.md`; (c) parameter-condition `emulator.py` + a test that the DINN backprops through it.
3. **Prep for Jon (Paper #2-defining):** iron vs calcite closure target; what drives calcification (his call); offline transport scope OK; forcing realism (synthetic drawdown vs real seasonal cycle); what independent validation = discovery; fold in his two R_PICPOC points.

## Hard constraints
- **Local RTX 5090 is IN USE — cluster (Explorer H200, `ssh explorer`) or CPU only for compute.** Repo on cluster: `/projects/schultz/qi.zim/ecco-darwindiff` + `.venv`; deploy via `scp`, run via sbatch (`--partition=gpu --gres=gpu:h200:1`, or T4/A100 for light work).
- A caught CUDA OOM in a sweep poisons the context → run OOM-probing in a separate job from training.
- Commit conventions: scope-prefixed titles, **NO Co-Authored-By**, non-squash merges, `2imi9/` branches, stage explicit paths (shared checkout can switch branch mid-task — verify `git branch --show-current` before every commit). `verify_run.py`-gate any recovery number. **Research-first / cost-first.**

Start by reading `STATUS.md` + memory, confirm the shape, then begin with action 1.
