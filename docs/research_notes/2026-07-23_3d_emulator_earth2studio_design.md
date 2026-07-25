# 3D ocean-BGC emulator design — Earth2Studio-adaptable (2026-07-23)

> Produced by the `earth2studio-3d-emulator-design` workflow (4 study agents on the Earth2Studio model
> interface + data/IO, 3D-FNO ocean prior art, and our own emulator code; grounded in real sources +
> file:line). Track-2: the first ocean-BGC PrognosticModel for the NVIDIA Earth-2 / PhysicsNeMo stack.

I have everything I need — emulator.py is verified line-for-line, and the findings carry grounded emulator_poc.py references. Returning the design doc as my final output (per subagent contract, the parent reads my text response, not a file).

---

# Design Doc: Depth-Resolved 3D Ocean-BGC Emulator, Earth2Studio-Adaptable

**Track-2 / DarwinDiff v05 · target: first ocean-BGC PrognosticModel in the Earth-2 / PhysicsNeMo stack**
Status: DESIGN (approved-to-build). Scope: `src/darwindiff/emulator.py`, `scripts/emulator_poc.py` only, plus one new `src/darwindiff/e2s/` package for the Earth2Studio adapters.

---

## 0. TL;DR / decisions locked

| Decision | Choice | Why |
|---|---|---|
| Depth operator | **FNO2d-over-stacked-levels (channels), NOT FNO3d** — for both PoC and global production | Every production ocean emulator (Samudra, SamudrACE) treats depth as channels; v05 levels are irregular-thickness so a Fourier transform along z is ill-posed. Reserve FNO3d as a Phase-3 research probe only. |
| Global-grid operator | Keep FNO2d for AOI/PoC; **switch to SFNO for global 1° runs** | Flat FNO2d gives polar artifacts + spectral dissipation on lat/lon; SFNO fixes both and is a smaller lift than FNO3d. Known N-Atlantic-bloom bias is a global-grid failure mode SFNO directly targets. |
| E2S vertical encoding | **Depth baked into the `variable` name** (`DIC_k0`, `DIC_k1`, … `Chl1_k9`) — flat `variable` axis | Earth2Studio has no first-class depth dim; it flattens level into the variable string (`z500`). Our existing `f"{t}_k{k}"` channel naming (emulator_poc.py:442) is already E2S-lexicon-consistent. |
| Tensor layout | `[batch, variable=(tracers·levels), lat, lon]` — 4-D, depth folded into channels | Matches E2S canonical layout AND our current cube; no 5-D refactor needed for the shippable path. |
| Conservation | **Soft loss penalties** (depth-integrated mass + nonnegativity), NOT hard architecture constraints | Samudra learned conservation without hard constraints; the one physics-informed BGC 1D-CNN that hard-constrained it *underperformed persistence* at short range. Add penalties with small weights, validate they don't hurt skill. |
| Cube flow | Reuse existing `--dump-cube` / `--load-cube` — already level-aware | Round-trips `n_z` + `grid_shape` today (emulator_poc.py:1113-1123, 1063-1109); cluster transfer path already carries level metadata. |

The shippable deliverable is **depth-as-channel + a corrected E2S wrapper**. A true 5-D FNO3d is explicitly deferred and gated on a scientific need for vertical *spectral* coupling that the channel-mixing path cannot express.

---

## 1. Architecture

### 1.1 Operator choice — why not FNO3d

The instinct "go 3D → use FNO3d" is wrong here, and the prior art is unanimous:

- **Samudra** (arXiv 2412.03795, the closest proven analog: GFDL OM4, 1° global, 19 depth levels): represents all 19 levels as **channels of a 2D horizontal ConvNeXt-UNet** — "each channel is associated with a variable and a depth level." 135M params, centuries-stable, 150× faster than OM4, no hard conservation constraint. Input 158 channels, output 154.
- **SamudrACE** (arXiv 2509.12490, 2026 SOTA): 145 2D fields across 8 atmospheric + 19 oceanic levels, still a 2D-horizontal / stacked-level net. Has **no BGC** — the exact whitespace we occupy.
- **FNO3d verdict:** cost scales with an extra spectral axis (modes_z × compute) and needs a *regular, dense* vertical grid. v05/Samudra levels are irregular variable-thickness (2.5 m … 6000 m), which a Fourier transform along z handles poorly. Regional-ocean work that tried FNO3d found no decisive win over recurrent FNO2d-with-depth-as-channel.

