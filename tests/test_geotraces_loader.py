"""Tests for ``darwindiff.geotraces_loader``.

Covers the GEOTRACES IDP2025 discrete-bottle loader: variable mapping,
station-level AOI filter, 2D station-sample bin-to-grid aggregation,
QC-flag filtering, fill-value handling, and unit conversion.

The synthetic fixture mirrors the **real IDP2025 schema** (validated
2026-05-12 against ``D:\\geotraces\\GEOTRACES_IDP2025_Seawater.nc``):

    Dims:   N_STATIONS, N_SAMPLES (2D, not 1D)
    Coords: latitude, longitude (lowercase, per-station)
    2D:     DEPTH (m), Fe_D_CONC (nmol/kg), Fe_D_CONC_qc (SeaDataNet QC
            flag stored as ASCII char code: 49='1'=good, 50='2'=prob-good)
    Fill:   -1.0e10 sentinel (replaced with NaN by the loader)

One opt-in real-data test (``test_real_idp2025_iron``) gates on
``DARWINDIFF_TEST_LLC270=1`` + ``GEOTRACES_DATA_ROOT`` and validates the
loader against the actual ~60 MB IDP2025 NetCDF.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI
from darwindiff.geotraces_loader import (
    FILL_VALUE_THRESHOLD,
    GEOTRACES_VAR_MAP,
    QC_GOOD,
    RHO_SW,
    bin_to_grid,
    open_geotraces_bottle,
    subset_aoi_geotraces,
    to_mmol_per_m3,
)


def _make_synthetic_idp_netcdf(
    path: Path,
    n_stations: int = 20,
    n_samples_per_station: int = 10,
    seed: int = 42,
    lon_zero_to_360: bool = True,
) -> None:
    """Build a synthetic IDP2025-like NetCDF for loader tests.

    Schema mirrors the real IDP2025 ``GEOTRACES_IDP2025_Seawater.nc``:
    2D iron variables on ``(N_STATIONS, N_SAMPLES)``, per-station
    ``latitude`` / ``longitude``, per-sample ``DEPTH``, and a
    companion ``Fe_D_CONC_qc`` flag with GEOTRACES values {1, 2, 3, 4, 9}.

    A handful of cells are set to the IDP2025 fill value ``-1e10`` to
    exercise the masking path.
    """
    rng = np.random.default_rng(seed=seed)
    lats = rng.uniform(-60.0, 60.0, n_stations).astype(np.float32)
    if lon_zero_to_360:
        lons = rng.uniform(0.0, 360.0, n_stations).astype(np.float32)
    else:
        lons = rng.uniform(-180.0, 180.0, n_stations).astype(np.float32)
    depths = rng.uniform(5.0, 2000.0, (n_stations, n_samples_per_station)).astype(np.float32)
    fe_d = rng.uniform(0.05, 2.5, (n_stations, n_samples_per_station)).astype(np.float32)
    # Sprinkle fill values into ~10% of cells.
    fill_mask = rng.uniform(0.0, 1.0, fe_d.shape) < 0.1
    fe_d[fill_mask] = -1.0e10
    # SeaDataNet QC flags stored as ASCII char codes:
    #   49='1' good, 50='2' probably_good, 51='3' probably_bad,
    #   52='4' bad, 57='9' missing
    qc = rng.choice([49, 50, 51, 52, 57], size=fe_d.shape, p=[0.70, 0.15, 0.07, 0.03, 0.05]).astype(np.float32)

    ds = xr.Dataset(
        data_vars={
            "Fe_D_CONC": (
                ("N_STATIONS", "N_SAMPLES"), fe_d,
                {"units": "nmol/kg", "long_name": "Concentration of dissolved Fe", "_FillValue": -1.0e10},
            ),
            "Fe_D_CONC_qc": (
                ("N_STATIONS", "N_SAMPLES"), qc,
                {"long_name": "Fe_D_CONC QC flag"},
            ),
            "DEPTH": (
                ("N_STATIONS", "N_SAMPLES"), depths,
                {"units": "m", "positive": "down"},
            ),
        },
        coords={
            "latitude": ("N_STATIONS", lats, {"units": "degrees_north"}),
            "longitude": ("N_STATIONS", lons, {"units": "degrees_east"}),
        },
        attrs={
            "title": "GEOTRACES synthetic test fixture (matches real IDP2025 schema)",
            "source": "tests/test_geotraces_loader.py",
        },
    )
    ds.to_netcdf(path)


def test_geotraces_var_map_has_iron_phases() -> None:
    """The variable map exposes the four iron phases we care about."""
    assert "Fe_D" in GEOTRACES_VAR_MAP, "dissolved iron required for alpfe loss"
    assert "Fe_S" in GEOTRACES_VAR_MAP, "soluble iron"
    assert "Fe_TP" in GEOTRACES_VAR_MAP, "total particulate iron"
    assert "Fe_II_D" in GEOTRACES_VAR_MAP, "dissolved Fe(II)"
    # All map to the real IDP2025 <Param>_<Phase>_CONC form (no _BOTTLE/_PUMP).
    for k, v in GEOTRACES_VAR_MAP.items():
        assert v.endswith("_CONC"), f"unexpected GEOTRACES variable form: {v!r}"
        assert "_BOTTLE" not in v and "_PUMP" not in v, (
            f"IDP2025 drops _BOTTLE/_PUMP suffixes; got {v!r}"
        )


def test_open_geotraces_bottle_missing_file(tmp_path: Path) -> None:
    """Opening a non-existent path raises FileNotFoundError with the bad path."""
    bad = tmp_path / "does_not_exist.nc"
    with pytest.raises(FileNotFoundError, match="does_not_exist"):
        open_geotraces_bottle(bad)


def test_open_geotraces_bottle_normalizes_longitude(tmp_path: Path) -> None:
    """Longitudes 0..360 are rolled to -180..180 (DarwinDiff AOI convention)."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path, n_stations=5, n_samples_per_station=3, lon_zero_to_360=True)
    opened = open_geotraces_bottle(path)
    assert float(opened.longitude.min()) >= -180.0
    assert float(opened.longitude.max()) <= 180.0


