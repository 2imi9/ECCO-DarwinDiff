"""Tests for darwindiff.glodap_loader.

Uses synthetic in-memory NetCDFs that match the GLODAPv2.2016b on-disk
schema (33 × 180 × 360 grid, 0–360-roll longitudes ~20.5–379.5, µmol/kg
units). Avoids the on-disk 1.4 GB extracted product so tests run fast.

Real-data integration test guarded by ``DARWINDIFF_TEST_LLC270=1`` (same
env-var pattern as the other real-data opt-ins on this machine — GLODAP
lives alongside LLC270 on the same partition).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from darwindiff.ecco_darwin_loader import EQUATORIAL_PACIFIC_AOI
from darwindiff.glodap_loader import (
    GLODAP_VAR_MAP,
    RHO_SW,
    open_glodap_variable,
    subset_aoi_glodap,
    surface_layer_glodap,
    to_mmol_per_m3,
)

# Real-data GLODAP tests are guarded by DARWINDIFF_TEST_LLC270; the env-var
# DARWIN_DATA_ROOT is not consulted here because the GLODAP path is anchored
# to the repo via __file__, not to the LLC270 data root.
_REAL_GLODAP = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "glodap"
    / "GLODAPv2.2016b_MappedClimatologies"
)
_RUN_REAL = os.environ.get("DARWINDIFF_TEST_LLC270") == "1" and _REAL_GLODAP.is_dir()


def _make_synthetic_glodap_netcdf(tmp_path: Path, variable: str = "TCO2") -> Path:
    """Write a synthetic NetCDF mirroring the GLODAPv2.2016b schema."""
    lon = np.arange(20.5, 380.5)
    lat = np.arange(-89.5, 90.5)
    depth_surface = np.arange(33)
    Depth = np.linspace(5.0, 5500.0, 33)

    rng = np.random.default_rng(0)
    field = rng.uniform(1900.0, 2300.0, size=(33, 180, 360)).astype(np.float64)
    # Inject NaN over a land-like patch so we exercise the masking.
    field[:, 80:100, 180:220] = np.nan

    ds = xr.Dataset(
        data_vars={
            variable: (("depth_surface", "lat", "lon"), field,
                       {"units": "micro-mol kg-1"}),
            f"{variable}_error": (
                ("depth_surface", "lat", "lon"),
                rng.uniform(5.0, 20.0, size=(33, 180, 360)),
                {"units": "micro-mol kg-1"},
            ),
            "Depth": (("depth_surface",), Depth, {"units": "m", "positive": "down"}),
        },
        coords={
            "lon": (("lon",), lon),
            "lat": (("lat",), lat),
        },
    )
    path = tmp_path / f"GLODAPv2.2016b.{variable}.nc"
    ds.to_netcdf(path)
    return path


class TestGlodapVarMap:
    def test_dic_maps_to_tco2(self) -> None:
        assert GLODAP_VAR_MAP["DIC"] == "TCO2"

    def test_alk_maps_to_talk(self) -> None:
        assert GLODAP_VAR_MAP["ALK"] == "TAlk"

    def test_no3_maps_to_no3(self) -> None:
        assert GLODAP_VAR_MAP["NO3"] == "NO3"


class TestOpenGlodapVariable:
    def test_unknown_variable_raises(self, tmp_path) -> None:
        with pytest.raises(KeyError, match="unknown GLODAP variable"):
            open_glodap_variable(tmp_path, "NotARealVariable")

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match="GLODAP file not found"):
            open_glodap_variable(tmp_path, "DIC")

    def test_longitude_normalized_to_minus180_180(self, tmp_path) -> None:
        _make_synthetic_glodap_netcdf(tmp_path, variable="TCO2")
        ds = open_glodap_variable(tmp_path, "DIC")
        # After normalization lon must be in [-180, 180].
        assert float(ds.lon.min()) >= -180.0
        assert float(ds.lon.max()) <= 180.0
        # Should still have 360 lon cells (transform is a roll, not a crop).
        assert ds.sizes["lon"] == 360

    def test_loads_correct_variable_name(self, tmp_path) -> None:
        _make_synthetic_glodap_netcdf(tmp_path, variable="TAlk")
        ds = open_glodap_variable(tmp_path, "ALK")
        assert "TAlk" in ds.data_vars


class TestSurfaceLayerGlodap:
    def test_picks_depth_surface_zero(self, tmp_path) -> None:
        path = _make_synthetic_glodap_netcdf(tmp_path, variable="TCO2")
        ds = xr.open_dataset(path)
        surf = surface_layer_glodap(ds)
        assert "depth_surface" not in surf.dims
        # The k=0 slice should equal the explicit isel.
        np.testing.assert_array_equal(
            surf.TCO2.values, ds.TCO2.isel(depth_surface=0).values,
        )

    def test_no_op_if_no_depth_dim(self) -> None:
        ds = xr.Dataset({"x": xr.DataArray(np.zeros(10), dims=("lat",))})
        surf = surface_layer_glodap(ds)
        assert "depth_surface" not in surf.dims


class TestSubsetAoiGlodap:
    def test_eq_pacific_subset_shape(self, tmp_path) -> None:
        _make_synthetic_glodap_netcdf(tmp_path, variable="TCO2")
        ds = open_glodap_variable(tmp_path, "DIC")
        eqpac = subset_aoi_glodap(ds, EQUATORIAL_PACIFIC_AOI)
        # 5°S–15°N x 160°W–110°W on a 1° grid → 20 lat × 50 lon (inclusive).
        assert eqpac.sizes["lat"] in (20, 21)
        assert eqpac.sizes["lon"] in (50, 51)


class TestUnitConversion:
    def test_mmol_per_m3_factor(self) -> None:
        # 2050 µmol/kg × 1025 × 1e-3 = 2101.25 mmol/m³
        da = xr.DataArray([2050.0], attrs={"units": "micro-mol kg-1"})
        converted = to_mmol_per_m3(da)
        assert abs(float(converted[0]) - 2050.0 * RHO_SW * 1.0e-3) < 1.0e-9
        assert converted.attrs["units"] == "mmol / m^3"

    def test_metadata_preserved(self) -> None:
        da = xr.DataArray([100.0], attrs={"long_name": "test", "units": "micro-mol kg-1"})
        converted = to_mmol_per_m3(da)
        assert converted.attrs["long_name"] == "test"
        assert "unit_conversion" in converted.attrs


class TestRealGlodapData:
    """Integration test against the on-disk GLODAPv2.2016b product."""

    @pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 + GLODAP on disk")
    def test_real_dic_load_eq_pacific(self) -> None:
        ds = open_glodap_variable(_REAL_GLODAP, "DIC")
        eqpac = subset_aoi_glodap(ds, EQUATORIAL_PACIFIC_AOI)
        eqpac_surf = surface_layer_glodap(eqpac)
        # Surface DIC in the Eq Pacific is typically 1900–2100 µmol/kg.
        finite = eqpac_surf.TCO2.values[np.isfinite(eqpac_surf.TCO2.values)]
        assert finite.size > 100, "too few finite cells; AOI subset wrong"
        mean = float(finite.mean())
        assert 1800.0 < mean < 2200.0, f"surface DIC mean {mean:.1f} µmol/kg out of range"

    @pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 + GLODAP on disk")
    def test_real_alk_load_eq_pacific(self) -> None:
        ds = open_glodap_variable(_REAL_GLODAP, "ALK")
        eqpac = subset_aoi_glodap(ds, EQUATORIAL_PACIFIC_AOI)
        eqpac_surf = surface_layer_glodap(eqpac)
        finite = eqpac_surf.TAlk.values[np.isfinite(eqpac_surf.TAlk.values)]
        assert finite.size > 100
        mean = float(finite.mean())
        # Surface alkalinity Eq Pacific: ~2200–2400 µmol/kg
        assert 2100.0 < mean < 2500.0, f"surface ALK mean {mean:.1f} µmol/kg out of range"
