"""Tests for darwindiff.iron_forcing_loader (DB-1: spatial soluble-iron forcing).

The pure read/reshape/unit-conversion logic is exercised against **synthetic**
LLC270-compact binaries written to tmp (no 45 MB file needed), plus an integration
test that feeds the built dust field through the real transport consumer
(``bgc_tendency_field``). Opt-in real tests (``DARWINDIFF_TEST_IRON=1``) validate
against the on-disk LLC270 grid; the ones needing the actual ironfile skip cleanly
when it is absent (it is a public NAS download, input/darwin_forcing/; see
scripts/fetch/iron_forcing.sh).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest
import torch

import darwindiff.iron_forcing_loader as ifl
from darwindiff.carroll6 import P, PHI_DUST
from darwindiff.ecco_darwin_loader import AOI, EQUATORIAL_PACIFIC_AOI
from darwindiff.iron_forcing_loader import (
    IRON_INSCAL,
    IRON_N_RECORDS,
    IRONFILE_NAME,
    LLC270_NFACE,
    LLC270_NX,
    SECONDS_PER_DAY,
    coverage_mask,
    flux_to_phi_dust,
    iron_flux_aoi_grid,
    load_grid_lonlat,
    load_surface_dz,
    load_surface_ocean_mask,
    month_of_day,
    phi_dust_sanity,
    phi_dust_surface_field,
    read_llc270_compact,
    read_soluble_iron_flux,
)
from darwindiff.transport import bgc_tendency_field

_REAL_GRID_DIR = r"D:\ecco_darwin_v5\grid"
_REAL_IRON = Path(r"D:\ecco_darwin_v5\input") / IRONFILE_NAME
_RUN_REAL = os.environ.get("DARWINDIFF_TEST_IRON") == "1"


def _write_compact(path: Path, arr: np.ndarray) -> None:
    """Write an array as a big-endian float32 compact binary (MITgcm convention)."""
    arr.astype(">f4").tofile(path)


def _synthetic_ironfile(tmp_path: Path, *, nx: int = 4, per_record=None) -> Path:
    """A tiny 12-record compact ironfile. Record m (0-based) is filled with
    ``per_record(m)`` (default: constant m) so time-reductions are checkable."""
    if per_record is None:
        per_record = lambda m: float(m)
    stack = np.stack(
        [np.full((LLC270_NFACE, nx, nx), per_record(m)) for m in range(IRON_N_RECORDS)]
    )
    p = tmp_path / IRONFILE_NAME
    _write_compact(p, stack)
    return p


# --------------------------------------------------------------------------- #
# read_llc270_compact
# --------------------------------------------------------------------------- #
class TestReadCompact:
    def test_roundtrip_multi_record(self, tmp_path: Path) -> None:
        nx = 5
        rng = np.random.default_rng(0)
        arr = rng.standard_normal((IRON_N_RECORDS, LLC270_NFACE, nx, nx))
        p = tmp_path / "f.bin"
        _write_compact(p, arr)
        out = read_llc270_compact(p, n_records=IRON_N_RECORDS, nx=nx)
        assert out.shape == (IRON_N_RECORDS, LLC270_NFACE, nx, nx)
        np.testing.assert_allclose(out, arr.astype(">f4"), rtol=0, atol=0)

    def test_single_record_shape(self, tmp_path: Path) -> None:
        nx = 6
        arr = np.arange(LLC270_NFACE * nx * nx, dtype=float).reshape(LLC270_NFACE, nx, nx)
        p = tmp_path / "g.bin"
        _write_compact(p, arr)
        out = read_llc270_compact(p, n_records=1, nx=nx)
        assert out.shape == (LLC270_NFACE, nx, nx)

    def test_size_mismatch_raises(self, tmp_path: Path) -> None:
        nx = 4
        arr = np.zeros((LLC270_NFACE, nx, nx))
        p = tmp_path / "h.bin"
        _write_compact(p, arr)
        # Ask for the wrong nx -> element count won't match -> loud error.
        with pytest.raises(ValueError, match="expected"):
            read_llc270_compact(p, n_records=1, nx=nx + 1)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_llc270_compact(tmp_path / "nope.bin")

    def test_big_endian_required(self, tmp_path: Path) -> None:
        """A little-endian write is mis-read (guards the >f4 convention)."""
        nx = 4
        arr = np.full((LLC270_NFACE, nx, nx), 1.0)
        p = tmp_path / "le.bin"
        arr.astype("<f4").tofile(p)
        out = read_llc270_compact(p, n_records=1, nx=nx)  # read as >f4
        assert not np.allclose(out, 1.0)  # byte-swapped 1.0 is not 1.0


# --------------------------------------------------------------------------- #
# read_soluble_iron_flux: inscal + time reduction
# --------------------------------------------------------------------------- #
class TestReadFlux:
    def test_annual_mean_and_inscal(self, tmp_path: Path) -> None:
        # record m filled with m -> mean over 0..11 = 5.5; x inscal.
        p = _synthetic_ironfile(tmp_path, nx=4)
        flux = read_soluble_iron_flux(p, nx=4)
        assert flux.shape == (LLC270_NFACE, 4, 4)
        np.testing.assert_allclose(flux, 5.5 * IRON_INSCAL)

    def test_month_select(self, tmp_path: Path) -> None:
        p = _synthetic_ironfile(tmp_path, nx=4)
        # month=3 (1-based) -> record index 2 -> value 2.0 x inscal.
        flux = read_soluble_iron_flux(p, month=3, nx=4)
        np.testing.assert_allclose(flux, 2.0 * IRON_INSCAL)

    def test_month_first_and_last(self, tmp_path: Path) -> None:
        p = _synthetic_ironfile(tmp_path, nx=4)
        np.testing.assert_allclose(read_soluble_iron_flux(p, month=1, nx=4), 0.0)
        np.testing.assert_allclose(read_soluble_iron_flux(p, month=12, nx=4), 11.0 * IRON_INSCAL)

    @pytest.mark.parametrize("bad", [0, 13, -1])
    def test_month_out_of_range_raises(self, tmp_path: Path, bad: int) -> None:
        p = _synthetic_ironfile(tmp_path, nx=4)
        with pytest.raises(ValueError, match="month"):
            read_soluble_iron_flux(p, month=bad)

    def test_custom_inscal(self, tmp_path: Path) -> None:
        p = _synthetic_ironfile(tmp_path, nx=4, per_record=lambda m: 1.0)
        np.testing.assert_allclose(read_soluble_iron_flux(p, inscal=7.0, nx=4), 7.0)


# --------------------------------------------------------------------------- #
# flux_to_phi_dust: the load-bearing unit conversion
# --------------------------------------------------------------------------- #
class TestFluxToPhiDust:
    def test_formula(self) -> None:
        areal = 3.0e-8  # mmol/m^2/s
        dz = 25.0
        assert flux_to_phi_dust(areal, dz) == pytest.approx(areal * SECONDS_PER_DAY / dz)

    def test_independent_literal(self) -> None:
        """Pin the 86400 day-constant against HARDCODED values (not threaded through
        SECONDS_PER_DAY), so a wrong day-constant fails the suite instead of shipping
        green. 1e-8*86400/10 = 8.64e-5; 3e-8*86400/25 = 1.0368e-4."""
        assert flux_to_phi_dust(1.0e-8, 10.0) == pytest.approx(8.64e-5)
        assert flux_to_phi_dust(3.0e-8, 25.0) == pytest.approx(1.03680e-4)

    def test_recovers_scalar_phi_dust(self) -> None:
        """Areal flux implied by the tuned scalar PHI_DUST (at H_MLD=50 m) round-trips."""
        dz = 50.0
        areal = PHI_DUST * dz / SECONDS_PER_DAY  # invert the conversion
        assert flux_to_phi_dust(areal, dz) == pytest.approx(PHI_DUST, rel=1e-12)

    def test_array(self) -> None:
        areal = np.array([1.0e-8, 2.0e-8, 0.0])
        got = flux_to_phi_dust(areal, 10.0)
        np.testing.assert_allclose(got, areal * SECONDS_PER_DAY / 10.0)

    @pytest.mark.parametrize("dz", [0.0, -5.0])
    def test_bad_dz_raises(self, dz: float) -> None:
        with pytest.raises(ValueError, match="dz"):
            flux_to_phi_dust(1.0, dz)


# --------------------------------------------------------------------------- #
# phi_dust_surface_field: A4 surface-only placement + transport integration
# --------------------------------------------------------------------------- #
class TestSurfaceField:
    def test_places_at_surface_only(self) -> None:
        grid = np.array([[1.0e-8, 2.0e-8], [3.0e-8, 4.0e-8]])
        dz, n_z = 25.0, 5
        field = phi_dust_surface_field(grid, dz, n_z)
        assert field.shape == (2, 2, n_z)
        expected_surf = torch.as_tensor(grid * SECONDS_PER_DAY / dz, dtype=field.dtype)
        torch.testing.assert_close(field[..., 0], expected_surf)
        assert torch.all(field[..., 1:] == 0)  # zero below surface (A4)

    def test_nan_filled(self) -> None:
        grid = np.array([[1.0e-8, np.nan]])
        field = phi_dust_surface_field(grid, 10.0, 3, fill=0.0)
        assert field[0, 1, 0] == 0.0  # NaN land bin -> fill
        assert field[0, 0, 0] > 0.0

    def test_column_input_independent_of_nz(self) -> None:
        """A4 invariant: column-integrated dust (sum_z vol*dz) is independent of n_z."""
        grid = np.array([[5.0e-8]])
        dz = 25.0
        col_int = lambda nz: float((phi_dust_surface_field(grid, dz, nz).sum() * dz).item())
        assert col_int(2) == pytest.approx(col_int(8))
        # and equals areal * seconds_per_day (the areal input, per day)
        assert col_int(4) == pytest.approx(5.0e-8 * SECONDS_PER_DAY)

    def test_feeds_transport_bgc_tendency(self) -> None:
        """The built field drives per-cell surface DFe input in the real consumer."""
        ny, nx, n_z = 2, 2, 3
        # [Y, X, Z, tracer] 5-tracer state
        state = torch.zeros(ny, nx, n_z, 5, dtype=torch.float64)
        state[..., 0] = 0.1   # DFe
        state[..., 3] = 1.0   # POC
        params = torch.tensor(
            [0.928, 1.0e-8, 1.0, 1.0, 1.0, 0.0425], dtype=torch.float64
        )  # alpfe, scav_rat, mu_s, mu_l, g, R
        grid = np.array([[1.0e-8, 2.0e-8], [3.0e-8, 4.0e-8]])
        dz = 25.0
        dust = phi_dust_surface_field(grid, dz, n_z, dtype=torch.float64)
        d = bgc_tendency_field(state, params, dust=dust)
        # Surface dDFe source term = alpfe * dust; the per-cell surface value must
        # differ cell-to-cell (the whole point of a spatial forcing).
        alpfe = float(params[P.alpfe])
        src_surface = alpfe * torch.as_tensor(grid * SECONDS_PER_DAY / dz)
        # dDFe = alpfe*dust - scav - uptake; scav/uptake identical across cells here
        # (uniform DFe/POC/bio), so cell-to-cell DIFFERENCES in dDFe == alpfe*dust diffs.
        dDFe_surf = d[..., 0, 0]
        diff = dDFe_surf - dDFe_surf[0, 0]
        torch.testing.assert_close(diff, (src_surface - src_surface[0, 0]).to(diff.dtype))
        # sub-surface layers get NO dust source (A4)
        assert torch.allclose(d[0, 0, 1:, 0], d[1, 1, 1:, 0])  # same (dust-free) tendency


# --------------------------------------------------------------------------- #
# phi_dust_sanity: units guard
# --------------------------------------------------------------------------- #
class TestSanity:
    def test_correct_scale_within_tol(self) -> None:
        # A field whose mean volumetric rate == PHI_DUST at dz=50.
        areal = PHI_DUST * 50.0 / SECONDS_PER_DAY
        grid = np.full((3, 3), areal)
        s = phi_dust_sanity(grid, dz=50.0)
        assert s["within_tol"] is True
        assert s["ratio"] == pytest.approx(1.0, rel=1e-9)

    def test_hardcoded_areal_ratio(self) -> None:
        """Feed a HARDCODED areal value (not derived from SECONDS_PER_DAY): areal
        2.8935e-8 mmol/m^2/s at dz=50 -> vol = 2.8935e-8*86400/50 = 5.0e-5 ~= PHI_DUST.
        A wrong day-constant moves the mean off 5e-5 and trips this."""
        grid = np.full((2, 2), 2.8935e-8)
        s = phi_dust_sanity(grid, dz=50.0)
        assert s["mean_volumetric_mmol_m3_d"] == pytest.approx(5.0e-5, rel=1e-3)
        assert s["within_tol"] is True

    def test_units_blowup_flagged(self) -> None:
        areal = PHI_DUST * 50.0 / SECONDS_PER_DAY
        grid = np.full((3, 3), areal * 1.0e6)  # 6 orders too big (e.g. mol vs nmol slip)
        s = phi_dust_sanity(grid, dz=50.0)
        assert s["within_tol"] is False

    def test_nan_ignored(self) -> None:
        areal = PHI_DUST * 50.0 / SECONDS_PER_DAY
        grid = np.full((3, 3), areal)
        grid[0, 0] = np.nan
        s = phi_dust_sanity(grid, dz=50.0)
        assert s["within_tol"] is True


# --------------------------------------------------------------------------- #
# month_of_day
# --------------------------------------------------------------------------- #
class TestMonthOfDay:
    @pytest.mark.parametrize(
        "t,expected",
        [(0.0, 1), (30.0, 1), (31.0, 2), (364.0, 12), (365.0, 1), (400.0, 2)],
    )
    def test_mapping(self, t: float, expected: int) -> None:
        assert month_of_day(t) == expected

    def test_always_in_range(self) -> None:
        for t in np.linspace(0, 3 * 365, 500):
            assert 1 <= month_of_day(float(t)) <= 12


# --------------------------------------------------------------------------- #
# iron_flux_aoi_grid masking (non-opt-in, monkeypatched -- no real files needed)
# --------------------------------------------------------------------------- #
class TestAoiGridMasking:
    """Lock in the module's headline masking decision (hFacC>0 ocean, NOT field!=0)
    without the 45 MB ironfile: monkeypatch the three loaders to tiny synthetic
    native arrays and assert which cells survive into the 1-deg bin means."""

    def _patch(self, monkeypatch, lon, lat, flux, ocean):
        monkeypatch.setattr(ifl, "read_soluble_iron_flux", lambda *a, **k: flux)
        monkeypatch.setattr(ifl, "load_grid_lonlat", lambda *a, **k: (lon, lat))
        monkeypatch.setattr(ifl, "load_surface_ocean_mask", lambda *a, **k: ocean)

    def test_zero_deposition_ocean_cell_is_kept(self, monkeypatch) -> None:
        # Two ocean cells in the SAME 1-deg bin: one 2e-8, one genuine 0.0 deposition.
        # Correct '& ocean' mask keeps both -> mean 1e-8. The docstring-forbidden
        # '& (flux != 0)' would drop the zero cell -> mean 2e-8. This test fails if
        # anyone switches to the != 0 mask.
        lon = np.array([0.0, 0.0, 1.0, 0.0])
        lat = np.array([0.0, 0.0, 1.0, 1.0])
        flux = np.array([2.0e-8, 0.0, 5.0e-8, np.nan])
        ocean = np.array([True, True, False, True])
        self._patch(monkeypatch, lon, lat, flux, ocean)
        grid = iron_flux_aoi_grid("ignored", "ignored", AOI("tiny", 0.0, 1.0, 0.0, 1.0))
        assert grid.shape == (2, 2)
        assert grid[0, 0] == pytest.approx(1.0e-8)   # zero-deposition OCEAN cell retained
        assert np.isnan(grid[1, 1])                  # land cell (hFacC==0) excluded
        assert np.isnan(grid[1, 0])                  # non-finite flux excluded

    def test_land_cell_with_nonzero_flux_excluded(self, monkeypatch) -> None:
        # A land cell (ocean=False) carrying a spurious nonzero flux must NOT leak in.
        lon = np.array([0.0, 0.0])
        lat = np.array([0.0, 0.0])
        flux = np.array([9.9e-8, 3.0e-8])
        ocean = np.array([False, True])
        self._patch(monkeypatch, lon, lat, flux, ocean)
        grid = iron_flux_aoi_grid("x", "x", AOI("tiny", 0.0, 1.0, 0.0, 1.0))
        assert grid[0, 0] == pytest.approx(3.0e-8)   # only the ocean cell counts


# --------------------------------------------------------------------------- #
# load_surface_ocean_mask synthetic (pins k-outermost surface slice, no real grid)
# --------------------------------------------------------------------------- #
class TestSurfaceOceanMaskSynthetic:
    def test_reads_surface_level_k_outermost(self, tmp_path: Path) -> None:
        nk, nf, nx = 3, LLC270_NFACE, 4
        surf = np.zeros((nf, nx, nx))
        surf[:, 0, 0] = 1.0  # one ocean cell per face at the surface
        arr = np.empty((nk, nf, nx, nx))
        arr[0] = surf
        arr[1:] = 1.0 - surf  # deeper levels INVERSE -> a wrong-level read is caught
        _write_compact(tmp_path / "hFacC.data", arr)
        mask = load_surface_ocean_mask(tmp_path, nx=nx)
        assert mask.shape == (nf, nx, nx)
        np.testing.assert_array_equal(mask, surf > 0)
        assert not np.array_equal(mask, (arr[1] > 0))  # not a deeper level

    def test_short_read_raises(self, tmp_path: Path) -> None:
        (tmp_path / "hFacC.data").write_bytes(b"\x00" * 16)  # 4 floats << nface*nx*nx
        with pytest.raises(ValueError, match="short"):
            load_surface_ocean_mask(tmp_path, nx=4)


class TestCoverageMask:
    def test_finite_bins_true(self) -> None:
        grid = np.array([[1.0, np.nan], [2.0, 3.0]])
        np.testing.assert_array_equal(
            coverage_mask(grid), np.array([[True, False], [True, True]])
        )


# --------------------------------------------------------------------------- #
# Opt-in real-grid tests (grid is on disk; ironfile may not be)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not _RUN_REAL, reason="set DARWINDIFF_TEST_IRON=1 to run")
class TestRealGrid:
    def test_grid_lonlat_ranges(self) -> None:
        xc, yc = load_grid_lonlat(_REAL_GRID_DIR)
        assert xc.shape == (LLC270_NFACE, LLC270_NX, LLC270_NX)
        assert -180.0 <= float(xc.min()) and float(xc.max()) <= 180.0
        assert -90.0 <= float(yc.min()) and float(yc.max()) <= 90.0

    def test_surface_ocean_mask(self) -> None:
        ocean = load_surface_ocean_mask(_REAL_GRID_DIR)
        assert ocean.dtype == bool
        frac = float(ocean.mean())
        assert 0.4 < frac < 0.7  # ~0.577 ocean at the surface

    def test_surface_dz_is_10m(self) -> None:
        assert load_surface_dz(_REAL_GRID_DIR) == pytest.approx(10.0)

    def test_iron_aoi_grid(self) -> None:
        if not _REAL_IRON.is_file():
            pytest.skip(f"ironfile not staged at {_REAL_IRON}; see scripts/fetch/iron_forcing.sh")
        grid = iron_flux_aoi_grid(_REAL_IRON, _REAL_GRID_DIR, EQUATORIAL_PACIFIC_AOI)
        aoi = EQUATORIAL_PACIFIC_AOI
        assert grid.shape == (
            int(aoi.lat_max - aoi.lat_min + 1),
            int(aoi.lon_max - aoi.lon_min + 1),
        )
        finite = grid[np.isfinite(grid)]
        assert finite.size > 0
        assert np.all(finite >= 0.0)                     # deposition is non-negative
        assert finite.std() / finite.mean() > 0.05       # real spatial structure, not flat
        s = phi_dust_sanity(grid, dz=50.0)
        assert s["within_tol"] is True                   # areal flux in the physical range
        assert 1e-12 <= s["mean_areal_mmol_m2_s"] <= 1e-7
        # Finding: the REAL local deposition runs far BELOW the tuned box PHI_DUST
        # (dust-poor eqpac gets its iron from upwelling, not local dust) -- ratio << 1.
        assert s["ratio"] < 0.1
