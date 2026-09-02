"""DarwinBGCPrognostic -- an Earth2Studio ``PrognosticModel`` wrapper around the
DarwinDiff ocean-biogeochemistry FNO/SFNO emulator.

Depth is folded into the ``variable`` axis (``DIC_k0``, ``DIC_k1``, ...), exactly
as Earth2Studio encodes atmospheric levels (``z500``) -- so the model is 4-D
``[batch, variable=(tracers*levels), lat, lon]`` and needs no 5-D refactor. This
matches the cube emulator_poc.py builds at ``--levels N`` (``C = len(tracers)*n_z``).

Conformance points enforced (the three fixes vs the old scaffold):
  1. ``lead_time`` is a ``timedelta64`` array and ACCUMULATES across steps
     (not float-hours);
  2. ``input_coords`` advertises the canonical order
     ``batch, time, lead_time, variable, lat, lon`` (``batch`` first, empty);
  3. ``create_iterator`` is an UNBOUNDED generator that yields the IC as step 0,
     and the single-step entry point is ``__call__``.

earth2studio is a cluster-only dependency; on a laptop / CI the import-guarded
fallback shims below let this class import, instantiate, and run a forward pass.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator

import numpy as np
import torch

#: One emulator step. A module-level singleton rather than a call in the signature (B008).
DEFAULT_DT = np.timedelta64(30, "D")

# --- import guard: earth2studio is cluster-only ----------------------------------
try:  # pragma: no cover - exercised on the cluster
    from earth2studio.models.batch import batch_coords, batch_func
    from earth2studio.utils.coords import handshake_coords, handshake_dim, handshake_size
    from earth2studio.utils.type import CoordSystem

    E2S_AVAILABLE = True
except Exception:  # laptop / CI fallback -- keep the same call surface
    # ------------------------------------------------------------------------------
    # WARNING: these shims VALIDATE NOTHING. They exist so the module imports and the
    # call surface stays identical without earth2studio; they are not a substitute for
    # it. The real `batch_func` enforces `len(x.shape) == len(coords)` and flattens the
    # leading dims, and the real `handshake_*` reject mismatched coordinate systems.
    #
    # This gap has already cost us once: because the shim `batch_func` is a no-op, the
    # test suite passed for a `_forward` that assumed rank 4 and would have indexed the
    # *time* axis instead of *variable* under any real batched call. Tests that pass on
    # the shim path prove the code runs, NOT that it conforms.
    #
    # Conformance is checked by tests/test_e2s_conformance.py, which runs only when the
    # real package is present:   uv sync --extra earth2studio
    # ------------------------------------------------------------------------------
    CoordSystem = OrderedDict

    def handshake_dim(*_a, **_k):
        return None

    def handshake_coords(*_a, **_k):
        return None

    def handshake_size(*_a, **_k):
        return None

    def batch_func():
        def _wrap(fn):
            return fn

        return _wrap

    def batch_coords():
        def _wrap(fn):
            return fn

        return _wrap

    E2S_AVAILABLE = False


class DarwinBGCPrognostic(torch.nn.Module):
    """Earth2Studio ``PrognosticModel`` for depth-resolved ocean-BGC state.

    Parameters
    ----------
    core_model : torch.nn.Module
        The trained operator (FNO2d / SFNO) mapping z-scored state ``[B, V, H, W]``
        at month t to z-scored state at month t+1 (or its residual, see ``residual``).
    variables : sequence[str]
        Depth-tagged channel names in tensor order, e.g. ``['DIC_k0', ..., 'Chl1_kZ']``.
    lat, lon : array
        Regular grid coordinates (``lat`` length H, ``lon`` length W).
    means, stds : array [V]
        Per-channel standardization statistics (in the transformed space; see ``log_vars``).
    log_vars : sequence[str]
        Tracer stems (before ``_k``) that were log-transformed before z-scoring (e.g. ``Chl1``).
    ocean_mask : array [H, W] bool
        True over ocean cells; land is zero-filled after each step.
    residual : bool
        If True the core model predicts a per-step tendency and the wrapper applies
        ``z + f(z)`` (matches the ``--dt-scaled-residual`` / residual training).
    dt : np.timedelta64
        The forecast step (monthly by default).
    """

    def __init__(
        self,
        core_model: torch.nn.Module,
        variables,
        lat,
        lon,
        means,
        stds,
        # NO transform by default. A non-empty default silently applies log/exp to
        # checkpoints that were trained in linear space (--log-transform off), whose
        # means/stds and weights assume no transform -- which corrupts every forecast
        # for those channels. The transform is a property OF THE CHECKPOINT, so the
        # caller must pass the training-time value; emulator_poc.py records it as
        # config.log_tracers (empty list when the flag was off). Prefer from_config().
        log_vars=(),
        ocean_mask=None,
        residual: bool = True,
        dt: np.timedelta64 = DEFAULT_DT,
        log_floors=None,
    ) -> None:
        super().__init__()
        self.model = core_model
        self.variables = [str(v) for v in variables]
        self.lat = np.asarray(lat)
        self.lon = np.asarray(lon)
        n_var = len(self.variables)
        self.register_buffer(
            "means", torch.as_tensor(np.asarray(means), dtype=torch.float32).reshape(n_var))
        self.register_buffer(
            "stds", torch.as_tensor(np.asarray(stds), dtype=torch.float32).reshape(n_var))
        if ocean_mask is None:
            ocean_mask = np.ones((len(self.lat), len(self.lon)), dtype=bool)
        self.register_buffer("mask", torch.as_tensor(np.asarray(ocean_mask, dtype=bool)))
        log_stems = set(log_vars)
        self.log_idx = [i for i, v in enumerate(self.variables) if v.split("_k")[0] in log_stems]
        # Per-channel clip floor for the log transform. MUST match the value the checkpoint
        # was trained with (emulator_poc.py writes it to config.log_floors); a mismatch means
        # training and serving apply different transforms to the same input. Defaults to the
        # historical fixed 1e-12 so pre-existing checkpoints keep serving identically.
        _floors = np.full(n_var, 1e-12, dtype=np.float64)
        if log_floors is not None:
            if isinstance(log_floors, dict):
                for i, v in enumerate(self.variables):
                    if v in log_floors:
                        _floors[i] = float(log_floors[v])
            else:
                _floors = np.asarray(log_floors, dtype=np.float64).reshape(n_var)
        self.register_buffer(
            "log_floors", torch.as_tensor(_floors, dtype=torch.float32).reshape(n_var))
        self.residual = bool(residual)
        self.dt = dt

    # ---- construction from a training run's own config ---------------------------
    @classmethod
    def from_config(cls, core_model, variables, lat, lon, means, stds, config, **kw):
        """Build the wrapper from the ``config`` block that ``emulator_poc.py`` wrote.

        This is the safe path, and the reason it exists: the log transform is a property
        of the CHECKPOINT, not a preference of the caller. Serving a linear-space
        checkpoint through a log-space wrapper (or the reverse) silently corrupts every
        affected channel while producing plausible-looking output. Reading the flag,
        the stem list and the per-channel floors out of the run's own config makes the
        two sides impossible to desynchronise.

        Every setting below is a training-time property, and getting any of them wrong
        produces plausible output rather than an error:

        - ``log_transform`` / ``log_tracers`` / ``log_floors`` -- the input transform.
        - ``residual`` -- whether the core model predicts a DELTA or the next state
          outright. Defaulting to residual on a direct-prediction checkpoint adds the
          prediction to the input state, roughly doubling it.
        - ``dt_hours`` -- the forecast interval. Defaulting to 30 days on a
          different-cadence checkpoint labels every rollout step with the wrong valid
          time, and lead_time accumulates that error linearly.

        An explicit keyword always wins, so a caller can still override deliberately.
        """
        cfg = dict(config or {})
        log_vars = tuple(cfg.get("log_tracers") or ()) if cfg.get("log_transform") else ()
        kw.setdefault("log_floors", cfg.get("log_floors"))
        if "residual" in cfg and "residual" not in kw:
            kw["residual"] = bool(cfg["residual"])
        if "dt_hours" in cfg and "dt" not in kw:
            kw["dt"] = np.timedelta64(round(float(cfg["dt_hours"])), "h")
        return cls(core_model, variables, lat, lon, means, stds, log_vars=log_vars, **kw)

    # ---- coords contract --------------------------------------------------------
    def input_coords(self) -> CoordSystem:
        return CoordSystem(
            {
                "batch": np.empty(0),
                "time": np.empty(0),
                "lead_time": np.array([np.timedelta64(0, "h")]),
                "variable": np.array(self.variables),
                "lat": self.lat.copy(),
                "lon": self.lon.copy(),
            }
        )

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        oc = self.input_coords()
        oc["lead_time"] = np.array([self.dt])
        if input_coords is None:  # introspection path (matches SFNO): bare output template
            return oc
        target = self.input_coords()
        handshake_size(input_coords, "lead_time", 1)
        for i, k in enumerate(target):
            if k in ("batch", "time"):  # skip placeholders (SFNO convention)
                continue
            handshake_dim(input_coords, k, i)
            if k != "lead_time":
                handshake_coords(input_coords, target, k)
        oc["batch"] = input_coords["batch"]
        oc["time"] = input_coords["time"]
        oc["lead_time"] = np.array([self.dt]) + input_coords["lead_time"]  # accumulate
        return oc

    # ---- forward ----------------------------------------------------------------
    def _standardize(self, x: torch.Tensor) -> torch.Tensor:
        x = x.clone()
        for i in self.log_idx:
            x[:, i] = torch.log(torch.clamp(x[:, i], min=float(self.log_floors[i])))
        return (x - self.means.view(1, -1, 1, 1)) / self.stds.view(1, -1, 1, 1)

    def _destandardize(self, z: torch.Tensor) -> torch.Tensor:
        x = z * self.stds.view(1, -1, 1, 1) + self.means.view(1, -1, 1, 1)
        for i in self.log_idx:
            x[:, i] = torch.exp(x[:, i])
        return x

    @torch.inference_mode()
    def _forward(self, x: torch.Tensor) -> torch.Tensor:
        """``[..., V, H, W]`` physical units -> next-step physical state.

        The leading dimensions are collapsed into one batch axis and restored on the way
        out, so this works for any rank Earth2Studio hands us. That matters because
        ``batch_func`` only flattens the dims *beyond* the model's own declared
        ``input_coords``: since we declare six (``batch, time, lead_time, variable, lat,
        lon``), following the FCN3 convention, a workflow calling us with exactly those
        six passes a 6-D tensor straight through the decorator uncompressed. The previous
        implementation indexed ``x[:, i]`` for the channel axis, which silently assumed
        rank 4 and indexed *time* instead of *variable* under a real batched call. It went
        unnoticed because the fallback ``batch_func`` shim is a no-op, so the tests never
        exercised the real decorator. FCN3 solves the same problem with an explicit
        ``squeeze(2)``/``unsqueeze(2)``; collapsing is equivalent and rank-agnostic.

        Inference-only (matches the earth2studio reference models); avoids autograd graph
        accumulation over long rollouts. The differentiable-recovery path uses the box
        (``run_v3.0``), not this emulator wrapper.
        """
        if x.ndim < 3:
            raise ValueError(f"expected at least [V, H, W]; got shape {tuple(x.shape)}")
        lead_shape = x.shape[:-3]
        v, h, w = x.shape[-3:]
        if v != len(self.variables):
            raise ValueError(
                f"channel axis is {v} but the model declares {len(self.variables)} "
                f"variables; got shape {tuple(x.shape)} (expected [..., V, H, W])"
            )
        xf = x.reshape(-1, v, h, w)

        z = self._standardize(xf)
        out = self.model(z)
        z_next = z + out if self.residual else out
        x_next = self._destandardize(z_next)
        x_next = torch.clamp(x_next, min=0.0)  # nonnegativity guard
        x_next = torch.where(
            self.mask.view(1, 1, *self.mask.shape), x_next, torch.zeros_like(x_next)
        )
        return x_next.reshape(*lead_shape, v, h, w)

    @batch_func()
    # @batch_func() is required, not decorative: it flattens the leading batch dims
    # before the forward and restores them after, so the model works under Earth2Studio's
    # batched workflows. Both the official custom-prognostic example
    # (examples/08_extend/01_custom_prognostic.py) and the built-in Persistence model
    # decorate __call__ with it; _default_generator below already had it.
    @batch_func()
    def __call__(self, x: torch.Tensor, coords: CoordSystem):
        out_coords = self.output_coords(coords)
        return self._forward(x), out_coords

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem) -> Iterator:
        coords = coords.copy()
        self.output_coords(coords)  # validate
        yield x, coords.copy()  # step 0 == the initial condition
        while True:  # UNBOUNDED -- the caller (run.deterministic) decides nsteps
            coords = self.output_coords(coords)
            x = self._forward(x)
            yield x, coords.copy()

    def create_iterator(self, x: torch.Tensor, coords: CoordSystem) -> Iterator:
        yield from self._default_generator(x, coords)
