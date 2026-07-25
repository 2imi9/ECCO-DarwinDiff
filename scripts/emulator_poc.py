#!/usr/bin/env python
"""Track-2 emulator make-or-break proof-of-concept.

THE QUESTION
------------
Can a Fourier Neural Operator (FNO) learn ECCO-Darwin v05's *next-month* surface
state well enough to **beat persistence** (``x_hat(t+1) = x(t)``) on held-out
months? Persistence is a *strong* baseline because the ocean is strongly
autocorrelated month-to-month, so the honest headline metric is **skill over
persistence**::

    SKILL = 1 - MSE(model) / MSE(persistence)          (>0 means it beats copying)

not a raw R^2 (a raw R^2 near 1 is trivially achievable by near-copying the
input and says nothing about learned dynamics).

WHAT THIS SCRIPT DOES (and how it stays honest)
-----------------------------------------------
* Region: an AOI (default the Equatorial Pacific, ``eqpac``), a handful of
  carbon tracers (default DIC, ALK, PIC, POC, FeT, Chl1), surface level by
  default (``--levels`` reads the top-N depth levels).
* Data: native LLC270 monthly fields, read with the repo's low-level partial-read
  primitives (surface / top-N levels only -- never the full 181 MB/file), binned
  to the AOI's shared 1-deg grid. Tracers are joined on their **iteration stamp**
  (the shared physical-time key); channels present at different sets of months are
  intersected so every model input/target is a coherent same-date snapshot.
* Split: a purely **temporal** hold-out -- the earlier ``1-val_frac`` fraction of
  months trains, the later ``val_frac`` validates. Standardization statistics
  (per-tracer z-score) are computed from the **train months only** -- no leakage.
  Pairs never straddle the split boundary, and pairs across a missing-month gap
  are dropped so every ``(x_t -> x_{t+1})`` pair is a genuine one-snapshot step.
* Model: the repo's :func:`darwindiff.emulator.build_emulator` FNO (swaps in
  ``physicsnemo.models.fno.FNO`` on the cluster when installed), prognostic
  (input variable set == output variable set), one-month autoregressive step.
  Forcing channels (SST / wind / MLD) are an optional *input-only* augmentation.
* Baselines: (1) persistence ``x_hat(t+1)=x(t)``; (2) train climatology (per-cell
  temporal mean) for an anomaly-R^2.
* Metrics on the held-out months: per-tracer and overall MSE; the headline
  **skill over persistence**; anomaly-R^2 vs train climatology; a multi-step
  autoregressive **rollout stability** check (does it drift / blow up over k
  steps, and does it stay physical / conserve mass); reported alongside a clear
  verdict and a JSON summary.

Land handling: MITgcm writes land as exactly ``0.0`` in the tracer files, so land
cells are dropped at load (``!= 0`` + finite), binning leaves them ``NaN``, and a
fixed **valid-ocean mask** (finite across every channel and month) is the ONLY
region ever scored. For the FNO input, standardized land cells are filled with
``0`` (= the per-channel train mean in z-space, the least-biasing constant); those
cells are never in the metric mask, so a fabricated land value cannot inflate skill.

Determinism: seeded via ``torch.manual_seed`` / a seeded numpy RNG; no time-based
or unseeded randomness anywhere.

RUNNING
-------
Local CPU smoke (fp64, tiny)::

    python scripts/emulator_poc.py --cpu --n-months 24 --epochs 30 \
        --tracers DIC,ALK,PIC --out /tmp/emulator_poc_smoke.json

Cluster (Explorer H200, CUDA fp32, full)::

    python scripts/emulator_poc.py --epochs 300 \
        --forcing SST,wspeed,mldDepth \
        --out docs/findings/emulator_poc_h200.json

Device / dtype rule: CUDA (when available and ``--cpu`` not passed) runs fp32; CPU
runs fp64. The bundled fallback FNO stores its spectral weights as complex64, so
the fp64 CPU path upcasts every parameter (real -> float64, complex -> complex128)
before the forward -- verified to keep autograd flowing to all params.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# --- make the repo's src/ importable whether run from repo root or elsewhere ---
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import torch  # noqa: E402
from torch import nn  # noqa: E402

from darwindiff.ecco_darwin_loader import AOI, AOI_BY_KEY  # noqa: E402
from darwindiff.emulator import DarwinEmulator, FNO2d, build_emulator  # noqa: E402
from darwindiff.iron_forcing_loader import load_grid_lonlat  # noqa: E402
from darwindiff.llc270_loader import (  # noqa: E402
    DEFAULT_CONFIG,
    aoi_mask_from_xc_yc,
    bin_to_1deg_grid,
    list_available_iterations,
)
from darwindiff.velocity_loader import read_hfacc_topz  # noqa: E402

# LLC270 native geometry (compact big-endian float32).
NX = 270
NFACE = 13
NZ_FULL = 50
COMPACT_DTYPE = ">f4"

# Friendly aliases -> on-disk tracer directory names.
TRACER_ALIASES = {"DFe": "FeT", "Fe": "FeT", "IRON": "FeT"}
# 2-D surface forcing/diagnostic fields (single level; masked by ocean, not != 0).
KNOWN_FORCING = {"SST", "wspeed", "mldDepth", "apCO2", "CO2_flux", "PAR"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Track-2 FNO emulator make-or-break PoC (beat persistence?).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--tracers",
        default="DIC,ALK,PIC,POC,FeT,Chl1",
        help="Comma-separated prognostic tracers (input==output). DFe is aliased to FeT.",
    )
    p.add_argument(
        "--forcing",
        default="",
        help="Optional comma-separated INPUT-ONLY forcing channels "
        "(e.g. SST,wspeed,mldDepth). Empty = pure prognostic.",
    )
    p.add_argument(
        "--n-months",
        type=int,
        default=0,
        help="Cap on number of shared monthly snapshots to load (0 = all available).",
    )
    p.add_argument("--levels", type=int, default=1, help="Number of top depth levels per tracer.")
    p.add_argument("--grid-res", type=float, default=1.0,
                   help="AOI rectangular-grid resolution in degrees (1.0=1deg; 0.25~LLC270 native, "
                   "finer resolves more structure). Larger grid -> B200-scale.")
    p.add_argument("--aoi", default="eqpac", help=f"AOI key. One of {sorted(AOI_BY_KEY)}.")
    p.add_argument("--aoi-bounds", default=None,
                   help="Custom AOI 'lat_min,lat_max,lon_min,lon_max' (-180..180 lon). Overrides "
                   "--aoi's bounds while keeping --aoi as the label; enables whole-globe runs, "
                   "e.g. --aoi global --aoi-bounds -80,89.75,-180,180.")
    p.add_argument("--epochs", type=int, default=250, help="Training epochs.")
    p.add_argument("--batch-size", type=int, default=8, help="Minibatch size (pairs).")
    p.add_argument("--lr", type=float, default=1e-3, help="Adam learning rate.")
    p.add_argument("--val-frac", type=float, default=0.3, help="Fraction of latest months held out.")
    p.add_argument("--modes", type=int, default=8, help="FNO Fourier modes per axis.")
    p.add_argument("--width", type=int, default=32, help="FNO latent channels.")
    p.add_argument("--layers", type=int, default=4, help="FNO blocks.")
    p.add_argument("--rollout-steps", type=int, default=6, help="Max autoregressive rollout steps.")
    p.add_argument(
        "--rollout-positivity",
        action="store_true",
        help="Enforce the physical nonnegativity invariant (concentrations >= 0) between autoregressive "
        "rollout steps, so negative values cannot compound. Fixes the negative-concentration rollout.",
    )
    p.add_argument(
        "--rollout-mass-conserve",
        action="store_true",
        help="With --rollout-positivity: after clamping to >=0, rescale each tracer to its pre-clamp "
        "domain mean, so enforcing positivity does not inject mass (fixes the positivity/mean tension).",
    )
    p.add_argument(
        "--time-encoding",
        action="store_true",
        help="Add sin/cos(day-of-year) as 2 input-only channels so the model can place itself in the "
        "annual cycle (seasonal phase). Treated like forcing; no effect on outputs/metrics scope.",
    )
    p.add_argument(
        "--residual",
        action="store_true",
        help="Predict the tendency: x_hat(t+1) = x(t) + FNO(input). The model starts AT persistence "
        "and learns only the correction — the fix for slow tracers (DIC/ALK) where full-next-state hurt.",
    )
    p.add_argument(
        "--rollout-train-k",
        type=int,
        default=1,
        help="Rollout-aware training: accumulate the loss over K autoregressive steps (1 = single-step). "
        "Fixes multi-step rollout degradation.",
    )
    p.add_argument("--seed", type=int, default=0, help="Random seed (determinism).")
    p.add_argument(
        "--dump-fields",
        default=None,
        help="Save the held-out spatial fields (physical pred/true/persistence + lat/lon + rollout) "
        "to this .npz for visualization. No effect on metrics.",
    )
    p.add_argument(
        "--dump-cube",
        default=None,
        help="Extract the AOI state/forcing cube to this .npz (a few MB) and exit — ship it to a "
        "cluster with no native-tree access and train there via --load-cube.",
    )
    p.add_argument(
        "--load-cube",
        default=None,
        help="Load the AOI cube from a --dump-cube .npz instead of reading the native LLC270 tree.",
    )
    p.add_argument("--cpu", action="store_true", help="Force CPU (fp64 smoke).")
    p.add_argument(
        "--no-physicsnemo",
        action="store_true",
        help="Never swap in physicsnemo FNO; use the bundled fallback operator.",
    )
    p.add_argument(
        "--data-root",
        default=None,
        help="Override DARWIN_DATA_ROOT (defaults to env var, else D:\\ecco_darwin_v5).",
    )
    p.add_argument("--grid-dir", default=None, help="Override grid dir (defaults to <root>/grid).")
    p.add_argument(
        "--data-subdir", default="output/monthly",
        help="Subpath under --data-root that holds the per-variable dirs. Default "
        "'output/monthly' (v05 monthly tree). The daily surface layout is flat "
        "(<root>/<var>/), so pass '.' for daily cubes.",
    )
    p.add_argument(
        "--adjacency-tol",
        type=float,
        default=1.6,
        help="A (t,t+1) pair is a valid one-step if its gap <= tol * reference cadence "
        "(the expected monthly stride if --expected-step-days is set, else the median gap).",
    )
    p.add_argument(
        "--expected-step-days",
        type=float,
        default=None,
        help="True monthly stride (days) used as the adjacency reference. Set this when "
        "the cube is uniformly sparse (every gap equal but > 1 month), which the "
        "median-based check cannot detect on its own (#191). Default: infer from the median.",
    )
    p.add_argument(
        "--out",
        default=str(_REPO_ROOT / "docs" / "findings" / "emulator_poc.json"),
        help="Path for the JSON summary.",
    )
    p.add_argument(
        "--save-model",
        default=None,
        help="Save the trained model to this path (.safetensors preferred, else torch .pt): "
        "weights + standardization means/stds + the full config needed to rebuild the "
        "architecture (modes/width/layers/grid/channels). Portable across GPUs "
        "(load on H200 with map_location); no effect on metrics.",
    )
    p.add_argument(
        "--log-transform",
        action="store_true",
        help="Log-transform log-normal tracers (default Chl1..Chl5) BEFORE z-scoring and "
        "exp() back on de-standardization. Chl spans ~2.8e6x, so linear z-scoring gives "
        "NEGATIVE global skill; log-space fixes it. Off by default (bitwise-identical to no "
        "flag). Matches the earth2studio wrapper (src/darwindiff/e2s/prognostic.py): "
        "log(clip(x,1e-12)) before z, exp after, stem-matched on the tracer name before '_k'.",
    )
    p.add_argument(
        "--log-tracers",
        default="Chl1,Chl2,Chl3,Chl4,Chl5,PIC,POC,FeT",
        help="Comma-separated tracer stems to log-transform when --log-transform is set "
        "(matched against the channel-name stem before '_k'). Aligns with prognostic.py log_vars. "
        "PIC/POC/FeT are included because they are strictly-positive, wide-dynamic-range "
        "tracers with the same failure mode as Chl: under linear z-scoring they collapse to "
        "0.34-0.67 of the true log-range and emit 3-14%% non-physical (<=0) output, whereas "
        "log-transformed Chl1 retains 0.97 of its range with 0%% non-physical output.",
    )
    p.add_argument(
        "--log-floor-pct",
        type=float,
        default=1.0,
        help="Percentile of the POSITIVE train-month values used as the per-channel clip floor "
        "before log(). The old fixed 1e-12 floor mapped every non-positive cell to log(1e-12) "
        "= -27.6, ~21 log-units below a typical Chl of 1.8e-3; with 13%% of v05 Chl1 cells "
        "non-positive that inflated the log-space std by 1.72x and compressed the real signal "
        "from +/-1.0 to +/-0.58 z-units. Set 0 to restore the old fixed-epsilon behaviour.",
    )
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Data loading (native LLC270 -> AOI 1-deg grid, partial reads only)
# ---------------------------------------------------------------------------
def _resolve_roots(args) -> tuple[Path, Path]:
    import os

    root = args.data_root or os.environ.get("DARWIN_DATA_ROOT") or r"D:\ecco_darwin_v5"
    root = Path(root)
    subdir = getattr(args, "data_subdir", "output/monthly") or "output/monthly"
    monthly = (root / subdir).resolve() if subdir != "." else root
    grid = Path(args.grid_dir) if args.grid_dir else root / "grid"
    if not monthly.is_dir():
        raise FileNotFoundError(f"data dir not found: {monthly} (root={root}, subdir={subdir!r})")
    if not grid.is_dir():
        raise FileNotFoundError(f"grid dir not found: {grid}")
    return monthly, grid


def _resolve_tracer_dir(name: str) -> str:
    return TRACER_ALIASES.get(name, TRACER_ALIASES.get(name.upper(), name))


def _lon_axis(lon_min: float, lon_max: float, res: float) -> tuple[int, np.ndarray, bool]:
    """Longitude bin count + edges, periodic-aware.

    A full 360-deg span is periodic: the +180 and -180 meridians are the SAME
    line, so the inclusive-endpoint ``+1`` would create a redundant half-width
    column at the seam. For a global span we drop it (1440 cols at 0.25deg, not
    1441). Regional AOIs keep the inclusive-endpoint behavior unchanged.
    """
    is_global = abs((lon_max - lon_min) - 360.0) < res / 2
    if is_global:
        n_lon = int(round((lon_max - lon_min) / res))
        lon_edges = np.linspace(lon_min - res / 2, lon_max - res / 2, n_lon + 1)
    else:
        n_lon = int(round((lon_max - lon_min) / res)) + 1
        lon_edges = np.linspace(lon_min - res / 2, lon_max + res / 2, n_lon + 1)
    return n_lon, lon_edges, is_global


def _aoi_grid_shape(aoi: AOI, res: float = 1.0) -> tuple[int, int]:
    n_lat = int(round((aoi.lat_max - aoi.lat_min) / res)) + 1
    n_lon, _, _ = _lon_axis(aoi.lon_min, aoi.lon_max, res)
    return n_lat, n_lon


def _bin_grid(xc, yc, values, lat_min, lat_max, lon_min, lon_max, res: float = 1.0) -> np.ndarray:
    """Bin scattered native cells onto a ``res``-degree lat/lon grid. ``res=1.0`` reproduces
    ``bin_to_1deg_grid``; finer ``res`` (e.g. 0.25 ~ LLC270 native) resolves finer structure.
    Edge count is derived from :func:`_aoi_grid_shape` so shapes always agree. A global
    longitude span is treated as periodic (no duplicated antimeridian column)."""
    from scipy.stats import binned_statistic_2d
    n_lat = int(round((lat_max - lat_min) / res)) + 1
    lat_edges = np.linspace(lat_min - res / 2, lat_max + res / 2, n_lat + 1)
    n_lon, lon_edges, is_global = _lon_axis(lon_min, lon_max, res)
    xc = np.asarray(xc)
    if is_global:
        # fold cells in the wrapped-away last half-bin (near +180) onto the -180
        # column so the seam is a single column, not two half-width ones.
        xc = xc.copy()
        xc[xc >= lon_max - res / 2] -= 360.0
    binned, _, _, _ = binned_statistic_2d(
        yc.ravel(), xc.ravel(), values.ravel(), statistic="mean", bins=[lat_edges, lon_edges])
    return binned


def _common_iterations(monthly: Path, channels: list[str]) -> list[int]:
    sets = []
    for ch in channels:
        it = list_available_iterations(monthly, ch)
        if not it:
            raise FileNotFoundError(f"no monthly iterations for channel {ch!r} under {monthly}")
        sets.append(set(it))
    return sorted(set.intersection(*sets))


def _read_tracer_month(
    monthly: Path,
    var: str,
    it: int,
    n_z: int,
    xc: np.ndarray,
    yc: np.ndarray,
    ocean: np.ndarray,
    aoi_bbox: np.ndarray,
    aoi: AOI,
    shape2d: tuple[int, int],
    res: float = 1.0,
) -> np.ndarray:
    """Return a tracer's AOI field for one month: ``[Y, X, n_z]`` (NaN=land).

    Partial read of the first ``n_z`` levels only (``k`` outermost). Land is
    dropped via ``!= 0`` + finite (the tracer land-fill is exactly 0.0), then the
    surviving native cells are bin-averaged onto the shared AOI grid.
    """
    path = monthly / var / f"{var}.{it:010d}.data"
    count = n_z * NFACE * NX * NX
    a = np.fromfile(path, dtype=COMPACT_DTYPE, count=count)
    if a.size != count:
        raise ValueError(f"short read {a.size}<{count} from {path}")
    a = a.reshape(n_z, NFACE, NX, NX).astype(np.float64)
    ny, nx = shape2d
    out = np.full((ny, nx, n_z), np.nan, dtype=np.float64)
    for k in range(n_z):
        good = aoi_bbox & ocean[k] & np.isfinite(a[k]) & (a[k] != 0.0)
        if not good.any():
            continue
        out[:, :, k] = _bin_grid(
            xc[good], yc[good], a[k][good], aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max, res
        )
    return out


def _read_forcing_month(
    monthly: Path,
    var: str,
    it: int,
    xc: np.ndarray,
    yc: np.ndarray,
    ocean0: np.ndarray,
    aoi_bbox: np.ndarray,
    aoi: AOI,
    res: float = 1.0,
) -> np.ndarray:
    """Return a 2-D surface forcing field on the AOI grid ``[Y, X]`` (NaN=land).

    Forcing fields (SST/wind/MLD) can be legitimately near-zero over open ocean,
    so land is masked by the surface ocean mask (``hFacC>0``) + finite -- NOT by
    ``!= 0`` (which is only correct for tracers).
    """
    path = monthly / var / f"{var}.{it:010d}.data"
    count = NFACE * NX * NX
    a = np.fromfile(path, dtype=COMPACT_DTYPE, count=count)
    if a.size != count:
        raise ValueError(f"short read {a.size}<{count} from {path}")
    a = a.reshape(NFACE, NX, NX).astype(np.float64)
    good = aoi_bbox & ocean0 & np.isfinite(a)
    return _bin_grid(
        xc[good], yc[good], a[good], aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max, res
    )


def load_dataset(args, aoi: AOI, tracers: list[str], forcings: list[str]):
    """Load the full month x channel stack for the AOI.

    Returns a dict with:
        state       [M, C, H, W] float64, C = len(tracers)*levels  (NaN=land)
        forcing     [M, F, H, W] float64 or None                   (NaN=land)
        valid_mask  [H, W] bool  (finite across every state channel & month)
        iters       list[int] length M (shared iteration stamps)
        times_days  [M] float64  (days since ref_date)
        chan_names  list[str] length C
        forc_names  list[str] length F
    """
    monthly, grid = _resolve_roots(args)
    n_z = int(args.levels)
    tracer_dirs = [_resolve_tracer_dir(t) for t in tracers]
    channels = tracer_dirs + forcings

    common = _common_iterations(monthly, channels)
    if args.n_months and args.n_months > 0:
        common = common[: args.n_months]
    if len(common) < 6:
        raise RuntimeError(
            f"only {len(common)} shared months across {channels}; need >=6. "
            "Widen --n-months or reduce the channel set."
        )

    # Shared LLC270 geometry -- read once.
    xc, yc = load_grid_lonlat(grid)  # (13,270,270) each
    ocean = read_hfacc_topz(grid, n_z) > 0.0  # (n_z,13,270,270)
    aoi_bbox = aoi_mask_from_xc_yc(xc, yc, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
    res = float(getattr(args, "grid_res", 1.0))
    shape2d = _aoi_grid_shape(aoi, res)
    ny, nx = shape2d

    M = len(common)
    C = len(tracers) * n_z
    F = len(forcings)
    state = np.full((M, C, ny, nx), np.nan, dtype=np.float64)
    forcing = np.full((M, F, ny, nx), np.nan, dtype=np.float64) if F else None

    chan_names: list[str] = []
    for t in tracers:
        for k in range(n_z):
            chan_names.append(t if n_z == 1 else f"{t}_k{k}")

    t0 = time.time()
    for m, it in enumerate(common):
        ci = 0
        for tdir in tracer_dirs:
            field = _read_tracer_month(
                monthly, tdir, it, n_z, xc, yc, ocean, aoi_bbox, aoi, shape2d, res
            )  # [Y,X,n_z]
            for k in range(n_z):
                state[m, ci] = field[:, :, k]
                ci += 1
        if forcing is not None:
            for fi, fvar in enumerate(forcings):
                forcing[m, fi] = _read_forcing_month(
                    monthly, fvar, it, xc, yc, ocean[0], aoi_bbox, aoi, res
                )
        if (m + 1) % 20 == 0 or m == M - 1:
            print(
                f"  loaded {m + 1}/{M} months ({time.time() - t0:.1f}s)",
                flush=True,
            )

    # Valid-ocean mask: finite across every state channel and month. This is the
    # ONLY region ever scored, so fabricated land values cannot enter the metrics.
    valid_mask = np.all(np.isfinite(state), axis=(0, 1))  # [H,W]
    if not valid_mask.any():
        raise RuntimeError("no cell is finite across all months/channels; check AOI/data.")

    times_days = np.asarray(common, dtype=np.float64) * float(DEFAULT_CONFIG.delta_t) / 86400.0

    return {
        "state": state,
        "forcing": forcing,
        "valid_mask": valid_mask,
        "iters": list(common),
        "times_days": times_days,
        "chan_names": chan_names,
        "forc_names": list(forcings),
        "grid_shape": shape2d,
        "n_z": n_z,
    }


# ---------------------------------------------------------------------------
# Split, standardization, pairing (all leak-free)
# ---------------------------------------------------------------------------
def build_splits(data, val_frac: float, adjacency_tol: float, expected_step_days: float | None = None):
    """Temporal split + leak-free (t, t+1) pairs.

    Standardization stats come from TRAIN months only. Pairs never cross the
    split boundary, and pairs spanning a missing-month gap are dropped so each
    step is a genuine one-snapshot advance.

    Adjacency is measured against a reference cadence: ``expected_step_days`` when
    given (the cube's true monthly stride), else the median gap. Measuring against
    the median alone silently mislabels a *uniformly-sparse* axis -- one where every
    gap equals the median but is larger than one month (e.g. an every-other-month
    series, or an iter axis like ``[0, 1000, 2000, ...]``): all pairs pass as
    one-step transitions, so multi-month jumps get reported as next-month skill.
    We reject that case explicitly (#191) unless the caller supplies the true
    cadence via ``expected_step_days``.
    """
    times = data["times_days"]
    M = len(times)
    gaps = np.diff(times)
    med_gap = float(np.median(gaps)) if len(gaps) else 0.0
    NOMINAL_MONTH_DAYS = 365.25 / 12.0  # ~30.44 d; one v05 monthly step
    ref = expected_step_days if expected_step_days is not None else med_gap
    # Guard the uniformly-sparse failure mode: if the caller did not pin the cadence
    # and every gap is ~equal AND that common gap exceeds ~1.5 months, the axis is
    # sparse and the median-based test cannot see it -- raise instead of mislabeling.
    if (
        expected_step_days is None
        and len(gaps) >= 2
        and med_gap > 1.5 * NOMINAL_MONTH_DAYS
        # 0.02 was far too tight: real every-other-month calendar gaps run 59-62 d, so
        # ptp/med ~= 0.05 and the guard never fired on the very case it targets. 0.15
        # admits calendar month-length variation while still requiring a uniform stride.
        and float(np.ptp(gaps)) <= 0.15 * med_gap
    ):
        raise RuntimeError(
            f"uniformly-sparse time axis: every step is ~{med_gap:.1f} d "
            f"(> ~1.5 months, ~{med_gap / NOMINAL_MONTH_DAYS:.1f} months), so these are "
            f"multi-month jumps, not one-step transitions -- grading them as next-month "
            f"skill would mislabel the horizon. Pass expected_step_days to grade at the "
            f"true cadence, or rebuild the cube at monthly resolution."
        )
    adjacent = gaps <= adjacency_tol * ref  # adjacent[m] links month m -> m+1

    split_idx = int(round(M * (1.0 - val_frac)))
    split_idx = max(2, min(split_idx, M - 1))  # keep >=2 train months and >=1 val month
    train_months = list(range(0, split_idx))
    val_months = list(range(split_idx, M))

    train_pairs, val_pairs = [], []
    for m in range(M - 1):
        if not adjacent[m]:
            continue
        if m + 1 < split_idx:
            train_pairs.append(m)
        elif m >= split_idx:
            val_pairs.append(m)
        # m == split_idx-1 straddles the boundary -> dropped (no leakage)

    if not train_pairs:
        raise RuntimeError("no adjacent training pairs; loosen --adjacency-tol or add months.")
    if not val_pairs:
        raise RuntimeError("no adjacent validation pairs; loosen --adjacency-tol or add months.")

    return {
        "train_months": np.array(train_months),
        "val_months": np.array(val_months),
        "train_pairs": np.array(train_pairs),
        "val_pairs": np.array(val_pairs),
        "adjacent": adjacent,
        "split_idx": split_idx,
        "median_step_days": med_gap,
        "adjacency_ref_days": ref,
    }


# Log-transform epsilon: matches src/darwindiff/e2s/prognostic.py._standardize clamp,
# so a checkpoint trained with --log-transform is served identically by the e2s wrapper.
LOG_EPS = 1e-12


def build_log_mask(chan_names, log_transform, log_tracers):
    """Per-channel bool mask: True where the tracer stem (before '_k') is log-transformed.

    Stem-matching mirrors the earth2studio wrapper (prognostic.py:112, ``v.split("_k")[0]``)
    so training and serving agree channel-for-channel. Returns all-False when the flag is
    off, which guarantees the default path is bitwise-identical to the pre-log-transform code.
    """
    mask = np.zeros(len(chan_names), dtype=bool)
    if not log_transform:
        return mask
    stems = {s.strip() for s in str(log_tracers).split(",") if s.strip()}
    for i, name in enumerate(chan_names):
        if str(name).split("_k")[0] in stems:
            mask[i] = True
    return mask


def log_floors(state, train_months, valid_mask, log_mask, floor_pct):
    """Per-channel clip floor for the log transform, from TRAIN positives only (leak-free).

    A fixed ``LOG_EPS`` floor is wrong for these fields. v05 carries genuinely non-positive
    cells (13.3% of Chl1), and clipping them to 1e-12 puts them at log = -27.6, roughly 21
    log-units below a typical Chl of 1.8e-3. Measured on ``darwin_v05_L5_chl.npz``, that
    single artefact inflates the log-space std from 4.81 to 8.26 (1.72x) and compresses the
    real signal from +/-1.0 to +/-0.58 z-units, so ~42% of the model's output range is spent
    representing a spike of clipped zeros.

    Using a low percentile of the positive train values instead keeps non-positive cells at a
    plausible "very low" concentration rather than an outlier 21 decades away. ``floor_pct=0``
    restores the old fixed-epsilon behaviour.
    """
    C = state.shape[1]
    floors = np.full(C, LOG_EPS, dtype=np.float64)
    if log_mask is None or not log_mask.any() or floor_pct <= 0:
        return floors
    tr = state[train_months]
    for c in np.nonzero(log_mask)[0]:
        v = tr[:, c][:, valid_mask]
        v = v[np.isfinite(v) & (v > 0)]
        if v.size:
            floors[c] = max(float(np.percentile(v, floor_pct)), LOG_EPS)
    return floors


def standardize(state, train_months, valid_mask, log_mask=None, floors=None):
    """Per-channel z-score using train-month statistics on valid cells only.

    When ``log_mask`` flags a channel, it is log-transformed (``log(clip(x, floor))``)
    BEFORE the mean/std are computed, so the statistics — and the returned z — live in log
    space (Chl spans ~2.8e6x; linear z-scoring yields negative global skill). De-standardization
    must ``exp()`` those channels back. NaN land cells stay NaN through the clip/log and are
    zeroed by ``nan_to_num`` below exactly as before.

    ``floors`` is the per-channel clip floor from :func:`log_floors`; when omitted every
    logged channel falls back to ``LOG_EPS`` (the historical behaviour).
    """
    C = state.shape[1]
    means = np.zeros(C, dtype=np.float64)
    stds = np.ones(C, dtype=np.float64)
    if log_mask is not None and log_mask.any():
        if floors is None:
            floors = np.full(C, LOG_EPS, dtype=np.float64)
        state = state.copy()
        for c in np.nonzero(log_mask)[0]:
            state[:, c] = np.log(np.clip(state[:, c], a_min=floors[c], a_max=None))
    tr = state[train_months]  # [Mtr, C, H, W]
    for c in range(C):
        v = tr[:, c][:, valid_mask]
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        means[c] = float(v.mean())
        s = float(v.std())
        stds[c] = s if s > 1e-8 else 1.0
    z = (state - means[None, :, None, None]) / stds[None, :, None, None]
    z = np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)  # land -> mean (0 in z-space)
    return z, means, stds


def standardize_forcing(forcing, train_months):
    if forcing is None:
        return None, None, None
    C = forcing.shape[1]
    means = np.zeros(C, dtype=np.float64)
    stds = np.ones(C, dtype=np.float64)
    tr = forcing[train_months]
    for c in range(C):
        v = tr[:, c]
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        means[c] = float(v.mean())
        s = float(v.std())
        stds[c] = s if s > 1e-8 else 1.0
    z = (forcing - means[None, :, None, None]) / stds[None, :, None, None]
    z = np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)
    return z, means, stds


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
def _cast_model(model: nn.Module, dtype: torch.dtype) -> nn.Module:
    """Cast every parameter/buffer, complex-aware (real->dtype, complex->matching).

    The bundled FNO2d stores spectral weights as complex64; ``.double()`` leaves
    those unchanged in this torch build, so a naive fp64 forward raises. This
    upcasts complex params to complex128 too, giving a genuine fp64 forward with
    autograd flowing to all params.
    """
    cdt = torch.complex128 if dtype == torch.float64 else torch.complex64
    for mod in model.modules():
        for name, p in list(mod.named_parameters(recurse=False)):
            if p.is_complex():
                new = nn.Parameter(p.data.to(cdt), requires_grad=p.requires_grad)
            elif p.is_floating_point():
                new = nn.Parameter(p.data.to(dtype), requires_grad=p.requires_grad)
            else:
                continue
            setattr(mod, name, new)
        for bname, buf in list(mod.named_buffers(recurse=False)):
            if buf is None:
                continue
            if buf.is_complex():
                mod._buffers[bname] = buf.to(cdt)
            elif buf.is_floating_point():
                mod._buffers[bname] = buf.to(dtype)
    return model


def build_model(args, chan_names, n_forcing, grid_shape, dt_hours, dtype, device):
    """Build the prognostic FNO emulator.

    Pure prognostic (no forcing): the repo's ``build_emulator`` (swaps in
    physicsnemo's FNO on the cluster). Forcing-augmented (V_in > V_out): a
    custom :class:`FNO2d` operator wrapped in :class:`DarwinEmulator` (the
    scaffold's build_emulator hardwires in==out, so we build the operator
    directly -- documented cluster-phase extension).
    """
    V = len(chan_names)
    ny, nx = grid_shape
    lats = np.linspace(0.0, 1.0, ny)  # placeholder coords; metrics never use them
    lons = np.linspace(0.0, 1.0, nx)
    if n_forcing:
        op = FNO2d(
            in_ch=V + n_forcing,
            out_ch=V,
            modes1=args.modes,
            modes2=args.modes,
            width=args.width,
            n_layers=args.layers,
        )
        model = DarwinEmulator(
            variables=chan_names,
            grid_shape=grid_shape,
            modes=args.modes,
            width=args.width,
            n_layers=args.layers,
            dt_hours=dt_hours,
            lats=lats,
            lons=lons,
            operator=op,
        )
        op_kind = "fallback-FNO2d(forcing-augmented)"
    else:
        model = build_emulator(
            variables=chan_names,
            grid_shape=grid_shape,
            modes=args.modes,
            width=args.width,
            n_layers=args.layers,
            prefer_physicsnemo=not args.no_physicsnemo,
            dt_hours=dt_hours,
            lats=lats,
            lons=lons,
        )
        op_kind = type(model.model).__name__
    model = _cast_model(model, dtype).to(device)
    return model, op_kind


# ---------------------------------------------------------------------------
# Metric helpers (all in z-space; skill ratios are per-channel scale-invariant)
# ---------------------------------------------------------------------------
def _area_weights(lats, width):
    """cos(lat) per-cell area weight ``[H, W]`` for a regular lat/lon grid.

    On a regular lat/lon grid cell area scales as cos(lat); without this weight an
    unweighted cell sum over-counts high-latitude cells (a 89.75N cell has cos~0.004
    the area of an equatorial one). Clipped to >=0 so a pole row never goes negative.
    """
    w = np.clip(np.cos(np.deg2rad(np.asarray(lats, dtype=np.float64))), 0.0, None)
    return w[:, None] * np.ones((1, int(width)), dtype=np.float64)


def _sse_per_channel(pred, target, mask2d, w2d=None):
    """Sum of squared error per channel over pairs & valid cells. [C].

    ``w2d`` is an optional ``[H, W]`` per-cell area weight (e.g. from
    :func:`_area_weights`); when given, cells are area-weighted so the skill ratio
    is not polar-biased at global scale. ``None`` reproduces the unweighted sum.
    """
    d = pred - target  # [N,C,H,W]
    d = d[:, :, mask2d]  # [N,C,Nvalid]
    d2 = d * d
    if w2d is not None:
        d2 = d2 * w2d[mask2d]  # [Nvalid] broadcasts over [N,C,Nvalid]
    return d2.sum(axis=(0, 2))


def masked_mse(pred, target, mask_t):
    d = (pred - target)[..., mask_t]
    return float((d * d).mean().item())


# ---------------------------------------------------------------------------
# Training + evaluation
# ---------------------------------------------------------------------------
def train_and_eval(args, data, splits, z_state, means, stds, z_forcing, model, device, dtype,
                   floors=None):
    valid_mask = data["valid_mask"]
    mask_np = valid_mask
    mask_t = torch.as_tensor(valid_mask, device=device)
    C = z_state.shape[1]

    zt = torch.as_tensor(z_state, dtype=dtype, device=device)  # [M,C,H,W]
    zf = torch.as_tensor(z_forcing, dtype=dtype, device=device) if z_forcing is not None else None

    def make_input(month_idx: np.ndarray) -> torch.Tensor:
        xs = zt[month_idx]
        if zf is not None:
            return torch.cat([xs, zf[month_idx]], dim=1)
        return xs

    val_m = splits["val_pairs"]
    residual = bool(args.residual)
    K = max(1, int(args.rollout_train_k))
    adjacent = splits["adjacent"]           # adjacent[m] links month m -> m+1
    split_idx = splits["split_idx"]

    def predict_next(inp, prev_tracers):
        """One prognostic step. Residual mode adds the learned tendency to x(t) (the tracer
        part), so the model starts at persistence and learns only the correction."""
        out = model(inp)
        return prev_tracers + out if residual else out

    def step_input(x_tracers, month):
        """Model input at a given month: [tracers, forcing] (forcing input-only)."""
        if zf is None:
            return x_tracers
        return torch.cat([x_tracers, zf.index_select(0, torch.as_tensor(month, device=device))], dim=1)

    # K-step training starts: months m where m..m+K are all consecutive-adjacent and inside train.
    train_starts = [m for m in range(split_idx - K)
                    if all(adjacent[m + j] for j in range(K))]
    if not train_starts:                    # no K-length run -> fall back to single-step
        K = 1
        train_starts = [m for m in range(split_idx - 1) if adjacent[m]]
    train_starts = np.asarray(train_starts)
    n_train = len(train_starts)

    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    rng = np.random.default_rng(args.seed)
    denom = float(mask_t.sum().item()) * C

    def masked_mse_t(pred, tgt):
        d = (pred - tgt) * mask_t
        return (d * d).sum() / (pred.shape[0] * denom)

    print(f"  training: residual={residual} rollout_train_k={K} n_starts={n_train}", flush=True)
    model.train()
    hist = []
    for epoch in range(args.epochs):
        perm = rng.permutation(n_train)
        ep_loss = 0.0
        for s in range(0, n_train, args.batch_size):
            idx = train_starts[perm[s : s + args.batch_size]]
            opt.zero_grad()
            x = zt.index_select(0, torch.as_tensor(idx, device=device))   # tracers at t [B,C,H,W]
            loss = 0.0
            for j in range(1, K + 1):
                inp = step_input(x, idx + (j - 1))                        # forcing at the current step
                x = predict_next(inp, x)                                  # autoregressive
                tgt = zt.index_select(0, torch.as_tensor(idx + j, device=device))
                loss = loss + masked_mse_t(x, tgt)
            loss = loss / K
            loss.backward()
            opt.step()
            ep_loss += float(loss.item()) * len(idx)
        ep_loss /= n_train
        hist.append(ep_loss)
        if (epoch + 1) % max(1, args.epochs // 10) == 0 or epoch == 0:
            print(f"  epoch {epoch + 1}/{args.epochs}  train_mse(z)={ep_loss:.5f}", flush=True)

    # --- validation predictions (chunked); 1-step, residual-aware ---
    model.eval()
    val_in = make_input(val_m)
    preds = []
    with torch.no_grad():
        for s in range(0, val_in.shape[0], max(1, args.batch_size)):
            chunk = val_in[s : s + args.batch_size]
            pnext = predict_next(chunk, chunk[:, :C])   # residual adds x(t) (tracer part = first C chans)
            preds.append(pnext.detach().to("cpu").numpy())
    pred_z = np.concatenate(preds, axis=0).astype(np.float64)  # [Nval,C,H,W]

    tgt_z = z_state[val_m + 1]
    persist_z = z_state[val_m]  # persistence: copy current month

    # climatology (per-cell train temporal mean), in z-space
    log_mask = build_log_mask(data["chan_names"], args.log_transform, args.log_tracers)
    if log_mask.any():
        # The transform must be applied BEFORE the temporal mean, exactly as standardize()
        # does. Averaging first and logging after computes log(mean x) rather than
        # mean(log x); for a lognormal field those differ by ~sigma^2/2. Measured on
        # Chl1_k0 the old ordering displaced the baseline by +3.21 natural-log units
        # (median +2.54, max +20.6) = +0.39 sigma, with 29% of cells past 0.5 sigma, which
        # inflated skill_vs_climatology for every logged channel. Fixing the log floor
        # (F2) shrinks the std and would have made this *worse* (~0.67 sigma), so the two
        # belong together.
        _tr = data["state"][splits["train_months"]].copy()
        for _c in np.nonzero(log_mask)[0]:
            _tr[:, _c] = np.log(np.clip(_tr[:, _c], a_min=floors[_c], a_max=None))
        clim_t = np.nanmean(_tr, axis=0)  # [C,H,W]; logged channels averaged IN log space
    else:
        clim_t = np.nanmean(data["state"][splits["train_months"]], axis=0)
    clim_z = (clim_t - means[:, None, None]) / stds[:, None, None]
    clim_z = np.nan_to_num(clim_z, nan=0.0, posinf=0.0, neginf=0.0)
    clim_z_b = np.broadcast_to(clim_z[None], pred_z.shape)

    # Area-weight the metric so the headline skill is not polar-biased on the
    # global --aoi-bounds path (cos(lat) cell weight). Negligible for a narrow
    # AOI (near-uniform lat); load-bearing whole-globe. lats set in main().
    lats = data.get("lats")
    w2d = _area_weights(lats, valid_mask.shape[1]) if lats is not None else None
    sse_model = _sse_per_channel(pred_z, tgt_z, mask_np, w2d)
    sse_persist = _sse_per_channel(persist_z, tgt_z, mask_np, w2d)
    sse_clim = _sse_per_channel(clim_z_b, tgt_z, mask_np, w2d)
    n_elem = pred_z.shape[0] * (float(w2d[mask_np].sum()) if w2d is not None else int(mask_np.sum()))

    eps = 1e-30
    skill_c = 1.0 - sse_model / (sse_persist + eps)
    r2clim_c = 1.0 - sse_model / (sse_clim + eps)
    rmse_z_c = np.sqrt(sse_model / n_elem)
    rmse_phys_c = stds * rmse_z_c  # affine physical RMSE -- valid only for LINEAR channels
    # Logged channels: the std*rmse_z affine identity is INVALID under log, so
    # `stds*rmse_z` would report RMSE in natural-log units. Compute the genuine
    # concentration-space RMSE by exp-destandardizing pred and target.
    _log_mask_m = build_log_mask(data["chan_names"], args.log_transform, args.log_tracers)
    for _c in np.where(_log_mask_m)[0]:
        _pp = np.exp(pred_z[:, _c] * stds[_c] + means[_c])
        _tp = np.exp(tgt_z[:, _c] * stds[_c] + means[_c])
        rmse_phys_c[_c] = float(np.sqrt(np.nanmean(((_pp - _tp)[:, mask_np]) ** 2)))

    overall_skill = float(1.0 - sse_model.sum() / (sse_persist.sum() + eps))
    overall_r2clim = float(1.0 - sse_model.sum() / (sse_clim.sum() + eps))
    persist_beats_clim = float(1.0 - sse_persist.sum() / (sse_clim.sum() + eps))

    per_tracer = {}
    for c, name in enumerate(data["chan_names"]):
        per_tracer[name] = {
            "skill_vs_persistence": float(skill_c[c]),
            "anomaly_r2_vs_climatology": float(r2clim_c[c]),
            "rmse_z": float(rmse_z_c[c]),
            "rmse_physical": float(rmse_phys_c[c]),  # concentration-space (exp'd for log channels)
            "physical_std": float(stds[c]),  # NOTE: log-space std when log_space=True
            "log_space": bool(_log_mask_m[c]),  # rmse_z / physical_std are in log space for this channel
        }

    metrics = {
        "overall_skill_vs_persistence": overall_skill,
        "overall_anomaly_r2_vs_climatology": overall_r2clim,
        "persistence_skill_vs_climatology": persist_beats_clim,
        "per_tracer": per_tracer,
        "final_train_mse_z": hist[-1] if hist else None,
        "n_metric_cells": int(mask_np.sum()),
    }
    return metrics, zt, zf, mask_t, pred_z


# ---------------------------------------------------------------------------
# Multi-step autoregressive rollout stability + physical sanity
# ---------------------------------------------------------------------------
def rollout_check(args, data, splits, zt, zf, means, stds, model, mask_t, device, dtype,
                  floors=None):
    adjacent = splits["adjacent"]
    split_idx = splits["split_idx"]
    M = zt.shape[0]

    # Longest run of consecutive adjacent months entirely inside the val range.
    runs, cur = [], [split_idx]
    for m in range(split_idx, M - 1):
        if adjacent[m]:
            cur.append(m + 1)
        else:
            runs.append(cur)
            cur = [m + 1]
    runs.append(cur)
    best = max(runs, key=len)
    if len(best) < 2:
        return {
            "ran": False,
            "reason": "no contiguous adjacent val run of length >=2",
        }

    k_max = min(int(args.rollout_steps), len(best) - 1)
    means_t = torch.as_tensor(means, dtype=dtype, device=device).view(1, -1, 1, 1)
    stds_t = torch.as_tensor(stds, dtype=dtype, device=device).view(1, -1, 1, 1)
    C = zt.shape[1]
    # Channels z-scored in log space must be exp'd back to true physical for the physical
    # diagnostics below (positivity / mass-drift). Empty list when --log-transform is off,
    # keeping this path bitwise-identical to the pre-log-transform code.
    log_mask = build_log_mask(data["chan_names"], args.log_transform, args.log_tracers)
    log_idx = list(np.nonzero(log_mask)[0])
    _floors_t = floors if floors is not None else np.full(zt.shape[1], LOG_EPS, dtype=np.float64)

    model.eval()
    step_mse_model, step_mse_persist = [], []
    x = zt[best[0] : best[0] + 1].clone()  # [1,C,H,W]
    x0 = x.clone()  # persistence holds the IC fixed
    final_state = None
    with torch.no_grad():
        for j in range(1, k_max + 1):
            if zf is not None:
                inp = torch.cat([x, zf[best[j - 1] : best[j - 1] + 1]], dim=1)
            else:
                inp = x
            out = model(inp)
            x = (x + out) if args.residual else out   # residual-aware autoregressive step
            if getattr(args, "rollout_positivity", False):
                # Project onto the physical feasible set: concentrations are >= 0.
                # Enforced BETWEEN steps so negatives cannot compound down the rollout.
                x_phys = x * stds_t + means_t
                if log_idx:
                    # logged channels are in log space here; exp to TRUE physical so the
                    # >=0 clamp / mean-rescale act on concentrations, not on log values
                    # (log(Chl) is legitimately negative). Re-logged before z-scoring back.
                    x_phys[:, log_idx] = torch.exp(x_phys[:, log_idx])
                if getattr(args, "rollout_mass_conserve", False):
                    # Mass-conserving positivity: clamp to >=0, then rescale each tracer to
                    # its pre-clamp domain mean, so enforcing positivity does not inject mass
                    # (resolves the positivity-vs-mean-conservation tension).
                    pre = x_phys[..., mask_t].mean(dim=-1).view(1, -1, 1, 1)
                    x_phys = x_phys.clamp(min=0.0)
                    post = x_phys[..., mask_t].mean(dim=-1).view(1, -1, 1, 1)
                    scale = (pre / post.clamp(min=1e-30)).clamp(min=0.0, max=10.0)
                    x_phys = x_phys * scale
                else:
                    x_phys = x_phys.clamp(min=0.0)
                if log_idx:
                    # re-log with the SAME per-channel floor used at standardization,
                    # otherwise the rollout re-enters z-space on a different transform
                    for _li in log_idx:
                        x_phys[:, _li] = torch.log(
                            torch.clamp(x_phys[:, _li], min=float(_floors_t[_li]))
                        )
                x = (x_phys - means_t) / stds_t
            tj = zt[best[j] : best[j] + 1]
            step_mse_model.append(masked_mse(x, tj, mask_t))
            step_mse_persist.append(masked_mse(x0, tj, mask_t))
            final_state = x
        # physical de-standardization of the final rollout state
        final_phys = (final_state * stds_t + means_t).to("cpu").numpy()[0]  # [C,H,W]
    if log_mask.any():
        final_phys[log_mask] = np.exp(final_phys[log_mask])  # log-space -> true physical
    true_final_phys = data["state"][best[k_max]]  # [C,H,W] physical
    vm = data["valid_mask"]

    # positivity: all these tracers are physically >= 0
    positivity = {}
    mass_drift = {}
    for c, name in enumerate(data["chan_names"]):
        fp = final_phys[c][vm]
        tp = true_final_phys[c][vm]
        tp = tp[np.isfinite(tp)]
        positivity[name] = {
            "min_value": float(np.nanmin(fp)) if fp.size else None,
            "frac_negative": float(np.mean(fp < 0.0)) if fp.size else None,
        }
        pred_mean = float(np.nanmean(fp)) if fp.size else float("nan")
        true_mean = float(np.mean(tp)) if tp.size else float("nan")
        rel = (pred_mean - true_mean) / (abs(true_mean) + 1e-30)
        mass_drift[name] = {
            "pred_domain_mean": pred_mean,
            "true_domain_mean": true_mean,
            "relative_drift": float(rel),
        }

    finite = all(math.isfinite(v) for v in step_mse_model)
    # z-space: a blown-up rollout has MSE >> the O(1) variance scale.
    bounded = finite and max(step_mse_model) < 25.0
    beats_persist_final = finite and step_mse_model[-1] < step_mse_persist[-1]
    max_abs_neg_frac = max(
        (p["frac_negative"] for p in positivity.values() if p["frac_negative"] is not None),
        default=0.0,
    )
    max_abs_drift = max((abs(m["relative_drift"]) for m in mass_drift.values()), default=0.0)

    return {
        "ran": True,
        "run_length_months": len(best),
        "n_steps": k_max,
        "step_mse_z_model": [float(v) for v in step_mse_model],
        "step_mse_z_persistence": [float(v) for v in step_mse_persist],
        "finite": bool(finite),
        "bounded": bool(bounded),
        "stable": bool(bounded),
        "beats_persistence_at_final_step": bool(beats_persist_final),
        "positivity": positivity,
        "mass_drift": mass_drift,
        "max_frac_negative": float(max_abs_neg_frac),
        "max_abs_relative_mass_drift": float(max_abs_drift),
        "positivity_enforced": bool(getattr(args, "rollout_positivity", False)),
        "mass_conserve_enforced": bool(getattr(args, "rollout_mass_conserve", False)),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def save_checkpoint(path, model, config, means, stds):
    """Persist the trained model to `path` for reuse / cross-cluster transfer.

    Writes the weights, the per-channel standardization stats (means/stds — needed to
    map model z-space back to physical units at inference), and the full `config`
    (modes/width/layers/grid/channels/operator/residual) required to rebuild the
    architecture. Prefers safetensors (Hub-native, no pickle) when the path ends in
    .safetensors and the package is importable; else falls back to a torch .pt dict.
    State is moved to CPU so the checkpoint loads on any GPU (map_location).
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    sd = {k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}
    means_t = torch.as_tensor(np.asarray(means), dtype=torch.float32)
    stds_t = torch.as_tensor(np.asarray(stds), dtype=torch.float32)

    use_safetensors = p.suffix == ".safetensors"
    if use_safetensors:
        try:
            from safetensors.torch import save_file
        except Exception:
            print("  [save-model] safetensors not importable; falling back to torch .pt", flush=True)
            use_safetensors = False

    if use_safetensors:
        # safetensors has no complex dtype; the fallback FNO2d stores spectral
        # weights as complex64. Store those as a real view (last dim = 2) and
        # record their keys so a loader can rebuild them via view_as_complex.
        tensors, complex_keys = {}, []
        for k, v in sd.items():
            if v.is_complex():
                tensors[f"model.{k}"] = torch.view_as_real(v).contiguous()
                complex_keys.append(k)
            else:
                tensors[f"model.{k}"] = v
        tensors["stats.means"] = means_t
        tensors["stats.stds"] = stds_t
        save_file(
            tensors,
            str(p),
            metadata={"config": json.dumps(config), "complex_keys": json.dumps(complex_keys)},
        )
    else:
        torch.save(
            {"state_dict": sd, "means": means_t, "stds": stds_t, "config": config}, str(p)
        )
    return p


def main(argv=None) -> int:
    args = parse_args(argv)

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    use_cuda = torch.cuda.is_available() and not args.cpu
    device = torch.device("cuda" if use_cuda else "cpu")
    dtype = torch.float32 if use_cuda else torch.float64  # CUDA fp32, CPU fp64

    if args.aoi_bounds:
        try:
            _b = [float(x) for x in args.aoi_bounds.split(",")]
            if len(_b) != 4:
                raise ValueError
        except ValueError:
            raise SystemExit(
                f"--aoi-bounds must be 'lat_min,lat_max,lon_min,lon_max'; got {args.aoi_bounds!r}"
            )
        aoi = AOI(args.aoi, _b[0], _b[1], _b[2], _b[3])  # AOI validates ranges
    elif args.aoi not in AOI_BY_KEY:
        raise SystemExit(f"unknown --aoi {args.aoi!r}; choose from {sorted(AOI_BY_KEY)}")
    else:
        aoi = AOI_BY_KEY[args.aoi]
    tracers = [t.strip() for t in args.tracers.split(",") if t.strip()]
    forcings = [f.strip() for f in args.forcing.split(",") if f.strip()]
    for f in forcings:
        if f not in KNOWN_FORCING:
            print(f"  [warn] forcing {f!r} not in known 2-D set {sorted(KNOWN_FORCING)}", flush=True)

    print("=" * 72, flush=True)
    print("Track-2 emulator PoC  --  can an FNO beat persistence on v05 next-month?", flush=True)
    print("=" * 72, flush=True)
    print(
        f"aoi={args.aoi} tracers={tracers} forcing={forcings or None} levels={args.levels} "
        f"device={device} dtype={str(dtype).replace('torch.', '')}",
        flush=True,
    )

    if args.load_cube:
        print(f"[1/5] loading pre-extracted AOI cube from {args.load_cube} ...", flush=True)
        z = np.load(args.load_cube, allow_pickle=True)
        # load the cube's forcing ONLY if this run requests forcing (else run pure prognostic)
        cube_forc_names = [str(x) for x in z["forc_names"]]
        _use_forc = bool(forcings) and "forcing" in z.files and z["forcing"].ndim == 4
        if _use_forc:
            # Select ONLY the requested forcing channels from the cube (a cube may bake in
            # more forcings than a given run uses, e.g. a single-variable ablation). Match by
            # name so the model's forcing-channel count equals len(forcings), not the cube's.
            missing = [f for f in forcings if f not in cube_forc_names]
            if missing:
                raise SystemExit(
                    f"requested forcing {missing} not in cube forc_names {cube_forc_names}"
                )
            sel = [cube_forc_names.index(f) for f in forcings]
            forc_arr = np.asarray(z["forcing"])[:, sel]
            forc_names_out = list(forcings)
        else:
            # Requested forcing but the cube baked none -> the model would expect
            # forcing channels it can never be fed. Fail loudly instead.
            if forcings:
                raise SystemExit(
                    f"--forcing {forcings} requested but cube {args.load_cube} has no forcing "
                    f"channels (forc_names={cube_forc_names}); re-dump the cube with --forcing "
                    f"or drop --forcing."
                )
            forc_arr = None
            forc_names_out = []
        data = {
            "state": z["state"], "valid_mask": z["valid_mask"].astype(bool),
            "forcing": forc_arr,
            "iters": [int(x) for x in z["iters"]], "times_days": z["times_days"],
            "chan_names": [str(x) for x in z["chan_names"]],
            "forc_names": forc_names_out,
            "grid_shape": tuple(int(x) for x in z["grid_shape"]), "n_z": int(z["n_z"]),
        }
        # Reconcile the recorded tracer list with the cube's real channels so the
        # summary config.tracers matches config.channel_names (mirrors the forcing
        # reconciliation above). Strip any depth-level "_k<n>" suffix.
        cube_tracers = list(dict.fromkeys(c.split("_k")[0] for c in data["chan_names"]))
        if tracers and set(tracers) != set(cube_tracers):
            print(
                f"  [warn] --tracers {tracers} != cube channels {cube_tracers}; using the cube's.",
                flush=True,
            )
        tracers = cube_tracers
    else:
        print("[1/5] loading native LLC270 monthly fields -> AOI 1-deg grid ...", flush=True)
        data = load_dataset(args, aoi, tracers, forcings)
    if args.dump_cube:
        f = data["forcing"]
        np.savez_compressed(
            args.dump_cube, state=data["state"], valid_mask=data["valid_mask"],
            forcing=(f if f is not None else np.zeros((0,))), times_days=data["times_days"],
            iters=np.array(data["iters"]), chan_names=np.array(data["chan_names"]),
            forc_names=np.array(data["forc_names"]), grid_shape=np.array(data["grid_shape"]),
            n_z=data["n_z"])
        print(f"[dump-cube] wrote portable AOI cube -> {args.dump_cube} "
              f"(state {data['state'].shape}); ship this + run with --load-cube.", flush=True)
        return 0
    grid_shape = data["grid_shape"]
    # AOI cell-center latitudes (regular grid) -> cos(lat) area weight for the
    # metric, so global-scale skill is area-correct rather than polar-biased.
    data["lats"] = np.linspace(aoi.lat_min, aoi.lat_max, int(grid_shape[0]), dtype=float)
    M = len(data["iters"])
    print(
        f"      loaded M={M} shared months, grid={grid_shape}, "
        f"C={len(data['chan_names'])} state chans, "
        f"F={len(data['forc_names'])} forcing chans, "
        f"valid ocean cells={int(data['valid_mask'].sum())}/{grid_shape[0] * grid_shape[1]}",
        flush=True,
    )

    if args.time_encoding:
        # Seasonal phase as 2 input-only channels: the model otherwise cannot tell where in the
        # annual cycle it is, yet monthly next-state is largely seasonal. Treated like forcing.
        doy = (np.asarray(data["times_days"], dtype=float) % 365.25) / 365.25  # [M] year fraction
        tenc = np.stack([np.sin(2 * np.pi * doy), np.cos(2 * np.pi * doy)], axis=1)  # [M,2]
        H, W = grid_shape
        tf = np.broadcast_to(tenc[:, :, None, None], (M, 2, H, W)).astype(np.float64)
        data["forcing"] = tf if data["forcing"] is None else np.concatenate([data["forcing"], tf], axis=1)
        data["forc_names"] = list(data["forc_names"]) + ["sin_doy", "cos_doy"]
        print("      [time-encoding] +2 seasonal input channels (sin/cos day-of-year)", flush=True)

    print("[2/5] temporal split + leak-free standardization + pairing ...", flush=True)
    splits = build_splits(data, args.val_frac, args.adjacency_tol, args.expected_step_days)
    log_mask = build_log_mask(data["chan_names"], args.log_transform, args.log_tracers)
    if log_mask.any():
        logged = [data["chan_names"][i] for i in np.nonzero(log_mask)[0]]
        print(f"      [log-transform] log-space z-scoring for {len(logged)} channels: {logged}", flush=True)
    floors = log_floors(
        data["state"], splits["train_months"], data["valid_mask"], log_mask, args.log_floor_pct
    )
    if log_mask.any():
        _fl = {data["chan_names"][i]: float(floors[i]) for i in np.nonzero(log_mask)[0]}
        print(f"      [log-transform] per-channel clip floors (p{args.log_floor_pct}): {_fl}", flush=True)
    z_state, means, stds = standardize(
        data["state"], splits["train_months"], data["valid_mask"], log_mask, floors
    )
    z_forcing, f_means, f_stds = standardize_forcing(data["forcing"], splits["train_months"])
    print(
        f"      train months={len(splits['train_months'])} val months={len(splits['val_months'])} "
        f"| train pairs={len(splits['train_pairs'])} val pairs={len(splits['val_pairs'])} "
        f"| median step={splits['median_step_days']:.1f} d",
        flush=True,
    )

    dt_hours = max(1.0, splits["median_step_days"] * 24.0)
    print("[3/5] building FNO emulator ...", flush=True)
    n_forcing = data["forcing"].shape[1] if data["forcing"] is not None else 0
    model, op_kind = build_model(
        args, data["chan_names"], n_forcing, grid_shape, dt_hours, dtype, device
    )
    n_params = sum(p.numel() for p in model.parameters())
    print(f"      operator={op_kind}  params={n_params:,}", flush=True)

    print(f"[4/5] training {args.epochs} epochs (masked next-state MSE) ...", flush=True)
    metrics, zt, zf, mask_t, pred_z = train_and_eval(
        args, data, splits, z_state, means, stds, z_forcing, model, device, dtype, floors
    )

    print("[5/5] multi-step autoregressive rollout stability + sanity ...", flush=True)
    rollout = rollout_check(
        args, data, splits, zt, zf, means, stds, model, mask_t, device, dtype, floors
    )

    # --- optional: dump held-out spatial fields (physical) for visualization ---
    if args.dump_fields:
        val_m = splits["val_pairs"]
        pred_phys = pred_z * stds[None, :, None, None] + means[None, :, None, None]  # [Nval,C,H,W]
        if log_mask.any():
            # logged channels were z-scored in log space -> exp back to physical (do NOT
            # touch true/persist below: those are raw physical, never z-scored).
            pred_phys[:, log_mask] = np.exp(pred_phys[:, log_mask])
        true_phys = data["state"][val_m + 1]                                          # physical, NaN=land
        persist_phys = data["state"][val_m]
        vm = data["valid_mask"]
        # real AOI cell centers at the cube's actual resolution: the binning places
        # centers at lat_min..lat_max (H of them) / lon_min..lon_max (W of them), so
        # linspace over the grid shape is correct for 1deg AND finer (0.5/0.25deg) grids.
        lats = np.linspace(aoi.lat_min, aoi.lat_max, vm.shape[0], dtype=float)          # [H]
        lons = np.linspace(aoi.lon_min, aoi.lon_max, vm.shape[1], dtype=float)          # [W]
        Path(args.dump_fields).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            args.dump_fields,
            pred=pred_phys.astype(np.float32), true=true_phys.astype(np.float32),
            persistence=persist_phys.astype(np.float32), valid_mask=vm,
            lats=lats, lons=lons, chan_names=np.array(data["chan_names"]),
            val_iters=np.array([data["iters"][m + 1] for m in val_m]),
            aoi=args.aoi, residual=bool(args.residual), rollout_train_k=int(args.rollout_train_k),
        )
        print(f"[dump] wrote held-out fields -> {args.dump_fields} "
              f"({pred_phys.shape[0]} months x {pred_phys.shape[1]} chans, grid {vm.shape})", flush=True)

    # --- verdict ---
    skill = metrics["overall_skill_vs_persistence"]
    beats = skill > 0.0
    stable = rollout.get("stable", False) if rollout.get("ran") else None
    if not math.isfinite(skill):
        verdict = "ERROR"
    elif skill > 0.02 and (stable is None or stable):
        verdict = "MAKE"
    elif beats:
        verdict = "MARGINAL"
    else:
        verdict = "BREAK"

    summary = {
        "verdict": verdict,
        "question": "Can an FNO beat persistence on ECCO-Darwin v05 next-month state?",
        "headline_overall_skill_vs_persistence": skill,
        "beats_persistence": bool(beats),
        "config": {
            "aoi": args.aoi,
            "aoi_bounds": {
                "lat_min": aoi.lat_min,
                "lat_max": aoi.lat_max,
                "lon_min": aoi.lon_min,
                "lon_max": aoi.lon_max,
            },
            "tracers": tracers,
            "forcing": forcings,
            "levels": args.levels,
            "grid_shape": list(grid_shape),
            "channel_names": data["chan_names"],
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "val_frac": args.val_frac,
            "modes": args.modes,
            "width": args.width,
            "layers": args.layers,
            "operator": op_kind,
            "n_params": int(n_params),
            "residual": bool(args.residual),
            "rollout_train_k": int(args.rollout_train_k),
            "seed": args.seed,
            "device": str(device),
            "dtype": str(dtype).replace("torch.", ""),
            "adjacency_tol": args.adjacency_tol,
            "median_step_days": splits["median_step_days"],
            "dt_hours": dt_hours,
            # Log-transform provenance -> the e2s wrapper (prognostic.py) reconstructs the
            # served transform from these: log_transform flag, the resolved stem list
            # (log_vars, empty when off), and the clamp eps. Stem-matching on the channel
            # name before '_k' is identical on both sides.
            "log_transform": bool(args.log_transform),
            "log_tracers": (
                [s.strip() for s in str(args.log_tracers).split(",") if s.strip()]
                if args.log_transform
                else []
            ),
            "log_eps": LOG_EPS,
            "log_floor_pct": float(args.log_floor_pct),
            "log_floors": (
                {data["chan_names"][i]: float(floors[i]) for i in np.nonzero(log_mask)[0]}
                if args.log_transform
                else {}
            ),
        },
        "data": {
            "n_shared_months": M,
            "n_train_months": int(len(splits["train_months"])),
            "n_val_months": int(len(splits["val_months"])),
            "n_train_pairs": int(len(splits["train_pairs"])),
            "n_val_pairs": int(len(splits["val_pairs"])),
            "n_valid_ocean_cells": int(data["valid_mask"].sum()),
            "first_iter": data["iters"][0],
            "last_iter": data["iters"][-1],
        },
        "metrics": metrics,
        "rollout": rollout,
        "honesty_notes": [
            "Skill = 1 - MSE(model)/MSE(persistence); >0 means it beats copying x(t).",
            "Persistence is a strong baseline on an autocorrelated ocean; raw R^2 is not reported as headline.",
            "Standardization statistics use TRAIN months only; pairs never cross the split and never span a missing-month gap.",
            "Only the fixed valid-ocean mask (finite across all months/channels) is scored; land is fill-zero input only.",
            "Single AOI, single seed: treat as a go/no-go signal, not a converged benchmark. Repeat over seeds/AOIs before any claim.",
            (
                "Residual mode: the model predicts the TENDENCY added to x(t) (it starts AT persistence and "
                "learns only the correction), so positive skill reflects a learned month-to-month change that "
                "improves on copying."
                if bool(args.residual)
                else "Model predicts the FULL next state directly (not a persistence residual), so positive "
                "skill reflects learned month-to-month change."
            ),
        ],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "argv": sys.argv,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))

    if args.save_model:
        ckpt = save_checkpoint(args.save_model, model, summary["config"], means, stds)
        print(
            f"[save-model] wrote checkpoint -> {ckpt} "
            f"({n_params:,} params + standardization stats + rebuild config)",
            flush=True,
        )

    # --- console report ---
    print("\n" + "=" * 72, flush=True)
    print(f"VERDICT: {verdict}", flush=True)
    print(
        f"  overall skill vs persistence : {skill:+.4f}  "
        f"({'BEATS' if beats else 'does NOT beat'} persistence)",
        flush=True,
    )
    print(
        f"  overall anomaly-R2 vs clim   : {metrics['overall_anomaly_r2_vs_climatology']:+.4f}",
        flush=True,
    )
    print(
        f"  persistence skill vs clim    : {metrics['persistence_skill_vs_climatology']:+.4f} "
        f"(how strong the persistence baseline is)",
        flush=True,
    )
    print("  per-tracer skill vs persistence / anomaly-R2 vs climatology:", flush=True)
    for name, d in metrics["per_tracer"].items():
        print(
            f"    {name:<10} skill={d['skill_vs_persistence']:+.4f}  "
            f"anomR2={d['anomaly_r2_vs_climatology']:+.4f}  "
            f"rmse_phys={d['rmse_physical']:.4g}",
            flush=True,
        )
    if rollout.get("ran"):
        print(
            f"  rollout: {rollout['n_steps']} steps  stable={rollout['stable']}  "
            f"beats_persist@final={rollout['beats_persistence_at_final_step']}  "
            f"max|neg_frac|={rollout['max_frac_negative']:.3f}  "
            f"max|mass_drift|={rollout['max_abs_relative_mass_drift']:.3f}",
            flush=True,
        )
        print(f"    step MSE(z) model      : {[round(v, 4) for v in rollout['step_mse_z_model']]}", flush=True)
        print(f"    step MSE(z) persistence: {[round(v, 4) for v in rollout['step_mse_z_persistence']]}", flush=True)
    else:
        print(f"  rollout: skipped ({rollout.get('reason')})", flush=True)
    print(f"\nJSON summary -> {out_path}", flush=True)
    print("=" * 72, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
