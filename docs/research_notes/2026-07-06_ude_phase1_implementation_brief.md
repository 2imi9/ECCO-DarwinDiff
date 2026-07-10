Now I have the exact current signatures. My grounding confirms the briefs' load-bearing claims: `Tendency = Callable[[torch.Tensor], torch.Tensor]` (line 27), `rk4_step` evaluates `f(x)` with no time arg (lines 41–45), `checkpoint(..., use_reentrant=False)` (line 113), `relative_mass_drift` docstring already anticipates the open-system budget (lines 140–142), and the probe's multi-IC knee-sampling comment (lines 123–124). The briefs' code is accurate against the real source. Here is the synthesized brief.

---

# PHASE-1 IMPLEMENTATION BRIEF — Track-2 differentiable-BGC

Three shippable workstreams, ordered by dependency. All grounded against the current `src/darwindiff/integrators.py` (autonomous `f(x)` stepper, checkpoint path with `use_reentrant=False`, `relative_mass_drift` open-system-aware) and `scripts/hybrid_feasibility_probe.py` (multi-IC knee-sampling closure test). Local 5090 for all gates; H200 only after gates are green.

---

## 1. Time-aware forcing in the integrator

**What changes:** Generalize the tendency from autonomous `f(x)` to non-autonomous `f(t, x)`, thread a Python-float `t` through `integrate → step`, and evaluate forcing at the exact fractional RK4 times. This is the load-bearing correctness point: RK4 already uses stage offsets `t, t+½dt, t+½dt, t+dt` for the *state*; the forcing must be evaluated at those *same* offsets or the measured O(dt⁴) accuracy (0.02% vs Euler 68%) silently degrades toward O(dt) because the time-input becomes a piecewise-constant staircase.

**Exact code change** (`src/darwindiff/integrators.py`):

```python
Tendency = Callable[[float, torch.Tensor], torch.Tensor]   # was Callable[[Tensor], Tensor]

def euler_step(f, x, t, dt):
    return x + dt * f(t, x)

def rk4_step(f, x, t, dt):
    k1 = f(t,            x)
    k2 = f(t + 0.5*dt,   x + 0.5*dt*k1)
    k3 = f(t + 0.5*dt,   x + 0.5*dt*k2)
    k4 = f(t + dt,       x + dt*k3)
    return x + (dt/6.0)*(k1 + 2*k2 + 2*k3 + k4)
```

- `_make_segment(step, f, dt, k, t0)`: the segment closure tracks `t = t0 + j*dt` for local step `j`, so the recomputed `t` under `torch.utils.checkpoint` is bit-identical to the forward pass. Pass the segment's **start-step index** in, do not accumulate a running float across segments (checkpoint recomputation must reproduce identical `t`).
- `integrate`: track `t = i * dt` as a Python float in every loop path (checkpoint, no-snapshot, snapshot).
- **Back-compat shim** so all Track-1 boxes keep working untouched: at the top of `integrate`, detect a one-arg tendency and wrap it — `if len(inspect.signature(f).parameters) == 1: f = (lambda g: (lambda t, x: g(x)))(f)`.

**Forcing representation** — differentiable linear interpolant over an exogenous, **non-grad** buffer, not a lookup-by-integer-step:

```python
F = <registered buffer [n_samples, n_channels]>   # NOT a Parameter, no requires_grad
def force_at(t):
    pos = t / dt_forcing
    i = int(floor(pos)); i = max(0, min(i, N-2)); w = pos - i
    return (1-w)*F[i] + w*F[i+1]
```

The closure NN input becomes `cat([state_features, force_at(t), sin(2πt/365), cos(2πt/365)])`. The harmonic clock features recast the non-autonomous problem as autonomous in an augmented input space (this is also what makes a Neural-ODE a universal approximator), letting the correction be phase-dependent without breaking the Monod backbone `f = monod(DFe;K_FE)·(1 + eps·tanh_capped_nn(...))` that already cured equifinality.

