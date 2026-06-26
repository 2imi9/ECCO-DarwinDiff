"""Tests for darwindiff.daniels_loader.

Uses a synthetic in-memory PANGAEA-style .tab (metadata block + ``*/`` +
TSV header + rows) so the unit tests run without the on-disk file. A real-data
integration test against the staged ``data/daniels/...`` compilation is guarded
by ``DARWINDIFF_TEST_DANIELS=1`` (mirrors the GLODAP/LLC270 opt-in pattern).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

from darwindiff.daniels_loader import (
    DEFAULT_DANIELS_PATH,
    bin_to_grid,
    build_aoi_climatology,
    load_daniels_points,
    rain_ratio,
    valid_surface_mask,
)
from darwindiff.ecco_darwin_loader import (
    AOI,
    EQUATORIAL_PACIFIC_AOI,
)

_RUN_REAL = (
    os.environ.get("DARWINDIFF_TEST_DANIELS") == "1" and DEFAULT_DANIELS_PATH.is_file()
)

# A minimal PANGAEA textfile: a metadata block, the closing ``*/``, the TSV
# header (column order MUST match the real file's named columns), then rows.
_HEADER = (
    "PI\tExpedition\tOS region\tReference\tURL ref\tMethod comm\tDate/Time\t"
    "Station\tLatitude\tLongitude\tDepth water [m]\tPerc [%]\tInc dur [h]\t"
    "CaCO3 prod C [mmol/m**3/day]\tCaCO3 prod C std dev\tPP C [mmol/m**3/day]\t"
    "PP C std dev\tCoccolith [#/ml]\tE. huxleyi [#/ml]"
)


def _row(lat, lon, depth, cp, pp) -> str:
    """One data row; only the 5 numeric columns we read are meaningful."""
    cols = ["X"] * 19
    cols[8] = f"{lat}"
    cols[9] = f"{lon}"
    cols[10] = f"{depth}"
    cols[13] = "" if cp is None else f"{cp}"
    cols[15] = "" if pp is None else f"{pp}"
    return "\t".join(cols)


def _make_synthetic_tab(tmp_path: Path, rows: list[str]) -> Path:
    body = [
        "/* DATA DESCRIPTION:",
        "Citation:\tsynthetic test fixture",
        "*/",
        _HEADER,
        *rows,
    ]
    path = tmp_path / "daniels_synth.tab"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


class TestLoadDanielsPoints:
    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError, match="Daniels compilation not found"):
            load_daniels_points(tmp_path / "nope.tab")

    def test_parses_after_metadata_block(self, tmp_path) -> None:
        path = _make_synthetic_tab(
            tmp_path,
            [_row(4.0, -110.0, 6.8, 0.02, 0.64), _row(50.0, -20.0, 5.0, 0.1, 1.0)],
        )
        pts = load_daniels_points(path)
        assert len(pts.lat) == 2
        np.testing.assert_allclose(pts.lat, [4.0, 50.0])
        np.testing.assert_allclose(pts.lon, [-110.0, -20.0])
        np.testing.assert_allclose(pts.cp, [0.02, 0.1])
        np.testing.assert_allclose(pts.pp, [0.64, 1.0])

    def test_empty_numeric_cell_is_nan(self, tmp_path) -> None:
        path = _make_synthetic_tab(tmp_path, [_row(4.0, -110.0, 6.8, None, 0.64)])
        pts = load_daniels_points(path)
        assert np.isnan(pts.cp[0])


class TestRainRatio:
    def test_molar_ratio(self, tmp_path) -> None:
        path = _make_synthetic_tab(tmp_path, [_row(0.0, 0.0, 1.0, 0.02, 0.64)])
        pts = load_daniels_points(path)
        np.testing.assert_allclose(rain_ratio(pts), [0.02 / 0.64])

    def test_zero_pp_is_nan(self, tmp_path) -> None:
        path = _make_synthetic_tab(tmp_path, [_row(0.0, 0.0, 1.0, 0.02, 0.0)])
        pts = load_daniels_points(path)
        assert np.isnan(rain_ratio(pts)[0])


class TestValidSurfaceMask:
    def test_depth_cut(self, tmp_path) -> None:
        path = _make_synthetic_tab(
            tmp_path,
            [_row(0.0, 0.0, 10.0, 0.02, 0.64), _row(0.0, 0.0, 200.0, 0.02, 0.64)],
        )
        pts = load_daniels_points(path)
        m = valid_surface_mask(pts, depth_max=50.0)
        assert m.tolist() == [True, False]

    def test_zero_cp_excluded_when_positive_required(self, tmp_path) -> None:
        path = _make_synthetic_tab(
            tmp_path,
            [_row(0.0, 0.0, 10.0, 0.0, 0.64), _row(0.0, 0.0, 10.0, 0.02, 0.64)],
        )
        pts = load_daniels_points(path)
        assert valid_surface_mask(pts, require_positive=True).tolist() == [False, True]
        assert valid_surface_mask(pts, require_positive=False).tolist() == [True, True]


class TestBinToGrid:
    def test_geometric_mean_in_cell(self, tmp_path) -> None:
        # Two samples in the same 1° cell with ratios 0.01 and 0.04 → geomean 0.02.
        path = _make_synthetic_tab(
            tmp_path,
            [_row(0.2, 0.3, 5.0, 0.01, 1.0), _row(0.4, 0.1, 5.0, 0.04, 1.0)],
        )
        pts = load_daniels_points(path)
        vals, mask, counts = bin_to_grid(pts, np.array([0.0]), np.array([0.0]))
        assert mask[0, 0] and counts[0, 0] == 2
        np.testing.assert_allclose(vals[0, 0], np.sqrt(0.01 * 0.04))

    def test_out_of_box_samples_excluded(self, tmp_path) -> None:
        # Regression: a sample far outside the grid must NOT fold into an edge
        # cell (the global-cloud over-inclusion bug).
        path = _make_synthetic_tab(
            tmp_path,
            [_row(0.0, 0.0, 5.0, 0.02, 1.0), _row(80.0, 170.0, 5.0, 0.5, 1.0)],
        )
        pts = load_daniels_points(path)
        vals, mask, counts = bin_to_grid(pts, np.array([0.0]), np.array([0.0]))
        assert counts[0, 0] == 1  # only the in-box sample
        np.testing.assert_allclose(vals[0, 0], 0.02)

    def test_empty_grid_all_masked(self, tmp_path) -> None:
        path = _make_synthetic_tab(tmp_path, [_row(80.0, 170.0, 5.0, 0.5, 1.0)])
        pts = load_daniels_points(path)
        _, mask, counts = bin_to_grid(pts, np.array([0.0]), np.array([0.0]))
        assert not mask.any() and counts.sum() == 0


class TestBuildAoiClimatology:
    def test_eqpac_grid_shape(self, tmp_path) -> None:
        # One sample inside eqpac → 20×50-ish grid, exactly one finite cell.
        path = _make_synthetic_tab(tmp_path, [_row(4.0, -120.0, 6.8, 0.02, 0.64)])
        pts = load_daniels_points(path)
        vals, mask, counts = build_aoi_climatology(EQUATORIAL_PACIFIC_AOI, points=pts)
        assert vals.shape == mask.shape == counts.shape
        assert mask.shape[0] in (20, 21) and mask.shape[1] in (50, 51)
        assert int(mask.sum()) == 1
        np.testing.assert_allclose(vals[mask][0], 0.02 / 0.64)


class TestRealDanielsData:
    """Integration test against the staged Daniels compilation."""

    @pytest.mark.skipif(
        not _RUN_REAL, reason="set DARWINDIFF_TEST_DANIELS=1 + Daniels .tab on disk"
    )
    def test_real_eqpac_geomean_plausible(self) -> None:
        vals, mask, counts = build_aoi_climatology(EQUATORIAL_PACIFIC_AOI)
        n_cells = int(mask.sum())
        assert n_cells > 10, f"too few eqpac cells ({n_cells}); AOI bin wrong"
        gm = float(np.exp(np.nanmean(np.log(vals[mask]))))
        # Eq-Pacific surface CP:PP geomean ≈ 0.04 (log-normal); generous bounds.
        assert 0.01 < gm < 0.15, f"eqpac rain-ratio geomean {gm:.4f} out of range"

    @pytest.mark.skipif(
        not _RUN_REAL, reason="set DARWINDIFF_TEST_DANIELS=1 + Daniels .tab on disk"
    )
    def test_real_southern_ocean_pacific_empty(self) -> None:
        # The Daniels Southern-Ocean coverage is Atlantic/Indian-sector, so the
        # S-Pacific box has zero coverage and an empty mask (term auto-gates).
        so_pac = AOI("SO Pacific", -65.0, -50.0, -180.0, -100.0)
        _, mask, _ = build_aoi_climatology(so_pac)
        assert int(mask.sum()) == 0
