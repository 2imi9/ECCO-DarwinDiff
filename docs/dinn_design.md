# DINN Design — Per-Cell Differentiable Parameter Recovery

How DarwinDiff replaces ECCO-Darwin's Green's-functions biogeochemistry calibration with a per-cell neural network trained by gradient descent through a differentiable box model. Companion to [README.md](../README.md) (project overview) and [STATUS.md](../STATUS.md) (live results).

## The problem we're replacing

ECCO-Darwin (Carroll 2020 / 2022) calibrates its biogeochemistry side using **Green's functions** (Menemenlis et al. 2005). The mechanics:

1. Pick a small set of biogeochemical parameters to tune (Carroll's published calibration: 6 — `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC`).
2. Run the full ECCO-Darwin model forward at the baseline parameter values, then again with each parameter perturbed individually.
3. Linearly invert the perturbation responses against observations to find the parameter vector that best matches.

Two structural limits of this approach:

- **Global-scalar parameters.** Each tuned parameter takes a *single value* applied uniformly to every grid cell. The ocean isn't uniform — phytoplankton growth rates differ between subtropical gyres and HNLC equatorial upwelling, iron scavenging differs near coastal sediments vs the open ocean — but Carroll's calibration cannot express that heterogeneity by construction.
- **Per-parameter cost.** Each new tuned parameter requires a fresh full forward run. Carroll handled 6 parameters; scaling to 60+ tunable knobs is prohibitive.

DarwinDiff attacks both at once.

## The DarwinDiff approach (high level)

Two changes vs Green's functions:

1. **Make the BGC simulation differentiable.** Reimplement the box-model dynamics in PyTorch so autograd can compute gradients of the loss w.r.t. every parameter in one backward pass — replacing N independent perturbation runs with one gradient computation.
2. **Let parameters vary across space.** Instead of one global vector, predict a per-cell parameter vector via a small neural network conditioned on each cell's local environmental conditions (SST, mixed-layer depth, wind, latitude). The network is the function `env → params`; gradients flow from the loss through the box model into the network's weights.

This combines into a single training loop:

```
For each epoch:
  1. Network: env_per_cell → 6 raw values per cell
  2. Sigmoid bounding into Carroll's PARAM_BOUNDS → 6 physical params per cell
  3. Box model: integrate from initial state for N steps using per-cell params
  4. Loss: spatial-pattern MSE between predicted state and Darwin's actual state
  5. Backward: gradients reach the network via autograd through the box model
  6. Adam step on network weights
```

After training, the network *is* the calibration: feeding any (lat, lon) cell's environmental conditions through it produces that cell's calibrated Carroll-6 vector.

## The DINN architecture (current production)

`DINN` (Darwin-Informed Neural Network) and its upgrade `DINNDeep` live in [`src/darwindiff/networks.py`](../src/darwindiff/networks.py). Both are **per-cell**: every cell is processed independently by the same function, with no information shared between cells beyond what's already encoded in the cell's own environmental input.

### DINN (baseline, ~454 weights)

Used in notebooks 09–14 for the structural-ceiling argument.

```
Input:   [n_input_channels=1, H, W]   # SST normalized, per cell
Layer 1: 1×1 Conv → 16 channels       # per-cell linear
         Tanh
Layer 2: 1×1 Conv → 16 channels       # per-cell linear
         Tanh
Output:  1×1 Conv → 6 channels        # 6 Carroll-6 raw values per cell
         (no activation; sigmoid bounding happens via bounded_params)
```

The 1×1 kernel is the architectural commitment: every cell's parameter prediction depends only on that cell's own input. Adding spatial coupling (3×3+ kernels, attention) would let the network smooth predictions via neighbor information, conflating the per-cell parameter advantage with a smoothing advantage. See `docs/research_log.md` §F2 for the rationale in detail.

### DINNDeep (production for within-AOI fits, ~9.4K weights)

Used in notebooks 15, 16 when fit quality matters more than the cleanest structural-argument framing.

```
Input:        [n_input_channels=4, H, W]  # SST + MLD + windspeed + latitude
Input proj:   1×1 Conv → 32 channels
Block × 4:    pre-norm → GELU → 1×1 Conv → pre-norm → GELU → 1×1 Conv + skip
              (per-cell LayerNorm — see custom _PerCellLayerNorm)
Output norm:  pre-norm → GELU
Output proj:  1×1 Conv → 6 channels
```

`_PerCellLayerNorm` normalises over the channel dim independently at each (h, w) position. Vanilla `GroupNorm(num_groups=1)` would couple cells via shared normalisation statistics, breaking per-cell semantics — verified by the `test_dinn_deep_is_per_cell` test (perturb one cell's input → only that cell's output should change).

DINNDeep adds: more input features, more capacity, modern training niceties (residuals, GELU, layer norm). Stays per-cell so the structural argument is preserved.

### Sigmoid bounding (carroll6.bounded_params)

Both networks output unbounded values. Carroll's published parameter ranges are physical bounds — `alpfe ∈ [0.05, 1.0]`, `scav_rat ∈ [3e-8, 3e-6] /s`, etc. (see `src/darwindiff/carroll6.py::PARAM_BOUNDS`). The output is mapped via:

```
param_i = lo_i + (hi_i - lo_i) * sigmoid(raw_i)
```

This guarantees recovered parameters stay biologically sensible regardless of network output magnitude. It also makes the optimisation landscape friendlier — the network output can be unbounded while the box-model receives well-conditioned inputs.

## The training loop

```python
# Pseudocode of one epoch (matches the actual notebooks)
theta = network(env_dev)                    # [6, H, W] unbounded
params = bounded_params(theta, bounds_dev)  # [6, H, W] in physical ranges

state = state0_dev                          # [5, H, W] uniform initial state
for _ in range(N_STEPS=200):                # forward-Euler integration
    state = carroll6_step(state, params, dt=0.25)  # per-cell evolution

phyto = state[1] + state[2]                 # P_s + P_l, per-cell biomass
phyto_z = z_score(phyto[ocean_mask])        # standardise over ocean cells
target_z = z_score(target_field[ocean_mask])

loss = mean((phyto_z - target_z)**2 over ocean cells)
loss.backward()                              # autograd through 200 box-model steps
optimizer.step()                             # update network weights
```

Key points:

- **Loss is z-scored MSE** on the spatial pattern, not absolute magnitude. Decouples calibration from scale; the network only needs to match the *shape* of the target field.
- **Box model integrates 200 forward-Euler steps** to a near-steady state per epoch. This is the spin-up; the loss compares steady-state predictions, not transient dynamics. (Time-resolved fitting is Track 2.)
- **Mask is applied** so land cells don't contribute to the loss but the per-cell network still produces outputs everywhere (those outputs just don't affect gradients).
- **Adam at lr=5e-3, 1500 epochs.** Typical local-GPU run is ~7–8 min for one fit; DINNDeep is similar despite 21× more weights because the bottleneck is the 200-step box-model integration, not the network forward.

