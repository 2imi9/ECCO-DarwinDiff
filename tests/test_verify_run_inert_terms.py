"""The gate must reject a run that declares a loss term it never actually applied.

Why this exists. On 2026-07-29 a holdout run was launched with `DANIELS_RPICPOC_W=1` -- the real
calcite anchor the whole `R_PICPOC` result rests on -- with the PANGAEA compilation unstaged. The
runner printed a `[warn]`, skipped the term, and trained anyway. The run JSON recorded
`"daniels_rpicpoc_w": 1.0` alongside `"n_daniels_cells_per_aoi": {..all zero..}`, and
`verify_run.py` returned **exit 0, VERIFIED**.

`R_PICPOC` came out at 0.20-0.26x Carroll -- the anchor-off signature -- and would have been read
as a flagship number. The evidence was in the artifact the whole time; nothing read the two keys
together.

See `docs/findings/2026-07-29_inert_anchor_passes_the_gate.md`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_VERIFY = Path(__file__).resolve().parents[1] / "scripts" / "verify_run.py"

pytestmark = pytest.mark.skipif(not _VERIFY.is_file(), reason=f"{_VERIFY} not present")


@pytest.fixture(scope="module")
def vr():
    spec = importlib.util.spec_from_file_location("verify_run_under_test", _VERIFY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")


def _zero():
    return {k: 0 for k in AOIS}


def _covered():
    return {"eqpac": 34, "natlsubpolar": 26, "southernoceanpac": 0}


class TestInertTermDetection:
    def test_the_exact_regression_is_caught(self, vr) -> None:
        """The literal shape of the 2026-07-29 run JSON."""
        bad = vr.inert_terms(
            {"daniels_rpicpoc_w": 1.0, "n_daniels_cells_per_aoi": _zero()}
        )
        assert len(bad) == 1
        assert "daniels_rpicpoc_w" in bad[0]
        assert "SKIPPED" in bad[0]

    def test_a_term_with_real_coverage_is_not_flagged(self, vr) -> None:
        """The genuine flagship: Daniels cells in 2 of 3 AOIs. Must stay clean.

        Note `southernoceanpac` is legitimately 0 there -- the guard fires only when a term is
        empty in EVERY AOI, so partial coverage must not trip it.
        """
        assert vr.inert_terms(
            {"daniels_rpicpoc_w": 1.0, "n_daniels_cells_per_aoi": _covered()}
        ) == []

    def test_zero_weight_with_zero_cells_is_normal(self, vr) -> None:
        """The term is simply off. Not a discrepancy."""
        assert vr.inert_terms(
            {"daniels_rpicpoc_w": 0.0, "n_daniels_cells_per_aoi": _zero()}
        ) == []

    def test_zero_weight_with_populated_cells_is_normal(self, vr) -> None:
        """Cell counts are computed whether or not the term is used -- this is the common case
        and the reason the check has to be one-directional."""
        assert vr.inert_terms(
            {"pic_abs_w": 0.0, "n_pic_abs_cells_per_aoi": {"eqpac": 1071}}
        ) == []

    def test_every_mapped_term_is_checked_not_just_daniels(self, vr) -> None:
        """The bug was general; the fix must be too."""
        for w_key, n_key in vr._TERM_CELL_KEYS.items():
            out = vr.inert_terms({w_key: 2.5, n_key: _zero()})
            assert len(out) == 1, f"{w_key} -> {n_key} not detected"
            assert w_key in out[0]

    def test_iron_ablation_arms_declare_honestly(self, vr) -> None:
        """The scav_rat mechanism split turns one iron term off and leaves the other on.

        Both arms must pass clean, because a zero weight is an honest declaration -- and the
        surviving term must still be certified as live from the artifact rather than from a
        stdout line, which is why the counts are recorded per AOI at all.
        """
        so = {"southernoceanpac": 13}
        sub = {"southernoceanpac": 14}
        # surface-only ablation
        assert vr.inert_terms({
            "geotraces_w": 1.0, "n_geo_surf_cells_per_aoi": so,
            "geotraces_sub_w": 0.0, "n_geo_sub_cells_per_aoi": sub,
        }) == []
        # subsurface-only ablation
        assert vr.inert_terms({
            "geotraces_w": 0.0, "n_geo_surf_cells_per_aoi": so,
            "geotraces_sub_w": 1.0, "n_geo_sub_cells_per_aoi": sub,
        }) == []

    def test_iron_term_declared_on_an_aoi_with_no_iron_is_caught(self, vr) -> None:
        """The gap this closes: the whole scav_rat claim rests on GEOTRACES being live, and
        until now nothing compared the iron weights against their cell counts."""
        out = vr.inert_terms({
            "geotraces_sub_w": 1.0, "n_geo_sub_cells_per_aoi": _zero(),
        })
        assert len(out) == 1
        assert "geotraces_sub_w" in out[0]

    def test_multiple_inert_terms_all_reported(self, vr) -> None:
        out = vr.inert_terms({
            "daniels_rpicpoc_w": 1.0, "n_daniels_cells_per_aoi": _zero(),
            "posi_w": 2.0, "n_posi_cells_per_aoi": _zero(),
        })
        assert len(out) == 2

    @pytest.mark.parametrize("missing", [
        {"daniels_rpicpoc_w": 1.0},                        # no count key at all
        {"n_daniels_cells_per_aoi": _zero()},              # no weight key
        {"daniels_rpicpoc_w": 1.0, "n_daniels_cells_per_aoi": {}},
        {"daniels_rpicpoc_w": None, "n_daniels_cells_per_aoi": _zero()},
    ])
    def test_missing_or_malformed_keys_do_not_crash(self, vr, missing) -> None:
        """Older artifacts predate some keys. Absence must be silent, not an exception."""
        assert vr.inert_terms(missing) == []

    def test_bool_weight_is_not_treated_as_positive(self, vr) -> None:
        """`True > 0` in Python. A bool here means a malformed artifact, not a weight of 1."""
        assert vr.inert_terms(
            {"daniels_rpicpoc_w": True, "n_daniels_cells_per_aoi": _zero()}
        ) == []


class TestWiredIntoTheVerdict:
    def test_inert_terms_is_called_by_verify_seed(self) -> None:
        """A pure function nothing calls would guard nothing."""
        src = _VERIFY.read_text(encoding="utf-8")
        body = src.split("def verify_seed", 1)[1]
        assert "inert_terms(d)" in body, (
            "verify_seed must call inert_terms(d) and extend its discrepancy list -- "
            "otherwise the check exists but never affects the exit code."
        )

    def test_discrepancies_map_to_a_nonzero_exit(self, vr) -> None:
        """An inert term must land in the severity band that makes the gate fail."""
        assert vr.SEVERITY["DISCREPANCY"] != 0
