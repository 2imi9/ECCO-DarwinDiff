"""EccoDarwinV05 -- an Earth2Studio ``DataSource`` that feeds ECCO-Darwin v05
monthly initial conditions from a dumped emulator cube.

Earth2Studio's ``DataSource`` is a single-method protocol:
``__call__(time, variable) -> xr.DataArray`` with dims ``[time, variable, lat, lon]``.
E2S ``fetch_data`` only regrids lat/lon and does NOT interpolate depth, and its
``map_coords`` refuses curvilinear (LLC) grids -- so ALL depth remapping and
LLC->regular regridding is done upstream (in ``emulator_poc.py`` when the cube is
dumped). This source therefore just serves the already-regular, already-on-target-
levels cube, indexed by (month, depth-tagged variable).

Depth is encoded in the variable name (``DIC_k0``, ``FeT_k3``, ...), matching the
cube's ``chan_names`` and the ``DarwinBGCPrognostic`` wrapper.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np

try:  # xarray is a light dep but guard anyway for minimal envs
    import xarray as xr
except Exception:  # pragma: no cover
    xr = None

try:  # earth2studio helper; trivial fallback keeps the protocol working off-cluster
    from earth2studio.data.utils import prep_data_inputs
except Exception:
    def prep_data_inputs(time, variable):
        time = list(time) if isinstance(time, (list, tuple, np.ndarray)) else [time]
        variable = list(variable) if isinstance(variable, (list, tuple, np.ndarray)) else [variable]
        return time, variable


class EccoDarwinV05:
    """Serve v05 initial conditions from a dumped ``--dump-cube`` npz.

    Parameters
    ----------
    cube_path : str
        Path to the npz written by ``emulator_poc.py --dump-cube`` (keys: ``state``
        ``[M,C,H,W]``, ``chan_names`` ``[C]``, ``lats`` ``[H]``, ``lons`` ``[W]``;
        optionally ``iters`` / ``times_days`` ``[M]``).
    times : sequence[np.datetime64], optional
        Calendar timestamp for each of the M cube months. If omitted, months are
        addressed positionally (index 0 == first cube month) and any queried
        ``time`` is mapped to the nearest available month.
    """

    def __init__(self, cube_path: str, times=None) -> None:
        d = np.load(cube_path, allow_pickle=True)
        self.state = np.asarray(d["state"])  # [M, C, H, W]
        self.chan_names = [str(c) for c in d["chan_names"]]
        # Fail loudly rather than fabricating coordinates. Falling back to 0..H-1 /
        # 0..W-1 labels an ocean grid with array indices, and Earth2Studio then
        # regrids and verifies against those as if they were degrees -- silently
        # wrong, and wrong in a way that looks like a plausible map. Cubes written by
        # `emulator_poc.py --dump-cube` do not currently carry lats/lons, so this
        # raises for them by design; pass the AOI coordinates explicitly instead.
        if "lats" not in d or "lons" not in d:
            raise KeyError(
                f"cube {cube_path!r} has no 'lats'/'lons'; refusing to fabricate index "
                f"coordinates for a geospatial grid (shape {self.state.shape[2]}x"
                f"{self.state.shape[3]}). Re-dump the cube with real AOI coordinates, or "
                f"construct EccoDarwinV05 against a cube that carries them."
            )
        self.lat = np.asarray(d["lats"], dtype=float)
        self.lon = np.asarray(d["lons"], dtype=float)
        self._chan_idx = {name: i for i, name in enumerate(self.chan_names)}
        if times is not None:
            self.times = np.asarray(times, dtype="datetime64[ns]")
        elif "times_days" in d:
            base = np.datetime64("1992-01-01", "ns")
            self.times = base + (np.asarray(d["times_days"], dtype="float64") * np.timedelta64(1, "D"))
        else:
            self.times = None  # positional addressing

    # ---- DataSource protocol ----------------------------------------------------
    def __call__(self, time, variable):
        if xr is None:
            raise RuntimeError("xarray is required to serve DataArrays")
        time, variable = prep_data_inputs(time, variable)
        arrays, stamps = [], []
        for t in time:
            # Resolve the label FROM the cube, never by casting the request. Casting a
            # positional index turned 0 and 1 into 1970-01-01 timestamps one nanosecond
            # apart, so downstream alignment silently associated the states with dates
            # ~35 years wrong.
            if isinstance(t, (int, np.integer)):
                if self.times is None:
                    raise ValueError(
                        f"positional index {int(t)} cannot be given a timestamp: this cube "
                        f"has no calendar (no 'times_days' and no times= argument). Pass "
                        f"times= when constructing EccoDarwinV05 if you need datetime "
                        f"coordinates."
                    )
                stamps.append(np.datetime64(self.times[int(t)], "ns"))
            else:
                stamps.append(np.datetime64(t, "ns"))
            per_var = [self._read_field(t, v) for v in variable]  # each [H, W]
            arrays.append(np.stack(per_var, axis=0))  # [V, H, W]
        data = np.stack(arrays, axis=0)  # [T, V, H, W]
        return xr.DataArray(
            data=data,
            dims=["time", "variable", "lat", "lon"],
            coords=dict(
                time=np.array(stamps, dtype="datetime64[ns]"),
                variable=np.array(variable),
                lat=self.lat,
                lon=self.lon,
            ),
        )

    # ---- internals --------------------------------------------------------------
    def _month_index(self, t) -> int:
        if self.times is None:
            # Returning 0 here served EVERY datetime request from the first cube month
            # while labelling the output with the requested timestamp -- so a 40-month
            # rollout would silently reuse month 0 forty times and still look correct.
            # A positional cube can only be addressed positionally.
            raise ValueError(
                f"cube has no calendar (no 'times_days' and no times= argument), so the "
                f"datetime {t!r} cannot be resolved to a month. Pass times= when "
                f"constructing EccoDarwinV05, or address months positionally with an int."
            )
        t = np.datetime64(t, "ns")
        return int(np.argmin(np.abs(self.times - t)))

    def _read_field(self, t, e2s_var: str) -> np.ndarray:
        if e2s_var not in self._chan_idx:
            raise KeyError(f"variable {e2s_var!r} not in cube channels {self.chan_names[:6]}...")
        m = self._month_index(t) if not isinstance(t, (int, np.integer)) else int(t)
        c = self._chan_idx[e2s_var]
        return np.asarray(self.state[m, c])  # [H, W]

    @property
    def variables(self):
        return list(self.chan_names)
