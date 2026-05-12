"""Tests for ``darwindiff.geotraces_loader``.

Covers the GEOTRACES IDP2025 discrete-bottle loader: variable mapping,
discrete-sample AOI subsetting, the bin-to-grid aggregation that turns
irregular bottle samples into the regular 1° grid the box-model fits use,
and the nmol/kg → mmol/m³ unit conversion.

Most tests use a **synthetic NetCDF fixture** that mirrors the documented
GEOTRACES IDP variable schema (``Fe_D_CONC_BOTTLE`` etc. along an
``N_SAMPLES`` dimension with ``Latitude`` / ``Longitude`` / ``DEPTH``
coordinates). One opt-in real-data test (``test_real_idp2025_iron``) gates
on ``DARWINDIFF_TEST_LLC270=1`` plus an actual IDP2025 file at
``GEOTRACES_DATA_ROOT`` — kept skipped in normal CI until the data is
downloaded and the loader is validated against real bytes.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI
from darwindiff.geotraces_loader import (
    GEOTRACES_VAR_MAP,
    RHO_SW,
    bin_to_grid,
    open_geotraces_bottle,
    subset_aoi_geotraces,
    to_mmol_per_m3,
)


def _make_synthetic_idp_netcdf(path: Path) -> None:
    """Build a tiny synthetic IDP2025-like NetCDF for loader tests.

    20 bottle samples scattered across the global ocean with realistic
    iron concentrations (0.05–2.5 nmol/kg, typical for dissolved Fe in the
    open ocean). Schema matches the documented IDP variable naming so the
    loader can be validated without the real ~GB download.
    """
    rng = np.random.default_rng(seed=42)
    n_samples = 20
    lats = rng.uniform(-30.0, 30.0, n_samples)
    # Mix of 0..360 (will be normalized) and -180..180.
    lons = rng.uniform(-180.0, 180.0, n_samples)
    depths = rng.uniform(5.0, 200.0, n_samples)
    fe_d = rng.uniform(0.05, 2.5, n_samples)
    fe_t = fe_d + rng.uniform(0.0, 0.5, n_samples)

    ds = xr.Dataset(
        data_vars={
            "Fe_D_CONC_BOTTLE": (
                ("N_SAMPLES",), fe_d,
                {"units": "nmol/kg", "long_name": "Dissolved iron"},
            ),
            "Fe_T_CONC_BOTTLE": (
                ("N_SAMPLES",), fe_t,
                {"units": "nmol/kg", "long_name": "Total iron"},
            ),
        },
        coords={
            "Latitude": ("N_SAMPLES", lats),
            "Longitude": ("N_SAMPLES", lons),
            "DEPTH": (
                ("N_SAMPLES",), depths,
                {"units": "m", "positive": "down"},
            ),
        },
        attrs={
            "title": "GEOTRACES synthetic test fixture",
            "source": "tests/test_geotraces_loader.py",
        },
    )
    ds.to_netcdf(path)


def test_geotraces_var_map_has_iron_phases() -> None:
    """The variable map exposes dissolved, total, soluble, and particulate iron."""
    assert "Fe_D" in GEOTRACES_VAR_MAP, "dissolved iron required for alpfe loss"
    assert "Fe_T" in GEOTRACES_VAR_MAP, "total iron required for FeT comparison"
    assert "Fe_S" in GEOTRACES_VAR_MAP
    assert "Fe_TP" in GEOTRACES_VAR_MAP
    # All map to the documented GEOTRACES <Param>_<Type>_CONC_<Phase> form.
    for k, v in GEOTRACES_VAR_MAP.items():
        assert v.endswith("_BOTTLE") or v.endswith("_PUMP"), (
            f"unexpected GEOTRACES variable form: {v!r}"
        )


def test_open_geotraces_bottle_missing_file(tmp_path: Path) -> None:
    """Opening a non-existent path raises FileNotFoundError with the bad path."""
    bad = tmp_path / "does_not_exist.nc"
    with pytest.raises(FileNotFoundError, match="does_not_exist"):
        open_geotraces_bottle(bad)


def test_open_geotraces_bottle_normalizes_longitude(tmp_path: Path) -> None:
    """Longitudes > 180 are normalized to -180..180."""
    path = tmp_path / "synth.nc"
    # Build a fixture with all lons in 0..360 to force normalization.
    lats = np.array([0.0, 10.0, -5.0])
    lons = np.array([10.0, 200.0, 350.0])  # 200, 350 should become -160, -10
    fe = np.array([0.5, 1.0, 1.5])
    ds = xr.Dataset(
        data_vars={"Fe_D_CONC_BOTTLE": (("N_SAMPLES",), fe)},
        coords={
            "Latitude": ("N_SAMPLES", lats),
            "Longitude": ("N_SAMPLES", lons),
            "DEPTH": ("N_SAMPLES", np.array([10.0, 10.0, 10.0])),
        },
    )
    ds.to_netcdf(path)

    opened = open_geotraces_bottle(path)
    assert float(opened.Longitude.min()) >= -180.0
    assert float(opened.Longitude.max()) <= 180.0
    # The 200 and 350 should have been mapped to negative longitudes.
    assert float(opened.Longitude.values[1]) == pytest.approx(-160.0, abs=1e-9)
    assert float(opened.Longitude.values[2]) == pytest.approx(-10.0, abs=1e-9)


def test_subset_aoi_geotraces_filters_to_box(tmp_path: Path) -> None:
    """Discrete-sample AOI subset keeps only stations inside the lat/lon box."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path)
    ds = open_geotraces_bottle(path)

    # Pick an Eq Pacific AOI (5°S–15°N, 160°W–110°W). All synthetic samples
    # are in -30..30 lat × -180..180 lon, so the AOI should cull most.
    aoi = AOI(
        name="EqPac",
        lat_min=-5.0,
        lat_max=15.0,
        lon_min=-160.0,
        lon_max=-110.0,
    )
    filtered = subset_aoi_geotraces(ds, aoi)
    # No samples outside the box.
    assert (filtered.Latitude >= aoi.lat_min).all()
    assert (filtered.Latitude <= aoi.lat_max).all()
    assert (filtered.Longitude >= aoi.lon_min).all()
    assert (filtered.Longitude <= aoi.lon_max).all()
    # The full fixture has at least one sample outside the box (rng seed=42,
    # 20 samples uniformly over global ocean → most outside this small AOI).
    assert filtered.sizes["N_SAMPLES"] < ds.sizes["N_SAMPLES"]


