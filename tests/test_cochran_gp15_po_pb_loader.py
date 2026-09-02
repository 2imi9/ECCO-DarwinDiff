"""Tests for the Cochran GP15 210Po/210Pb loader.

Why this exists. The observation-design study (docs/findings/2026-07-23_observation_design.md)
ranks a particulate-Fe *scavenging rate* observable as the single best new measurement for
breaking the alpfe/scav_rat degeneracy -- it collapses the iron-block Fisher condition number
from 2930 to about 7, where a second identical surface-[DFe] survey leaves it unchanged.

This loader is that observable. It has been in the repo, with its data staged, and with
``load_scavenging_anchor`` explicitly documented as "the field the two-anchor inversion pairs
with the Daniels/MODIS calcite anchor" -- and **no test and no caller**. Before wiring an
untested loader into a loss that produces published numbers, it gets a test.

The load-bearing question these tests answer is not "does it parse" but **which AOIs the
STAGED DATA actually covers**.

    CORRECTED 2026-07-28. An earlier version of this docstring, and commit 1e4b9ac, said
    "GP15 covers NONE of the three flagship AOIs" and read that as an observing-system
    limit. That was wrong. Both staged CSVs are **Leg 1 only** (Seattle -> Hilo), spanning
    19.68 N to 56.06 N -- the filename says `leg1_`. GP15 as a campaign also has **Leg 2**
    (Hilo -> Papeete, RR1815, Oct-Nov 2018), which crosses the equator, and its dissolved
    + total 210Po/210Pb is published at BCO-DMO dataset 883797,
    DOI 10.26008/1912/bco-dmo.883797.1.

    So the top-ranked rate observable is NOT unavailable in the equatorial Pacific. We
    simply have not staged the leg that goes there. That is a data-staging gap, not a
    property of the observing system, and it is fixable by a download.

The coverage test below therefore pins what the STAGED FILES contain, and says nothing
about what GP15 as a whole measured.
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
            got = len(getattr(points, name))
            assert got == n, f"{name} length {got} != {n}"

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
        """Pins what the STAGED files cover. Not a claim about GP15 as a campaign.

        Leg 1 spans 19.68 N to 56.06 N, so eqpac/natl/sopac are all empty here. Leg 2
        (BCO-DMO 883797) crosses the equator and is not staged -- see the module docstring.
        If Leg 2 is downloaded, this test SHOULD start seeing eqpac coverage, and that is
        the signal to re-run the observation-design ranking with it included.
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


# ---------------------------------------------------------------------------
# Leg 2 — downloaded 2026-07-28 from BCO-DMO 883797 (leg2.csv, 10.76 KB),
# DOI 10.26008/1912/bco-dmo.883797.1. This is the leg that crosses the equator.
# ---------------------------------------------------------------------------

_LEG2 = DEFAULT_DATA_DIR / "leg2_dissolved_total_po_pb.csv"


@pytest.mark.skipif(not _LEG2.is_file(), reason="GP15 Leg 2 not staged")
class TestLeg2ReachesTheEquator:
    """Leg 2 is what makes the equatorial-Pacific anchor possible at all."""

    @pytest.fixture(scope="class")
    def leg2(self):
        return load_gp15_points(_LEG2, kind="dissolved_total")

    def test_it_spans_the_equator(self, leg2) -> None:
        assert leg2.lat.min() < 0 < leg2.lat.max(), (
            f"Leg 2 should cross the equator, got {leg2.lat.min():.2f}..{leg2.lat.max():.2f}"
        )

    def test_it_covers_eqpac(self, leg2) -> None:
        """The correction to commit 1e4b9ac, pinned."""
        n = len(subset_aoi(leg2, AOI_BY_KEY["eqpac"]).lat)
        assert n > 0, "Leg 2 must reach eqpac -- that is the whole point of staging it"
        assert n >= 50, f"expected ~67 eqpac samples, got {n}"

    def test_the_dissolved_phase_is_the_usable_one(self, leg2) -> None:
        """Practical trap for whoever wires this into a loss.

        In eqpac the TOTAL phase has ~3 finite samples, all at the surface, while the
        DISSOLVED phase has ~64 spanning 20-5340 m. ``load_scavenging_anchor`` defaults to
        phase="T", which is very nearly empty here -- so the default silently yields an
        almost-empty anchor in the one basin we care about.
        """
        e = subset_aoi(leg2, AOI_BY_KEY["eqpac"])
        n_t = int(np.isfinite(e.activity["Po_210_T"]).sum())
        n_d = int(np.isfinite(e.activity["Po_210_D"]).sum())
        assert n_d > 10 * n_t, f"expected D to dominate T in eqpac, got D={n_d} T={n_t}"

    def test_dissolved_phase_resolves_depth(self, leg2) -> None:
        """Depth structure is the informative part: the observation-design study found a
        subsurface concentration breaks the alpfe/scav_rat symmetry because alpfe injects
        iron only at the surface."""
        e = subset_aoi(leg2, AOI_BY_KEY["eqpac"])
        d = e.depth[np.isfinite(e.activity["Po_210_D"])]
        assert d.max() > 1000, f"expected a full-depth profile, max depth {d.max():.0f} m"
        assert len(np.unique(np.round(d / 500))) >= 4, "too few distinct depth bands"
