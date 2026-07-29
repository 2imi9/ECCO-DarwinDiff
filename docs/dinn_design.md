# DINN Design — Per-Cell Differentiable Parameter Recovery

How DarwinDiff replaces ECCO-Darwin's Green's-functions biogeochemistry calibration with a per-cell neural network trained by gradient descent through a differentiable box model. Companion to [README.md](../README.md) (project overview) and [STATUS.md](../STATUS.md) (live results).

## The problem we're replacing

ECCO-Darwin (Carroll 2020 / 2022) calibrates its biogeochemistry side using **Green's functions** (Menemenlis et al. 2005). The mechanics:

1. Pick a small set of biogeochemical parameters to tune (Carroll's published calibration: 6 — `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC`).
2. Run the full ECCO-Darwin model forward at the baseline parameter values, then again with each parameter perturbed individually.
3. Linearly invert the perturbation responses against observations to find the parameter vector that best matches.

Two structural limits of this approach:

- **Global-scalar parameters.** Each tuned parameter takes a *single value* applied uniformly to every grid cell. The ocean isn't uniform — phytoplankton growth rates differ between subtropical gyres and HNLC equatorial upwelling, iron scavenging differs near coastal sediments vs the open ocean — but Carroll's calibration cannot express that heterogeneity by construction.
- **Per-parameter cost.** Each new tuned parameter requires a fresh full forward run. Carroll handled 6 parameters; scaling to the ~103 independently tunable knobs audited in [ecco_darwin_parameter_inventory.md](ecco_darwin_parameter_inventory.md) is prohibitive on cost alone. **Removing the cost barrier does not make a parameter identifiable**, and those are separate claims: DarwinDiff has only ever targeted the same Carroll-6, and even there no config recovers all four observables.

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
  4. Loss: MSE against REAL absolute-unit observations (GEOTRACES iron; Daniels/MODIS calcite)
     plus Darwin-target terms — NB the 0-D box homogenizes spatial structure, so box-vs-Darwin
     *pattern* r is not a fidelity metric; the real absolute anchors carry the identifying signal
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

The answer is yes, and the 2026-06-27 homogenization finding makes it concrete and *stronger*: at uniform parameters the box relaxes to a spatially **near-uniform** state (tracer CV → ~1e-15 by 6400 steps; `docs/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md`), so the global-scalar class produces **no** spatial structure at all — only per-cell parameter variation can. **Caveat (important):** because the box homogenizes, box-vs-Darwin spatial-pattern `r` is **not** a fidelity metric. The per-cell advantage is established (a) by the loss comparison — per-cell achieves strictly lower loss — and (b), crucially, by *where the identifying information comes from*: real, absolute, Darwin-independent observations (GEOTRACES dissolved iron; Daniels CP:PP / MODIS PIC calcite), which vary per cell and therefore require a per-cell parameter map.

This is the cleanest restatement of the DarwinDiff scientific claim: **per-cell parameters can be identified from per-cell real observations where a global-scalar vector cannot, and Carroll's published global-scalar calibration is bounded by that ceiling.** The study characterizes *which* of the **4 observable** Carroll-6 params {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`} are identifiable from real data; the growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real-world data constrains growth rates).

Quantitative results live in [STATUS.md](../STATUS.md) and [`docs/findings/`](findings/).

## Network variants

All three networks live in [`src/darwindiff/networks.py`](../src/darwindiff/networks.py).

| Network | Inputs | Params | When to use |
|---|---|---|---|
| `DINN` (baseline) | SST only (1 channel) | ~454 | Structural-argument fits where the comparison to global-scalar matters more than absolute fit quality. Default for cross-basin claims — less interpolation slack to mask extrapolation failure. |
| `DINNDeep` | SST + MLD + wind + lat (4 channels) | ~9.4K | Within-AOI fits where box-internal fit is the goal (note: r against the homogenized box field is *not* a Darwin-fidelity metric). Saturates on biomass tracers but recovers fewer real-data-identifiable Carroll-6 params than the baseline; from v2.2.x onward the project trains DINN baseline only by default. **Does not extrapolate across spatial blocks.** |
| `DINNRegional` | Region-level scalar features | ~166 | Region-level (not per-cell) fits. Superseded by DINN per-cell variants for current work. |

## Multi-AOI and PER_AOI variants

From v3.0 onward DarwinDiff trains jointly across multiple AOIs (Equatorial Pacific + N Atlantic Subpolar; v3.1 adds Southern Ocean Pacific). Two architectural patterns:

- **Shared DINN, AOI-ID channel** (`AOI_ID_CHANNEL=1`, default for v3.0+): one DINN shared across AOIs, with a per-AOI identity scalar appended to the environmental input so the shared MLP can produce regime-specific parameter mappings.
- **Per-AOI DINN with consistency penalty** (`PER_AOI_DINN=1` + `CONSISTENCY_LAMBDA=λ`): each AOI gets its own DINN, with a soft penalty on parameter divergence across AOIs. Falsified at 2-AOI in PR #58 (0/40 seeds held all six, best λ=0.1 at 3/10 for five — below baseline), and it unlocked one such path at 3-AOI with low λ (v3.1 `w2e_peraoi_lam0.1`). Both counts are historical: they are scored against the **retracted 6/6 denominator** and predate the n=50 per-AOI reconciliation; the live denominator is the 4 observable params.

## Scope and honest caveats

- **The box model is a 5-tracer proxy of full Darwin 3.** `carroll6_step` integrates DFe + Ps + Pl + POC + PIC. Darwin 3 has 5 phytoplankton functional types (collapsed to Ps + Pl in the proxy) + 2 zooplankton + DOM + carbonate chemistry + more. The 5-PFT box (`carroll6_5pft.py`) and 2-layer extension (`carroll6_5pft_2layer.py`) close part of this gap. The binding limitation is **dimensional**: the 0-D box homogenizes spatial structure (tracer CV → ~1e-15 at convergence), so identifiability must come from real *absolute* anchors rather than box-vs-Darwin pattern fidelity. Of the 4 observable params, the iron pair and `R_PICPOC` are identifiable from real data (`geo1` holds that 3-of-4 trio jointly in **25/50** seeds at n=50 under the honest per-AOI ≥2-of-3 metric — `alpfe` 49/50, `R_PICPOC` 50/50, and the binding leg `scav_rat` 25/50, which itself rises to 41/50 at 4000 epochs; the n=10 `7/10` was the precursor); `diatomgraz` is recoverable once **MLD** is a DINN input channel (SST-only sits at chance; 10/10 with MLD, and still 35/50 per-AOI with the biogenic-silica diagnostic off), but only against Darwin's own chlorophyll — model-internal consistency, not independent real-data validation; the growth pair is unobservable by construction.
- **DINN is per-cell, not spatially-coupled.** The current setup ignores advection/diffusion between cells because the truth structure for parameter values is per-cell — each cell has its own Carroll-6 vector. Track 2 (emulator) uses different architectures with explicit spatial coupling; it is built, and it is a clean negative result — physically valid, but its useful horizon is one step with no significant skill over a per-cell seasonal AR(1) baseline.
- **DINNDeep does not extrapolate spatially.** Block cross-validation gives held-out r=0.301 on FeT (vs r=1.000 in-distribution). For applying a network trained on AOI A to AOI B, train per-AOI or use the smaller DINN baseline.
- **Climatology, not time-resolved.** All current fits use the time-mean over 23 years of monthly Darwin output. Time-resolved fitting opens Track 2 emulator territory and needs cluster compute.

## Where in code

| Concept | File |
|---|---|
| Box-model dynamics + Carroll's optima + parameter bounds | [`src/darwindiff/carroll6.py`](../src/darwindiff/carroll6.py) |
| 5-PFT box matching Darwin v05 | [`src/darwindiff/carroll6_5pft.py`](../src/darwindiff/carroll6_5pft.py) |
| 2-layer extension (v2.7+) | [`src/darwindiff/carroll6_5pft_2layer.py`](../src/darwindiff/carroll6_5pft_2layer.py) |
| Carbonate chemistry (Follows 2006 + Wanninkhof 2014) | [`src/darwindiff/carbonate.py`](../src/darwindiff/carbonate.py) |
| `DINN`, `DINNDeep`, `DINNRegional` networks | [`src/darwindiff/networks.py`](../src/darwindiff/networks.py) |
| Sigmoid bounding (`bounded_params`) | [`src/darwindiff/carroll6.py`](../src/darwindiff/carroll6.py) |
| NaN-safe Pearson r diagnostic | [`src/darwindiff/diagnostics.py`](../src/darwindiff/diagnostics.py) |
| Darwin v05 loaders + AOI presets | [`src/darwindiff/ecco_darwin_loader.py`](../src/darwindiff/ecco_darwin_loader.py), [`src/darwindiff/llc270_loader.py`](../src/darwindiff/llc270_loader.py) |
| Training loops + per-AOI experiments | [`notebooks/`](../notebooks/), [`scripts/run_v3.0_*.py`](../scripts/) |
| Overnight sweep orchestration | [`scripts/overnight_v3.0_basinC_*.py`](../scripts/) |
| Tests | [`tests/`](../tests/) (run via `uv run pytest -q`) |

## See also

- [README.md](../README.md) — project overview
- [STATUS.md](../STATUS.md) — live state and findings
- [docs/cluster_setup.md](cluster_setup.md) — running on Northeastern Explorer
- [docs/findings/](findings/) — per-version technical writeups
- [docs/ecco_darwin_parameter_inventory.md](ecco_darwin_parameter_inventory.md) — verified Carroll-6 parameter list
