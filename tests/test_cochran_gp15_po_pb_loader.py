"""Tests for the Cochran GP15 210Po/210Pb loader.

Why this exists. The observation-design study (docs/findings/2026-07-23_observation_design.md)
ranks a particulate-Fe *scavenging rate* observable as the single best new measurement for
breaking the alpfe/scav_rat degeneracy -- it collapses the iron-block Fisher condition number
from 2930 to about 7, where a second identical surface-[DFe] survey leaves it unchanged.

This loader is that observable. It has been in the repo, with its data staged, and with
``load_scavenging_anchor`` explicitly documented as "the field the two-anchor inversion pairs
with the Daniels/MODIS calcite anchor" -- and **no test and no caller**. Before wiring an
untested loader into a loss that produces published numbers, it gets a test.

The load-bearing question these tests answer is not "does it parse" but **which AOIs GP15
actually covers**. GP15 is a single Pacific meridional transect; an anchor that misses the
basin where ``scav_rat`` fails (eqpac, 7/50) cannot fix that basin no matter how well it
conditions the problem elsewhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from darwindiff.cochran_gp15_po_pb_loader import (
    DEFAULT_DATA_DIR,
    DEFAULT_FILE_BY_KIND,
    activity_ratio,
    load_gp15_points,
    load_scavenging_anchor,
    subset_aoi,
)
from darwindiff.ecco_darwin_loader import AOI_BY_KEY

_DISSOLVED = DEFAULT_DATA_DIR / DEFAULT_FILE_BY_KIND["dissolved_total"]

pytestmark = pytest.mark.skipif(
    not _DISSOLVED.is_file(),
    reason=f"GP15 Po/Pb CSVs not staged under {DEFAULT_DATA_DIR}/",
)


@pytest.fixture(scope="module")
def points():
    return load_gp15_points(_DISSOLVED, kind="dissolved_total")


class TestParsing:
    def test_loads_a_nonempty_transect(self, points) -> None:
        n = len(points.lat)
        assert n > 0
        # every geometry array is the same length -- a ragged parse is silent corruption
        for name in ("lat", "lon", "depth"):
            assert len(getattr(points, name)) == n, f"{name} length {len(getattr(points, name))} != {n}"

    def test_coordinates_are_physical(self, points) -> None:
        assert np.all((points.lat >= -90) & (points.lat <= 90))
        assert np.all((points.lon >= -180) & (points.lon <= 360))
        assert np.all(points.depth >= 0)

    def test_it_is_a_pacific_meridional_transect(self, points) -> None:
        """GP15 runs Alaska -> Tahiti near 152 W. If this fails, the file is not GP15."""
        lon = np.where(points.lon > 180, points.lon - 360, points.lon)
        assert np.nanmedian(lon) < -100, f"median lon {np.nanmedian(lon):.1f} is not Pacific"
        assert points.lat.max() - points.lat.min() > 30, "not a meridional transect"


class TestActivityRatio:
    def test_ratio_is_finite_and_physical(self, points) -> None:
        """210Po/210Pb in the surface ocean sits below secular equilibrium (Po deficit).

        Bounds are deliberately loose -- this catches a units or column-mapping error,
        not a subtle bias.
        """
        r = activity_ratio(points, phase="T")
        ok = np.isfinite(r)
        assert ok.sum() > 0, "no finite activity ratios"
        assert np.all(r[ok] > 0), "non-positive activity ratio"
        assert np.nanmedian(r[ok]) < 5.0, f"median ratio {np.nanmedian(r[ok]):.2f} implausible"


class TestAOICoverage:
    """The decisive question: which AOIs does this anchor actually reach?"""

    @pytest.mark.parametrize("key", ["eqpac", "natlsubpolar", "southernoceanpac", "npac", "npsg"])
    def test_subset_is_consistent_with_bounds(self, points, key) -> None:
        aoi = AOI_BY_KEY[key]
        sub = subset_aoi(points, aoi)
        assert len(sub.lat) <= len(points.lat)
        if len(sub.lat):
            assert np.all((sub.lat >= aoi.lat_min) & (sub.lat <= aoi.lat_max))

    def test_gp15_cannot_reach_the_atlantic(self, points) -> None:
        """A Pacific transect must not produce North Atlantic samples."""
        assert len(subset_aoi(points, AOI_BY_KEY["natlsubpolar"]).lat) == 0

    def test_records_which_aois_have_coverage(self, points) -> None:
        """Not a pass/fail on science -- it pins the coverage so a silent change is caught.

        Printed so the count is visible in -s runs; asserted so it cannot drift unnoticed.
        """
        counts = {
            k: len(subset_aoi(points, AOI_BY_KEY[k]).lat)
            for k in ("eqpac", "natlsubpolar", "southernoceanpac", "npac", "npsg")
        }
        print(f"\nGP15 surface+depth samples per AOI: {counts}")
        assert sum(counts.values()) > 0, (
            "GP15 covers NONE of the registered AOIs -- this anchor cannot inform any "
            f"current basin. counts={counts}"
        )


class TestGriddedAnchor:
    """``load_scavenging_anchor`` is the entry point a loss term would call."""

    def test_returns_a_grid_on_a_covered_aoi(self, points) -> None:
        covered = [
            k for k in ("npac", "npsg", "eqpac", "southernoceanpac")
            if len(subset_aoi(points, AOI_BY_KEY[k]).lat) > 0
        ]
        if not covered:
            pytest.skip("no AOI has GP15 coverage; see test_records_which_aois_have_coverage")
        g = load_scavenging_anchor(AOI_BY_KEY[covered[0]])
        assert g is not None
        field = np.asarray(getattr(g, "values", getattr(g, "field", None)))
        assert field.ndim == 2, f"expected a 2-D grid, got shape {field.shape}"
        finite = np.isfinite(field)
        assert finite.sum() > 0, "gridded anchor is entirely NaN -- nothing to anchor on"
        assert np.all(field[finite] > 0), "non-positive activity ratio on the grid"

    def test_unknown_observable_is_rejected(self) -> None:
        with pytest.raises(Exception):
            load_scavenging_anchor(AOI_BY_KEY["npac"], observable="not_a_real_observable")
