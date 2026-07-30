"""Guards on which loss targets are *observations* and which are Darwin's own output.

Why this exists. The observations-only accounting
(`docs/research_notes/2026-07-29_observations_only_scope.md`) classifies all 28 loss terms in
`scripts/run_v3.0_joint_multi_aoi.py` as model-target (D) or real-observation (R), and the
headline result -- dropping the Darwin target keeps 2 of 4 observables -- depends entirely on
that split being right.

One target is named to defeat exactly that audit: the dict key ``"co2_flux_obs"`` is assigned
from Darwin's own ``CO2_flux`` diagnostic, not from any observation. Anyone classifying the
loss by variable name misreads it, and misreads term 26 (``F_CO2_ABS_W``) with it.

The key cannot simply be renamed: it is a ``torch.save`` cache key with no version field, and
the read happens outside the cache-rebuild guard, so a rename would raise ``KeyError`` against
every cache already on disk instead of triggering a rebuild. The fix is therefore a comment at
the definition plus ``co2_flux_darwin`` locals -- and these tests, which keep both in place and
catch the next Darwin target that arrives wearing an ``_obs`` name.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "run_v3.0_joint_multi_aoi.py"

pytestmark = pytest.mark.skipif(not _RUNNER.is_file(), reason=f"{_RUNNER} not present")


@pytest.fixture(scope="module")
def src() -> str:
    return _RUNNER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lines(src: str) -> list[str]:
    return src.splitlines()


def test_no_local_variable_is_named_co2_flux_obs(src: str) -> None:
    """The misleading spelling survives *only* as the cache key, never as a readable name."""
    bare = re.findall(r'(?<!")\bco2_flux_obs\b(?!")', src)
    assert not bare, (
        f"{len(bare)} local use(s) of `co2_flux_obs` -- this name says the target is an "
        "observation when it is Darwin's own CO2_flux diagnostic. Use `co2_flux_darwin`; the "
        'quoted key "co2_flux_obs" stays only because it is a cache key.'
    )


def test_the_cache_key_still_carries_its_warning(lines: list[str]) -> None:
    """Each assignment of the key must be preceded by the 'NOT an observation' note.

    If the comment is dropped, the trap is live again and the next audit misclassifies it.
    """
    sites = [i for i, ln in enumerate(lines) if '"co2_flux_obs":' in ln]
    assert sites, 'no `"co2_flux_obs":` assignment found -- did the key get renamed?'
    for i in sites:
        window = "\n".join(lines[max(0, i - 8):i])
        assert "NOT an observation" in window, (
            f"{_RUNNER.name}:{i + 1} assigns the co2_flux_obs cache key with no warning comment "
            "within the preceding 8 lines. The name claims an observation; the source is Darwin."
        )


def test_no_new_darwin_target_arrives_wearing_an_obs_name(src: str) -> None:
    """Forward guard on the whole target-builder, not just the one known offender.

    Both builders read Darwin fields -- `aligned(...)` (native) and `ds_avg_local[...]`
    (binned). Every key assigned from those is model output by construction, so any *new* one
    ending in `_obs` is a fresh instance of the same trap and should be caught when it lands,
    not during the next audit.
    """
    darwin_keys = set(
        re.findall(r'"(\w+)":\s*(?:aligned\(|ds_avg_local\[)', src)
    )
    assert darwin_keys, "found no Darwin-sourced target keys -- the builder shape changed"

    misnamed = {k for k in darwin_keys if k.endswith("_obs")}
    assert misnamed == {"co2_flux_obs"}, (
        f"Darwin-sourced targets whose names claim to be observations: {sorted(misnamed)}. "
        "Only the grandfathered cache key `co2_flux_obs` is allowed. A target read from "
        "`aligned(...)` or `ds_avg_local[...]` is ECCO-Darwin model output, so an `_obs` "
        "suffix will get it counted on the wrong side of the observations-only tally in "
        "docs/research_notes/2026-07-29_observations_only_scope.md."
    )
