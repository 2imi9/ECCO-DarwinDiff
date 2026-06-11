"""Track-2 Darwin emulator scaffold -- PhysicsNeMo / Earth-2 Studio schema.

Status: SCAFFOLD. This module provides the *interface* and a small,
self-contained Fourier Neural Operator so the Track-2 emulator path lives in the
repo and is CPU-unit-testable today, before the NVIDIA / Nebius cluster
onboarding. It is deliberately import-guarded: ``physicsnemo`` and
``earth2studio`` are NOT yet dependencies of this project (see the grant briefs:
"Phase 2: PhysicsNeMo + Earth-2 Studio onboarding"). When those packages are
installed on the cluster:

  - :class:`DarwinEmulator` already subclasses ``physicsnemo.Module`` (falling
    back to ``torch.nn.Module`` here), so it slots into the PhysicsNeMo model
    registry / checkpoint tooling unchanged.
  - The Earth-2 Studio prognostic contract is mirrored by
    :meth:`DarwinEmulator.input_coords`, :meth:`DarwinEmulator.output_coords`,
    :meth:`DarwinEmulator.step`, and :meth:`DarwinEmulator.create_iterator`. A
    ``CoordSystem`` is an ``OrderedDict`` of named coordinate arrays, exactly as
    earth2studio uses; ``step`` is the one-shot analog of earth2studio's
    prognostic ``__call__``.
  - :func:`build_emulator` swaps the fallback FNO for
    ``physicsnemo.models.fno.FNO`` when available.

Nothing here trains or touches a GPU on import. The real operator-learning run
(FNO / AFNO on ECCO-Darwin v05 monthly fields) happens on the cluster.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import torch
from torch import nn

# --- Optional PhysicsNeMo base class (import-guarded) -----------------------
try:  # pragma: no cover - exercised only when physicsnemo is installed
    from physicsnemo import Module as _BaseModule  # type: ignore

    HAS_PHYSICSNEMO = True
except Exception:  # ImportError, or a partial install
    _BaseModule = nn.Module  # type: ignore[assignment, misc]
    HAS_PHYSICSNEMO = False

# A CoordSystem mirrors earth2studio's: an ordered mapping from dimension name
# to the 1-D array of coordinate values along that dimension.
CoordSystem = OrderedDict

# Default prognostic state: the 7-tracer Carroll-6 carbonate surface state, so
# the emulator's variables line up with the differentiable box model
# (darwindiff.carroll6.carroll6_carbonate_step).
DEFAULT_VARIABLES: list[str] = ["DFe", "Ps", "Pl", "POC", "PIC", "DIC", "ALK"]


class SpectralConv2d(nn.Module):
    """2-D spectral convolution -- the FNO mixing layer (Li et al. 2021).

    Multiplies the lowest ``modes1 x modes2`` Fourier coefficients by learnable
    complex weights. Unlike the per-cell DINN (1x1 convs), this couples cells
    globally through the FFT -- the defining property of an operator surrogate.
    """

    def __init__(self, in_ch: int, out_ch: int, modes1: int, modes2: int) -> None:
        super().__init__()
        self.modes1 = modes1
        self.modes2 = modes2
        scale = 1.0 / (in_ch * out_ch)
        self.w1 = nn.Parameter(
            scale * torch.randn(in_ch, out_ch, modes1, modes2, dtype=torch.cfloat)
        )
        self.w2 = nn.Parameter(
            scale * torch.randn(in_ch, out_ch, modes1, modes2, dtype=torch.cfloat)
        )

    @staticmethod
    def _mul(inp: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
        return torch.einsum("bixy,ioxy->boxy", inp, w)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, _, h, w = x.shape
        x_ft = torch.fft.rfft2(x)
        wf = x_ft.shape[-1]
        m1 = min(self.modes1, h)
        m2 = min(self.modes2, wf)
        out_ft = torch.zeros(
            b, self.w1.shape[1], h, wf, dtype=torch.cfloat, device=x.device
        )
        out_ft[:, :, :m1, :m2] = self._mul(x_ft[:, :, :m1, :m2], self.w1[:, :, :m1, :m2])
        out_ft[:, :, -m1:, :m2] = self._mul(x_ft[:, :, -m1:, :m2], self.w2[:, :, :m1, :m2])
        return torch.fft.irfft2(out_ft, s=(h, w))


class FNO2d(nn.Module):
    """Minimal Fourier Neural Operator (fallback when physicsnemo is absent)."""

    def __init__(
        self,
        in_ch: int,
        out_ch: int,
        modes1: int = 8,
        modes2: int = 8,
        width: int = 20,
        n_layers: int = 4,
    ) -> None:
        super().__init__()
        self.lift = nn.Conv2d(in_ch, width, 1)
        self.spectral = nn.ModuleList(
            [SpectralConv2d(width, width, modes1, modes2) for _ in range(n_layers)]
        )
        self.local = nn.ModuleList([nn.Conv2d(width, width, 1) for _ in range(n_layers)])
        self.proj1 = nn.Conv2d(width, 2 * width, 1)
        self.proj2 = nn.Conv2d(2 * width, out_ch, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.lift(x)
        for sp, lo in zip(self.spectral, self.local, strict=False):
            x = nn.functional.gelu(sp(x) + lo(x))
        return self.proj2(nn.functional.gelu(self.proj1(x)))


def _validate_coords(x: torch.Tensor, coords: OrderedDict, variables: list[str]) -> None:
    if "variable" not in coords:
        raise KeyError("coords missing 'variable' dimension")
    cvars = [str(v) for v in np.asarray(coords["variable"])]
    if cvars != list(variables):
        raise ValueError(
            f"coords variables {cvars} != emulator variables {list(variables)}"
        )
    if x.ndim < 3 or x.shape[-3] != len(variables):
        raise ValueError(
            f"x variable axis (dim -3) must be {len(variables)}; got shape {tuple(x.shape)}"
        )


class DarwinEmulator(_BaseModule):  # type: ignore[misc, valid-type]
    """Prognostic Darwin surrogate -- PhysicsNeMo Module + Earth-2 schema.

    Maps a multi-tracer surface state ``[B, V, H, W]`` to the next state one
    ``dt`` ahead. Variables are prognostic (input set == output set) so the
    Earth-2 rollout iterator is autoregressive. Forcing-augmented variants
    (extra input channels for SST / wind / dust) are a documented cluster-phase
    extension.
    """

    def __init__(
        self,
        variables: list[str] | None = None,
        grid_shape: tuple[int, int] = (64, 128),
        modes: int = 8,
        width: int = 20,
        n_layers: int = 4,
        dt_hours: float = 720.0,
        lats: np.ndarray | None = None,
        lons: np.ndarray | None = None,
        operator: nn.Module | None = None,
    ) -> None:
        super().__init__()
        self.variables = list(variables) if variables is not None else list(DEFAULT_VARIABLES)
        v = len(self.variables)
        self.grid_shape = (int(grid_shape[0]), int(grid_shape[1]))
        self.dt_hours = float(dt_hours)
        h, w = self.grid_shape
        self.lats = np.asarray(lats) if lats is not None else np.linspace(-90.0, 90.0, h)
        self.lons = (
            np.asarray(lons) if lons is not None else np.linspace(0.0, 360.0, w, endpoint=False)
        )
        self.model = operator if operator is not None else FNO2d(
            v, v, modes1=modes, modes2=modes, width=width, n_layers=n_layers
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)

    # --- Earth-2 Studio prognostic contract --------------------------------
    def input_coords(self) -> OrderedDict:
        return CoordSystem(
            [
                ("variable", np.array(self.variables)),
                ("lat", self.lats.copy()),
                ("lon", self.lons.copy()),
            ]
        )

    def output_coords(self, input_coords: OrderedDict) -> OrderedDict:
        out: OrderedDict = CoordSystem()
        for k, val in input_coords.items():
            if k == "lead_time_h":
                continue
            out[k] = np.array(self.variables) if k == "variable" else np.asarray(val).copy()
        prev = (
            float(np.asarray(input_coords["lead_time_h"])[0])
            if "lead_time_h" in input_coords
            else 0.0
        )
        out["lead_time_h"] = np.array([prev + self.dt_hours])
        return out

    def step(self, x: torch.Tensor, coords: OrderedDict) -> tuple[torch.Tensor, OrderedDict]:
        """One prognostic step. Returns ``(x_next, coords_next)``."""
        _validate_coords(x, coords, self.variables)
        return self.forward(x), self.output_coords(coords)

    def create_iterator(self, x: torch.Tensor, coords: OrderedDict, n_steps: int):
        """Autoregressive rollout. Yields ``(x, coords)`` starting from the IC."""
        yield x, coords
        for _ in range(int(n_steps)):
            x, coords = self.step(x, coords)
            yield x, coords


def build_emulator(
    variables: list[str] | None = None,
    grid_shape: tuple[int, int] = (64, 128),
    modes: int = 8,
    width: int = 20,
    n_layers: int = 4,
    prefer_physicsnemo: bool = True,
    **kwargs,
) -> DarwinEmulator:
    """Construct a :class:`DarwinEmulator`.

    When ``physicsnemo`` is installed and ``prefer_physicsnemo`` is set, the
    operator is swapped for ``physicsnemo.models.fno.FNO``; otherwise it falls
    back to the self-contained :class:`FNO2d` so the scaffold runs on a laptop
    with neither physicsnemo nor a GPU.
    """
    variables = list(variables) if variables is not None else list(DEFAULT_VARIABLES)
    v = len(variables)
    operator: nn.Module | None = None
    if prefer_physicsnemo and HAS_PHYSICSNEMO:
        try:  # pragma: no cover - cluster-only path
            from physicsnemo.models.fno import FNO  # type: ignore

            operator = FNO(
                in_channels=v,
                out_channels=v,
                dimension=2,
                latent_channels=width,
                num_fno_layers=n_layers,
                num_fno_modes=modes,
            )
        except Exception:
            operator = None
    return DarwinEmulator(
        variables=variables,
        grid_shape=grid_shape,
        modes=modes,
        width=width,
        n_layers=n_layers,
        operator=operator,
        **kwargs,
    )
