"""Tests for darwindiff.ecco_darwin_loader.

Uses synthetic in-memory NetCDF datasets that match the on-disk
``v05_ECCO-Darwin_bin_average_1x1_deg.nc`` structure (180 lat x 360 lon x N
time, MATLAB datenum time coord, 2-D lat/lon vars). Avoids the on-disk file
so tests run without it.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import numpy as np
import pytest
import xarray as xr

from darwindiff.ecco_darwin_loader import (
    AOI,
    EQUATORIAL_PACIFIC_AOI,
    MID_ATLANTIC_AOI,
    NORTH_PACIFIC_AOI,
    matlab_datenum_to_datetime64,
    monthly_climatology,
    ocean_mask,
    open_bin_average,
    subset_aoi,
    time_mean,
    total_chlorophyll,
)

# Real on-disk bin_average product. Opt-in (same env var as the LLC270 tree
# opt-in, since both live under DARWIN_DATA_ROOT on the local setup). Honors
# DARWIN_DATA_ROOT so the same test runs on ORCD with the PI-shared pool path
# without local edits.
_DATA_ROOT = os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")
_REAL_BIN_AVG = os.path.join(
    _DATA_ROOT, "bin_average", "v05_ECCO-Darwin_bin_average_1x1_deg.nc"
)
_RUN_REAL = os.environ.get("DARWINDIFF_TEST_LLC270") == "1"


def _make_synthetic_bin_average(tmp_path, n_time: int = 12) -> str:
    """Build a synthetic NetCDF mirroring the bin_average schema, return path."""
    lat_1d = np.arange(-90.0, 90.0)  # 180 cells, integer centers
    lon_1d = np.arange(-180.0, 180.0)  # 360 cells, integer centers
    lat_2d, lon_2d = np.meshgrid(lat_1d, lon_1d, indexing="ij")
    rng = np.random.default_rng(0)

    # Build a few time-varying vars matching the on-disk schema. Use float64 to
    # match the real file. Inject some NaN cells to simulate land masking.
    def _var(scale: float = 1.0) -> np.ndarray:
        arr = rng.standard_normal((n_time, 180, 360)) * scale
        # Mark ~10% of cells as land (NaN at all timesteps).
        land_mask = rng.random((180, 360)) < 0.1
        arr[:, land_mask] = np.nan
        return arr

    # MATLAB datenums for monthly cadence starting 1995-01-01.
    base = datetime(1995, 1, 1)
    matlab_times = np.array(
        [(base + timedelta(days=30 * i) - datetime(1, 1, 1)).days + 367 for i in range(n_time)],
        dtype=np.float64,
    )

    ds = xr.Dataset(
        data_vars={
            "lat": (("y", "x"), lat_2d),
            "lon": (("y", "x"), lon_2d),
            "area": (("y", "x"), np.ones_like(lat_2d) * 1e10),
            "SST": (("time", "y", "x"), _var(scale=10.0)),
            "SSS": (("time", "y", "x"), _var(scale=2.0)),
            "Chl1": (("time", "y", "x"), _var(scale=0.5)),
            "Chl2": (("time", "y", "x"), _var(scale=0.5)),
            "Chl3": (("time", "y", "x"), _var(scale=0.5)),
            "Chl4": (("time", "y", "x"), _var(scale=0.5)),
            "Chl5": (("time", "y", "x"), _var(scale=0.5)),
            "CO2_flux": (("time", "y", "x"), _var(scale=1e-7)),
            "windSpeed": (("time", "y", "x"), _var(scale=5.0)),
        },
        coords={"time": matlab_times},
    )
    ds["time"].attrs = {"units": "MATLAB datenum"}
    path = tmp_path / "synthetic_bin_average.nc"
    ds.to_netcdf(path)
    return str(path)


class TestMatlabDatenum:
    def test_known_value_matches_carroll_paper_window(self) -> None:
        # bin_average file's first time stamp is 728660 -> 1995-01-01 per the
        # NAS portal documentation. Verify the conversion lands correctly.
        result = matlab_datenum_to_datetime64(np.array([728660.0]))
        assert str(result[0])[:10] == "1995-01-01"

    def test_known_last_value_matches(self) -> None:
        # 737030 -> 2017-12-01.
        result = matlab_datenum_to_datetime64(np.array([737030.0]))
        assert str(result[0])[:10] == "2017-12-01"

    def test_array_shape_preserved(self) -> None:
        result = matlab_datenum_to_datetime64(np.array([728660.0, 737030.0]))
        assert result.shape == (2,)
        assert result.dtype.name == "datetime64[ns]"


class TestAOI:
    def test_valid_aoi_constructs(self) -> None:
        aoi = AOI(name="test", lat_min=-10, lat_max=10, lon_min=-20, lon_max=20)
        assert aoi.name == "test"

    def test_inverted_lat_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid lat"):
            AOI(name="bad", lat_min=10, lat_max=-10, lon_min=0, lon_max=10)

    def test_out_of_range_lat_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid lat"):
            AOI(name="bad", lat_min=-100, lat_max=10, lon_min=0, lon_max=10)

    def test_inverted_lon_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid lon"):
            AOI(name="bad", lat_min=0, lat_max=10, lon_min=10, lon_max=-10)

    def test_out_of_range_lon_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid lon"):
            AOI(name="bad", lat_min=0, lat_max=10, lon_min=-200, lon_max=10)

    def test_preset_aois_valid(self) -> None:
        # Sanity: the three preset AOIs construct without error and have the
        # documented coordinates from the May 7 collaboration call.
        assert MID_ATLANTIC_AOI.lat_min == 30.0
        assert MID_ATLANTIC_AOI.lat_max == 50.0
        assert MID_ATLANTIC_AOI.lon_min == -60.0
        assert MID_ATLANTIC_AOI.lon_max == -30.0
        assert NORTH_PACIFIC_AOI.lon_min == -160.0
        assert EQUATORIAL_PACIFIC_AOI.lat_min < 0


class TestOpenBinAverage:
    def test_loads_with_decoded_time(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path, n_time=12)
        ds = open_bin_average(path)
        assert "time" in ds.coords
        assert ds.time.dtype.name == "datetime64[ns]"
        # First synthetic time is 1995-01-01.
        assert str(ds.time.values[0])[:7] == "1995-01"

    def test_renames_y_x_to_lat_lon(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        assert "lat" in ds.dims and "lon" in ds.dims
        assert "y" not in ds.dims and "x" not in ds.dims

    def test_lat_lon_are_coordinates(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        # lat and lon should be 1-D numeric coords, not 2-D data vars.
        assert ds.lat.ndim == 1
        assert ds.lon.ndim == 1
        assert ds.lat.values[0] == -90.0
        assert ds.lon.values[0] == -180.0

    def test_drops_redundant_2d_lat_lon_vars(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        # The original 2-D lat/lon data vars should be dropped (info now in coords).
        assert "lat" not in ds.data_vars
        assert "lon" not in ds.data_vars


class TestSubsetAOI:
    def test_mid_atlantic_subset_shape(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        sub = subset_aoi(ds, MID_ATLANTIC_AOI)
        # 30..50 inclusive on integer-center 1-deg grid = 21 lat cells (30, 31, ..., 50)
        # -60..-30 inclusive = 31 lon cells (-60, -59, ..., -30)
        assert sub.sizes["lat"] == 21
        assert sub.sizes["lon"] == 31

    def test_north_pacific_subset_shape(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        sub = subset_aoi(ds, NORTH_PACIFIC_AOI)
        assert sub.sizes["lat"] == 21
        assert sub.sizes["lon"] == 31

    def test_subset_preserves_time(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path, n_time=12)
        ds = open_bin_average(path)
        sub = subset_aoi(ds, MID_ATLANTIC_AOI)
        assert sub.sizes["time"] == 12

    def test_subset_preserves_data_vars(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        sub = subset_aoi(ds, MID_ATLANTIC_AOI)
        for v in ["SST", "Chl1", "CO2_flux"]:
            assert v in sub.data_vars


class TestTotalChlorophyll:
    def test_sums_all_five_groups_by_default(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        chl = total_chlorophyll(ds)
        # Compare against manual sum.
        manual = ds.Chl1 + ds.Chl2 + ds.Chl3 + ds.Chl4 + ds.Chl5
        # NaN-aware comparison
        assert np.allclose(chl.values, manual.values, equal_nan=True)
        assert chl.name == "Chl_total"

    def test_can_select_subset_of_groups(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        chl_diatom = total_chlorophyll(ds, groups=[5])
        # Just Chl5.
        assert np.allclose(chl_diatom.values, ds.Chl5.values, equal_nan=True)

    def test_missing_group_raises(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        ds_partial = ds.drop_vars(["Chl3"])
        with pytest.raises(KeyError, match="Chl3"):
            total_chlorophyll(ds_partial)


class TestTimeReductions:
    def test_monthly_climatology_has_12_months(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path, n_time=24)  # 2 yrs
        ds = open_bin_average(path)
        clim = monthly_climatology(ds)
        assert clim.sizes["month"] == 12

    def test_time_mean_collapses_time(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path, n_time=12)
        ds = open_bin_average(path)
        tm = time_mean(ds)
        assert "time" not in tm.dims


class TestOceanMask:
    def test_mask_identifies_ocean_cells(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        mask = ocean_mask(ds)
        # Mask should be 2-D (lat, lon) — time stripped.
        assert mask.dims == ("lat", "lon")
        assert mask.dtype == bool
        # Synthetic data has ~10% land; mask should have >80% True.
        ocean_frac = float(mask.sum()) / mask.size
        assert 0.8 < ocean_frac < 0.95

    def test_unknown_reference_var_raises(self, tmp_path) -> None:
        path = _make_synthetic_bin_average(tmp_path)
        ds = open_bin_average(path)
        with pytest.raises(KeyError, match="not in dataset"):
            ocean_mask(ds, reference_var="DoesNotExist")


class TestRealBinAverageCarbonateVars:
    """Verify nb20 dependencies (CO₂_flux, pCO₂, apCO₂) exist on the real file.

    nb20's joint loss adds the carbonate variables from the bin_average product
    on top of nb19's 4-tracer setup. The loader docstring claims these variables
    are present, but no existing test exercises that claim against the actual
    file. Opt-in so CI stays fast.
    """

    @pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 to run")
    def test_carbonate_vars_present_and_eq_pac_in_range(self) -> None:
        ds = open_bin_average(_REAL_BIN_AVG)
        # nb20 needs all three.
        for var in ("CO2_flux", "pCO2", "apCO2"):
            assert var in ds.data_vars, f"{var} missing — nb20 cannot run"
        # Sanity-check magnitudes over Eq Pacific climatology.
        eqpac = time_mean(subset_aoi(ds, EQUATORIAL_PACIFIC_AOI))
        finite_co2_flux = eqpac.CO2_flux.values[np.isfinite(eqpac.CO2_flux.values)]
        finite_pco2 = eqpac.pCO2.values[np.isfinite(eqpac.pCO2.values)]
        # CO₂_flux in mol C / m² / s — typical surface ocean values are
        # |F| < 1e-6. Eq Pacific is a CO₂ source so mean is positive.
        assert abs(float(finite_co2_flux.mean())) < 1.0e-5, (
            "CO₂_flux magnitude suspect — check units"
        )
        # pCO₂ in atm; Eq Pacific surface climatology ~350-450 µatm = ~4e-4 atm.
        mean_pco2 = float(finite_pco2.mean())
        assert 1.0e-4 < mean_pco2 < 1.0e-3, f"pCO₂ {mean_pco2:.2e} atm off"
