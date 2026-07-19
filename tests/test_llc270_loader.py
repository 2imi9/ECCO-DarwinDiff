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
    bin_native_tracer_to_1deg,
    bin_to_1deg_grid,
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
        #
        # delta_t was asserted as 900 here until 2026-07-19. That was WRONG, and
        # this test is why the bug survived: it locked in the incorrect constant
        # and turned a silent data defect into a "verified" one. The value is
        # 1200 s -- see the LLC270Config docstring for the five independent lines
        # of evidence. Guard the invariant that actually pins it down.
        assert DEFAULT_CONFIG.delta_t == 1200
        assert DEFAULT_CONFIG.ref_date == "1992-01-01"
        assert DEFAULT_CONFIG.nx == 270
        assert DEFAULT_CONFIG.nz == 50

    def test_daily_output_cadence_is_exactly_one_day(self) -> None:
        # The decisive check the original test lacked. v05 daily output steps by
        # 72 iterations; that must be exactly 86400 s of model time. At the old
        # delta_t=900 this yields 0.75 day, which is not a daily cadence -- so
        # this assertion fails loudly if delta_t is ever wrong again.
        assert 72 * DEFAULT_CONFIG.delta_t == 86400

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


class TestBinTo1DegGrid:
    """Pure-math tests for the bin-averaging math used by nb19+ joint-loss fits."""

    def test_shape_matches_eqpac_aoi(self) -> None:
        # Eq Pacific 5°S–15°N × 160°W–110°W → 21 lat bins × 51 lon bins,
        # matching nb19's (21, 51) shape against the bin_average product.
        xc = np.array([-130.0])
        yc = np.array([0.0])
        values = np.array([1.0])
        out = bin_to_1deg_grid(xc, yc, values, -5.0, 15.0, -160.0, -110.0)
        assert out.shape == (21, 51)

    def test_single_cell_binned_to_correct_index(self) -> None:
        # A point at (lat=0, lon=-130) sits in lat bin 5 (centers -5..15) and
        # lon bin 30 (centers -160..-110). Verify the value lands there.
        xc = np.array([-130.0])
        yc = np.array([0.0])
        values = np.array([42.0])
        out = bin_to_1deg_grid(xc, yc, values, -5.0, 15.0, -160.0, -110.0)
        assert out[5, 30] == 42.0
        # All other bins should be NaN (empty).
        mask = np.zeros_like(out, dtype=bool)
        mask[5, 30] = True
        assert np.isnan(out[~mask]).all()

    def test_multiple_cells_in_same_bin_are_averaged(self) -> None:
        # Two points within ±0.4° of (0, -130) both land in the same bin.
        xc = np.array([-130.2, -129.8])
        yc = np.array([-0.2, 0.2])
        values = np.array([10.0, 20.0])
        out = bin_to_1deg_grid(xc, yc, values, -5.0, 15.0, -160.0, -110.0)
        assert out[5, 30] == 15.0   # mean of 10 and 20

    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="shape mismatch"):
            bin_to_1deg_grid(
                np.array([0.0]), np.array([0.0, 1.0]), np.array([1.0]),
                -5.0, 15.0, -160.0, -110.0,
            )

    def test_handles_2d_native_input(self) -> None:
        # Native LLC270 tiles are (face, j, i); the binner should flatten them.
        # Synthesize a small 2D field with known cell centers.
        xc = np.array([[-130.0, -129.0], [-128.0, -127.0]])
        yc = np.array([[0.0, 0.0], [1.0, 1.0]])
        values = np.array([[1.0, 2.0], [3.0, 4.0]])
        out = bin_to_1deg_grid(xc, yc, values, -5.0, 15.0, -160.0, -110.0)
        # Each of the 4 points lands in its own bin.
        assert out[5, 30] == 1.0   # (0, -130)
        assert out[5, 31] == 2.0   # (0, -129)
        assert out[6, 32] == 3.0   # (1, -128)
        assert out[6, 33] == 4.0   # (1, -127)


class TestBinNativeTracerTo1Deg:
    """Integration test using xmitgcm + real data — opt-in via env var."""

    @pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_LLC270=1 to run")
    def test_real_dic_bin_to_1deg_eqpac(self) -> None:
        # nb20 needs DIC bin-averaged to Eq Pac 1° grid; matches the existing
        # FeT / POC / PIC pattern from nb19 but for the new DIC + ALK tracers
        # that Day 2's carroll6_carbonate_integrate consumes.
        out = bin_native_tracer_to_1deg(
            monthly_root=_REAL_MONTHLY_ROOT,
            grid_dir=_REAL_GRID_DIR,
            variable="DIC",
            lat_min=-5.0, lat_max=15.0, lon_min=-160.0, lon_max=-110.0,
            iters="first",   # one iter is enough for a smoke-style assert
        )
        assert out.shape == (21, 51)
        # Surface DIC in the equatorial Pacific is typically 1900-2100 mmol/m^3
        # (Carroll 2022 climatology) — anything outside that means the loader
        # produced something wrong.
        finite = out[np.isfinite(out)]
        assert finite.size > 100, "too few finite cells; AOI masking went wrong"
        mean_dic = float(finite.mean())
        assert 1800.0 < mean_dic < 2200.0, f"Eq Pac surface DIC mean {mean_dic:.1f} off"


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
