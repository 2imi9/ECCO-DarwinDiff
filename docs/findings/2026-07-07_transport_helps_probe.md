# Finding — "does transport help?" go/no-go probe (2026-07-07)

**Verdict: PASS (unanimous, n=5 seeds).** Adding prescribed vertical transport flips held-out iron
prediction from **negative** (the Track-1 surrogate gap) to **≈ +1.0**, on the already-merged Track-2 code,
CPU-only, with **zero new GCM runs**. This green-lights the route-(B) Phase-1 build per the decision note
([2026-07-07_param_conditioned_emulator_decision.md](../research_notes/2026-07-07_param_conditioned_emulator_decision.md), §4).

## What was tested

`scripts/transport_helps_probe.py`. A single water column (Z=16 layers, dz=25 m) with a **surface-only dust
iron source**. Truth DFe is generated **with** vertical mixing (`kz_true=50 m²/day`, so iron is carried
downward — deep iron is a *transport* product coupling the layers). We hold out a random ~30% of layers, fit
the one identifiable iron parameter `alpfe` to the observed layers **by gradient descent through the merged
forward model**, and score held-out-layer R². The *only* thing that differs between the two arms is transport
on/off:

- **A "local box"** (`kz=0`): each layer independent — the Track-1 0-D-box analog.
- **B "transport"** (`kz=kz_true`): vertical mixing present — the route-(B) analog.

## Result

| seed | local-box held-out R² | transport held-out R² |
|---|---|---|
| 0 | −0.313 | +0.993 |
| 1 | −0.628 | +1.000 |
| 2 | −0.141 | +0.996 |
| 3 | −0.306 | +1.000 |
| 4 | −0.516 | +1.000 |
| **mean** | **−0.381** (all < 0) | **+0.998** |

(A higher-resolution single run — iters=80, nsteps=250 — gives local −0.315 / transport +0.997, consistent.)

Both arms fit `alpfe` well on the *observed* layers (train R² ≈ +1.0; local recovers `alpfe`≈0.928 ≈ Carroll),
so the local box's failure is **not** a fitting failure — it is **structural**: with no mixing it has no
mechanism to place iron below the surface, so no parameter value predicts the held-out layers. Truth DFe has
depth **CV ≈ 3.2** (real spatial structure), versus the 0-D box's ~4e-5 homogenized CV (STATUS.md #163).
Gradients flowed through the merged transport in both arms (`grad flowed: True`) — a bonus mini-validation
that the Track-2 forward map is differentiable end-to-end.

## Honesty scope (memory: track2-feasibility-not-realdata)

This is a **synthetic self-twin, vertical-1D capacity result** — it demonstrates that transport gives the
forward model the *capacity* to represent per-cell iron structure the 0-D box structurally lacks. It is a
**necessary precondition** for the real E2 gate, **not** E2 itself. The real gate is **held-out R² > 0 on
real GEOTRACES/calcite cells with horizontal transport** — which needs (i) the horizontal centered-advection
operator (a Phase-1 build item, not yet merged; the merged transport is vertical-only), and (ii) real v05
velocity/κz fields for the AOI (Jon Q2). Do **not** report this as "made Darwin differentiable on real data".

## Decision consequence

Per the note's §4 rule, `R²_B > 0` where the local box gives `R²_B ≤ 0` **green-lights route (B)'s Phase-1
build order**: integrator `f(t,x)` edit (done, uncommitted WIP) → excitation design + offline-Fisher gate →
symbolic-distillation go/no-go → batched-Thomas semi-implicit diffusion → tanh-blended centered advection —
all local/CPU-gated before any H200 spend.
