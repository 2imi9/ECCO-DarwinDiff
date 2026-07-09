"""Held-out real-observation harness for the Track-2 (UDE) E2 gate (DB-3).

This is the last data-staging piece before a *real-data* E2 number. It packages a
real, Darwin-independent observation (calcite rain ratio; iron as the counterexample)
into the exact tuple :func:`darwindiff.trainer.train_ude_closure` consumes — target
field, train/held-out masks, closure env channels, an observable, and the anomaly-R^2
scoring pieces — on the **shared 1-deg grid** the DB-1 forcing and DB-2 velocity loaders
already align to.

**What the E2 gate asks.** Can a learned closure, fit on part of a real observation and
scored on **held-out** cells *through prescribed transport*, beat a constant (null)
closure run through the *identical* transport? That is the make-or-break that would turn
Track-1's consistency check into a genuine held-out validation. This module supplies the
observation side of that question; the runner (``scripts/e2_real_calcite_eqpac.py``)
supplies the IC / DB-1 forcing / DB-2 velocity and the null-vs-learned + K_num controls.

**Calcite leads; iron is the counterexample.** Per the E2 guardrails
(``docs/research_notes/2026-07-07_deep_review_e2_readiness.md``):

- **Calcite** (:func:`held_out_calcite_obs`). The observable is **log PIC:POC**, which is
  ~= the parameter it constrains (``R_PICPOC``), so a held-out pass is *meaningful*. The
  target is the **Daniels et al. 2018 CP:PP** compilation (:mod:`darwindiff.daniels_loader`)
  — direct, georeferenced calcite-*production* ratios that are **Darwin-independent** (not
  MODIS PIC, not Darwin's own PIC field), so the recovery is non-circular. Honest caveat:
  Daniels is **low-powered** (eqpac geomean 0.039 ~= Darwin's 0.042, ~1.6x the global mean)
  — it *corroborates* a regionally-variable rain ratio, it does not sharply validate a
  specific value. Calcite is **environment-dominated** (Omega_calcite, SST), with
  composition a *minor* modulation.
- **Iron** (:func:`held_out_iron_obs`). GEOTRACES dissolved iron, same methodology, as the
  documented **information-wall counterexample**: iron *concentration* is a low-information
  projection of the scavenging *rate* (Tagliabue decoupling), so a held-out iron R^2>0 can
  come from an equifinal, meaningless ``scav_rat``. Report it *as* the counterexample, not
  a second attempt.

**Env-regime hold-out, not spatial blocking.** For a *per-cell env* closure ``g(env)``,
spatial blocking leaks — env interpolates across spatial blocks. The hold-out here is an
**env regime**: the upper quartile of Omega_calcite (an extrapolation to an unseen
environmental band). This is the split :func:`env_regime_split` builds.

**Anomaly-R^2 against the train basin mean.** Level-R^2 rewards predicting the basin mean;
the metric here (:func:`anomaly_masked_r2`) scores skill *relative to the constant train
basin mean*, so only genuine held-out spatial/regime structure counts.

**Honesty guardrail.** Nothing here produces an E2 number — it stages the *inputs*. Until
the runner lands a learned-minus-null held-out anomaly-R^2 at physical ``kh`` (with the
K_num ablation as the load-bearing control), Track-2 remains synthetic/feasibility. Do not
say "made Darwin differentiable" / "confirmed the thesis".

**NaN-poisoning precaution (load-bearing).** The learned closure is evaluated at *every*
cell of the rollout, not only the scored ones — so a single non-finite env value at any
cell emits a NaN gradient that transport then spreads into the train cells, silently
poisoning the whole optimizer (a class of bug prior Track-2 reviews caught). Every env
channel returned here is standardized **and** ``nan_to_num``-ed to a neutral (0 = mean)
value at non-covered / non-finite cells, so the closure never sees a NaN.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import NamedTuple

import numpy as np
import torch
from torch import nn

from darwindiff.carbonate import calcite_saturation
from darwindiff.daniels_loader import (
    DEFAULT_DANIELS_PATH,
    DanielsPoints,
    build_aoi_climatology,
)
from darwindiff.ecco_darwin_loader import AOI
from darwindiff.transport import interior_mask

# --- cache resolution ---------------------------------------------------------
# The AOI .pt caches (SST/SSS/DIC/ALK on the shared 1-deg grid) carry the legacy
# ``eqpac_targets_`` filename prefix from the probe era; keyed here by AOI name so
# aoi_env_field can find them. Override with ``cache_path`` at the call site.
_DEFAULT_CACHE_DIR = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"
CACHE_FILENAMES: dict[str, str] = {
    "Equatorial Pacific": "eqpac_targets_equatorial_pacific.pt",
    "North Atlantic Subpolar": "eqpac_targets_north_atlantic_subpolar.pt",
    "Southern Ocean Pacific": "eqpac_targets_southern_ocean_pacific.pt",
}

# Env channels aoi_env_field exposes (2-D fields on the shared grid). "omega_c" is
# the calcite saturation state (the primary rain-ratio driver); "sst"/"sss" are raw.
ENV_CHANNELS: tuple[str, ...] = ("sst", "sss", "omega_c", "co3")

# Standardization floor so a (near-)constant channel does not divide by ~0.
_STD_FLOOR = 1e-8


class HeldOutObs(NamedTuple):
    """Everything :func:`darwindiff.trainer.train_ude_closure` needs for one E2 fit.

    All spatial tensors are on the AOI's shared 1-deg grid ``[Y, X]`` (with a depth
    axis ``Z`` where noted), aligned cell-for-cell with the DB-1 forcing and DB-2
    velocity. The observation is **surface** (Daniels/GEOTRACES surface cut), so the
    3-D fields carry the signal only at ``Z=0`` and the masks are ``True`` only there.

    Attributes:
        target: ``[Y, X, Z]`` observed field of the (log) observable, surface-lifted
            (value at ``Z=0``, 0 below). Non-covered cells are 0 (masked out of any loss).
        train_mask, val_mask: ``[Y, X, Z]`` bool. ``val_mask`` selects the held-out env
            regime (upper-quartile Omega band); ``train_mask`` the complement over covered
            cells. Disjoint; both ``False`` off-surface and at non-covered cells.
        coverage_mask: ``[Y, X]`` bool — cells with real observation + env coverage that
            survived the interior-ring and (optional) DB-1 forcing-coverage AND. The union
            of train and val at the surface.
        env: ``[Y, X, Z, n_env]`` standardized + NaN-sanitized closure env channels,
            surface-lifted, ready to construct e.g. :class:`darwindiff.closures.EnvCalciteClosure`.
        env_stats: ``{"channels", "mean" [n_env], "std" [n_env]}`` used to standardize.
        observable: field ``->`` scored quantity (``log PIC:POC`` / ``log DFe``), matching
            ``target``; pass straight to the trainer's ``observable=``.
        hook: which ``grid_tendency`` closure slot the fitted module fills
            (``"calcite_closure"`` / ``"scav_closure"``).
        basin_mean: scalar train-set mean of the (log) observable — the constant baseline
            :func:`anomaly_masked_r2` scores skill against.
        band_edge: the Omega_calcite band edge (least-extreme held-out value) of the
            rank-based env-regime split.
        n_train, n_val: covered-cell counts in each split.
    """

    target: torch.Tensor
    train_mask: torch.Tensor
    val_mask: torch.Tensor
    coverage_mask: torch.Tensor
    env: torch.Tensor
    env_stats: dict
    observable: Callable[[torch.Tensor], torch.Tensor]
    hook: str
    basin_mean: float
    band_edge: float
    n_train: int
    n_val: int


# --- observables --------------------------------------------------------------
def log_picpoc_observable(field: torch.Tensor, eps: float = 1e-9) -> torch.Tensor:
    """Log PIC:POC rain-ratio observable ``log(PIC/POC)`` (tracer 4 / tracer 3).

    The rain ratio is log-normal (~0.0002-6), so it is scored in log space (decision #2
    for the E2 run: log-space scoring). PIC and POC are floored before the ratio and the
    ratio before the log, so the observable is autograd-clean for any physical state.
    """
    ratio = field[..., 4].clamp_min(eps) / field[..., 3].clamp_min(eps)
    return torch.log(ratio.clamp_min(eps))


def log_dfe_observable(field: torch.Tensor, eps: float = 1e-9) -> torch.Tensor:
    """Log dissolved-iron observable ``log(DFe)`` (tracer 0), floored for the log."""
    return torch.log(field[..., 0].clamp_min(eps))


class SurfaceGatedClosure(nn.Module):
    r"""Wrap a calcite closure so its learned deviation acts ONLY at the surface (Z=0).

    **Why (adversarial-review fix, the E2-attribution control).** The obs is surface-only,
    but a per-cell closure is evaluated at *every* depth of the rollout, and its
    iron-limitation term ``f_lim = DFe/(DFe+K_FE)`` reads the *subsurface* state DFe (which
    the surface-neutralized env cannot zero out). So after training ``g != 1`` below the
    surface, and that untrained-regime subsurface calcite is mixed/advected up to Z=0,
    contaminating the scored surface PIC:POC. The learned-minus-null held-out delta could
    then move for reasons unrelated to surface env skill, breaking the E2 control's
    interpretation.

    This wrapper forces the wrapped closure's output to the **baseline** constant-ratio
    production ``R0 * mort_total`` (i.e. ``g == 1``) at every ``Z > 0`` and uses the learned
    closure only at ``Z = 0``. Because the null (frozen ``g == 1``) closure already equals
    ``R0 * mort_total`` everywhere, gating is a **no-op on the null** and the learned-minus-
    null delta is isolated to the surface layer — the clean, attributable E2 number. Run the
    ungated closure as the *diagnostic* control that measures the subsurface contribution.

    ``mort_total`` (and the returned ``pic_prod``) has the depth axis last (``[..., Z]``),
    so ``[..., 0]`` selects the surface layer. Only wraps calcite-style closures with an
    ``R0`` (e.g. :class:`darwindiff.closures.EnvCalciteClosure`).
    """

    def __init__(self, closure: nn.Module) -> None:
        super().__init__()
        if not hasattr(closure, "R0"):
            raise TypeError(
                "SurfaceGatedClosure wraps a calcite closure with an R0 (baseline ratio); "
                f"{type(closure).__name__} has none."
            )
        self.closure = closure
        self.R0 = float(closure.R0)

    def forward(self, state: torch.Tensor, mort_total: torch.Tensor) -> torch.Tensor:
        full = self.closure(state, mort_total)          # learned, [..., Z]
        base = self.R0 * mort_total                     # g == 1 baseline
        gate = torch.zeros_like(mort_total)
        gate[..., 0] = 1.0                              # surface layer only
        return gate * full + (1.0 - gate) * base


# --- helpers ------------------------------------------------------------------
def _lift_surface(field2d: torch.Tensor, n_z: int, *, fill: float = 0.0) -> torch.Tensor:
    """Lift a ``[Y, X]`` surface field to ``[Y, X, Z]``: value at ``Z=0``, ``fill`` below.

    The observation is a surface measurement and the rollout state is 3-D, so the target
    and env fields carry the signal only in the top layer. ``fill=0`` leaves sub-surface
    env at the standardized mean (neutral) and sub-surface target at 0 (masked out).
    """
    ny, nx = field2d.shape
    out = torch.full((ny, nx, n_z), float(fill), dtype=field2d.dtype, device=field2d.device)
    out[..., 0] = field2d
    return out


def _lift_mask_surface(mask2d: torch.Tensor, n_z: int) -> torch.Tensor:
    """Lift a ``[Y, X]`` bool mask to ``[Y, X, Z]``, ``True`` only at ``Z=0``."""
    ny, nx = mask2d.shape
    out = torch.zeros((ny, nx, n_z), dtype=torch.bool, device=mask2d.device)
    out[..., 0] = mask2d
    return out


def env_regime_split(
    field: torch.Tensor,
    coverage: torch.Tensor,
    *,
    q: float = 0.25,
    hold: str = "upper",
) -> tuple[torch.Tensor, torch.Tensor, float]:
    """Split covered cells by an env-channel **rank** — the env-regime hold-out.

    Holds out an *environmental band* rather than a spatial block: for a per-cell env
    closure ``g(env)``, spatial blocking leaks because env interpolates across blocks,
    whereas holding out the top-``q`` (or bottom-``q``) Omega_calcite cells forces the
    closure to **extrapolate to an unseen env regime** — the honest E2 test.

    **Rank-based, not a value threshold** (adversarial-review fix): holding out exactly
    ``ceil(q * n_covered)`` cells by rank is robust to ties/near-constant channels. A
    naive ``field >= quantile`` threshold silently holds out *all* covered cells when the
    split channel is constant (every cell ``>=`` the constant edge) — a degenerate,
    scientifically-void split. Rank selection always yields ``1 <= n_val < n_covered``
    for ``n_covered >= 2``.

    Args:
        field: ``[Y, X]`` env channel to split on (e.g. Omega_calcite).
        coverage: ``[Y, X]`` bool of admissible (covered) cells.
        q: tail fraction to hold out (0.25 = upper/lower quartile).
        hold: ``"upper"`` (default) holds out the highest-``q`` cells; ``"lower"`` the
            lowest.

    Returns:
        ``(train_mask, val_mask, band_edge)`` — disjoint ``[Y, X]`` bool masks over
        covered cells and the float band edge (the least-extreme held-out value). If no
        cells are covered, both masks are all-``False`` and ``band_edge`` is ``nan``.
    """
    if hold not in ("upper", "lower"):
        raise ValueError(f"hold must be 'upper' or 'lower', got {hold!r}")
    cov_idx = coverage.nonzero(as_tuple=False)          # [n_cov, ndim]
    n_cov = int(cov_idx.shape[0])
    if n_cov == 0:
        empty = torch.zeros_like(coverage)
        return empty, empty.clone(), float("nan")
    vals = field[coverage]
    k = max(1, int(np.ceil(q * n_cov)))                 # number of cells held out
    order = torch.argsort(vals)                         # ascending
    sel = order[-k:] if hold == "upper" else order[:k]  # top-k / bottom-k by rank
    val = torch.zeros_like(coverage)
    picked = cov_idx[sel]
    val[tuple(picked.T)] = True
    train = coverage & ~val
    band_edge = float(vals[sel].min() if hold == "upper" else vals[sel].max())
    return train, val, band_edge


def anomaly_masked_r2(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
    basin_mean: float,
) -> torch.Tensor:
    """Anomaly-R^2 over ``mask`` scored against the constant train ``basin_mean``.

    ``1 - SS_res / SS_tot`` where ``SS_tot`` is the error of predicting the *train basin
    mean everywhere* (not the held-out cells' own mean). So a model that only reproduces
    the basin mean scores ~0, and positive R^2 requires capturing genuine held-out
    spatial/regime structure — the deep-review metric that stops level-R^2 from rewarding
    trivial mean-matching. Returns a 0-d tensor (``SS_tot`` floored, so finite), or ``NaN``
    for an **empty** mask — so a degenerate (0-cell) held-out split can never masquerade as
    perfect skill (``R^2=1`` from ``SS_res=0`` over no cells).
    """
    if int(mask.sum()) == 0:
        return torch.tensor(float("nan"), dtype=pred.dtype, device=pred.device)
    p, t = pred[mask], target[mask]
    ss_res = ((p - t) ** 2).sum()
    ss_tot = ((t - basin_mean) ** 2).sum().clamp_min(torch.finfo(t.dtype).tiny)
    return 1.0 - ss_res / ss_tot


def _resolve_cache(
    aoi: AOI,
    *,
    cache_dir: str | Path | None,
    cache_path: str | Path | None,
    cache: dict | None,
) -> dict:
    """Load the AOI .pt env cache (or return an injected ``cache`` dict for tests)."""
    if cache is not None:
        return cache
    if cache_path is None:
        fname = CACHE_FILENAMES.get(aoi.name)
        if fname is None:
            raise KeyError(
                f"no env cache registered for AOI {aoi.name!r}; pass cache_path= or cache="
            )
        cache_path = Path(cache_dir or _DEFAULT_CACHE_DIR) / fname
    cache_path = Path(cache_path)
    if not cache_path.is_file():
        raise FileNotFoundError(
            f"AOI env cache not found: {cache_path}. Set DARWIN_DATA_ROOT, pass "
            f"cache_dir=/cache_path=, or inject cache= (hermetic tests)."
        )
    return torch.load(cache_path, weights_only=False)


def aoi_env_field(
    aoi: AOI,
    *,
    cache_dir: str | Path | None = None,
    cache_path: str | Path | None = None,
    cache: dict | None = None,
    dtype: torch.dtype = torch.float64,
    device: torch.device | None = None,
) -> dict:
    """Build the AOI's 2-D env channels on the shared 1-deg grid from the .pt cache.

    Reads the cached surface ``sst``/``sss``/``dic_binned``/``alk_binned`` (all
    ``[Y, X]`` on the ``darwin_lats``/``darwin_lons`` grid that aligns with Daniels /
    DB-1 / DB-2) and derives **Omega_calcite** via
    :func:`darwindiff.carbonate.calcite_saturation` (and CO3). Returns raw (un-standardized)
    fields plus a per-cell ``finite`` mask (all inputs + derived Omega finite).

    Returns a dict: ``{channel: [Y, X] tensor for channel in ENV_CHANNELS}`` plus
    ``"lats"``, ``"lons"`` (grid centers) and ``"finite"`` (``[Y, X]`` bool).
    """
    c = _resolve_cache(aoi, cache_dir=cache_dir, cache_path=cache_path, cache=cache)
    sst = np.asarray(c["sst"], dtype=np.float64)
    sss = np.asarray(c["sss"], dtype=np.float64)
    dic = np.asarray(c["dic_binned"], dtype=np.float64)
    alk = np.asarray(c["alk_binned"], dtype=np.float64)
    lats = np.asarray(c["darwin_lats"], dtype=np.float64)
    lons = np.asarray(c["darwin_lons"], dtype=np.float64)

    # Omega_calcite on the full grid; carbonate.* is shape-agnostic. NaN inputs
    # propagate to NaN Omega, captured by the finite mask below.
    carb = calcite_saturation(
        torch.as_tensor(dic), torch.as_tensor(alk),
        torch.as_tensor(sst), torch.as_tensor(sss),
    )
    omega = np.asarray(carb["omega_c"].detach().to(torch.float64))
    co3 = np.asarray(carb["CO3"].detach().to(torch.float64))

    finite = (
        np.isfinite(sst) & np.isfinite(sss) & np.isfinite(dic) & np.isfinite(alk)
        & np.isfinite(omega) & np.isfinite(co3)
    )

    def _t(a):
        return torch.as_tensor(a, dtype=dtype, device=device)

    return {
        "sst": _t(sst), "sss": _t(sss), "omega_c": _t(omega), "co3": _t(co3),
        "lats": _t(lats), "lons": _t(lons),
        "finite": torch.as_tensor(finite, dtype=torch.bool, device=device),
    }


def _standardize_env(
    env_dict: dict,
    channels: tuple[str, ...],
    train2d: torch.Tensor,
    n_z: int,
) -> tuple[torch.Tensor, dict]:
    """Standardize the requested channels over **train** cells, NaN-sanitize, surface-lift.

    Each channel is standardized ``(x-mean)/std`` using **train-cell** statistics only
    (adversarial-review fix: standardizing over train+val would let the closure's input
    scaling *see* the held-out env band, weakening the "unseen regime" extrapolation the
    E2 claim rests on). The result is then ``nan_to_num``-ed to 0 (= the train mean,
    neutral) everywhere non-finite — so the closure, which is evaluated at *every* rollout
    cell (all Z, all cells), never sees a NaN (the optimizer-poisoning precaution).

    ``std`` uses the **population** convention (``correction=0``) and is floored, so a
    single-cell train set gives ``std = _STD_FLOOR`` rather than the unbiased ``std``'s
    ``NaN`` (which ``clamp_min`` does not sanitize and which would silently zero the whole
    channel). Returns the ``[Y, X, Z, n_env]`` env tensor and the ``env_stats`` dict.
    """
    for ch in channels:
        if ch not in env_dict:
            raise KeyError(f"unknown env channel {ch!r}; available: {sorted(ENV_CHANNELS)}")
    means, stds, lifted = [], [], []
    for ch in channels:
        field = env_dict[ch]
        vals = field[train2d]
        mean = vals.mean()
        std = torch.nan_to_num(vals.std(correction=0), nan=0.0).clamp_min(_STD_FLOOR)
        z = (field - mean) / std
        z = torch.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)
        lifted.append(_lift_surface(z, n_z, fill=0.0))
        means.append(mean)
        stds.append(std)
    env = torch.stack(lifted, dim=-1)  # [Y, X, Z, n_env]
    stats = {
        "channels": tuple(channels),
        "mean": torch.stack(means),
        "std": torch.stack(stds),
    }
    return env, stats


def _assemble(
    aoi: AOI,
    target2d: torch.Tensor,
    target_finite2d: torch.Tensor,
    *,
    observable: Callable[[torch.Tensor], torch.Tensor],
    hook: str,
    n_z: int,
    split_channel: str,
    hold: str,
    q: float,
    closure_env_channels: tuple[str, ...],
    env_dict: dict,
    forcing_coverage: torch.Tensor | None,
    interior_ring: int,
    log_target: bool,
) -> HeldOutObs:
    """Shared assembly: coverage AND, env-regime split, lift, package (calcite & iron)."""
    ny, nx = target2d.shape
    dtype, device = target2d.dtype, target2d.device
    if split_channel not in env_dict:
        raise KeyError(
            f"split_channel {split_channel!r} not in env; available: {sorted(ENV_CHANNELS)}"
        )
    split_field = env_dict[split_channel]

    # coverage = real obs & env-finite & split-finite & interior ring & (opt) DB-1 forcing.
    interior = interior_mask(ny, nx, interior_ring, device=device)
    coverage = (
        target_finite2d
        & env_dict["finite"]
        & torch.isfinite(split_field)
        & interior
    )
    if forcing_coverage is not None:
        coverage = coverage & forcing_coverage.to(device=device, dtype=torch.bool)

    train2d, val2d, band_edge = env_regime_split(split_field, coverage, q=q, hold=hold)
    n_train = int(train2d.sum())
    n_val = int(val2d.sum())

    # Degenerate-split guard (adversarial-review fix): a 0-cell train or val split is
    # scientifically void, and an empty val_mask would otherwise score a FALSE perfect
    # held-out R^2. Fail loudly rather than return a plausible-looking but meaningless obs.
    if n_train == 0 or n_val == 0:
        raise ValueError(
            f"degenerate env-regime split: n_train={n_train}, n_val={n_val} from "
            f"{int(coverage.sum())} covered cells (q={q}, interior_ring={interior_ring}). "
            f"Too few covered cells for a hold-out — raise q, lower interior_ring, relax "
            f"forcing_coverage, or pool AOIs (E2 decision #1)."
        )

    # target -> (log) observable target, surface-lifted; non-covered set to 0 (masked out).
    tgt2d = torch.log(target2d.clamp_min(torch.finfo(dtype).tiny)) if log_target else target2d
    tgt2d = torch.where(coverage, tgt2d, torch.zeros_like(tgt2d))
    tgt2d = torch.nan_to_num(tgt2d, nan=0.0, posinf=0.0, neginf=0.0)

    # standardize env over TRAIN cells only (held-out band stays unseen in input scaling too)
    env, env_stats = _standardize_env(env_dict, closure_env_channels, train2d, n_z)

    train_mask = _lift_mask_surface(train2d, n_z)
    val_mask = _lift_mask_surface(val2d, n_z)
    target = _lift_surface(tgt2d, n_z, fill=0.0)

    basin_mean = float(tgt2d[train2d].mean())

    return HeldOutObs(
        target=target,
        train_mask=train_mask,
        val_mask=val_mask,
        coverage_mask=coverage,
        env=env,
        env_stats=env_stats,
        observable=observable,
        hook=hook,
        basin_mean=basin_mean,
        band_edge=band_edge,
        n_train=n_train,
        n_val=n_val,
    )


def held_out_calcite_obs(
    aoi: AOI,
    *,
    n_z: int = 6,
    split_channel: str = "omega_c",
    hold: str = "upper",
    q: float = 0.25,
    closure_env_channels: tuple[str, ...] = ("sst", "omega_c"),
    depth_max: float = 50.0,
    daniels_path: str | Path = DEFAULT_DANIELS_PATH,
    points: DanielsPoints | None = None,
    cache_dir: str | Path | None = None,
    cache_path: str | Path | None = None,
    cache: dict | None = None,
    forcing_coverage: torch.Tensor | None = None,
    interior_ring: int = 1,
    eps: float = 1e-9,
    dtype: torch.dtype = torch.float64,
    device: torch.device | None = None,
) -> HeldOutObs:
    """Held-out **calcite** (log PIC:POC) observation for the E2 gate — the primary target.

    Target = Daniels et al. 2018 CP:PP geometric-mean rain ratio on the AOI's shared 1-deg
    grid (:func:`darwindiff.daniels_loader.build_aoi_climatology`, Darwin-independent, so
    non-circular). Observable = ``log(PIC/POC)``. Held-out band = the upper quartile of
    Omega_calcite (env-regime extrapolation). Coverage ANDs the Daniels finite cells with
    env-finite, the interior ring (A6 wall exclusion), and — if given — the DB-1
    ``iron_forcing_loader.coverage_mask`` (harmless on eqpac, load-bearing on coastal AOIs).

    Args mirror :class:`HeldOutObs`'s knobs; ``points``/``cache``/``forcing_coverage`` are
    injectable for hermetic tests. ``hook`` is fixed to ``"calcite_closure"``.

    Honest scope: this stages the observation only; it does not produce an E2 number, and
    Daniels is a low-powered (corroborating, not sharply validating) anchor.
    """
    values, dmask, _counts = build_aoi_climatology(
        aoi, daniels_path=daniels_path, depth_max=depth_max, points=points,
    )
    env_dict = aoi_env_field(
        aoi, cache_dir=cache_dir, cache_path=cache_path, cache=cache,
        dtype=dtype, device=device,
    )
    _assert_grid_aligned(aoi, values.shape, env_dict, "Daniels calcite")
    target2d = torch.as_tensor(values, dtype=dtype, device=device)
    target_finite2d = torch.as_tensor(dmask, dtype=torch.bool, device=device) & torch.isfinite(target2d)
    return _assemble(
        aoi, target2d, target_finite2d,
        observable=partial(log_picpoc_observable, eps=eps),
        hook="calcite_closure",
        n_z=n_z, split_channel=split_channel, hold=hold, q=q,
        closure_env_channels=closure_env_channels, env_dict=env_dict,
        forcing_coverage=forcing_coverage, interior_ring=interior_ring,
        log_target=True,
    )


def held_out_iron_obs(
    aoi: AOI,
    *,
    n_z: int = 6,
    split_channel: str = "omega_c",
    hold: str = "upper",
    q: float = 0.25,
    closure_env_channels: tuple[str, ...] = ("sst", "omega_c"),
    depth_max: float = 50.0,
    geotraces_path: str | Path | None = None,
    dfe_grid: np.ndarray | None = None,
    cache_dir: str | Path | None = None,
    cache_path: str | Path | None = None,
    cache: dict | None = None,
    forcing_coverage: torch.Tensor | None = None,
    interior_ring: int = 1,
    eps: float = 1e-9,
    dtype: torch.dtype = torch.float64,
    device: torch.device | None = None,
) -> HeldOutObs:
    """Held-out **iron** (log DFe) observation — the information-wall COUNTEREXAMPLE.

    Same methodology as :func:`held_out_calcite_obs` but the target is GEOTRACES IDP2025
    dissolved iron (:func:`darwindiff.geotraces_loader.dfe_aoi_1deg_grid`, edge-aligned to
    the shared grid) and the fitted hook is ``"scav_closure"`` (the learnable iron sink).
    Reported *as the counterexample*: a held-out iron R^2>0 need not mean a meaningful
    ``scav_rat`` — iron concentration under-constrains the scavenging rate (Tagliabue).

    Pass ``geotraces_path`` to load the NetCDF, or inject ``dfe_grid`` ``[Y, X]`` (mmol/m^3)
    for hermetic tests.
    """
    if dfe_grid is None:
        if geotraces_path is None:
            raise ValueError("pass geotraces_path= (load) or dfe_grid= (inject)")
        from darwindiff.geotraces_loader import dfe_aoi_1deg_grid
        dfe_grid = dfe_aoi_1deg_grid(geotraces_path, aoi, depth_max=depth_max)
    env_dict = aoi_env_field(
        aoi, cache_dir=cache_dir, cache_path=cache_path, cache=cache,
        dtype=dtype, device=device,
    )
    _assert_grid_aligned(aoi, np.asarray(dfe_grid).shape, env_dict, "GEOTRACES DFe")
    target2d = torch.as_tensor(np.asarray(dfe_grid), dtype=dtype, device=device)
    target_finite2d = torch.isfinite(target2d) & (target2d > 0)
    return _assemble(
        aoi, target2d, target_finite2d,
        observable=partial(log_dfe_observable, eps=eps),
        hook="scav_closure",
        n_z=n_z, split_channel=split_channel, hold=hold, q=q,
        closure_env_channels=closure_env_channels, env_dict=env_dict,
        forcing_coverage=forcing_coverage, interior_ring=interior_ring,
        log_target=True,
    )


def _assert_grid_aligned(aoi: AOI, target_shape, env_dict: dict, what: str) -> None:
    """Fail loudly if the target grid and the env grid are not the same 1-deg cells.

    The whole DB-1/DB-2/DB-3 story rests on cell-for-cell alignment; a silent (20,51) vs
    (21,51) mismatch (the GEOTRACES edge-convention bug this module's ``dfe_aoi_1deg_grid``
    fixes) would misregister every target against its env. Cheap guard, load-bearing.
    """
    lats, lons = env_dict["lats"], env_dict["lons"]
    env_shape = (int(lats.shape[0]), int(lons.shape[0]))
    if tuple(target_shape) != env_shape:
        raise ValueError(
            f"{what} grid {tuple(target_shape)} != env grid {env_shape} for AOI "
            f"{aoi.name!r}. Both must be the shared integer-degree 1-deg grid "
            f"(bin_to_1deg_grid / Daniels _aoi_centers)."
        )
    # centers must be integer-degree and span the AOI inclusive (both loaders agree).
    # Check VALUES, not just counts (adversarial-review fix): a same-count but
    # half-degree-offset cache (integer+0.5 centers) would misregister every target
    # against its env yet pass a shape-only check.
    exp_lats = np.arange(aoi.lat_min, aoi.lat_max + 0.5, 1.0)
    exp_lons = np.arange(aoi.lon_min, aoi.lon_max + 0.5, 1.0)
    if env_shape != (len(exp_lats), len(exp_lons)):
        raise ValueError(
            f"{what}: env grid {env_shape} != AOI-expected {(len(exp_lats), len(exp_lons))} "
            f"(lat {aoi.lat_min}..{aoi.lat_max}, lon {aoi.lon_min}..{aoi.lon_max})."
        )
    got_lats = np.asarray(lats.detach().cpu() if torch.is_tensor(lats) else lats, dtype=float)
    got_lons = np.asarray(lons.detach().cpu() if torch.is_tensor(lons) else lons, dtype=float)
    if not (np.allclose(got_lats, exp_lats, atol=1e-6) and np.allclose(got_lons, exp_lons, atol=1e-6)):
        raise ValueError(
            f"{what}: env grid CENTERS are not the shared integer-degree centers for AOI "
            f"{aoi.name!r} (lat0={got_lats[0]} vs {exp_lats[0]}, lon0={got_lons[0]} vs "
            f"{exp_lons[0]}). A half-degree offset would misregister every target vs its env."
        )
