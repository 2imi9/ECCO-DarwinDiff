"""Tests for darwindiff.llc270_loader.

Most behaviour is exercised against synthetic .meta files written to a
tmp directory, which avoids needing the real 50+ GB-per-tracer LLC270
data on disk. The xmitgcm-based open path is covered by an integration-
style test guarded by an opt-in env var (``DARWINDIFF_TEST_LLC270=1``)
that hits the real ``D:\\ecco_darwin_v5\\`` data when available — keeps
CI fast while still letting Lucas validate end-to-end locally.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
import xarray as xr

from darwindiff.llc270_loader import (
    DEFAULT_CONFIG,
    TRAC_MAPPING,
    LLC270Config,
    aoi_mask_from_xc_yc,
    discover_tracer_meta,
    list_available_iterations,
    open_llc270_tracer,
    surface_layer,
)

# Path to the real on-disk data; only used by opt-in integration tests.
_REAL_MONTHLY_ROOT = r"D:\ecco_darwin_v5\output\monthly"
_REAL_GRID_DIR = r"D:\ecco_darwin_v5\grid"
_RUN_REAL = os.environ.get("DARWINDIFF_TEST_LLC270") == "1"


def _write_synthetic_meta(path, fld_name: str = "TRAC18") -> None:
    """Write an MITgcm .meta sidecar that mimics the on-disk schema."""
    content = f""" nDims = [   3 ];
 dimList = [
   270,    1,  270,
  3510,    1, 3510,
    50,    1,   50
 ];
 dataprec = [ 'float32' ];
 nrecords = [          1 ];
 timeStepNumber = [       2232 ];
 timeInterval = [  2.635200000000E+06  2.678400000000E+06 ];
 missingValue = [ -9.99000000000000E+02 ];
 nFlds = [    1 ];
 fldList = {{
 '{fld_name:<8s}'
 }};