def test_bin_to_grid_aggregates_to_aoi(tmp_path: Path) -> None:
    """bin_to_grid produces a regular lat/lon grid with the right shape."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path)
    ds = open_geotraces_bottle(path)

    # AOI covering the full synthetic distribution (lats -30..30, lons full).
    # Guarantees at least some samples in the box regardless of rng seed.
    aoi = AOI(
        name="TestBox",
        lat_min=-30.0,
        lat_max=30.0,
        lon_min=-180.0,
        lon_max=180.0,
    )
    ds_sub = subset_aoi_geotraces(ds, aoi)
    assert ds_sub.sizes["N_SAMPLES"] > 0, (
        "synthetic fixture should have samples in -30..30 × -180..180"
    )

    grid = bin_to_grid(ds_sub, "Fe_D", aoi, lat_res=1.0, lon_res=1.0)
    assert grid.dims == ("lat", "lon")
    assert grid.shape == (60, 360)
    # Cell centers offset by 0.5°.
    assert float(grid.lat.values[0]) == pytest.approx(-29.5, abs=1e-9)
    assert float(grid.lon.values[0]) == pytest.approx(-179.5, abs=1e-9)
    # Units propagate to the output array.
    assert grid.attrs["units"] == "nmol/kg"
    # At least one bin has a sample.
    assert np.isfinite(grid.values).any()
    # All non-NaN bin values are within the synthetic Fe_D range [0.05, 2.5].
    finite_vals = grid.values[np.isfinite(grid.values)]
    assert (finite_vals >= 0.05).all() and (finite_vals <= 2.5).all()


def test_bin_to_grid_unknown_variable_raises(tmp_path: Path) -> None:
    """Asking for an unmapped variable raises KeyError listing known options."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path)
    ds = open_geotraces_bottle(path)
    aoi = AOI("Tiny", -1.0, 1.0, -1.0, 1.0)
    with pytest.raises(KeyError, match="Fe_unknown"):
        bin_to_grid(ds, "Fe_unknown", aoi)


def test_bin_to_grid_missing_variable_raises(tmp_path: Path) -> None:
    """Asking for a known variable not in the dataset raises ValueError."""
    path = tmp_path / "synth.nc"
    # Synthetic fixture lacks Fe_S_CONC_BOTTLE despite the friendly name
    # being in the map.
    _make_synthetic_idp_netcdf(path)
    ds = open_geotraces_bottle(path)
    aoi = AOI("Tiny", -90.0, 90.0, -180.0, 180.0)
    with pytest.raises(ValueError, match="Fe_S_CONC_BOTTLE.*not.*present"):
        bin_to_grid(ds, "Fe_S", aoi)


