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

from darwindiff.carroll6 import N_PARAMS


class DINNRegional(nn.Module):
    """Region-level Darwin-Informed Neural Network (fully-connected MLP).

    Maps environmental covariates to Carroll-6 outputs at the region level.
    The architecture from notebook 06: a small MLP with one hidden layer of
    16 units (Tanh activation), 166 weights at the default size including
    biases.

    Args:
        n_features: number of environmental input features (default 3 for
            SST, wind speed, MLD).
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
        n_outputs: int = N_PARAMS,
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
            3 for SST, wind speed, MLD).
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
        n_outputs: int = N_PARAMS,
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


class PerParamDINN(nn.Module):
    r"""One independent per-cell network per parameter — no representation sharing.

    WHY THIS EXISTS
    ---------------
    The parameterisation ladder (``GLOBAL_SCALAR > POINTWISE > PER_AOI_DINN > DINN``) varies
    **spatial** sharing at every rung: one scalar, a per-cell free field, one network per basin.
    None of them varies **parameter** sharing. :class:`DINN` puts all ``N_PARAMS`` outputs on one
    shared trunk, so every parameter is forced through a single representation of a single
    input-channel set.

    That is a candidate cause of the 3-of-4 observable frontier. The Fisher rank is 4/4 in eqpac
    and natlsubpolar — the information to recover all four is present — yet no single configuration
    recovers more than three, and the documented conflict is representational rather than
    informational: the MLD input channel helps ``diatomgraz`` and breaks ``scav_rat``. An input
    channel cannot change what the observations contain; it changes what the shared trunk can
    express. See ``docs/findings/2026-08-03_prereg_per_parameter_routing.md``.

    This module removes that sharing entirely: ``n_outputs`` independent trunks, each emitting one
    parameter, each seeing all input channels. It is a drop-in for :class:`DINN` — same forward
    signature, same unbounded output ordered by the registry — so
    :func:`darwindiff.carroll6.bounded_params` applies unchanged.

    CAPACITY IS THE CONFOUND. Independent trunks at the same ``hidden_dim`` have roughly
    ``n_outputs`` times the parameters of one shared trunk, and "a bigger network fits better" is
    exactly the confound that made the 2026-07-12 resolution-sharpening result null. Use
    :meth:`matched_hidden_dim` to size a shared-trunk control to the same budget, and compare
    against that, not against the default width.

    Args:
        n_input_channels: environmental channels per cell.
        hidden_dim: width of each per-parameter trunk.
        n_outputs: number of parameters, one trunk each.
        n_hidden_layers: 1x1 hidden layers per trunk.

    Forward:
        ``[n_input_channels, H, W] -> [n_outputs, H, W]``, or batched
        ``[B, n_input_channels, H, W] -> [B, n_outputs, H, W]``.
    """

    def __init__(
        self,
        n_input_channels: int = 3,
        hidden_dim: int = 16,
        n_outputs: int = N_PARAMS,
        n_hidden_layers: int = 2,
    ) -> None:
        super().__init__()
        self.n_outputs = int(n_outputs)
        self.heads = nn.ModuleList([
            DINN(
                n_input_channels=n_input_channels,
                hidden_dim=hidden_dim,
                n_outputs=1,
                n_hidden_layers=n_hidden_layers,
            )
            for _ in range(self.n_outputs)
        ])

    @staticmethod
    def matched_hidden_dim(
        n_input_channels: int,
        hidden_dim: int,
        n_outputs: int = N_PARAMS,
        n_hidden_layers: int = 2,
    ) -> int:
        """Width a shared-trunk :class:`DINN` needs to match this module's parameter count.

        Returns the largest width whose shared-trunk count does not exceed the per-parameter
        budget, so the capacity-matched control is never *advantaged*. Search rather than solve:
        the count is quadratic in width once ``n_hidden_layers > 1`` and an off-by-one here would
        silently reintroduce the confound it exists to remove.
        """
        def count(cls_kwargs: dict) -> int:
            return sum(p.numel() for p in DINN(**cls_kwargs).parameters())

        budget = n_outputs * count({
            "n_input_channels": n_input_channels, "hidden_dim": hidden_dim,
            "n_outputs": 1, "n_hidden_layers": n_hidden_layers,
        })
        best = 1
        for w in range(1, 4096):
            if count({
                "n_input_channels": n_input_channels, "hidden_dim": w,
                "n_outputs": n_outputs, "n_hidden_layers": n_hidden_layers,
            }) <= budget:
                best = w
            else:
                break
        return best

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        outs = [h(env) for h in self.heads]
        return torch.cat(outs, dim=0 if env.ndim == 3 else 1)


class _PerCellLayerNorm(nn.Module):
    """LayerNorm over the channel dim only, applied independently at each (h, w).

    Required for per-cell architecture — alternatives like ``GroupNorm(num_groups=1)``
    or ``InstanceNorm2d`` couple cells via shared normalisation statistics, which
    breaks the per-cell parameter-recovery argument.
    """

    def __init__(self, n_channels: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(n_channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # [B, C, H, W] -> [B, H, W, C] -> norm over last dim -> [B, C, H, W]
        return self.norm(x.permute(0, 2, 3, 1)).permute(0, 3, 1, 2)


class _PerCellResBlock(nn.Module):
    """A per-cell residual block: norm -> 1x1 conv -> GELU -> norm -> 1x1 conv + skip.

    All operations are 1x1 convolutions plus per-cell LayerNorm, so each cell
    is processed independently (no spatial coupling, no shared normalisation
    statistics across cells).
    """

    def __init__(self, hidden_dim: int) -> None:
        super().__init__()
        self.norm1 = _PerCellLayerNorm(hidden_dim)
        self.conv1 = nn.Conv2d(hidden_dim, hidden_dim, kernel_size=1)
        self.norm2 = _PerCellLayerNorm(hidden_dim)
        self.conv2 = nn.Conv2d(hidden_dim, hidden_dim, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.conv1(nn.functional.gelu(self.norm1(x)))
        x = self.conv2(nn.functional.gelu(self.norm2(x)))
        return x + residual


class DINNDeep(nn.Module):
    """Upgraded per-cell Darwin-Informed Neural Network for production fits.

    Drops the 2-layer 16-dim Tanh design of :class:`DINN` for a deeper, wider,
    modern network: multi-channel input, configurable depth, residual blocks
    with GELU + GroupNorm, all built from 1x1 convolutions to preserve the
    per-cell parameter-recovery semantics (no spatial coupling between cells).

    The structural argument from notebooks 09-14 (per-cell DINN class beats
    global-scalar Green's-functions class) is unchanged — both still represent
    a single parameter vector per cell, just with different network capacity.
    DINNDeep is what you reach for when you want the actual best fit DarwinDiff
    can produce on a given (AOI, target) combination, not the smallest network
    that demonstrates the structural argument.

    Default config (~8.5K weights at 4 input channels):
        - 4 input channels (e.g. SST + MLD + windspeed + latitude)
        - 32 hidden dim
        - 4 residual blocks (8 conv layers + skip connections)
        - GELU activation, pre-norm LayerNorm-equivalent (GroupNorm groups=1)

    Args:
        n_input_channels: number of environmental covariates per cell. Default
            4. Set to 1 for SST-only (matches the SST-only DINN baseline).
        hidden_dim: width of the hidden representation. Default 32.
        n_outputs: number of Carroll parameters per cell. Default 6.
        n_blocks: number of residual blocks. Default 4.

    Forward:
        ``env`` shape ``[n_input_channels, H, W]`` -> ``[n_outputs, H, W]``.
        Batched ``[B, n_input_channels, H, W]`` -> ``[B, n_outputs, H, W]`` also works.

        The output is **unbounded**; pair with
        :func:`darwindiff.carroll6.bounded_params` to map into physical Carroll-6
        ranges.
    """

    def __init__(
        self,
        n_input_channels: int = 4,
        hidden_dim: int = 32,
        n_outputs: int = N_PARAMS,
        n_blocks: int = 4,
    ) -> None:
        super().__init__()
        if n_blocks < 1:
            raise ValueError(f"n_blocks must be >= 1, got {n_blocks}")
        if hidden_dim < 1:
            raise ValueError(f"hidden_dim must be >= 1, got {hidden_dim}")
        # Project from input channels into the hidden representation.
        self.input_proj = nn.Conv2d(n_input_channels, hidden_dim, kernel_size=1)
        # Stack of residual blocks at hidden width.
        self.blocks = nn.Sequential(
            *[_PerCellResBlock(hidden_dim) for _ in range(n_blocks)]
        )
        # Final norm + project to Carroll-6 outputs.
        self.output_norm = _PerCellLayerNorm(hidden_dim)
        self.output_proj = nn.Conv2d(hidden_dim, n_outputs, kernel_size=1)

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        squeeze = env.ndim == 3
        if squeeze:
            env = env.unsqueeze(0)
        x = self.input_proj(env)
        x = self.blocks(x)
        x = self.output_proj(nn.functional.gelu(self.output_norm(x)))
        if squeeze:
            x = x.squeeze(0)
        return x


class GlobalScalarNet(nn.Module):
    """Ablation control: a single GLOBAL parameter vector applied to every cell.

    Drop-in replacement for :class:`DINN` with the identical call signature
    (``env -> [n_outputs, H, W]``), but the output is **constant across cells**:
    one learnable ``n_outputs``-vector broadcast to the whole grid. Pair with
    :func:`darwindiff.carroll6.bounded_params` exactly like ``DINN`` (the raw
    vector is unbounded; the sigmoid map is applied downstream).

    This is the control for the per-cell-vs-global-scalar ablation. It is the
    differentiable analogue of Carroll's actual calibration, which produces a
    *single* global Carroll-6 parameter set (one Green's-functions optimum), not
    a per-cell field. Holding the forcing, the forward integrator, the loss, and
    the scoring byte-identical and swapping ONLY the parameter source isolates
    what the per-cell predictor buys: if per-cell does not beat this control on
    the real-anchor loss, the per-cell architecture is not load-bearing.

    The forward ignores the per-cell content of ``env`` (by construction — a
    global scalar cannot use per-cell covariates) but still reads its spatial
    shape so the broadcast matches whatever grid the runner feeds in.
    """

    def __init__(self, n_input_channels: int = 3, hidden_dim: int = 16,
                 n_outputs: int = N_PARAMS, n_hidden_layers: int = 2) -> None:
        # Signature mirrors DINN so the runner can construct it the same way;
        # only n_outputs is used. theta starts near 0 (-> mid-bounds via sigmoid),
        # with small per-seed jitter for ensemble spread (seed set by the caller).
        super().__init__()
        self.theta = nn.Parameter(0.01 * torch.randn(n_outputs))

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        n = self.theta.shape[0]
        if env.ndim == 3:
            h, w = env.shape[-2], env.shape[-1]
            return self.theta.view(n, 1, 1).expand(n, h, w)
        b, h, w = env.shape[0], env.shape[-2], env.shape[-1]
        return self.theta.view(1, n, 1, 1).expand(b, n, h, w)


class PerCellFreeField(nn.Module):
    """Ablation control: an UNCONSTRAINED per-cell parameter field, no network.

    Drop-in replacement for :class:`DINN` with the identical call signature
    (``env -> [n_outputs, H, W]``), but the output is a raw learnable tensor of
    shape ``[n_outputs, H, W]`` — one free value per parameter per grid cell,
    with no covariate conditioning and no spatial coupling of any kind. Pair
    with :func:`darwindiff.carroll6.bounded_params` exactly like ``DINN``.

    This is the third rung of the parameterisation ladder, and it is the control
    the inverse-problems literature uses for a neural field. Xu & Darve's ADCME
    compares a DNN-parameterised coefficient field against a *pointwise*
    estimate and reports that the DNN generalises better, i.e. that the network
    acts as a regulariser restricting the admissible function space. Our
    published ablation compares :class:`DINN` (~406 weights) only against
    :class:`GlobalScalarNet` (6 scalars), which shows that per-cell *structure*
    matters but cannot show that the *network* does. This class supplies the
    missing arm:

        global scalar (6)  <  DINN (406)  <  per-AOI DINN (3x406)  <  free field

    Interpretation is fixed in advance (see
    ``docs/findings/2026-07-29_preregistration_obsonly_and_ladder.md``): if the
    free field recovers *worse* than ``DINN`` despite having ~40x the degrees of
    freedom, the network is regularising and "the per-cell architecture is
    load-bearing" is earned. If it recovers the same, the claim must be scoped
    to per-cell *structure*. If it recovers better, degrees of freedom are doing
    the work and the DINN claim is deflated.

    Deliberately carries **no** smoothness or magnitude penalty. An
    unregularised free field is the actual pointwise control; adding a penalty
    would make it a third parameterisation rather than a null.

    Because the field is tied to one grid, it **cannot be shared across AOIs**
    the way the flagship ``DINN`` is. That is a real asymmetry, not an
    implementation detail: this arm gets per-cell freedom *and* per-AOI freedom
    at once, which is why ``PER_AOI_DINN=1`` must be run alongside it to
    separate the two axes.

    Args:
        height: grid rows ``H`` for the AOI this field is bound to.
        width: grid columns ``W`` for the AOI this field is bound to.
        n_outputs: number of Carroll parameters per cell (registry-derived).

    ``n_input_channels`` / ``hidden_dim`` / ``n_hidden_layers`` are accepted and
    ignored so the runner can construct this the same way it constructs
    ``DINN``.
    """

    def __init__(
        self,
        height: int,
        width: int,
        n_input_channels: int = 3,
        hidden_dim: int = 16,
        n_outputs: int = N_PARAMS,
        n_hidden_layers: int = 2,
    ) -> None:
        super().__init__()
        if height <= 0 or width <= 0:
            raise ValueError(f"PerCellFreeField needs a positive grid, got {height}x{width}")
        self.height = int(height)
        self.width = int(width)
        # Same init geometry as GlobalScalarNet (0.01 * randn -> sigmoid maps to
        # mid-bounds) so the UNTRAINED distribution is comparable across rungs
        # and the measured chance baseline stays interpretable. Seed is set by
        # the caller, exactly as for DINN / GlobalScalarNet.
        self.theta = nn.Parameter(0.01 * torch.randn(n_outputs, self.height, self.width))

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        h, w = env.shape[-2], env.shape[-1]
        if (h, w) != (self.height, self.width):
            raise ValueError(
                f"PerCellFreeField was built for a {self.height}x{self.width} grid "
                f"but received env of {h}x{w}. This field is bound to one AOI; "
                f"build a separate instance per AOI."
            )
        if env.ndim == 3:
            return self.theta
        return self.theta.unsqueeze(0).expand(env.shape[0], *self.theta.shape)