def test_open_geotraces_bottle_masks_fill_values(tmp_path: Path) -> None:
    """Fill-value sentinels (-1e10) on Fe variables become NaN."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path, seed=7)
    ds = open_geotraces_bottle(path)
    # The synthetic fixture seeds ~10% of cells with -1e10; after loading,
    # those cells should be NaN, not -1e10.
    fe_arr = ds.Fe_D_CONC.values
    assert not (fe_arr < FILL_VALUE_THRESHOLD).any(), (
        "fill-value sentinels should have been masked to NaN"
    )
    # At least some cells are NaN (the masked ones).
    assert np.isnan(fe_arr).any()


def test_subset_aoi_geotraces_filters_by_station(tmp_path: Path) -> None:
    """AOI subset drops stations outside the box, keeps all samples on the rest."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path, n_stations=40, n_samples_per_station=5, seed=11)
    ds = open_geotraces_bottle(path)

    aoi = AOI(name="EqPac", lat_min=-5.0, lat_max=15.0, lon_min=-160.0, lon_max=-110.0)
    filtered = subset_aoi_geotraces(ds, aoi)
    if filtered.sizes["N_STATIONS"] > 0:
        assert (filtered.latitude >= aoi.lat_min).all()
        assert (filtered.latitude <= aoi.lat_max).all()
        assert (filtered.longitude >= aoi.lon_min).all()
        assert (filtered.longitude <= aoi.lon_max).all()
    # Sample dimension is preserved; only N_STATIONS shrinks.
    assert filtered.sizes["N_SAMPLES"] == ds.sizes["N_SAMPLES"]
    assert filtered.sizes["N_STATIONS"] <= ds.sizes["N_STATIONS"]


