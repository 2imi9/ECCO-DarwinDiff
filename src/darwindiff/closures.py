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

import math

import torch
from torch import nn
from torch.nn import functional as F

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
        # clamp to physical iron (DFe >= 0) BEFORE the ratio: this removes the
        # ``DFe = -K_FE`` pole (which horizontal-advection overshoot can reach and
        # which otherwise emits a NaN gradient that poisons the whole optimizer),
        # while staying byte-identical for every physical state. f_lim in [0, 1).
        dfe = state[..., 0].clamp_min(0.0)
        f_lim = (dfe / (dfe + K_FE)).unsqueeze(-1)           # [..., cells, 1]
        feat = torch.cat([self.env.to(f_lim.dtype), f_lim], dim=-1)
        a = self.net(feat).squeeze(-1)                       # [..., cells]
        return 10.0 ** (self.A * torch.tanh(a))              # in [10**-A, 10**A]

    def forward(self, state: torch.Tensor, mort_total: torch.Tensor) -> torch.Tensor:
        return self.R0 * self.g(state) * mort_total


class ScavClosure(nn.Module):
    r"""Learned iron-*scavenging* sink closure. Learns **shape**, never the rate.

        ``scav_sink(DFe, POC; env) = r0 * (POC/POC0)**p * DFe * G``
        ``G = (1 + eps*tanh(MLP(feat))) / exp(mean_ref log(1 + eps*tanh(MLP(feat))))``

    **The level is not learnable, by construction (issue #217).** ``r0`` is a fixed
    float derived from ``scav_rat_per_day``, exactly as
    :class:`EnvCalciteClosure` holds ``R0`` fixed. It was an ``nn.Parameter`` until
    2026-08-02, which made it *exactly* redundant with the registry parameter
    ``scav_rat``: the sink is homogeneous of degree one in the level, so
    ``(scav_rat, r0) -> (lambda*scav_rat, r0/lambda)`` leaves the predicted field
    unchanged and any profile likelihood of ``scav_rat`` against this closure was
    **flat by theorem rather than by measurement**. See
    ``docs/findings/2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md``.

    Removing the parameter alone does not close the gauge: a network that learns a
    *constant* ``tanh`` output is a multiplicative level smuggled back in. So ``G`` is
    **mean-centred in log space over a fixed reference support** (``ref_feat``),
    recomputed every forward pass because the weights move, but never taken over the
    current batch -- a batch-dependent normaliser would make the closure's meaning
    depend on what it was evaluated on. The geometric mean of ``G`` over that support
    is 1 by construction, so ``scav_rat`` carries the entire level and the network
    carries only shape.

    The default reference support is a **convention, not a derived quantity**: a 3x3
    lattice over ``f1 = log10(DFe)+4`` and ``f2 = log10(POC/POC0)`` at the
    standardised-env origin. Pass ``ref_feat`` to state a different one. Changing it
    changes what "level" means and therefore what the closure claims.

    Motivation (finding 2026-07-07): iron *solubility* (``alpfe``) is a global
    scalar already baked into the (soluble) forcing, so the learnable iron physics
    is the **scavenging sink**. The box's sink ``scav_rat_per_day * DFe * POC`` is a
    triple simplification of Darwin3/Parekh scavenging (it scavenges *total* DFe not
    free Fe', uses *linear* POC not POC**0.58, and has no ligand chemistry). This
    closure keeps the Parekh backbone analytic and lets a small bounded net augment
    the two dropped pieces: the POC sublinearity via a learnable exponent ``p`` and
    the Fe'/ligand curvature via the bounded ``(1 + eps*tanh)`` correction.

    Anchor: ``p = softplus(raw_p)`` is initialised to **exactly 1**, the correction
    readout is zero-initialised (``corr == 1``), and ``r0 = scav_rat_per_day * POC0``,
    so at init this **reproduces the box sink** ``scav_rat_per_day*DFe*POC`` to float
    round-off (~1e-7, from the ``exp(log r0)`` round-trip -- a strict superset in
    practice; the test asserts ``rtol=1e-6``). The Darwin/Parekh empirical exponent is
    ``p ~ 0.58``; report ``(p - 1)`` as a diagnostic -- if data pulls ``p`` below 1 the
    box's linear-POC simplification is being falsified.

    Positivity: ``r0>0`` (exp), ``(POC/POC0)**p>=0``, ``DFe>=0``, ``corr in
    [1-eps, 1+eps]`` -> the sink is non-negative (a proper loss term). ``DFe``,
    ``POC`` are ``[..., cells]``; optional ``env`` (caller-standardised, e.g. T) is
    ``[..., cells, n_env]`` and cell-aligned.
    """

    def __init__(
        self,
        env: torch.Tensor | None = None,
        scav_rat_per_day: float | None = None,
        POC0: float = 0.5,
        hidden: int = 16,
        eps: float = 0.2,
        ref_feat: torch.Tensor | None = None,
    ) -> None:
        super().__init__()
        base = (
            float(CARROLL_VALUES[P.scav_rat]) * 86400.0
            if scav_rat_per_day is None
            else float(scav_rat_per_day)
        )
        self.POC0 = float(POC0)
        self.eps = float(eps)
        # FIXED level, not an nn.Parameter -- see the class docstring and issue #217.
        # Held in log space so the forward is unchanged and `exp(log r0)` keeps the same
        # round-off it always had (the init-anchor test asserts rtol=1e-6, not equality).
        self.log_r0 = float(math.log(base * self.POC0))
        # p = softplus(raw_p); log(e - 1) makes softplus == 1 exactly at init
        self.raw_p = nn.Parameter(torch.tensor(math.log(math.e - 1.0)))
        self._has_env = env is not None
        if env is not None:
            self.register_buffer("env", env)
        n_env = int(env.shape[-1]) if env is not None else 0
        self.net = nn.Sequential(
            nn.Linear(2 + n_env, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)  # corr == 1 at init

        if ref_feat is None:
            # Convention (see docstring): DFe at 1e-5 / 1e-4 / 1e-3 crossed with
            # POC/POC0 at 0.1 / 1 / 10, env columns at the standardised origin.
            grid = torch.tensor([-1.0, 0.0, 1.0])
            f1, f2 = torch.meshgrid(grid, grid, indexing="ij")
            ref_feat = torch.stack([f1.reshape(-1), f2.reshape(-1)], dim=-1)
            if n_env:
                ref_feat = torch.cat(
                    [ref_feat, ref_feat.new_zeros(ref_feat.shape[0], n_env)], dim=-1)
        if int(ref_feat.shape[-1]) != 2 + n_env:
            raise ValueError(
                f"ref_feat has {int(ref_feat.shape[-1])} columns, expected {2 + n_env} "
                f"(2 state features + {n_env} env channels)"
            )
        self.register_buffer("ref_feat", ref_feat)

    @property
    def p(self) -> torch.Tensor:
        """The learnable POC exponent (init 1.0; Darwin/Parekh reference 0.58)."""
        return F.softplus(self.raw_p)

    def _corr(self, feat: torch.Tensor) -> torch.Tensor:
        """The raw bounded correction in ``[1-eps, 1+eps]``, before mean-centring."""
        return 1.0 + self.eps * torch.tanh(self.net(feat).squeeze(-1))

    def G(self, feat: torch.Tensor) -> torch.Tensor:
        """The **level-free** shape factor: geometric mean 1 over ``ref_feat``.

        Recomputed each call because the weights move during training; taken over the
        fixed reference support, never the batch. At init the readout is zero, so
        ``_corr == 1`` exactly, ``log`` of it is exactly 0, and ``G == 1`` bitwise.
        """
        log_mean = torch.log(self._corr(self.ref_feat.to(feat.dtype))).mean()
        return self._corr(feat) / torch.exp(log_mean)

    def forward(self, DFe: torch.Tensor, POC: torch.Tensor) -> torch.Tensor:
        r0 = math.exp(self.log_r0)
        # floor the normalised POC before BOTH the log feature and the pow
        # backbone: pocn**p has an infinite d/dp (and d/dPOC for p<1) at pocn=0,
        # so the clamp keeps the closure autograd-clean across the p<1 (Parekh
        # ~0.58) regime it is built to explore. Byte-identical for physical POC.
        pocn = (POC / self.POC0).clamp_min(1e-12)
        f1 = torch.log10(DFe.clamp_min(1e-12)) + 4.0
        f2 = torch.log10(pocn)
        feat = torch.stack([f1, f2], dim=-1)                 # [..., cells, 2]
        if self._has_env:
            feat = torch.cat([feat, self.env.to(feat.dtype)], dim=-1)
        return r0 * pocn.pow(self.p) * DFe * self.G(feat)