## The structural argument

The clean version of the project's scientific claim:

Define two parametric classes for Carroll-6 calibration:

- **Global-scalar class (Carroll's Green's-functions class):** a single 6-vector applied uniformly to every cell. Equivalent to a per-cell function that ignores its input and returns a constant.
- **DINN per-cell class:** a per-cell function `env → 6-vector` parameterised by a small neural network.

The DINN class **strictly contains** the global-scalar class — a network can collapse to a constant function by learning zero weights. So DINN's loss can never be worse than the optimal global-scalar fit. The interesting question is whether DINN's loss is strictly lower, which happens iff the target field has spatial structure expressible only by per-cell parameters.

In every fit (notebooks 09–14), the answer is yes: the global-scalar class produces a constant prediction (mathematically required by uniform parameters + uniform initial state) and Pearson r against the spatially-varying Darwin field is undefined. DINN per-cell produces a non-trivial r in every fit. The loss ratio Global / DINN quantifies how much spatial structure the per-cell class captures that the global-scalar class cannot.

This is the cleanest restatement of the DarwinDiff scientific claim: **per-cell parameters can express what global-scalar parameters cannot, and Carroll's published calibration is bounded by the global-scalar ceiling**, no matter how well the 6 numbers themselves are tuned.

See `docs/findings/2026_05_09.md` for quantitative results across three basins.

