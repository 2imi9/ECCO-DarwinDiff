# Pre-scale-up verification — before NU AICR (B200) / native resolution

Companion to [STATUS](../../STATUS.md). Records what was verified (and fixed) on the
laptop and the free Explorer H200 **before** spending paid AICR B200 time, on the
principle *maximize cheap verification before expensive cluster runs*.

**Method.** A 5-dimension adversarial audit (parallel subagents grounded in the
code, each finding independently re-verified) on 2026-06-18, then direct laptop
execution of the cheap items. Hardware: RTX 5090 **Laptop, 23.9 GB** (not 32 GB).

## Verified good — no action

| Assumption | Result | Evidence |
|---|---|---|
| Batched-seeds ≡ sequential | exact, `0.0` diff | element-wise step; `test_seasonal_integrate` |
| `steps_per_month=122` converged | inorganic <0.03%; phyto diff on a near-zero value | spm 122 vs 976 |
| torch Blackwell-capable (B200 = sm_100) | `sm_100` + `sm_90` in `get_arch_list()` | torch 2.11.0+cu128, all-wheel lock |
| Native LLC270 load + bin-to-1° | works end-to-end (ran live) | `llc270_loader` |
| Required tracers present | PIC/POC native; Chl1/CO2_flux via bin_average | disk audit |
| env builds without a compiler | uv.lock is all wheels, no sdist | login-node `uv sync` is safe |

## Fixed (laptop)

1. **Stale editable install.** Bare `python` resolved `darwindiff` to a stale
   worktree (`.claude/worktrees/…`), so the documented command ImportError'd and a
   fresh `pip install -e .` could run old code. Re-pointed the editable install to
   main `src`; runner docstring → `uv run`. (The project `.venv` was always correct.)
2. **DIC/ALK runaway** (commit `4b7f147`). At the upper `PARAM_BOUNDS` the surface
   carbonate budget (`dDIC_1`/`dALK_1` have no analytic floor, forward-Euler has no
   clamp) ran away monotonically negative under multi-cycle seasonal spin-up —
   `DIC_1` → −2.3e4 by 8 cycles — while staying `torch.isfinite`, so the one-step
   finiteness test missed it; a latent NaN-at-native-resolution. Added a `>= 0`
   floor in `carroll6_5pft_2layer_step`. **Provably result-neutral:** an eqpac
   time-mean recovery (250 ep) is bit-identical pre/post; all 20 2-layer + seasonal
   tests pass; new `test_param_bound_extremes_stay_nonnegative_under_spinup` fails
   pre-fix.

## Verified (laptop measurement)

- **Memory scaling holds at 5×.** Measured **21.24 GB at 64M cell·step** vs **21.25
  GB predicted** by the 356 B/(cell·step) fit — the linear law does not bend at 5×
  beyond the prior max measured point. Shrinks the LLC270 time-mean extrapolation
  gap 14.8× → 2.96×. NB `torch.compile` cannot run on this Windows laptop (Inductor
  needs MSVC; silently falls back to eager), so the *compiled* memory constant and
  the seasonal speed-up remain Explorer/AICR checks.

## Forward-model probes (laptop) — can the B200 ask be shrunk?

Adversarial point from the audit: R_PICPOC may be blocked by **forward-model
physics, not resolution** — one global `W_SINK` serves both PIC and POC (collapsing
surface PIC/POC to exactly R_PICPOC) and coccolithophore-only calcite is OFF by
default, so one R_PICPOC scalar must fit the 23× eqpac↔natl PIC/POC spread.

- **Coccolith-only calcite + light PIC anchor** (`COCCOLITH_ONLY=1`, `PIC_ABS_W=0.02`,
  3-AOI, n=10): **NEGATIVE — the mutex holds.** Mean **0.30/6** (max 1/6). The iron
  pair is wiped (`alpfe` 0/10, recovered 0.10–0.39 vs Carroll 0.93; `scav_rat`
  0/10) and R_PICPOC is **not** recovered (1/10 — a single fluke at 0.041; the rest
  drift *high* to 0.13–0.24 vs Carroll 0.042). Even the lightest PIC anchor the
  mutex was probed at (0.02) still triggers the binary PIC-anchor mutex *with*
  coccolith-only calcite — an **8th independent box-scale exclusion of R_PICPOC**
  (joining loss weight, AOI mix, architecture, IC, Eppley physics, PIC anchor, ALK
  anchor). This does **not** shrink the B200 ask; it strengthens the
  native-resolution case. Untested laptop lever remaining: a PIC:POC **ratio** loss
  (vs the absolute PIC anchor) — the "estimator-side is laptop-fixable" claim.
- **Box-vs-Darwin forward fidelity** (box at Carroll values vs Darwin v05 1°):
  _planned._ If the box can't reproduce Darwin even at the true params, native-res
  recovery is precise-but-wrong (physics gap, not resolution).

## Cluster-gated — do on the FREE Explorer H200 before paid B200

- Env build / `uv sync` on a login node (confirm `download-r2.pytorch.org` reachable).
- `compile ≡ eager` recovery-grade equivalence (Linux has the compiler).
- GPU-util + wall-clock profile at native cell counts — the "~1 h/run, ~0% util" is
  *assumed, never measured*, yet it underpins both the GPU-hour ask and the AICR
  idle-GPU-reaper risk (which would kill the Python-loop-bound seasonal runner).
- Native-resolution single-AOI seasonal recovery on H200.

## B200-only (unavoidable paid checks)

- `sm_100` runtime driver satisfies the cu128 runtime (the sbatch matmul line).
- Global LLC270 seasonal fits 192 GB without checkpointing.

## Takeaway

Most of the AICR premise is testable **without** AICR, and most "native-resolution"
testing runs on the *free, granted* Explorer H200 — the genuinely B200-only checks
are narrow. Run the fast forward-model probes first: if they recover R_PICPOC on the
laptop, the wall is physics not resolution and the B200 ask shrinks accordingly.