**Excitation design** (the payload, not the plumbing): drive DFe across its full identifiability domain *within a single trajectory* using multi-frequency seasonal forcing + episodic pulses, not one sinusoid. A nonlinear (Monod) closure needs **amplitude** richness, not just frequency — a pure sinusoid traces a 1-D loop in `(DFe, forcing)` space and leaves the closure unconstrained off it (exactly the equifinality seen). `dust(t)=dust_mean·(1 + a1·sin(2πt/365) + a2·sin(2πt/182+p2) + pulse_train(t))`, randomize IC DFe per trajectory, and diagnose by scatter-plotting the visited `(DFe, dust, PAR)` cloud — trust the bounded-NN correction only inside that convex hull. **Gate the forcing design offline** by reusing the repo's empirical-Fisher diagnostics (`identifiability_sloppiness.py`): accumulate `G = Σ Jᵀ J` of the closure output w.r.t. its params along the forced trajectory, and maximize `λ_min(G)` / minimize `cond(G)` *before* spending H200 hours — this turns "design the forcing" into a fast offline D/E-optimal design instead of a training-time gamble.

- **Risk:** LOW mechanically (~15-line signature change; scalar `t` is cheap, checkpointing/snapshots untouched). The real risk is silent accuracy loss if forcing is evaluated at the wrong (staircase) times — mitigated by the fractional-time RK4 above and a gradcheck. Secondary risk: forcing leaking into the backward graph — mitigated by keeping `t` a Python float and `F` a non-grad buffer; verify `d(loss)/d(F)` is unused and `d(loss)/d(θ)` finite. Mass conservation stays valid because dust input is a known source: accumulate `integrated_dust_input = Σ dt·dust(t_i)` into `relative_mass_drift`'s open-system budget path (already anticipated in the docstring, lines 140–142).
- **Needs Jon?** **No** for the integrator edit and the synthetic-twin excitation design (self-twin box, no real-data claim per the Track-2-feasibility-not-real-data guardrail). **Yes, later** only if seasonal light/dust amplitudes are meant to match a *real* Darwin/observational forcing climatology — that's a data question, not a Phase-1 blocker.

---

## 2. Symbolic-distillation acceptance test (add to the ablation)

**What it is:** a cheap, local (5090) **go/no-go gate that runs BEFORE any native-resolution H200 fit**. It distills the trained closure NN into a symbolic law and uses the recovery quality as a *second, independent identifiability oracle* that must agree with the existing Fisher/profile-likelihood diagnostics (the diatomgraz flat-profile signature).

**Exact pipeline** (new `scripts/symbolic_distill_probe.py`, extending the Test-B closure):

1. **Dense-query the frozen NN on the VISITED support only.** Register a forward hook on the closure (or append inputs/outputs inside `forward` under `torch.no_grad()`) during an eval rollout; stack `X:(N,d_in)`, `Y:(N,)`. Dedup/subsample to ~10–50k rows, record a support mask (per-dim 1–99% quantiles), and reweight by `1/kde(x)` so rare-but-real regimes (high-DFe SO cells) aren't drowned by abundant eqpac points. **Do not query a uniform grid** — off-support is where the NN extrapolates garbage and SINDy fits the garbage.
2. **Regress `Y_nn` *algebraically* against a candidate library — no numerical derivatives.** This is the key simplification vs vanilla SINDy: the closure already outputs a clean analytic flux, so it's a plain over-determined STLSQ on a static `(Θ(X), y)` table — no finite differences, no weak form needed. Standardize `Θ` columns to unit variance before thresholding, un-standardize coefficients after.
3. **Physics dictionary anchored on the Monod atom + its confounders:** a fixed-`k` bank `{DFe/(DFe+k_j)}` on a log grid (~8–12 values over 0.01–1.0), degree-2 polynomials in `(DFe, biomass)` (the confounders a NN uses to *fake* saturation), and the environmental atoms the closure actually saw (Eppley `exp(rT)`, PAR-Monod). The Monod column *winning against* the polynomial/temperature confounders IS the identifiability signal. After STLSQ picks bank column `k_j*`, refine `k` by a 1-D `minimize_scalar` line search and report against Carroll's alpfe/half-sat. Escalate to SINDy-PI null-space rational recovery **only** if the denominator structure is genuinely unknown (co-limitation `DFe/(DFe+k)·N/(N+kN)`).
4. **Term selection by Pareto + stability, not a single λ:** scan STLSQ threshold over `logspace(-4,0,25)`, take the L-corner; wrap in Ensemble-SINDy bootstrapping (pysindy `EnsembleOptimizer`, `n_models≈100`) and read per-atom **inclusion probability** — the headline identifiability metric.
5. **Three-tier validation** (in-sample R² is necessary, not sufficient): (a) held-out R² with a **spatial split** (train eqpac+natl / test SO — probes transfer); (b) **out-of-support extrapolation** — symbolic Monod must stay physical (saturate → asymptotes to 1, half-max at k) while the NN diverges; (c) **closed-loop parity** — substitute the recovered `a·DFe/(DFe+k)` back into `carroll6` growth, re-run the forward pipeline, and confirm recovery metrics hold via `verify_run.py`.

