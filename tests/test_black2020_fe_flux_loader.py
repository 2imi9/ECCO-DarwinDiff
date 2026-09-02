"""Tests for the Black et al. (2020) upper-ocean Fe export loader, and for whether it can
anchor anything.

Why this exists. `black2020_fe_flux_loader` has sat in the repo as the designated SINK anchor
for `scav_rat`, documented as the partner that -- with a source anchor -- lifts the rank-1
(alpfe <-> scav_rat) degeneracy. It had **zero importers and zero tests**. Before wiring an
untested loader into a loss that produces published numbers, it gets a test.

The load-bearing question is not "does it parse". It is **whether the observable it carries can
see `scav_rat` at all**, and the answer, established here in arithmetic that needs no fit, is no:

  - COVERAGE. Of 20 georeferenced programs, the three flagship AOIs hold ONE between them
    (natlsubpolar, GA01 GEOVIDE, a `transect` row whose single representative coordinate the
    loader's own docstring warns "badly under-represents" the program). eqpac and
    southernoceanpac hold zero.
  - LEVERAGE. The quantity Black measures is TOTAL upper-ocean Fe export. In a 0-D box at
    steady state the total iron leaving the surface layer equals the iron entering it, so that
    total is `alpfe * PHI_DUST` and is INDEPENDENT of `scav_rat` by mass conservation. The
    invariant is pinned below. It is a source anchor wearing a sink label.

Both facts are design-time. Neither is fixed by more coverage or more optimisation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from darwindiff.black2020_fe_flux_loader import (
    DEFAULT_BLACK_PATH,
    UMOL_PER_DAY_TO_MMOL_PER_YR,
    fe_export_province,
    load_black_points,
    subset_aoi,
)
from darwindiff.ecco_darwin_loader import AOI_BY_KEY

pytestmark = pytest.mark.skipif(
    not DEFAULT_BLACK_PATH.is_file(),
    reason=f"Black 2020 Table 1 CSV not staged at {DEFAULT_BLACK_PATH}",
)

FLAGSHIP_AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")


@pytest.fixture(scope="module")
def points():
    return load_black_points()


class TestParsing:
    def test_loads_the_twenty_table_one_programs(self, points):
        assert len(points.lat) == 20
        for name in ("lon", "fe_export", "fe_export_sigma", "n", "method", "coord_kind"):
            assert len(getattr(points, name)) == 20

    def test_point_estimate_is_the_geometric_mean_of_the_province_range(self, points):
        """Fe export is log-normal across orders of magnitude, so the midpoint would be wrong."""
        expect = np.sqrt(points.fe_export_min * points.fe_export_max)
        np.testing.assert_allclose(points.fe_export, expect, rtol=1e-12)

    def test_sigma_is_the_half_range(self, points):
        expect = (points.fe_export_max - points.fe_export_min) / 2.0
        np.testing.assert_allclose(points.fe_export_sigma, expect, rtol=1e-12)

    def test_unit_conversion_matches_the_documented_constant(self):
        assert pytest.approx(1.0e-3 * 365.25) == UMOL_PER_DAY_TO_MMOL_PER_YR

    def test_coordinates_are_in_the_minus180_convention(self, points):
        assert points.lon.min() >= -180.0 and points.lon.max() <= 180.0
        assert points.lat.min() >= -90.0 and points.lat.max() <= 90.0


class TestCoverage:
    """What the staged table actually reaches. These numbers gate every wiring proposal."""

    @pytest.mark.parametrize(
        "key,expected", [("eqpac", 0), ("natlsubpolar", 1), ("southernoceanpac", 0)])
    def test_flagship_aoi_counts(self, points, key, expected):
        assert len(subset_aoi(points, AOI_BY_KEY[key]).lat) == expected

    def test_the_three_flagship_aois_hold_one_program_between_them(self, points):
        total = sum(len(subset_aoi(points, AOI_BY_KEY[k]).lat) for k in FLAGSHIP_AOIS)
        assert total == 1, "a one-program anchor cannot carry a three-basin result"

    def test_the_one_covered_program_is_a_transect_row(self, points):
        """The loader's own docstring: a single point 'badly under-represents these'."""
        sub = subset_aoi(points, AOI_BY_KEY["natlsubpolar"])
        assert sub.coord_kind[0] == "transect"

    def test_uncovered_provinces_return_nan_rather_than_a_silent_zero(self):
        value, sigma, n = fe_export_province(AOI_BY_KEY["eqpac"])
        assert n == 0
        assert math.isnan(value) and math.isnan(sigma)

    def test_the_covered_province_sigma_exceeds_its_own_value(self):
        """n=1 leaves no between-program scatter, so the 1-sigma is a bounding statement."""
        value, sigma, n = fe_export_province(AOI_BY_KEY["natlsubpolar"])
        assert n == 1
        assert sigma > value, f"sigma/value = {sigma / value:.2f}"


class TestLeverage:
    """The structural half: what a bulk Fe-export anchor can and cannot constrain."""

    @staticmethod
    def _steady_total(scav_multiplier: float) -> float:
        """Total Fe leaving the box per year, integrated to steady state."""
        from darwindiff import carroll6 as C
        from darwindiff.carroll6 import PARAMS, P

        params = torch.tensor([p.carroll_value for p in PARAMS], dtype=torch.float64)
        params[P.scav_rat] = params[P.scav_rat] * scav_multiplier
        s = torch.tensor([5.0e-4, 0.1, 0.1, 0.05, 0.005], dtype=torch.float64)
        for _ in range(40000):
            s = torch.clamp(s + 0.25 * C.carroll6_tendency(s, params), min=1e-12)
        DFe, Ps, Pl, POC = s[0], s[1], s[2], s[3]
        scav = params[P.scav_rat] * 86400.0 * DFe * POC
        f_fe = DFe / (DFe + C.K_FE)
        upt = C.Q_FE * (
            params[P.Smallgrow] * f_fe * C.LIGHT * Ps + params[P.Biggrow] * f_fe * C.LIGHT * Pl
        )
        return float(scav + upt)

    def test_total_export_is_independent_of_scav_rat_at_steady_state(self):
        """Mass conservation, and the reason this anchor cannot grade `scav_rat`.

        What comes in must go out. `scav_rat` sets HOW iron leaves (scavenged versus biogenic),
        never HOW MUCH. So the quantity Black measures is pinned by the source term and a
        16x sweep of `scav_rat` moves it by nothing.
        """
        lo = self._steady_total(0.25)
        hi = self._steady_total(4.0)
        assert lo == pytest.approx(hi, rel=1e-6)

    def test_total_export_at_steady_state_equals_the_dust_source(self):
        from darwindiff import carroll6 as C
        from darwindiff.carroll6 import PARAMS, P

        params = [p.carroll_value for p in PARAMS]
        source = params[P.alpfe] * C.PHI_DUST
        assert self._steady_total(1.0) == pytest.approx(source, rel=1e-6)
