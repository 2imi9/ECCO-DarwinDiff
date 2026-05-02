"""Small MLP that maps environmental covariates to a local biogeochemical parameter.

For the toy, the input is normalised depth and the output is lambda(z), the depth-dependent
loss rate. The same architecture later takes richer covariates (T, salinity, mixed-layer
depth, nutrients) and predicts real Darwin parameters (iron scavenging rate, remineralisation
rate).

Why a small MLP and not something fancier: BINN (Xu et al. 2025) uses a 4-layer MLP for the
same kind of pointwise parameter prediction. Spatial context (CNN, GNN, attention) is not
needed when the parameter is a function of local environment. Keeping the network small also
keeps the inverse problem well-posed — we want the physics to do the work, not the network.
"""

from __future__ import annotations

import torch
from torch import nn


class ParameterMLP(nn.Module):
    """Feed-forward network predicting one or more positive parameters per cell.

    Final activation is Softplus so all outputs are strictly positive — physical rate
    parameters (loss, scavenging, remineralisation, growth, mortality) cannot be
    negative, and we want this enforced by construction rather than by clipping.

    With ``n_outputs > 1`` the same shared trunk predicts multiple parameter profiles
    simultaneously. This is the multi-parameter recovery setup that lets gradient
    descent learn many DarwinDiff parameters in one training run, the central
    architectural difference from Green's-functions one-at-a-time calibration.
    """

    def __init__(
        self,
        n_features: int = 1,
        hidden_dim: int = 32,
        n_hidden_layers: int = 3,
        n_outputs: int = 1,
    ) -> None:
        super().__init__()
        layers: list[nn.Module] = [nn.Linear(n_features, hidden_dim), nn.ReLU()]
        for _ in range(n_hidden_layers - 1):
            layers += [nn.Linear(hidden_dim, hidden_dim), nn.ReLU()]
        layers += [nn.Linear(hidden_dim, n_outputs), nn.Softplus()]
        self.net = nn.Sequential(*layers)
        self.n_outputs = n_outputs

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        """Args:
            features: shape [Nz, n_features].
        Returns:
            parameter values: shape [Nz] when ``n_outputs == 1`` (backward-compatible
            with the single-parameter prototype), shape [Nz, n_outputs] otherwise.
        """
        out = self.net(features)
        if self.n_outputs == 1:
            return out.squeeze(-1)
        return out
