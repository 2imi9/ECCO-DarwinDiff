# Learned-closure lineage — theoretical spine for Track-2 (and SOP framing)

Captured 2026-07-23 (Lucas, mid-session). Connects the DarwinDiff Track-2 UDE/emulator work to the
kinetic-theory → hydrodynamics ML-closure literature, with a rigorous-derivation anchor.

## The anchor (why coarse-scale learned operators are legitimate)
- **Deng, Hani, Ma (2025, Hilbert's 6th / Boltzmann-from-Newton).** Proves the micro→macro passage *exists*:
  the macro PDE is the provable statistical limit of the micro system under explicit scaling. Their move
  mirrors closure modeling — instead of assuming molecular chaos (particles decorrelate), they track the
  full collision history as interaction graphs and prove most of the graph can be cut without accumulating
  error. Structurally the same question a learned subgrid closure answers empirically: **which correlations
  must be kept, which are statistically negligible.** (Cite the mathematical content only — any prize/ICM
  attribution is unverified and load-bearing on nothing.)
- **Pitch line (for SOP / the emulator writeup):** Deng-Hani-Ma proved the micro-to-macro passage exists;
  the closure-learning literature below *learns* it when the analytic derivation is intractable — which is
  exactly the ocean-subgrid situation.

## The literature trail (learned moment closures)
Starting point:
- **Han, Ma, Ma, E — PNAS 2019**, "Uniformly accurate ML-based hydrodynamic models for kinetic equations."
  Autoencoder learns generalized moments, then learns the closure on them. Weinan E's group; direct ancestor.

Learned moment closures (closest to the BINN / physics-constrained per-cell philosophy):
- **Huang, Ma et al. — arXiv:2110.03682**, invariance-preserving moment closure for Boltzmann-BGK
  (Galilean / reflecting / scaling invariance built in). *If you read one for architecture discipline, this.*
- **Huang, Chen et al.** — ML moment closure for radiative transfer, series I-IV (IV: arXiv:2604.20143);
  learns the gradient of the unclosed moment with hyperbolicity constraints. Extended to linear Boltzmann
  with UQ (arXiv:2412.01932).
- **Schotthöfer et al. — arXiv:2404.14312**, structure-preserving NN for entropy-based closures
  (entropy dissipation + hyperbolicity in the architecture).

Accelerating kinetic solvers directly:
- **Xiao & Frank — JCP 2021**, NNs to accelerate the Boltzmann solution.
- **Miller et al. — JCP 2022**, NN collision operators (learns the expensive collision integral).
- **Lou, Meng, Karniadakis — JCP 2021**, PINNs via Boltzmann-BGK.

Plasma closures (same math, different field):
- **Ma et al. — Phys. Plasmas 2020**, ML surrogates for Landau fluid closure; Maulik et al. on plasma fluid closures.

If you read only two: **Han et al. 2019** (the concept) + the **invariance-preserving BGK paper** (the discipline).

## How this lands for DarwinDiff
- Track-2's learned BGC closures on prescribed transport are the ocean-subgrid instance of this program:
  the analytic closure is intractable, so learn it — but keep the invariances/constraints the physics dictates
  (the honesty guardrail: box-scale probes are synthetic self-twin, not "learned real biology").
- This reframes the deflated 1-month forward-emulator result productively: the *value* was never a weather-style
  forecaster; it is a **learned closure / coarse operator** whose legitimacy the Deng-Hani-Ma result underwrites,
  and whose correct test is multi-month/scenario horizon + invariance preservation, not 1-step skill vs AR(1).
- Feeds the FourCastNet-lineage research task (handoff #6): architecture/geometry, not the accuracy headline.
