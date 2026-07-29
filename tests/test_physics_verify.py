"""Tests for the physics validator behind the project's headline emulator claim.

Why this exists. `scripts/physics_verify.py` produces the result the CCAI paper leads
with -- the emulator scores +0.43 while emitting 4.51% negative dissolved iron against a
v05 control at 1.89e-07. That number is the argument that skill metrics are blind to
physical invalidity. It had **no test**.

`physics_report` is a pure function over numpy arrays, so it needs no cube, no checkpoint
and no GPU. There was never a good reason for it to be uncovered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

physics_verify = pytest.importorskip("physics_verify", reason="scripts/ not importable")
physics_report = physics_verify.physics_report

NAMES = ["DIC_k0", "ALK_k0", "FeT_k0", "Chl1_k0"]
H, W = 4, 5


def _state(vals: dict[str, float], shape=(2, len(NAMES), H, W)) -> np.ndarray:
    """Uniform field per tracer, in physical units."""
    s = np.zeros(shape, dtype=np.float64)
    for i, n in enumerate(NAMES):
        s[:, i] = vals[n.split("_k")[0]]
    return s


@pytest.fixture
def mask():
    m = np.ones((H, W), dtype=bool)
    m[0, 0] = False          # one land cell, to prove masking is applied
    return m


class TestPositivity:
    def test_clean_field_reports_zero_negative(self, mask):
        r = physics_report(_state({"DIC": 2000, "ALK": 2300, "FeT": 1e-4, "Chl1": 0.1}),
                           mask, NAMES, "clean")
        for t in ("DIC", "ALK", "FeT", "Chl1"):
            assert r["A_positivity"][t]["neg_fraction"] == 0.0

    def test_it_detects_a_known_negative_fraction(self, mask):
        """The load-bearing behaviour: neg_fraction must be the true proportion."""
        s = _state({"DIC": 2000, "ALK": 2300, "FeT": 1e-4, "Chl1": 0.1})
        fe = NAMES.index("FeT_k0")
        n_ocean = int(mask.sum())
        s[0, fe][mask] = np.where(np.arange(n_ocean) < n_ocean // 2, -1e-5, 1e-4)
        r = physics_report(s, mask, NAMES, "seeded")
        # half of one batch member of two => 0.25 of all ocean samples
        assert r["A_positivity"]["FeT"]["neg_fraction"] == pytest.approx(0.25, abs=0.02)
        assert r["A_positivity"]["FeT"]["min"] < 0

    def test_land_cells_are_excluded(self, mask):
        """A negative value under land must not count -- otherwise the headline
        number would be an artifact of the fill value, not the model."""
        s = _state({"DIC": 2000, "ALK": 2300, "FeT": 1e-4, "Chl1": 0.1})
        s[:, NAMES.index("FeT_k0"), 0, 0] = -999.0        # the masked-off cell
        r = physics_report(s, mask, NAMES, "land")
        assert r["A_positivity"]["FeT"]["neg_fraction"] == 0.0


class TestAlkDicBand:
    def test_physical_ratio_is_in_band(self, mask):
        r = physics_report(_state({"DIC": 2000, "ALK": 2300, "FeT": 1e-4, "Chl1": 0.1}),
                           mask, NAMES, "ok")
        b = r["B_alk_dic_ratio"]
        assert b["median"] == pytest.approx(1.15, abs=1e-6)
        assert b["frac_in_physical_band_1.0_1.25"] == 1.0

    def test_unphysical_ratio_is_caught(self, mask):
        r = physics_report(_state({"DIC": 2000, "ALK": 4000, "FeT": 1e-4, "Chl1": 0.1}),
                           mask, NAMES, "bad")
        assert r["B_alk_dic_ratio"]["frac_in_physical_band_1.0_1.25"] == 0.0


class TestCommittedArtifactIsConsistent:
    """Pin the published contrast so a regenerated artifact cannot silently flip it."""

    ART = REPO / "docs" / "findings" / "track2_runs" / "physics_3d.json"

    @pytest.mark.skipif(not ART.is_file(), reason="physics_3d.json not committed")
    def test_emulator_invents_iron_the_control_does_not(self):
        d = json.loads(self.ART.read_text(encoding="utf-8"))
        ctrl = d["v05_truth"]["A_positivity"]["FeT"]["neg_fraction"]
        emu = d["emulator"]["A_positivity"]["FeT"]["neg_fraction"]
        assert ctrl < 1e-6, f"control FeT should be numerically zero, got {ctrl}"
        assert emu > 0.04, f"emulator FeT neg-fraction should be ~4.5%, got {emu}"
        # the claim is a CONTRAST; a run where both are bad proves nothing
        assert emu > ctrl * 1000