"""
    path.write_text(content)


class TestTracMapping:
    def test_alk_maps_to_trac18(self) -> None:
        # Ground truth from the on-disk .meta files. If MITgcm-Darwin ever
        # renumbers its TRAC indices in v06+, this test forces us to update.
        assert TRAC_MAPPING["ALK"] == "TRAC18"

    def test_dic_maps_to_trac01(self) -> None:
        assert TRAC_MAPPING["DIC"] == "TRAC01"

    def test_no3_maps_to_trac02(self) -> None:
        # NO3 is the headline target for nb13's Carroll-6 fit. Pin it.
        assert TRAC_MAPPING["NO3"] == "TRAC02"

    def test_iron_maps_to_trac06(self) -> None:
        # Iron pair (alpfe / scav_rat) recovery test (nb14) needs FeT.
        assert TRAC_MAPPING["FeT"] == "TRAC06"

    def test_chlorophyll_indices_consecutive(self) -> None:
        # Darwin packs the 5 PFTs as consecutive TRAC indices (one per PFT).
        # Pin the order so chlorophyll-group sums match the bin_average product.
        for i in range(1, 6):
            assert TRAC_MAPPING[f"Chl{i}"] == f"TRAC{26 + i}"


class TestDiscoverTracerMeta:
    def test_reads_tracer_name_from_meta(self, tmp_path) -> None:
        var_dir = tmp_path / "ALK"
        var_dir.mkdir()
        _write_synthetic_meta(var_dir / "ALK.0000002232.meta", fld_name="TRAC18")
        # Need a corresponding .data file so xmitgcm-style listing works
        (var_dir / "ALK.0000002232.data").write_bytes(b"\x00" * 100)
        result = discover_tracer_meta(tmp_path)
        assert result == {"ALK": "TRAC18"}

    def test_skips_directories_without_meta(self, tmp_path) -> None:
        (tmp_path / "EMPTY").mkdir()
        var_dir = tmp_path / "DIC"
        var_dir.mkdir()
        _write_synthetic_meta(var_dir / "DIC.0000004320.meta", fld_name="TRAC01")
        (var_dir / "DIC.0000004320.data").write_bytes(b"\x00" * 100)
        result = discover_tracer_meta(tmp_path)
        assert "EMPTY" not in result
        assert result.get("DIC") == "TRAC01"

    def test_missing_root_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            discover_tracer_meta(tmp_path / "does_not_exist")


class TestListAvailableIterations:
    def test_returns_sorted_iters(self, tmp_path) -> None:
        var_dir = tmp_path / "ALK"
        var_dir.mkdir()
        for it in [4320, 2232, 6552]:
            _write_synthetic_meta(var_dir / f"ALK.{it:010d}.meta", fld_name="TRAC18")
            (var_dir / f"ALK.{it:010d}.data").write_bytes(b"\x00" * 100)
        result = list_available_iterations(tmp_path, "ALK")
        assert result == [2232, 4320, 6552]

    def test_ignores_non_data_files(self, tmp_path) -> None:
        var_dir = tmp_path / "ALK"
        var_dir.mkdir()
        _write_synthetic_meta(var_dir / "ALK.0000002232.meta", fld_name="TRAC18")
        (var_dir / "ALK.0000002232.data").write_bytes(b"\x00" * 100)
        (var_dir / "index.html.tmp").write_text("garbage")  # wget partial files
        (var_dir / "ALK.0000002232.dat").write_bytes(b"\x00")  # wrong extension
        result = list_available_iterations(tmp_path, "ALK")
        assert result == [2232]

    def test_missing_var_dir_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            list_available_iterations(tmp_path, "NONEXISTENT")


class TestAoiMaskFromXcYc:
    def test_simple_box_inclusive(self) -> None:
        xc = np.array([[-10.0, 0.0, 10.0], [-10.0, 0.0, 10.0]])
        yc = np.array([[-5.0, -5.0, -5.0], [5.0, 5.0, 5.0]])
        mask = aoi_mask_from_xc_yc(xc, yc, lat_min=-5, lat_max=5, lon_min=-5, lon_max=5)
        # Only the (0, 5) and (0, -5) boundaries are included; the corners
        # at (+/-10, +/-5) are outside the lon range.
        expected = np.array([[False, True, False], [False, True, False]])
        np.testing.assert_array_equal(mask, expected)

    def test_accepts_dataarray_inputs(self) -> None:
        xc = xr.DataArray(np.array([0.0, 10.0]))
        yc = xr.DataArray(np.array([0.0, 0.0]))
        mask = aoi_mask_from_xc_yc(xc, yc, lat_min=-5, lat_max=5, lon_min=-5, lon_max=5)
        np.testing.assert_array_equal(mask, [True, False])

    def test_midatlantic_aoi_boundaries(self) -> None:
        # Mid-Atl AOI from the project: 30..50 N, -60..-30 E. Verify boundary cells.
        xc = np.array([-60.0, -45.0, -30.0, -29.0])
        yc = np.array([30.0, 40.0, 50.0, 50.0])
        mask = aoi_mask_from_xc_yc(xc, yc, 30, 50, -60, -30)
        np.testing.assert_array_equal(mask, [True, True, True, False])


class TestLLC270Config:
    def test_default_matches_v05(self) -> None:
        # Carroll 2022 v05/llc270 setup uses these. If they change in v06+
        # we'll need a separate config preset.
        assert DEFAULT_CONFIG.delta_t == 900
        assert DEFAULT_CONFIG.ref_date == "1992-01-01"
        assert DEFAULT_CONFIG.nx == 270
        assert DEFAULT_CONFIG.nz == 50

    def test_custom_config_constructs(self) -> None:
        cfg = LLC270Config(delta_t=600, ref_date="1995-01-01", nx=270, nz=75)
        assert cfg.delta_t == 600


class TestOpenLLC270Tracer:
    def test_unknown_variable_raises(self) -> None:
        with pytest.raises(KeyError, match="unknown variable"):
            open_llc270_tracer(
                monthly_root="/dev/null",
                grid_dir="/dev/null",
                variable="NotARealTracer",
            )

    def test_missing_var_dir_raises(self, tmp_path) -> None:
        # ALK is in TRAC_MAPPING but the directory doesn't exist on disk.
        with pytest.raises(FileNotFoundError, match="not found"):
            open_llc270_tracer(
                monthly_root=str(tmp_path),
                grid_dir=str(tmp_path),
                variable="ALK",
            )

    @pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 to run")
    def test_real_alk_load(self) -> None:
        # Integration test against the on-disk D:\ data. Opt-in via env var.
        ds = open_llc270_tracer(
            monthly_root=_REAL_MONTHLY_ROOT,
            grid_dir=_REAL_GRID_DIR,
            variable="ALK",
            iters="first",
        )
        assert "ALK" in ds.data_vars
        # LLC270 native: 13 faces x 270 x 270 cells x 50 levels x 1 time
        assert ds.ALK.shape == (1, 50, 13, 270, 270)
        assert "XC" in ds.coords and "YC" in ds.coords
        # ALK is total alkalinity in seawater; surface values typically 1500-3500 mmol/m^3.
        surf = ds.ALK.isel(time=0, k=0).values
        nonzero = surf[surf != 0]
        assert 1000 < float(nonzero.mean()) < 4000


class TestSurfaceLayer:
    def test_picks_k_zero_and_drops_dim(self) -> None:
        data = xr.DataArray(
            np.arange(50 * 13 * 270 * 270, dtype=np.float32).reshape(50, 13, 270, 270),
            dims=("k", "face", "j", "i"),
        )
        ds = xr.Dataset({"ALK": data})
        surf = surface_layer(ds)
        assert "k" not in surf.dims
        # Should equal the k=0 slice of the original.
        np.testing.assert_array_equal(surf.ALK.values, data.isel(k=0).values)

    def test_no_op_if_no_k_dim(self) -> None:
        ds = xr.Dataset({"ALK": xr.DataArray(np.zeros((10, 10)), dims=("j", "i"))})
        surf = surface_layer(ds)
        # Should round-trip unchanged.
        assert "k" not in surf.dims
        assert surf.ALK.shape == (10, 10)
