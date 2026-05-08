"""Neural networks for DarwinDiff parameter learning.

Two patterns extracted from notebooks 06 and 07, both following the BINN-family
convention (cf. Xu et al. 2025, Biogeochemistry-Informed Neural Network) where
a small per-location network produces parameter values that are fed through
sigmoid bounding into a differentiable physics simulator and optimised by
backpropagation through the simulator's adjoint.

- :class:`DINN` — Darwin-Informed Neural Network. Per-cell architecture
  expressed as a stack of 1×1 convolutions, used by notebook 07's per-cell
  fit on a 2-D grid. Equivalent to applying a tiny MLP independently at every
  grid cell. No spatial coupling — chosen because the truth structure is
  per-cell (each cell's parameters depend only on its own covariates). When
  spatial coupling enters the production pipeline (advection / diffusion in
  notebook 09+), a separate class with non-trivial receptive field will be
  added; the current ``DINN`` is reserved for the no-spatial-coupling case.

- :class:`DINNRegional` — fully-connected MLP variant for region-level fits
  (notebook 06's two-regime benchmark). Takes scalar environmental features
  per region and predicts a Carroll-6 vector per region.

Both networks are intentionally tiny (a few hundred to a few thousand weights):
the structural argument behind DarwinDiff over Green's-functions calibration is
about *what the parameters can be conditioned on* (per-cell environmental
covariates) rather than network capacity. Sigmoid bounding to physical
Carroll-6 ranges is provided by :func:`darwindiff.carroll6.bounded_params`,
which broadcasts naturally over scalar (``[6]``), 2-D (``[6, H, W]``), and
batched (``[B, 6]`` / ``[B, 6, H, W]``) shapes via the ``param_axis`` argument.
"""

from __future__ import annotations

import torch
from torch import nn


class DINNRegional(nn.Module):
    """Region-level Darwin-Informed Neural Network (fully-connected MLP).

    Maps environmental covariates to Carroll-6 outputs at the region level.
    The architecture from notebook 06: a small MLP with one hidden layer of
    16 units (Tanh activation), 166 weights at the default size including
    biases.

    Args:
        n_features: number of environmental input features (default 3 for
            SST, dust flux, MLD).
        hidden_dim: width of the single hidden layer (default 16).
        n_outputs: number of Carroll parameters to predict (default 6, matching
            Carroll's tuned set).

    Forward:
        ``env`` shape ``[n_features]`` → ``[n_outputs]``, or
        ``env`` shape ``[B, n_features]`` → ``[B, n_outputs]``.

        The output is **unbounded**; pair with
        :func:`darwindiff.carroll6.bounded_params` (with ``param_axis=-1`` for
        the batched case) to map into physical ranges.
    """

    def __init__(
        self,
        n_features: int = 3,
        hidden_dim: int = 16,
        n_outputs: int = 6,
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, n_outputs),
        )

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        return self.net(env)


class DINN(nn.Module):
    """Darwin-Informed Neural Network — per-cell variant as 1×1 convolutions.

    Equivalent to a tiny MLP applied independently at every grid cell. 1×1
    kernels mean **no spatial smoothing** — each cell's output depends only on
    its own covariates, which matches the truth structure for the per-cell
    setups in notebook 07. ~438 weights at the default config.

    The "Informed" suffix follows the BINN / PINN convention: the network's
    loss is structured by a differentiable physics simulator (in our case,
    Darwin biogeochemistry through ``carroll6_step`` and eventually the full
    Darwin pkg), and gradients reach the network's weights via that simulator's
    adjoint computed by autograd.

    Args:
        n_input_channels: number of environmental covariates per cell (default
            3 for SST, dust flux, MLD).
        hidden_dim: number of channels in the hidden layer(s) (default 16).
        n_outputs: number of Carroll parameters per cell (default 6).
        n_hidden_layers: how many 1×1 hidden layers (default 2).

    Forward:
        ``env`` shape ``[n_input_channels, H, W]`` → ``[n_outputs, H, W]``.
        Optionally accepts a batch dim ``[B, n_input_channels, H, W]`` →
        ``[B, n_outputs, H, W]``.

        The output is **unbounded**; pair with
        :func:`darwindiff.carroll6.bounded_params` (default ``param_axis=0``
        for unbatched, ``param_axis=1`` for batched) to map into physical
        ranges.
    """

    def __init__(
        self,
        n_input_channels: int = 3,
        hidden_dim: int = 16,
        n_outputs: int = 6,
        n_hidden_layers: int = 2,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = [
            nn.Conv2d(n_input_channels, hidden_dim, kernel_size=1),
            nn.Tanh(),
        ]
        for _ in range(n_hidden_layers - 1):
            layers += [
                nn.Conv2d(hidden_dim, hidden_dim, kernel_size=1),
                nn.Tanh(),
            ]
        layers += [nn.Conv2d(hidden_dim, n_outputs, kernel_size=1)]
        self.net = nn.Sequential(*layers)

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        if env.ndim == 3:
            return self.net(env.unsqueeze(0)).squeeze(0)
        return self.net(env)
