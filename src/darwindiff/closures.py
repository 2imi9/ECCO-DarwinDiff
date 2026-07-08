"""Learned closures for the Track-2 UDE (Phase 1).

These are the small, bounded, *anchored* neural nets that replace Darwin's
uncertain closures inside the otherwise-analytic BGC tendency. They satisfy the
same contract as the ``ffe_closure`` / ``calcite_closure`` hooks in
:func:`darwindiff.carroll6.carroll6_ude_tendency` and
:func:`darwindiff.transport.bgc_tendency_field`, and every closure here is a
*strict superset* of the baseline law: at initialisation it byte-reproduces the
constant-parameter term, so the UDE starts as "no change" and only earns
deviations from data.
"""
from __future__ import annotations

import torch
from torch import nn

from darwindiff.carroll6 import CARROLL_VALUES, K_FE, P


class EnvCalciteClosure(nn.Module):
    r"""Environment-driven calcite (PIC production) closure.

    ``PIC_prod = R0 * g_theta(env, state) * mort_total`` with

        ``g_theta = 10 ** (A * tanh(MLP(feat)))``  in ``[10**-A, 10**A]``

    a log-symmetric multiplicative envelope. The MLP's final layer is
    zero-initialised, so ``g_theta == 1`` at init and (with ``R0`` = Carroll
    ``R_PICPOC``) this **byte-reproduces the constant-ratio baseline**
    ``R_PICPOC * mort_total``.

    Motivation (finding 2026-07-07): composition alone is *refuted* against
    Darwin's real Chl2 (the calcifier fraction is flat while bulk PIC:POC spans
    ~100x) -- the spread is driven by **environment / carbonate chemistry**. So
    the drivers are exogenous env channels (**SST, Omega_calcite, PAR**;
    caller-standardised) plus the state-dependent iron-limitation factor
    ``f_lim = DFe/(DFe + K_FE)`` (PIC:POC rises under Fe/nutrient stress).

    Shapes: ``env`` is ``[..., cells, n_env]`` and must be cell-aligned with the
    ``state`` (``[..., cells, tracer]``) passed to :meth:`forward`; ``mort_total``
    is ``[..., cells]``. ``R0`` defaults to Carroll's ``R_PICPOC``.
    """

    def __init__(
        self,
        env: torch.Tensor,
        R0: float | None = None,
        hidden: int = 16,
        A: float = 1.0,
    ) -> None:
        super().__init__()
        self.register_buffer("env", env)
        self.A = float(A)
        self.R0 = float(CARROLL_VALUES[P.R_PICPOC]) if R0 is None else float(R0)
        n_in = int(env.shape[-1]) + 1  # env channels + f_lim
        self.net = nn.Sequential(
            nn.Linear(n_in, hidden),
            nn.Tanh(),
            nn.Linear(hidden, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )
        # zero-init the readout so g_theta == 1 at initialisation (baseline anchor)
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def g(self, state: torch.Tensor) -> torch.Tensor:
        """The bounded multiplicative envelope ``g_theta`` over the cells."""
        DFe = state[..., 0]
        f_lim = (DFe / (DFe + K_FE)).unsqueeze(-1)          # [..., cells, 1]
        feat = torch.cat([self.env, f_lim], dim=-1)          # [..., cells, n_env+1]
        a = self.net(feat).squeeze(-1)                       # [..., cells]
        return 10.0 ** (self.A * torch.tanh(a))              # in [10**-A, 10**A]

    def forward(self, state: torch.Tensor, mort_total: torch.Tensor) -> torch.Tensor:
        return self.R0 * self.g(state) * mort_total