For ~10 levels × 6-15 tracers (60-150 channels), stacked-channel 2D dominates FNO3d on both cost and correctness.

### 1.2 Tensor shapes

**Shippable path (depth-as-channel, 4-D):**
```
state:   [M, C, H, W]   with C = len(tracers) · n_z          # M=months, H=171, W=360
E2S in:  [B, V, H, W]   with V = C, variable = ['DIC_k0','DIC_k1',...,'Chl1_kZ']
```
This is exactly what `emulator_poc.py` builds today at `--levels N` (`C = len(tracers)*n_z`, emulator_poc.py:434; chan_names `f"{t}_k{k}"`, :439-442).

**Deferred true-3D path (Phase 3, 5-D):**
```
state:   [M, V, Z, H, W]                                     # separate level axis
E2S in:  [B, V, Z, H, W]  — E2S flattens Z back into variable at the interface anyway
```

### 1.3 Tracer set

Prognostic (input set == output set, so the rollout is autoregressive):
```
DIC, ALK, PIC, POC, FeT (DFe), Chl1     # 6 core, matches emulator_poc.py PoC
```
Optionally extend to the Carroll carbonate 7-state (`DFe, Ps, Pl, POC, PIC, DIC, ALK`, the current `DEFAULT_VARIABLES`, emulator.py:51). Depth-resolved variable list = tracer × level cross product.

**Forcing** (SST, wspeed, mldDepth, …) stays surface-only, concatenated on the channel axis (emulator_poc.py:114 `KNOWN_FORCING`; cat at :728-731, :891-892). In the 4-D path forcing is broadcast/left as single-level channels. In the deferred 5-D path, forcing must gain a Z axis (inject at surface level, zero-pad the rest).

### 1.4 Standardization

Per-`(tracer, level)` channel z-scoring already exists and is correct for depth-as-channel — each level is a distinct channel `c`, so DIC-surface vs DIC-deep get independent mean/std (emulator_poc.py:561-577). **Chl must be log-transformed before z-scoring** (`--log-transform`; Chl spans 2.8e6× and linear z-scoring gives negative global skill — established finding). Broadcast is `means[None,:,None,None]`.

For the deferred 5-D cube the *only* standardization change is the broadcast shape: `means[None,:,:,None,None]` and rollout de-standardize `means_t.view(1,V,Z,1,1)`.

### 1.5 Rollout