## Variants and when to use them

| Network | Inputs | Params | When to use |
|---|---|---|---|
| `DINN` (baseline) | SST only (1 channel) | ~454 | Structural-argument fits where the cleanest comparison to global-scalar matters more than absolute fit quality. Default for cross-basin claims (notebook 11, 13, 14) — less interpolation slack to mask extrapolation failure (see notebook 16 finding). |
| `DINNDeep` (production) | SST + MLD + wind + lat (4 channels) | ~9.4K | Within-AOI fits where you want maximum r. Notebook 15. **Don't extrapolate across spatial blocks** — notebook 16 cross-validation showed DINNDeep's r=1.000 is interpolation only (held-out r drops to 0.301 on block hold-out). |
| `DINNRegional` | Region-level scalar features | ~166 | Region-level (not per-cell) fits. Notebook 06's two-regime synthetic benchmark. Largely superseded by DINN per-cell variants for current work. |

## Scope and honest caveats

- **The box model is a 5-tracer proxy of full Darwin 3.** `carroll6_step` integrates DFe + Ps + Pl + POC + PIC. Darwin 3 has 5 phytoplankton functional types (collapsed here into Ps + Pl) + 2 zooplankton + DOM + carbonate chemistry + more. **This proxy is the dominant recovery-bias source** (notebook 15: more network capacity does not reduce the systematic offsets vs Carroll's published parameter values). Closing the gap to Carroll's actual values requires extending the box model — currently the highest-priority follow-up.
- **DINN is per-cell, not spatially-coupled.** Real ocean BGC has advection / diffusion connecting cells. The current setup ignores that because the truth structure for parameter values is per-cell — each cell has its own Carroll-6 vector. Track 2 (emulator) will use different architectures with explicit spatial coupling.
- **DINNDeep doesn't extrapolate spatially** (notebook 16). For within-AOI fits, fine. For applying a network trained on AOI A to AOI B, it'll fail — train per-AOI or use the smaller DINN baseline.
- **Single-target loss per fit** so far. Multi-tracer joint loss (NO₃ + Chl + DIC + FeT simultaneously) is a future direction; should reduce parameter degeneracy that DINNDeep exposes.
- **Climatology only, not time-resolved.** All current fits use the time-mean over 23 years of monthly Darwin output. Time-resolved fitting opens Track 2 emulator territory and needs cluster compute.

## Where in code

| Concept | File |
|---|---|
| Box-model dynamics + Carroll's optima + parameter bounds | [`src/darwindiff/carroll6.py`](../src/darwindiff/carroll6.py) |
| `DINN` and `DINNDeep` networks | [`src/darwindiff/networks.py`](../src/darwindiff/networks.py) |
| Sigmoid bounding (`bounded_params`) | [`src/darwindiff/carroll6.py`](../src/darwindiff/carroll6.py) |
| NaN-safe Pearson r diagnostic for evaluation | [`src/darwindiff/diagnostics.py`](../src/darwindiff/diagnostics.py) |
| Loaders for ECCO-Darwin v05 outputs | [`src/darwindiff/ecco_darwin_loader.py`](../src/darwindiff/ecco_darwin_loader.py), [`src/darwindiff/llc270_loader.py`](../src/darwindiff/llc270_loader.py) |
| Training loops + per-AOI experiments | [`notebooks/`](../notebooks/) (10–16) |
| Tests | [`tests/`](../tests/) (104 passing as of Track 1 v1.5) |

## See also

- [README.md](../README.md) — project overview and headline results
- [STATUS.md](../STATUS.md) — live status and checklists
- [docs/findings/2026_05_09.md](findings/2026_05_09.md) — quantitative findings from notebooks 10–16
- [docs/research_log.md](research_log.md) — chronological decision log (Section F covers Track 1 v1.0–v1.5)
- [docs/ecco_darwin_parameter_inventory.md](ecco_darwin_parameter_inventory.md) — verified Carroll-6 parameter list