**One-line verdict** (per-PFT, per-AOI to mirror the 6/6 structure):
```
DISTILL-PASS  iff  inclusion(Monod) > 0.85  and  k stable within 20%  and  closed_loop dLoss < tol
DISTILL-FAIL  else  ->  do not spend native H200 budget
```
Guard the two dominant failure modes: (a) off-support garbage → strict support masking; (b) confounder aliasing — before regressing, compute VIF/correlation among dictionary columns; if `|corr(Monod, confounder)| > 0.95`, report **"non-identifiable given this support"** and recommend adding DFe excitation + retraining (§1) rather than trusting any single fit. This directly operationalizes the Night-1 "equifinality is a support problem, excitation cures it" finding.

- **Risk:** LOW-MEDIUM. The math (algebraic distillation, fixed-k bank) is standard and robust; the residual risk is a *false* DISTILL-PASS from an aliased confounder — mitigated by the VIF guard and the mandatory cross-check that a flat profile-likelihood must **also** fail bootstrap inclusion (agreement validates both oracles). Adds a pysindy dependency (`de Silva 2020`, `Kaptanoglu 2021`).
- **Needs Jon?** **No** — runs entirely on the synthetic-twin box, self-contained, cheap, and is precisely the artifact that *saves* his H200 budget. Report the verdict to him as a compute-gating result, not a scientific claim about real biology (Track-2-feasibility guardrail).

---

## 3. Batched-Thomas + centered-advection transport upgrade

**Do NOT build a custom `autograd.Function` first.** The Thomas algorithm (forward elimination + back-substitution) is a sequence of differentiable scalar ops; written as a pure-PyTorch loop over the Z axis (tens of layers), autograd records the ~2·Z ops and backprops exactly. Tape is O(Z) per solve — trivially small here. `torch.linalg` has **no** tridiagonal solver, so never route through the O(Z³) dense `torch.linalg.solve`.

**Exact code change** (new `src/darwindiff/transport.py` + `tests/test_transport.py`):

**(a) Semi-implicit vertical diffusion (backward-Euler, θ=1)** — this removes the explicit-diffusion CFL cap (`kz·dt/dz² ≤ ½`) that forces tiny `dt`. Build the symmetric tridiagonal `(I − dt·L)` from **shared interface diffusivities** and solve with batched Thomas:

```python
def thomas_solve(a, b, c, d):   # a,b,c,d: [B, Z] (or [B, Z, T]); a[...,0], c[...,-1] unused
    # forward elimination + back-sub via torch.unbind/stack (out-of-place -> autograd-clean)
    ...
# interior layer k, interface diffusivity kz_iface[k] shared between a[k] and c[k-1]:
#   a[k] = -dt*kz_iface[k]/dz^2 ;  c[k] = -dt*kz_iface[k+1]/dz^2 ;  b[k] = 1 - a[k] - c[k]
# no-flux ends: a[0]=0, c[-1]=0 (drop the missing flux; do NOT lump/scale the boundary rows)
```

Backward-Euler is A-stable for any `dt>0` (amplification `1/(1+dt·λ) ∈ (0,1]`); the matrix is diagonally dominant so Thomas needs no pivoting. **Mass conservation is a property of the flux-difference form, not the solver:** shared interface fluxes + exact no-flux ends make each column of `(I−dt·L)` sum to 1, so `1ᵀx_new = 1ᵀx_old` to machine precision. Assert `(A.sum(dim=-2) - 1).abs().max() < 1e-12`.

**(b) Batch over columns, sequential in Z:** flatten all leading dims to one batch axis `[B, Z, T]`, solve all tracers in one sweep, compute the diagonals **once per step** (they depend on `kz,dz,dt`, not tracer values — only the RHS changes). `torch.compile` the Z-loop into a fused kernel — this is where the H200 speedup over the 5090 shows for wide fields. **Do not reach for cuSPARSE/PCR** — not autodiff-friendly, tridiag perf regressed post-CUDA-7, and PCR's extra work only pays off at Z in the hundreds (not this regime).

