"""Tests for darwindiff.velocity_loader (DB-2: v05 prescribed velocity).

Component logic (partial top-z read, time-mean, missing-value masking, m/s->m/day, the
divergence-free transport-velocity helper) is tested hermetically with synthetic native
files; the full AOI path is validated by an opt-in real test against the on-disk v05
monthly velocities (``DARWINDIFF_TEST_LLC270=1``), which recovers the westward South
Equatorial Current.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import torch

from darwindiff.ecco_darwin_loader import AOI, EQUATORIAL_PACIFIC_AOI
from darwindiff.transport import grid_tendency
from darwindiff.velocity_loader import (
    LLC270_NFACE,
    M_PER_S_TO_M_PER_DAY,
    MITGCM_MISSING,
    depth_mean,
    divfree_barotropic_velocity,
    read_velocity_native_topz,
    velocity_aoi_grid,
)

_MON = r"D:\ecco_darwin_v5\output\monthly"
_GRID = r"D:\ecco_darwin_v5\grid"
_RUN_REAL = os.environ.get("DARWINDIFF_TEST_LLC270") == "1"


def _write_native(dir_: Path, var: str, it: int, arr: np.ndarray) -> None:
    """Write a synthetic native velocity .data (compact, big-endian f4, k outermost)."""
    (dir_ / var).mkdir(parents=True, exist_ok=True)
    arr.astype(">f4").tofile(dir_ / var / f"{var}.{it:010d}.data")


class TestReadNativeTopZ:
    def test_timemean_over_iters(self, tmp_path: Path) -> None:
        nx, nz = 4, 2
        # two iters filled with 2.0 and 4.0 -> mean 3.0
        _write_native(tmp_path, "uVel_C", 1, np.full((nz, LLC270_NFACE, nx, nx), 2.0))
        _write_native(tmp_path, "uVel_C", 2, np.full((nz, LLC270_NFACE, nx, nx), 4.0))
        out = read_velocity_native_topz(tmp_path, "uVel_C", n_z=nz, iters=[1, 2], nx=nx)
        assert out.shape == (nz, LLC270_NFACE, nx, nx)
        np.testing.assert_allclose(out, 3.0)

    def test_partial_read_takes_top_levels(self, tmp_path: Path) -> None:
        nx = 4
        # file has 5 levels, level k filled with value k; read top 2 -> levels 0,1
        arr = np.stack([np.full((LLC270_NFACE, nx, nx), float(k)) for k in range(5)])
        _write_native(tmp_path, "uVel_C", 1, arr)
        out = read_velocity_native_topz(tmp_path, "uVel_C", n_z=2, iters=[1], nx=nx)
        np.testing.assert_allclose(out[0], 0.0)
        np.testing.assert_allclose(out[1], 1.0)

    def test_missing_value_masked(self, tmp_path: Path) -> None:
        nx, nz = 3, 1
        a1 = np.full((nz, LLC270_NFACE, nx, nx), 6.0)
        a2 = np.full((nz, LLC270_NFACE, nx, nx), 6.0)
        a2[0, 0, 0, 0] = MITGCM_MISSING  # land/fill in one cell of iter 2
        _write_native(tmp_path, "uVel_C", 1, a1)
        _write_native(tmp_path, "uVel_C", 2, a2)
        out = read_velocity_native_topz(tmp_path, "uVel_C", n_z=nz, iters=[1, 2], nx=nx)
        # the missing cell averages only the valid iter -> 6.0 (not (6-999)/2)
        assert out[0, 0, 0, 0] == pytest.approx(6.0)

    def test_unknown_var_raises(self, tmp_path: Path) -> None:
        with pytest.raises(KeyError, match="velocity var"):
            read_velocity_native_topz(tmp_path, "TEMP", n_z=1, iters=[1])


class TestDivFree:
    def test_depth_mean(self) -> None:
        f = np.arange(2 * 3 * 4, dtype=float).reshape(2, 3, 4)  # [Y,X,Z]
        np.testing.assert_allclose(depth_mean(f), f.mean(axis=-1))

    def test_barotropic_velocity_is_divergence_free(self) -> None:
        # A synthetic barotropic (u, v) -> divfree (u, v, w) must give a uniform tracer
        # ~zero tendency under pure transport (the A1 property the loader must preserve).
        ny, nx, n_z = 5, 6, 4
        rng = np.random.default_rng(0)
        u2d = rng.standard_normal((ny, nx)) * 100.0   # m/day
        v2d = rng.standard_normal((ny, nx)) * 100.0
        dx = dy = 1.11e5
        u, v, w = divfree_barotropic_velocity(u2d, v2d, dx, dy, dz=10.0, n_z=n_z)
        assert w.shape == (ny, nx, n_z + 1)
        assert torch.all(w[..., 0] == 0)              # rigid lid
        state = torch.ones(ny, nx, n_z, 5, dtype=torch.float64) * 0.3
        params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425], dtype=torch.float64)
        d = grid_tendency(state, params, u=u, v=v, w=w, dx=dx, dy=dy, kz=0.0, dz=10.0,
                          kh=0.0, bgc=False, include_vdiff=False)
        assert float(d.abs().max()) < 1e-10           # divergence-free to machine precision


class TestSignAndUnits:
    """CI-level guard (no real data) that velocity_aoi_grid preserves the EASTWARD sign
    (no negation) AND applies the m/s->m/day conversion -- the two things the review found
    were only checked in the opt-in real test, so a u-flip or a x86400 error shipped green."""

    def _synth(self, tmp_path: Path, u_ms: float, v_ms: float, nx: int = 4, nz: int = 1):
        grid = tmp_path / "grid"
        grid.mkdir()
        mon = tmp_path / "monthly"
        n = LLC270_NFACE * nx * nx
        # put every native cell at lon=0.3, lat=0.3 -> all land in AOI bin (0,0)
        np.full(n, 0.3).astype(">f4").tofile(grid / "XC.data")
        np.full(n, 0.3).astype(">f4").tofile(grid / "YC.data")
        np.full(nz * n, 1.0).astype(">f4").tofile(grid / "hFacC.data")   # all ocean
        np.full(50, 10.0).astype(">f4").tofile(grid / "DRF.data")
        _write_native(mon, "uVel_C", 1, np.full((nz, LLC270_NFACE, nx, nx), u_ms))
        _write_native(mon, "vVel_C", 1, np.full((nz, LLC270_NFACE, nx, nx), v_ms))
        return mon, grid

    def test_eastward_sign_and_conversion(self, tmp_path: Path) -> None:
        mon, grid = self._synth(tmp_path, u_ms=0.5, v_ms=0.3)
        aoi = AOI("t", 0.0, 1.0, 0.0, 1.0)
        vf = velocity_aoi_grid(mon, grid, aoi, n_z=1, iters=[1], nx=4)
        # +0.5 m/s eastward -> +0.5*86400 m/day: POSITIVE (no flip) AND unit-converted.
        assert vf["u"][0, 0, 0] == pytest.approx(0.5 * M_PER_S_TO_M_PER_DAY)  # = 43200
        assert vf["v"][0, 0, 0] == pytest.approx(0.3 * M_PER_S_TO_M_PER_DAY)
        assert vf["u"][0, 0, 0] > 0                                           # kills a u-negation

    def test_no_conversion_when_disabled(self, tmp_path: Path) -> None:
        mon, grid = self._synth(tmp_path, u_ms=0.5, v_ms=0.3)
        aoi = AOI("t", 0.0, 1.0, 0.0, 1.0)
        vf = velocity_aoi_grid(mon, grid, aoi, n_z=1, iters=[1], nx=4, to_m_per_day=False)
        assert vf["u"][0, 0, 0] == pytest.approx(0.5)   # raw m/s
        assert vf["units"] == "m/s"


@pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 to run")
class TestRealVelocity:
    def test_eqpac_recovers_westward_sec(self) -> None:
        vf = velocity_aoi_grid(_MON, _GRID, EQUATORIAL_PACIFIC_AOI, n_z=6, iters="all",
                               max_iters=12)
        aoi = EQUATORIAL_PACIFIC_AOI
        assert vf["u"].shape == (
            int(aoi.lat_max - aoi.lat_min + 1),
            int(aoi.lon_max - aoi.lon_min + 1),
            6,
        )
        assert vf["units"] == "m/day"
        # surface climatology zonal flow is the westward South Equatorial Current (< 0)
        u_surf_ms = vf["u"][..., 0].mean() / M_PER_S_TO_M_PER_DAY
        assert -1.0 < u_surf_ms < 0.0
        assert np.abs(vf["u"] / M_PER_S_TO_M_PER_DAY).max() < 3.0  # physical (< 3 m/s)

    def test_real_velocity_is_divergence_free(self) -> None:
        vf = velocity_aoi_grid(_MON, _GRID, EQUATORIAL_PACIFIC_AOI, n_z=6, max_iters=6)
        u, v, w = divfree_barotropic_velocity(depth_mean(vf["u"]), depth_mean(vf["v"]),
                                              dx=1.11e5, dy=1.11e5, dz=10.0, n_z=6)
        ny, nx = vf["u"].shape[:2]
        state = torch.ones(ny, nx, 6, 5, dtype=torch.float64) * 0.3
        params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425], dtype=torch.float64)
        d = grid_tendency(state, params, u=u, v=v, w=w, dx=1.11e5, dy=1.11e5, kz=0.0,
                          dz=10.0, kh=0.0, bgc=False, include_vdiff=False)
        assert float(d.abs().max()) < 1e-9