Keep the autoregressive 2-input residual scheme with N=2-4 recurrent training steps (`--rollout-train-k`; matches Samudra's N=4). Rollout guards already implemented: nonnegativity clamp (`--rollout-positivity`) and column-mean mass rescale (`--rollout-mass-conserve`, emulator_poc.py rollout_check). **Promote these two guards from per-step rollout hooks INTO the training loss** (§5) so conservation is learned, not just clamped at inference.

### 1.6 Global operator: SFNO

For the global 1° path, swap FNO2d → **SFNO** (spherical harmonic transform, SO(3)-equivariant, kills polar artifacts + spectral dissipation). Available in `neuraloperator` and PhysicsNeMo, same API family. Alternative: Samudra-style ConvNeXt-UNet (135M params is the proven global-1°-19-level working point; a UNet handles 150 channels more memory-cheaply than an FNO whose spectral weights scale modes²×width²). Use **circular longitude padding + polar zero-pad** regardless of operator.

---

## 2. Earth2Studio wrapper — `PrognosticModel` skeleton

The wrapper is the existing `DarwinEmulator` class (emulator.py:134), which already mirrors the contract but has **three conformance bugs** to fix (§2.2). Target file: `src/darwindiff/e2s/prognostic.py` (or edit `DarwinEmulator` in place).

### 2.1 Skeleton (real code)

```python
# src/darwindiff/e2s/prognostic.py
from collections import OrderedDict
from typing import Iterator
import numpy as np
import torch

# earth2studio is a cluster-only dep; import-guard exactly like emulator.py:36-42
try:
    from earth2studio.utils.type import CoordSystem
    from earth2studio.utils import handshake_coords, handshake_dim, handshake_size
    from earth2studio.models.batch import batch_coords, batch_func
except Exception:  # laptop / CI fallback
    CoordSystem = OrderedDict
    def handshake_dim(*a, **k): pass
    def handshake_coords(*a, **k): pass
    def handshake_size(*a, **k): pass
    def batch_func(): return (lambda f: f)
    def batch_coords(): return (lambda f: f)


class DarwinBGCPrognostic(torch.nn.Module):
    """First ocean-BGC PrognosticModel for the Earth-2 stack.

    State tensor after @batch_func compresses batch: [B, V, H, W],
    V = n_tracers * n_levels, variable names are depth-tagged: 'DIC_k0', ...
    Standardization + log(Chl) + ocean-mask fill live INSIDE this wrapper
    because Earth2Studio pipes PHYSICAL-unit tensors.
    """

    def __init__(self, core_model, variables, lat, lon,
                 means, stds, log_vars, ocean_mask,
                 dt=np.timedelta64(30, "D")):
        super().__init__()
        self.model = core_model              # the trained FNO2d / SFNO
        self.variables = list(variables)     # ['DIC_k0','DIC_k1',...,'Chl1_kZ']
        self.lat = np.asarray(lat)           # regular grid, linspace over 171
        self.lon = np.asarray(lon)           # linspace(0,360,360,endpoint=False)
        self.register_buffer("means", torch.as_tensor(means))   # [V]
        self.register_buffer("stds",  torch.as_tensor(stds))    # [V]
        self.register_buffer("mask",  torch.as_tensor(ocean_mask))  # [H,W] bool
        self.log_idx = [i for i, v in enumerate(self.variables)
                        if v.split("_k")[0] in set(log_vars)]     # Chl channels
        self.dt = dt

    # ---- coords contract -------------------------------------------------
    def input_coords(self) -> CoordSystem:
        return CoordSystem({
            "batch":     np.empty(0),
            "time":      np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable":  np.array(self.variables),
            "lat":       self.lat.copy(),
            "lon":       self.lon.copy(),
        })

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        target = self.input_coords()
        handshake_size(input_coords, "lead_time", 1)
        for i, (k, _) in enumerate(target.items()):
            handshake_dim(input_coords, k, i)
            if k not in ("batch", "time", "lead_time"):
                handshake_coords(input_coords, target, k)
        oc = self.input_coords()
        oc["batch"] = input_coords["batch"]
        oc["time"]  = input_coords["time"]
        oc["lead_time"] = np.array([self.dt]) + input_coords["lead_time"]  # accumulate
        return oc

    # ---- forward ---------------------------------------------------------
    def _standardize(self, x):          # physical -> z-space (with log(Chl))
        x = x.clone()
        for i in self.log_idx:
            x[:, i] = torch.log(torch.clamp(x[:, i], min=1e-12))
        return (x - self.means.view(1, -1, 1, 1)) / self.stds.view(1, -1, 1, 1)

    def _destandardize(self, z):        # z-space -> physical
        x = z * self.stds.view(1, -1, 1, 1) + self.means.view(1, -1, 1, 1)
        for i in self.log_idx:
            x[:, i] = torch.exp(x[:, i])
        return x

    def _forward(self, x):              # x: [B, V, H, W] physical units
        z = self._standardize(x)
        z_next = self.model(z)          # residual/positivity logic can live here
        x_next = self._destandardize(z_next)
        x_next = torch.clamp(x_next, min=0.0)          # nonnegativity guard
        x_next[:, :, ~self.mask] = 0.0                  # land fill
        return x_next

    @batch_func()
    def __call__(self, x, coords):
        out_coords = self.output_coords(coords)
        return self._forward(x), out_coords

    @batch_func()
    def _default_generator(self, x, coords) -> Iterator:
        coords = coords.copy()
        self.output_coords(coords)      # validate
        yield x, coords                 # 0th step = initial condition
        while True:                     # UNBOUNDED — caller decides nsteps
            coords = self.output_coords(coords)
            x = self._forward(x)
            yield x, coords.copy()

    def create_iterator(self, x, coords) -> Iterator:
        yield from self._default_generator(x, coords)

    # to(device) is inherited free from nn.Module
```

Key contract points enforced: `batch` is the **first** coord key (required by `_compress_batch`); `lead_time` is a `timedelta64` array and **accumulates** across steps; the iterator yields the **IC first** (0th step); `output_coords` **validates then transforms** via the handshake helpers.

### 2.2 The three bugs in the current `DarwinEmulator` to fix

These are the exact deltas from the scaffold at emulator.py:174-207:

1. **`lead_time_h` float-hours → `lead_time` timedelta64.** emulator.py:186,194 use a float-hours array named `lead_time_h`. E2S requires `np.timedelta64`. Replace with `np.array([self.dt])` accumulation.
2. **Missing `batch`/`time` dims and wrong order.** input_coords (emulator.py:175-181) advertises only `(variable, lat, lon)`. Prepend `batch` (as `np.empty(0)`) and `time`, in canonical order `batch, time, lead_time, variable, lat, lon`.
3. **`create_iterator` is bounded + entry point is `step` not `__call__`.** emulator.py:202-207 takes `n_steps` and stops; E2S wants an **unbounded** generator driven by the caller, and the single-step entry must be `__call__` (add `__call__ = step` or rename). Also move the residual/positivity logic (currently in emulator_poc.py:740-744, 896-912) INTO `_forward` so the packaged model is self-contained.

### 2.3 Wrapping the checkpoint

`save_checkpoint()` already writes weights + standardization means/stds + rebuild config (safetensors) — the right shape. **Add to the bundle:** the CoordSystem metadata (depth-tagged `variable` names, `lat`/`lon` arrays, `dt` as timedelta64, `ocean_mask`, `log_vars` list) so `input_coords`/`output_coords` reconstruct at load. Optionally add `AutoModelMixin` + `Package` for `Model.load_model(Model.load_default_package())` hub-style loading (point `Package` at a HF/local path).

---

## 3. Custom ECCO-Darwin `DataSource` skeleton

`DataSource` is a single-method runtime-checkable Protocol: `__call__(time, variable) -> xr.DataArray` with dims `['time','variable','lat','lon']`. Target file: `src/darwindiff/e2s/datasource.py`.

```python
# src/darwindiff/e2s/datasource.py
from datetime import datetime
import numpy as np
import xarray as xr
try:
    from earth2studio.data.utils import prep_data_inputs
except Exception:
    def prep_data_inputs(t, v):
        t = [t] if isinstance(t, datetime) else list(t)
        v = [v] if isinstance(v, str) else list(v)
        return t, v


class EccoDarwinV05(object):
    """Feeds v05 monthly initial conditions on a REGULAR lat/lon grid.

    Emits already-regridded, already-on-target-depth-levels fields:
    E2S fetch_data only regrids lat/lon and does NOT interpolate depth,
    and map_coords REFUSES curvilinear (LLC) grids -- so do ALL depth
    remapping and LLC->regular regridding HERE, inside __call__.
    """

    def __init__(self, cube_path, lat, lon, level_index):
        self.cube = ...            # memory-map the dumped [M,C,H,W] cube
        self.lat = np.asarray(lat)
        self.lon = np.asarray(lon)
        self.levels = list(level_index)     # k-indices baked into var names

    def __call__(self, time, variable) -> xr.DataArray:
        time, variable = prep_data_inputs(time, variable)
        # variable entries are depth-tagged E2S names: 'DIC_k0', 'FeT_k3', ...
        arrays = []
        for t in time:
            per_var = [self._read_field(t, v) for v in variable]  # each [H,W]
            arrays.append(np.stack(per_var, axis=0))              # [V,H,W]
        data = np.stack(arrays, axis=0)                           # [T,V,H,W]
        return xr.DataArray(
            data=data,
            dims=["time", "variable", "lat", "lon"],
            coords=dict(
                time=np.array(time, dtype="datetime64[ns]"),
                variable=np.array(variable),
                lat=self.lat, lon=self.lon,
            ),
        )

    def _read_field(self, t, e2s_var):
        tracer, k = e2s_var.split("_k")           # 'DIC', '0'
        # index the dumped cube by (month(t), channel(tracer,k)); returns [H,W]
        ...
```

Then drive the whole thing with the stock loop — **no `run.py`/`io.py` changes for the surface/depth-as-channel case:**
```python
import earth2studio.run as run
from earth2studio.io import ZarrBackend
io = run.deterministic(["2016-01-01"], nsteps=12,
                       prognostic=DarwinBGCPrognostic(...),
                       data=EccoDarwinV05(...),
                       io=ZarrBackend("darwin_bgc.zarr"))
```
Optionally register a `DarwinLexicon(metaclass=LexiconType)` with a `VOCAB` mapping DIC/ALK/PIC/POC/FeT/Chl1 to v05 field names (they are not in `E2STUDIO_VOCAB`, so a custom lexicon is needed if fetching from a real remote source rather than a local cube). Add a `'depth'`-aware chunk entry to `ZarrBackend` chunks only if you go true-5-D; the depth-as-channel path needs nothing.

---

## 4. Exactly what to change in our code

### 4.1 Shippable path — depth-as-channel (days, no operator rewrite)

Depth-resolved output **already runs today** via `--levels N`. The changes are the E2S wrapper fixes plus loss-side conservation.

| File:line | Current | Change |
|---|---|---|
| `emulator.py:174-181` | `input_coords` emits `(variable, lat, lon)` | Emit `batch, time, lead_time, variable, lat, lon` in E2S order; `batch=np.empty(0)`; depth-tagged variable names. |
| `emulator.py:183-195` | `output_coords` uses `lead_time_h` float hours | Use `lead_time` timedelta64, accumulate `+ input_coords["lead_time"]`; decorate `@batch_coords()`; validate with handshake helpers. |
| `emulator.py:197-207` | entry point `step`, bounded `create_iterator(n_steps)` | Add `__call__ = step` (decorate `@batch_func()`); make `_default_generator` an **unbounded** `while True`. |
| `emulator.py:170-171,166-168` | `forward` calls `self.model`; residual logic external | Move residual + positivity + mask-fill (from emulator_poc.py:740-744, 896-912) into a `_forward` in the wrapper. |
| `emulator_poc.py` (run) | — | Run `--levels 5 --log-transform --rollout-train-k 4 --rollout-positivity --rollout-mass-conserve` to produce a depth-resolved cube today. |

No change needed to the read side — `read_hfacc_topz(grid, n_z)` (velocity_loader.py:51-60), `_read_tracer_month` (emulator_poc.py:333-367 → `[Y,X,n_z]`), and `--dump-cube`/`--load-cube` (emulator_poc.py:1113-1123, 1063-1109) are already level-aware.

### 4.2 Deferred path — true 5-D FNO3d (Phase 3, larger)

Only if vertical *spectral* coupling proves scientifically necessary:

| File:line | Change |
|---|---|
| `emulator.py:54-89` | Add `SpectralConv3d`: `torch.fft.rfftn(x, dim=[-3,-2,-1])`, weights `[in,out,m1,m2,m3]`, einsum `"bixyz,ioxyz->boxyz"`, **4 corner blocks** (2^(ndim-1)). |
| `emulator.py:92-117` | Add `FNO3d` using `nn.Conv3d` for lift/local/proj. |
| `emulator.py:128` | `_validate_coords`: variable axis moves to dim **-4**, add `x.shape[-3] == len(levels)` check; require `x.ndim >= 5`. |
| `emulator.py:236` | PhysicsNeMo FNO `dimension=2` → `dimension=3`; feed `[B,V,Z,H,W]`. |
| `emulator_poc.py:434,451-453` | Stop folding levels into C; build `[M,V,Z,H,W]`. |
| `emulator_poc.py:467` | `valid_mask` `np.all(isfinite, axis=(0,1))` → per-level `[Z,H,W]` (deep cells have more land). |
| `emulator_poc.py:561-577,809-811,880-881` | Standardization/climatology/de-standardize broadcasts gain a Z axis: `means[None,:,:,None,None]`, `means_t.view(1,V,Z,1,1)`. |
| `emulator_poc.py:728-731,746-750,891-892,1137-1145` | Retarget every `torch.cat([..., zf], dim=1)` to the variable axis with matching Z (surface-inject + zero-pad); fix time-encoding 4-D broadcast `(M,2,H,W)`. |
| `emulator_poc.py:763-767` | `masked_mse_t` denom `mask_t.sum()*C` → count `Z*` cells. |

Files touched in both phases: `src/darwindiff/emulator.py` and `scripts/emulator_poc.py` only (plus the new `src/darwindiff/e2s/` package).

---

## 5. Mass / tracer-conservation checks across depth

Recipe from the physics-informed BGC 1D-CNN (arXiv 2606.27168), the only depth-resolved BGC-emulator prior art. Add as **soft loss terms with small weights**, promoted from the existing rollout guards into the training objective (which is currently only masked next-state MSE):

1. **Depth-integrated mass conservation.** For each conserved element (C via DIC+PIC+POC, N, P) penalize drift of the column-integral over ocean cells:
   `L_mass = mean_over_columns( (Σ_k h_k · c_pred − Σ_k h_k · c_true)² )`, with layer thicknesses `h_k`. Extends the current `--rollout-mass-conserve` (which rescales to pre-clamp domain mean) from a per-step rescale into a differentiable penalty.
2. **Nonnegativity.** `L_pos = mean(relu(−c_pred)²)` — extends `--rollout-positivity`.
3. **Upper bound.** `L_cap = mean(relu(c_pred − 20·mean_c)²)` — bounds each tracer at 20× its climatological mean.

**Validation harness (physics as a third validator — needs no reference data):**
- After every rollout, assert (a) column-integrated tracer drift < threshold per year, (b) zero cells with negative concentration (the emulator has been caught inventing 4.5% negative iron while scoring +0.43 skill — this check catches exactly that), (c) mixed-layer vs thermocline vertical gradient sign preserved.

**Critical caveat from the prior art:** the hard-constrained 1D-CNN *diverged earlier and underperformed persistence at 10-day range* vs the unconstrained LSTM. So: start conservation weights small, and gate them on a check that short-range skill (vs persistence, in log-space for Chl) does not regress. Conservation is a tie-breaker, not a primary objective.

---

## 6. Staged build + test plan

**Stage 0 — surface baseline (regression anchor).**
Run `emulator_poc.py --levels 1 --log-transform` on the current AOI. Confirm the known **+0.66 skill vs persistence** reproduces. Lock it as the regression baseline. Verify via `scripts/verify_run.py` (exit 0) — never report an unverified number.

**Stage 1 — add levels (depth-as-channel).**
`--levels 5 --log-transform --rollout-train-k 4 --rollout-positivity --rollout-mass-conserve`. Acceptance: (a) per-level skill vs persistence ≥ 0 at every level; (b) surface-level skill within noise of the Stage-0 baseline (adding depth must not hurt the surface); (c) `--dump-cube` round-trips `n_z=5` and `--load-cube` reconstructs tracer names by stripping `_k<n>`.

**Stage 2 — Earth2Studio wrapper.**
Implement `src/darwindiff/e2s/{prognostic,datasource}.py`; fix the three `DarwinEmulator` bugs (§2.2). Tests: (a) `isinstance(model, PrognosticModel)` passes (duck-typed); (b) `create_iterator` yields IC as step-0 then N steps with `lead_time` accumulating monthly; (c) a numeric round-trip test — E2S `run.deterministic` for 1 step equals the native `emulator_poc.py` rollout for the same IC (bit-comparable after de-standardization); (d) CI runs the import-guarded fallback (no earth2studio installed) exactly like the existing scaffold. Extend `tests/test_emulator_poc.py`.

**Stage 3 — conservation loss.**
Add the three penalties (§5) at small weight. Acceptance: conservation-drift check passes AND Stage-1 short-range skill does not regress. If skill regresses, lower weights (per the prior-art caveat).

**Stage 4 — global + SFNO (production).**
Swap operator to SFNO, circular-lon + polar-zero padding, global bounds `--aoi-bounds -80,89.75,-180,180`. Target: no polar artifacts, and check whether SFNO reframes the N-Atlantic-bloom bias (a known global-grid failure mode).

### First concrete cluster experiment

**Explorer H200** (default per user preference; single fit is launch-bound so same speed as B200 — use H200 for dev throughput). One job, self-contained (no OOM-probing in the same job — caught OOMs poison the CUDA context):

```
Stage 1 depth-resolved fit:
  emulator_poc.py --levels 5
    --tracers DIC,ALK,PIC,POC,FeT,Chl1
    --log-transform
    --rollout-train-k 4
    --rollout-positivity --rollout-mass-conserve
    --dump-cube darwin_v05_L5.npz        # dump locally first, transfer, train on cluster
  build_emulator(dimension=2, operator=physicsnemo FNO or SFNO)
```
Build inside a Slurm job, **not** the login node (known build gotcha). Gate the reported skill through `scripts/verify_run.py` (exit 0), n≥3 seeds for variance, compared vs persistence in log-space for Chl.

**Success criterion for the cluster run:** a 5-level depth-resolved v05 BGC emulator with per-level skill ≥ a per-cell seasonal AR(1) baseline at every level (persistence alone is not a sufficient bar) and surface skill matching the +0.66 persistence-relative regression check — i.e. the first global multi-tracer depth-resolved ocean-BGC operator, wrappable as the first ocean-BGC `PrognosticModel` in the Earth-2 stack.

---

### Positioning (for the related-work / grant framing)
No production 3D ocean emulator carries BGC — Samudra, Samudra-2, SamudrACE, NeuralOM, OceanNet all stop at T/S/U/V/SSH. The only depth-resolved BGC-ML art is two 1D single-water-column emulators (arXiv 2606.27168). The **global, multi-tracer, depth-resolved BGC operator is genuinely first-of-kind**, and the Earth-2 stack has zero ocean/BGC models (verified). That whitespace is the asset.