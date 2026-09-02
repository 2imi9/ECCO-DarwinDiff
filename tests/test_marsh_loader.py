"""Tests for the Marsh et al. 2025 calcite compilation loader (darwindiff.marsh_loader).

Hermetic: parse a tiny synthetic Marsh-format .tab (PANGAEA metadata block + µmol columns +
std-dev companion columns) and check the columns are located by prefix (not the µ-unicode)
and the ratio machinery matches Daniels. Opt-in real: the eqpac/natl geomean + cell counts
from the staged file (skipped if it is not on disk).
"""
from __future__ import annotations

import numpy as np
import pytest

from darwindiff import marsh_loader as M
from darwindiff.daniels_loader import rain_ratio
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
)

_SYNTH = """/* metadata block
several lines
*/
PI\tLatitude\tLongitude\tDepth water [m]\tCaCO3 prod C [µmol/m**3/day]\tCaCO3 prod C std dev [±]\tPP C [µmol/m**3/day]\tPP C std dev [±]
Balch\t1.0\t2.0\t5.0\t20.0\t3.0\t400.0\t50.0
Balch\t3.0\t4.0\t10.0\t10.0\t1.0\t500.0\t20.0
"""


class TestMarshParse:
    def test_prefix_columns_and_ratio(self, tmp_path) -> None:
        p = tmp_path / "marsh.tab"
        p.write_text(_SYNTH, encoding="utf-8")
        pts = M.load_marsh_points(p)
        assert pts.lat.tolist() == [1.0, 3.0]
        assert pts.lon.tolist() == [2.0, 4.0]
        assert pts.depth.tolist() == [5.0, 10.0]
        # CP/PP picked from the value columns, NOT the adjacent std-dev columns
        assert pts.cp.tolist() == [20.0, 10.0]
        assert pts.pp.tolist() == [400.0, 500.0]
        # ratio is dimensionless (µmol cancels), matches CP/PP directly
        assert np.allclose(rain_ratio(pts), [20.0 / 400.0, 10.0 / 500.0])

    def test_missing_column_raises(self, tmp_path) -> None:
        p = tmp_path / "bad.tab"
        p.write_text("/*\n*/\nPI\tLatitude\tLongitude\n1\t2\t3\n", encoding="utf-8")
        with pytest.raises(KeyError):
            M.load_marsh_points(p)

    def test_missing_file_raises(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            M.load_marsh_points(tmp_path / "nope.tab")


@pytest.mark.skipif(not M.DEFAULT_MARSH_PATH.is_file(),
                    reason="Marsh 2025 .tab not staged under data/marsh/")
class TestRealMarsh:
    def test_eqpac_natl_coverage(self) -> None:
        # Marsh keeps eqpac at 34 cells but densifies natl vs Daniels' 26 (>=30).
        ev, em, _ = M.build_aoi_climatology(EQUATORIAL_PACIFIC_AOI)
        nv, nm, _ = M.build_aoi_climatology(NORTH_ATLANTIC_SUBPOLAR_AOI)
        assert ev.shape == (21, 51) and nv.shape == (16, 31)
        assert int(em.sum()) >= 30
        assert int(nm.sum()) >= 30  # denser than Daniels natl (26)
        # eqpac geomean rain ratio stays in the physical ~0.02-0.06 band
        assert 0.02 <= float(np.exp(np.log(ev[em]).mean())) <= 0.06