**(c) Horizontal advection — centered flux-form with a tanh-blended limiter:** classic limiters (minmod/superbee/van Leer) contain `min/max/abs` with subgradient kinks and flat zero-gradient regions that starve backprop. Use a smooth convex blend: `φ(r) = σ·φ_low + (1−σ)·φ_high` with `σ = ½(1+tanh((r−1)/eps))` and softmin `smin(a,b)=½(a+b−√((a−b)²+eps²))`. Compute `r` with a clamped denominator (`r = num·den/(den²+eps)`) to avoid 0/0 at extrema; take the tendency as `−(F[i+½]−F[i−½])/dx` so it telescopes → conserves. This keeps mass conservation **and** smooth nonzero gradients everywhere — the same structure+smoothness that cured Night-1 equifinality.

**(d) Compose via Strang splitting** — backward-Euler diffusion is a *solve*, not a `d/dt`, so you can't add it as a tendency into RK4. Split per outer step, routing through the existing checkpoint path so decadal tapes stay bounded:
```python
def step(x):
    x = rk4_step(f_adv_bgc, x, t,        dt/2)
    x = implicit_diffuse(x, kz, dz, dt)          # full Thomas solve
    x = rk4_step(f_adv_bgc, x, t+dt/2,   dt/2)
    return x
```
This composes with the `integrators` module **without changing it**.

**Validation gates (5090, before any H200 run):** `torch.autograd.gradcheck` (double precision, tiny system) on the Thomas solve, the diffusion operator w.r.t. `kz` and the field, and the smooth-limiter flux; plus a `relative_mass_drift < 1e-10` closed-column regression (`bgc=False`, sources off) through the split stepper, and an analytic single-mode decay check at rate `1/(1+dt·λ)`.

- **Risk:** LOW on the diffusion/Thomas path (standard BTCS, unconditionally stable, exact conservation, vanilla autograd). MEDIUM only on the limiter `eps` (problem-scaled: too small reintroduces kink-like gradients, too large smears fronts — worth one small H200 sweep). The **custom `autograd.Function` adjoint** (adjoint = transposed Thomas solve, `grad_A = −λ⊗x` on three diagonals) stays **in reserve** — adopt only if profiling shows the backward tape hurts at your rollout length, which for tens-of-layers columns it won't.
- **Needs Jon?** **No** for the numerics, the differentiability, and the conservation gates — all self-contained and validated on synthetic closed columns. **Yes, eventually** for the real `kz` / advective-velocity fields and the offline-transport geometry when moving from the 0-D/1-D box to real decadal spatial rollouts (data/config, not a Phase-1 blocker).

---

## Build order — next 1–2 rounds

**Round 1 (all local 5090, no Jon, no H200):**
1. **Integrator `f(t,x)` edit + back-compat shim** (§1 plumbing). Smallest, lowest-risk, and it *unblocks* everything else. Land with a gradcheck confirming RK4 accuracy is preserved under fractional-time forcing and that `d(loss)/d(F)` is unused.
2. **Excitation design + offline Fisher gate** (§1 payload). Multi-frequency + pulse forcing, clock features, `cond(G)` coverage check on the synthetic twin. Produces the forced-closure training data §2 consumes.
3. **Symbolic-distillation acceptance test** (§2), wired into the existing ablation next to `identifiability_sloppiness.py`. Cross-check its inclusion-probability verdict against the profile-likelihood diagnostics — they must agree (diatomgraz flat → DISTILL-FAIL). This is the gate that decides whether any §3 native H200 spend is warranted.

**Round 2 (local gates first, then H200 only if Round-1 verdicts are green):**
4. **Batched-Thomas semi-implicit diffusion + Strang split** (§3 a,b,d) with the gradcheck + mass-drift regression on the 5090. Pure-PyTorch, no custom adjoint.
5. **Tanh-blended centered advection** (§3c), gradchecked, with the one small `eps` sweep — the only step that plausibly wants H200 time, and only after §2 returns DISTILL-PASS on the target parameter.

Rationale for the order: §1-plumbing is a hard dependency for §1-payload and §2; §2 is the cheap oracle that *gates* the expensive §3 native rollouts; §3 numerics are validated on synthetic closed columns so they never block on Jon. Custom `autograd.Function` adjoints and SINDy-PI null-space recovery both stay off the critical path — reserve, not Phase-1.

**Key files:** `src/darwindiff/integrators.py` (the `f(t,x)` edit), `scripts/hybrid_feasibility_probe.py:120-166` (closure test to extend from multi-IC to time-varying forcing), new `scripts/symbolic_distill_probe.py`, new `src/darwindiff/transport.py` + `tests/test_transport.py`, cross-checked against the existing `identifiability_sloppiness.py`.