def test_bin_to_grid_respects_depth_max(tmp_path: Path) -> None:
    """Samples deeper than depth_max are excluded from the surface bin-mean."""
    path = tmp_path / "synth.nc"
    # Build a fixture where half the samples are shallow (<50 m) and half deep.
    lats = np.full(10, 0.5)  # all in the same bin
    lons = np.full(10, 0.5)
    depths = np.array([10.0, 20.0, 30.0, 40.0, 49.0, 100.0, 200.0, 500.0, 1000.0, 2000.0])
    fe = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 5.0, 5.0])
    ds = xr.Dataset(
        data_vars={"Fe_D_CONC_BOTTLE": (("N_SAMPLES",), fe)},
        coords={
            "Latitude": ("N_SAMPLES", lats),
            "Longitude": ("N_SAMPLES", lons),
            "DEPTH": ("N_SAMPLES", depths),
        },
    )
    ds.to_netcdf(path)
    opened = open_geotraces_bottle(path)
    aoi = AOI("OneBin", 0.0, 1.0, 0.0, 1.0)

    surface = bin_to_grid(opened, "Fe_D", aoi, depth_max=50.0)
    # All 5 shallow samples = 1.0; deep samples excluded.
    assert float(surface.values[0, 0]) == pytest.approx(1.0, abs=1e-9)
    assert surface.attrs["n_samples_aggregated"] == 5

    full = bin_to_grid(opened, "Fe_D", aoi, depth_max=np.inf)
    # All 10 samples averaged: (5*1.0 + 5*5.0) / 10 = 3.0
    assert float(full.values[0, 0]) == pytest.approx(3.0, abs=1e-9)
    assert full.attrs["n_samples_aggregated"] == 10


def test_to_mmol_per_m3_conversion_factor() -> None:
    """nmol/kg × ρ_sw × 1e-6 = mmol/m³. Verify the round number."""
    da = xr.DataArray(
        np.array([1.0, 2.0, 0.5]),
        dims=("N_SAMPLES",),
        attrs={"units": "nmol/kg", "long_name": "Dissolved iron"},
    )
    converted = to_mmol_per_m3(da)
    # 1 nmol/kg × 1025 kg/m³ × 1e-6 = 1.025e-3 mmol/m³
    assert float(converted.values[0]) == pytest.approx(RHO_SW * 1.0e-6, abs=1e-12)
    assert float(converted.values[1]) == pytest.approx(2.0 * RHO_SW * 1.0e-6, abs=1e-12)
    assert converted.attrs["units"] == "mmol / m^3"
    # Original metadata preserved (long_name) + conversion note added.
    assert converted.attrs["long_name"] == "Dissolved iron"
    assert "unit_conversion" in converted.attrs


@pytest.mark.skipif(
    os.environ.get("DARWINDIFF_TEST_LLC270", "0") != "1"
    or "GEOTRACES_DATA_ROOT" not in os.environ,
    reason="set DARWINDIFF_TEST_LLC270=1 + GEOTRACES_DATA_ROOT to a real IDP2025 NetCDF",
)
def test_real_idp2025_iron() -> None:
    """Opt-in: validates the loader against real IDP2025 bytes when available.

    Confirms variable names + coordinate conventions + units match the
    documented schema. Run after the IDP2025 NetCDF is downloaded to
    ``$GEOTRACES_DATA_ROOT``.
    """
    geotraces_root = Path(os.environ["GEOTRACES_DATA_ROOT"])
    # Expected canonical filename; refine when IDP2025 is on disk.
    candidates = list(geotraces_root.glob("GEOTRACES_IDP2025*.nc"))
    if not candidates:
        pytest.skip(f"no GEOTRACES_IDP2025*.nc in {geotraces_root}")
    ds = open_geotraces_bottle(candidates[0])
    # Smoke checks: dissolved iron present, lon normalized, coords sensible.
    assert "Fe_D_CONC_BOTTLE" in ds, (
        "real IDP2025 should have Fe_D_CONC_BOTTLE; "
        f"available vars: {sorted(ds.data_vars)}"
    )
    assert float(ds.Longitude.min()) >= -180.0
    assert float(ds.Longitude.max()) <= 180.0
