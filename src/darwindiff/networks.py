"""Neural networks for DarwinDiff parameter learning.

Two patterns extracted from notebooks 06 and 07:

- :class:`CarrollMLP` — environmental covariates → Carroll-6 parameters, used by
  notebook 06's two-regime fit. Input shape ``[n_features]`` (one regime) or
  ``[B, n_features]`` (batched regimes); output ``[6]`` or ``[B, 6]``.

- :class:`CarrollCNN` — covariates as ``(n_input_channels, H, W)`` → parameters
  as ``(n_outputs, H, W)``, used by notebook 07's per-cell fit on a 128×128
  grid. Built as 1×1 convolutions: equivalent to applying a tiny MLP independently
  at every grid cell. No spatial coupling — chosen because the truth structure
  is per-cell (each cell's parameters depend only on its own covariates).

Both networks are intentionally tiny (a few hundred to a few thousand weights):
the win for DarwinDiff over Green's-functions calibration comes from *what the
parameters can be conditioned on* (per-cell environmental covariates) rather
than from network capacity. When the production fit needs spatial coupling
(notebook 09+), a separate ``CarrollCNN`` variant with non-trivial receptive
field will be added.

Sigmoid bounding to physical Carroll-6 ranges is provided by
:func:`darwindiff.carroll6.bounded_params`, which broadcasts naturally over
both the scalar (``[6]``) and 2-D (``[6, H, W]``) cases.
"""

from __future__ import annotations

import torch
from torch import nn


class CarrollMLP(nn.Module):
    """Per-feature MLP mapping environmental covariates to Carroll-6 outputs.

    The architecture from notebook 06: a small MLP with one hidden layer of
    16 units (Tanh activation), 144 weights at the default size.

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
        :func:`darwindiff.carroll6.bounded_params` to map into physical ranges.
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


class CarrollCNN(nn.Module):
    """Per-cell network expressed as a stack of 1×1 convolutions.

    Equivalent to a tiny MLP applied independently at every grid cell. 1×1
    kernels mean **no spatial smoothing** — each cell's output depends only on
    its own covariates, which matches the truth structure for the per-cell
    setups in notebook 07. ~438 weights at the default config.

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
        :func:`darwindiff.carroll6.bounded_params` to map into physical ranges.
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