def test_bin_to_grid_shape_and_units(tmp_path: Path) -> None:
    """bin_to_grid produces a regular lat/lon grid with the right shape + units."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path, n_stations=200, n_samples_per_station=10, seed=23)
    ds = open_geotraces_bottle(path)

    aoi = AOI(name="Global", lat_min=-60.0, lat_max=60.0, lon_min=-180.0, lon_max=180.0)
    ds_sub = subset_aoi_geotraces(ds, aoi)
    grid = bin_to_grid(ds_sub, "Fe_D", aoi, lat_res=1.0, lon_res=1.0)
    assert grid.dims == ("lat", "lon")
    assert grid.shape == (120, 360)
    # Cell centers offset by 0.5°.
    assert float(grid.lat.values[0]) == pytest.approx(-59.5, abs=1e-9)
    assert float(grid.lon.values[0]) == pytest.approx(-179.5, abs=1e-9)
    assert grid.attrs["units"] == "nmol/kg"
    # All non-NaN values are in the synthetic Fe_D range [0.05, 2.5].
    finite = grid.values[np.isfinite(grid.values)]
    assert finite.size > 0
    assert (finite >= 0.05).all() and (finite <= 2.5).all()


def test_bin_to_grid_unknown_variable_raises(tmp_path: Path) -> None:
    """Asking for an unmapped variable raises KeyError."""
    path = tmp_path / "synth.nc"
    _make_synthetic_idp_netcdf(path, n_stations=5, n_samples_per_station=3)
    ds = open_geotraces_bottle(path)
    aoi = AOI("Tiny", -1.0, 1.0, -1.0, 1.0)
    with pytest.raises(KeyError, match="Fe_unknown"):
        bin_to_grid(ds, "Fe_unknown", aoi)


def test_bin_to_grid_missing_variable_raises(tmp_path: Path) -> None:
    """Asking for a known variable not in the dataset raises ValueError."""
    path = tmp_path / "synth.nc"
    # Synthetic fixture only has Fe_D_CONC; asking for Fe_S fails.
    _make_synthetic_idp_netcdf(path)
    ds = open_geotraces_bottle(path)
    aoi = AOI("Tiny", -90.0, 90.0, -180.0, 180.0)
    with pytest.raises(ValueError, match="Fe_S_CONC.*not.*present"):
        bin_to_grid(ds, "Fe_S", aoi)


def test_bin_to_grid_respects_depth_max(tmp_path: Path) -> None:
    """Samples deeper than depth_max are excluded from the surface bin-mean."""
    # Build a fixture where half the samples are shallow (<50 m) and half deep.
    # Single station, all in the same bin.
    path = tmp_path / "synth.nc"
    n_samples = 10
    depths = np.array([10.0, 20.0, 30.0, 40.0, 49.0, 100.0, 200.0, 500.0, 1000.0, 2000.0],
                      dtype=np.float32)
    fe = np.array([1.0, 1.0, 1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 5.0, 5.0], dtype=np.float32)
    qc = np.full(n_samples, 49.0, dtype=np.float32)  # SeaDataNet '1' = good
    ds = xr.Dataset(
        data_vars={
            "Fe_D_CONC": (("N_STATIONS", "N_SAMPLES"), fe[None, :], {"units": "nmol/kg"}),
            "Fe_D_CONC_qc": (("N_STATIONS", "N_SAMPLES"), qc[None, :]),
            "DEPTH": (("N_STATIONS", "N_SAMPLES"), depths[None, :], {"units": "m"}),
        },
        coords={
            "latitude": ("N_STATIONS", np.array([0.5], dtype=np.float32)),
            "longitude": ("N_STATIONS", np.array([0.5], dtype=np.float32)),
        },
    )
    ds.to_netcdf(path)
    opened = open_geotraces_bottle(path)
    aoi = AOI("OneBin", 0.0, 1.0, 0.0, 1.0)

    surface = bin_to_grid(opened, "Fe_D", aoi, depth_max=50.0)
    assert float(surface.values[0, 0]) == pytest.approx(1.0, abs=1e-6)
    assert surface.attrs["n_samples_aggregated"] == 5

    full = bin_to_grid(opened, "Fe_D", aoi, depth_max=np.inf)
    assert float(full.values[0, 0]) == pytest.approx(3.0, abs=1e-6)
    assert full.attrs["n_samples_aggregated"] == 10


def test_bin_to_grid_qc_filter(tmp_path: Path) -> None:
    """QC filter retains only flags in qc_flags (default {49, 50} for SeaDataNet good/prob-good)."""
    # Two stations sharing one bin. Station A all qc=49 (good), station B all qc=51 (probably_bad).
    path = tmp_path / "synth.nc"
    fe = np.array([[1.0, 1.0, 1.0], [9.0, 9.0, 9.0]], dtype=np.float32)
    qc = np.array([[49, 49, 49], [51, 51, 51]], dtype=np.float32)
    depths = np.full((2, 3), 10.0, dtype=np.float32)
    ds = xr.Dataset(
        data_vars={
            "Fe_D_CONC": (("N_STATIONS", "N_SAMPLES"), fe, {"units": "nmol/kg"}),
            "Fe_D_CONC_qc": (("N_STATIONS", "N_SAMPLES"), qc),
            "DEPTH": (("N_STATIONS", "N_SAMPLES"), depths, {"units": "m"}),
        },
        coords={
            "latitude": ("N_STATIONS", np.array([0.5, 0.5], dtype=np.float32)),
            "longitude": ("N_STATIONS", np.array([0.5, 0.5], dtype=np.float32)),
        },
    )
    ds.to_netcdf(path)
    opened = open_geotraces_bottle(path)
    aoi = AOI("OneBin", 0.0, 1.0, 0.0, 1.0)

    # Default {1, 2}: only the 3 station-A samples count → mean = 1.0
    good_only = bin_to_grid(opened, "Fe_D", aoi)
    assert float(good_only.values[0, 0]) == pytest.approx(1.0, abs=1e-6)
    assert good_only.attrs["n_samples_aggregated"] == 3

    # Disable QC: all 6 samples → mean = (3*1 + 3*9) / 6 = 5.0
    no_qc = bin_to_grid(opened, "Fe_D", aoi, qc_flags=())
    assert float(no_qc.values[0, 0]) == pytest.approx(5.0, abs=1e-6)
    assert no_qc.attrs["n_samples_aggregated"] == 6


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
    assert converted.attrs["long_name"] == "Dissolved iron"
    assert "unit_conversion" in converted.attrs


@pytest.mark.skipif(
    os.environ.get("DARWINDIFF_TEST_LLC270", "0") != "1"
    or "GEOTRACES_DATA_ROOT" not in os.environ,
    reason="set DARWINDIFF_TEST_LLC270=1 + GEOTRACES_DATA_ROOT to a real IDP2025 NetCDF",
)
def test_real_idp2025_iron() -> None:
    """Opt-in: validates the loader against real IDP2025 bytes.

    Validated 2026-05-12 against ``D:\\geotraces\\GEOTRACES_IDP2025_Seawater.nc``
    (4094 stations × 698 samples, 23,912 finite ``Fe_D_CONC``).
    """
    geotraces_root = Path(os.environ["GEOTRACES_DATA_ROOT"])
    candidates = list(geotraces_root.glob("GEOTRACES_IDP2025*Seawater*.nc"))
    if not candidates:
        pytest.skip(f"no GEOTRACES_IDP2025*Seawater*.nc in {geotraces_root}")

    ds = open_geotraces_bottle(candidates[0])
    # Schema sanity checks.
    assert "Fe_D_CONC" in ds, f"real IDP2025 should have Fe_D_CONC; got {sorted(ds.data_vars)[:10]}"
    assert "latitude" in ds and "longitude" in ds
    assert "DEPTH" in ds
    assert ds["Fe_D_CONC"].dims == ("N_STATIONS", "N_SAMPLES")
    # Longitude properly normalized to -180..180.
    assert float(ds.longitude.min()) >= -180.0
    assert float(ds.longitude.max()) <= 180.0
    # Raw Fe_D_CONC has some negative values (below-detection-limit artifacts
    # reported by individual labs; flagged via the _qc companion). These get
    # filtered downstream by bin_to_grid's QC filter.
    fe = ds.Fe_D_CONC.values
    finite = fe[np.isfinite(fe)]
    assert finite.size > 10000, f"expected ~24k finite Fe_D_CONC measurements; got {finite.size}"
    # After fill-value masking, no -1e10 sentinels leak through.
    assert (finite > FILL_VALUE_THRESHOLD).all(), (
        f"unmasked fill-value sentinel leak; min={finite.min()}"
    )
    # Eq Pacific AOI subset should have a non-trivial station count.
    eqpac = AOI(name="EqPac", lat_min=-5.0, lat_max=15.0, lon_min=-160.0, lon_max=-110.0)
    sub = subset_aoi_geotraces(ds, eqpac)
    assert sub.sizes["N_STATIONS"] > 0, "Eq Pacific should have stations in IDP2025"
    # Bin to 1° + verify shape, units, sample count is sensible.
    grid = bin_to_grid(sub, "Fe_D", eqpac)
    assert grid.shape == (20, 50)
    assert grid.attrs["units"] == "nmol/kg"
    # QC-filtered surface bin means: physically plausible for HNLC Eq Pacific
    # (0.05–1.5 nmol/kg typical, occasional higher near coasts).
    finite_grid = grid.values[np.isfinite(grid.values)]
    assert finite_grid.size > 0, "expected at least one populated bin in Eq Pacific"
    assert (finite_grid > 0).all(), (
        f"QC filter should drop negative below-detection values; "
        f"min binned = {finite_grid.min()}"
    )
