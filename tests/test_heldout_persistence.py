"""The held-out real-data score must reach an artifact, not just stdout.

Why this exists. README states that the 0-D box "does not produce held-out spatial skill on real
data". That claim is computed by `scripts/run_v3.0_joint_multi_aoi.py` -- and, until 2026-07-29,
only *printed*. No committed artifact carried it, so the README had to footnote it as
reported-but-unarchived, and the one number separating a consistency check from a cross-validated
claim (#163) lived in a terminal scrollback.

These guards keep it in the run JSON.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_v3.0_joint_multi_aoi.py"

pytestmark = pytest.mark.skipif(not _RUNNER.is_file(), reason=f"{_RUNNER} not present")


@pytest.fixture(scope="module")
def src() -> str:
    return _RUNNER.read_text(encoding="utf-8")


def test_the_result_dict_carries_the_heldout_block(src: str) -> None:
    for key in ('"heldout_geotraces_iron"', '"geotraces_holdout_frac"'):
        assert key in src, (
            f"{key} missing from the run result -- the held-out score would be printed and "
            "dropped again, and README's claim has no artifact behind it."
        )


def test_the_score_is_indexed_per_seed(src: str) -> None:
    """`_r2` is computed for all seeds at once, before the per-seed loop.

    Writing the whole vector into every seed's JSON, or writing seed 0's value into all of
    them, would silently make every seed look identical.
    """
    assert '_v["r2_per_seed"][seed_idx]' in src, (
        "the per-seed R2 must be indexed by seed_idx when building each seed's result"
    )
    assert '_v["rel_err_per_seed"][seed_idx]' in src


def test_non_finite_scores_are_sanitised(src: str) -> None:
    """The writer uses `json.dump(..., allow_nan=False)`, which raises on NaN/inf.

    One degenerate AOI must not cost the whole run its JSON.
    """
    assert "allow_nan=False" in src, "writer changed; re-check the sanitisation requirement"
    assert "_finite_or_none" in src, (
        "non-finite held-out scores must be coerced to None before json.dump(allow_nan=False)"
    )


def test_holdout_defaults_to_off(src: str) -> None:
    """Enabling it removes real observations from training, so it must never be the default."""
    assert 'os.environ.get("GEOTRACES_HOLDOUT_FRAC", "0")' in src, (
        "GEOTRACES_HOLDOUT_FRAC must default to 0 -- a nonzero default would silently drop "
        "iron observations out of every run's training set."
    )
