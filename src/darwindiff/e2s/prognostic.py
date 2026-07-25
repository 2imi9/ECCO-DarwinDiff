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
from typing import Iterator

import numpy as np
import torch

# --- import guard: earth2studio is cluster-only ----------------------------------
try:  # pragma: no cover - exercised on the cluster
    from earth2studio.utils.type import CoordSystem
    from earth2studio.utils.coords import handshake_coords, handshake_dim, handshake_size
    from earth2studio.models.batch import batch_coords, batch_func

    E2S_AVAILABLE = True
except Exception:  # laptop / CI fallback -- keep the same call surface
    CoordSystem = OrderedDict

    def handshake_dim(*_a, **_k):  # noqa: D401
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
        log_vars=("Chl1", "Chl2", "Chl3", "Chl4", "Chl5", "PIC", "POC", "FeT"),
        ocean_mask=None,
        residual: bool = True,
        dt: np.timedelta64 = np.timedelta64(30, "D"),
        log_floors=None,
    ) -> None:
        super().__init__()
        self.model = core_model
        self.variables = [str(v) for v in variables]
        self.lat = np.asarray(lat)
        self.lon = np.asarray(lon)
        V = len(self.variables)
        self.register_buffer("means", torch.as_tensor(np.asarray(means), dtype=torch.float32).reshape(V))
        self.register_buffer("stds", torch.as_tensor(np.asarray(stds), dtype=torch.float32).reshape(V))
        if ocean_mask is None:
            ocean_mask = np.ones((len(self.lat), len(self.lon)), dtype=bool)
        self.register_buffer("mask", torch.as_tensor(np.asarray(ocean_mask, dtype=bool)))
        log_stems = set(log_vars)
        self.log_idx = [i for i, v in enumerate(self.variables) if v.split("_k")[0] in log_stems]
        # Per-channel clip floor for the log transform. MUST match the value the checkpoint
        # was trained with (emulator_poc.py writes it to config.log_floors); a mismatch means
        # training and serving apply different transforms to the same input. Defaults to the
        # historical fixed 1e-12 so pre-existing checkpoints keep serving identically.
        _floors = np.full(V, 1e-12, dtype=np.float64)
        if log_floors is not None:
            if isinstance(log_floors, dict):
                for i, v in enumerate(self.variables):
                    if v in log_floors:
                        _floors[i] = float(log_floors[v])
            else:
                _floors = np.asarray(log_floors, dtype=np.float64).reshape(V)
        self.register_buffer("log_floors", torch.as_tensor(_floors, dtype=torch.float32).reshape(V))
        self.residual = bool(residual)
        self.dt = dt

    # ---- coords contract --------------------------------------------------------
    def input_coords(self) -> "CoordSystem":
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
    def output_coords(self, input_coords: "CoordSystem") -> "CoordSystem":
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
        """x : [B, V, H, W] physical units -> next-step physical state (self-contained).

        Inference-only (matches the earth2studio reference models); avoids autograd
        graph accumulation over long rollouts. The differentiable-recovery path uses
        the box (run_v3.0), not this emulator wrapper.
        """
        z = self._standardize(x)
        out = self.model(z)
        z_next = z + out if self.residual else out
        x_next = self._destandardize(z_next)
        x_next = torch.clamp(x_next, min=0.0)  # nonnegativity guard
        x_next = torch.where(self.mask.view(1, 1, *self.mask.shape), x_next, torch.zeros_like(x_next))
        return x_next

    @batch_func()
    def __call__(self, x: torch.Tensor, coords: "CoordSystem"):
        out_coords = self.output_coords(coords)
        return self._forward(x), out_coords

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: "CoordSystem") -> Iterator:
        coords = coords.copy()
        self.output_coords(coords)  # validate
        yield x, coords.copy()  # step 0 == the initial condition
        while True:  # UNBOUNDED -- the caller (run.deterministic) decides nsteps
            coords = self.output_coords(coords)
            x = self._forward(x)
            yield x, coords.copy()

    def create_iterator(self, x: torch.Tensor, coords: "CoordSystem") -> Iterator:
        yield from self._default_generator(x, coords)
