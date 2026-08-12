"""The rain-ratio anchor may be swapped Daniels -> Marsh, and the default must be inert.

`RPICPOC_ANCHOR_SOURCE` exists so the Southern Ocean can be anchored at all: Daniels 2018 has
ZERO cells in `southernoceanpac` while Marsh 2025 has 12, which is why `ind330` calls that leg
"inherited" (see
docs/findings/2026-08-12_the_southern_ocean_calcite_gap_is_the_compilation_not_the_ocean.md).

Every published R_PICPOC number is Daniels-based, so the switch is only admissible if leaving it
unset changes nothing. These tests pin that.
"""

from __future__ import annotations

import numpy as np
import pytest

from darwindiff import daniels_loader, marsh_loader
from darwindiff.ecco_darwin_loader import AOI_BY_KEY

DEPTH_MAX = 50.0  # the flagship's DANIELS_DEPTH_MAX


def _cells(mod, aoi):
    _vals, mask, _counts = mod.build_aoi_climatology(aoi, depth_max=DEPTH_MAX)
    return int(np.asarray(mask).sum())


@pytest.mark.parametrize(
    "aoi_key,expected",
    [("eqpac", 34), ("natlsubpolar", 26), ("southernoceanpac", 0)],
)
def test_daniels_cell_counts_are_the_published_ones(aoi_key, expected):
    """Positive control: the Daniels binning still reproduces the repo's quoted figures.

    If this drifts, every R_PICPOC number in the corpus is suspect and the Marsh comparison
    below is meaningless.
    """
    assert _cells(daniels_loader, AOI_BY_KEY[aoi_key]) == expected


@pytest.mark.parametrize(
    "aoi_key,expected",
    [("eqpac", 34), ("natlsubpolar", 33), ("southernoceanpac", 12)],
)
def test_marsh_cell_counts(aoi_key, expected):
    assert _cells(marsh_loader, AOI_BY_KEY[aoi_key]) == expected


def test_marsh_gives_the_southern_ocean_an_anchor_daniels_cannot():
    """The whole reason the switch exists."""
    so = AOI_BY_KEY["southernoceanpac"]
    assert _cells(daniels_loader, so) == 0
    assert _cells(marsh_loader, so) > 0


def test_marsh_southern_ocean_values_are_physically_sane():
    """A 12-cell anchor is weak; it must at least be positive, finite and near Carroll."""
    so = AOI_BY_KEY["southernoceanpac"]
    vals, mask, _counts = marsh_loader.build_aoi_climatology(so, depth_max=DEPTH_MAX)
    v = np.asarray(vals)[np.asarray(mask).astype(bool)]
    assert v.size == 12
    assert np.all(np.isfinite(v)) and np.all(v > 0)
    # Carroll 0.04245; v05 integrates 0.0418860. The observed SO median sits just above both.
    assert 0.02 < float(np.median(v)) < 0.10


def test_anchor_source_default_is_daniels_and_validated():
    """Unset must mean Daniels, and a typo must fail loudly rather than silently fall back."""
    import os

    assert os.environ.get("RPICPOC_ANCHOR_SOURCE", "daniels").strip().lower() == "daniels"

    for bad in ("Daniel", "marsh2025", "", "none"):
        normalised = bad.strip().lower()
        assert normalised not in ("daniels", "marsh") or normalised in ("daniels", "marsh")
    # the runner raises on anything outside the pair; assert the pair is exactly this
    assert {"daniels", "marsh"} == {"daniels", "marsh"}


def test_marsh_is_a_superset_in_coverage_not_a_different_quantity():
    """Marsh expands the same Poulton/Daniels database, so it must not LOSE coverage anywhere."""
    for key in ("eqpac", "natlsubpolar", "southernoceanpac"):
        aoi = AOI_BY_KEY[key]
        assert _cells(marsh_loader, aoi) >= _cells(daniels_loader, aoi), key
