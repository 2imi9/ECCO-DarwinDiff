"""Golden + consistency tests for the Carroll-N declarative parameter registry.

``carroll6.PARAMS`` is the single source of truth for the learnable-parameter
layout; ``PARAM_NAMES``, ``CARROLL_VALUES``, ``PARAM_BOUNDS``, ``PARAM_INDEX`` and
the ``P`` named-index namespace are all derived from it (see CONTRIBUTING.md
"Adding or removing a Carroll-N parameter").

These tests lock the refactor as a behaviour-preserving change:

1. **Golden values** — the registry-derived objects exactly equal the literal
   values the pre-registry code hardcoded (catches an accidental reorder, a typo
   in a Carroll optimum, or a drifted bound).
2. **Internal consistency** — every derived view stays the same length/order as
   ``PARAMS`` (this is the property that makes add/remove a one-entry edit).
3. **Forward equivalence** — the box step + a short integration at the Carroll
   optimum reproduce, bitwise, output captured from the pre-registry code.

The golden numbers below were captured from the hardcoded ``carroll6.py`` before
the registry refactor; they must never change for a pure maintainability edit.
"""

from __future__ import annotations

import dataclasses

import pytest
import torch

from darwindiff.carroll6 import (
    CARROLL_VALUES,
    PARAM_BOUNDS,
    PARAM_INDEX,
    PARAM_NAMES,
    PARAMS,
    P,
    Param,
    bounded_params,
    carroll6_integrate,
    carroll6_step,
)

# --- Golden constants captured from the pre-registry hardcoded carroll6.py -----

GOLDEN_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]

# Exact float32 values (``.tolist()`` widens float32 -> float64 losslessly, so
# torch.tensor(...) of these reconstructs the identical float32 tensor).
GOLDEN_CARROLL_VALUES = [
    0.928309977054596,
    6.025023253641848e-07,
    0.6609799861907959,
    0.4314799904823303,
    0.8300300240516663,
    0.04244999960064888,
]
GOLDEN_BOUNDS = [
    [0.05000000074505806, 1.0],
    [2.999999892949745e-08, 3.000000106112566e-06],
    [0.10000000149011612, 2.0],
    [0.10000000149011612, 2.0],
    [0.05000000074505806, 1.0],
    [0.004999999888241291, 1.5],
]

# Golden forward outputs at CARROLL_VALUES on the notebook-05 fixture (the
# 5-tracer model is pure +-*/ arithmetic, so these are IEEE-deterministic).
_STATE0 = [5.0e-4, 1.0, 1.0, 0.5, 0.025]  # DFe, Ps, Pl, POC, PIC
_DT = 0.25
GOLDEN_STEP1 = [
    0.0005058675305917859,
    1.0127227306365967,
    0.8983113765716553,
    0.8247522711753845,
    0.038691356778144836,
]
GOLDEN_INTEG_FINAL = [
    0.0001631446648389101,
    0.9114505052566528,
    0.0762980654835701,
    4.881889343261719,
    0.20726007223129272,
]


# --- Golden equality: derived views == pre-registry literals -------------------


def test_param_names_golden() -> None:
    assert PARAM_NAMES == GOLDEN_NAMES


def test_carroll_values_golden_bitwise() -> None:
    assert CARROLL_VALUES.dtype == torch.float32
    torch.testing.assert_close(
        CARROLL_VALUES, torch.tensor(GOLDEN_CARROLL_VALUES), rtol=0, atol=0
    )


def test_param_bounds_golden_bitwise() -> None:
    assert PARAM_BOUNDS.dtype == torch.float32
    assert PARAM_BOUNDS.shape == (len(GOLDEN_NAMES), 2)
    torch.testing.assert_close(
        PARAM_BOUNDS, torch.tensor(GOLDEN_BOUNDS), rtol=0, atol=0
    )


def test_param_index_golden() -> None:
    assert {name: i for i, name in enumerate(GOLDEN_NAMES)} == PARAM_INDEX


def test_named_index_namespace_matches_positions() -> None:
    assert (P.alpfe, P.scav_rat, P.Smallgrow, P.Biggrow, P.diatomgraz, P.R_PICPOC) == (
        0, 1, 2, 3, 4, 5,
    )


# --- Internal consistency: every derived view tracks PARAMS --------------------


def test_registry_entries_are_frozen_param_dataclasses() -> None:
    assert all(isinstance(p, Param) for p in PARAMS)
    # frozen -> assignment raises (guards against accidental in-place mutation).
    with pytest.raises(dataclasses.FrozenInstanceError):
        PARAMS[0].carroll_value = 1.0  # type: ignore[misc]


def test_derived_views_stay_in_sync_with_registry() -> None:
    """The 'one-entry change' guarantee: all views are length/order-locked to PARAMS."""
    n = len(PARAMS)
    assert [p.name for p in PARAMS] == PARAM_NAMES
    assert CARROLL_VALUES.shape == (n,)
    assert PARAM_BOUNDS.shape == (n, 2)
    assert len(PARAM_INDEX) == n
    for i, p in enumerate(PARAMS):
        assert PARAM_INDEX[p.name] == i
        assert getattr(P, p.name) == i
        # Compare through the same float32 conversion the derivation uses.
        torch.testing.assert_close(
            CARROLL_VALUES[i], torch.tensor(p.carroll_value), rtol=0, atol=0
        )
        torch.testing.assert_close(
            PARAM_BOUNDS[i], torch.tensor(p.bounds), rtol=0, atol=0
        )


def test_param_names_unique() -> None:
    assert len(set(PARAM_NAMES)) == len(PARAM_NAMES)


def test_registry_well_formed() -> None:
    for p in PARAMS:
        lo, hi = p.bounds
        assert lo < hi, f"{p.name}: bounds not ordered ({lo} >= {hi})"
        assert lo <= p.carroll_value <= hi, (
            f"{p.name}: Carroll value {p.carroll_value} outside bounds ({lo}, {hi})"
        )
        assert p.name.isidentifier(), f"{p.name!r} is not a valid identifier"


def test_all_six_params_currently_learned() -> None:
    assert [p.learned for p in PARAMS] == [True] * 6


# --- Forward equivalence: box step + integration reproduce golden output -------


def test_carroll6_step_golden_bitwise() -> None:
    state0 = torch.tensor(_STATE0)
    with torch.no_grad():
        out = carroll6_step(state0, CARROLL_VALUES, _DT)
    torch.testing.assert_close(out, torch.tensor(GOLDEN_STEP1), rtol=0, atol=0)


def test_carroll6_integration_golden_bitwise() -> None:
    state0 = torch.tensor(_STATE0)
    with torch.no_grad():
        traj = carroll6_integrate(
            state0=state0, params=CARROLL_VALUES, dt=_DT, n_steps=200,
            snapshot_indices=[40, 80, 120, 160, 200],
        )
    assert traj.shape == (5, 5)
    torch.testing.assert_close(traj[-1], torch.tensor(GOLDEN_INTEG_FINAL), rtol=0, atol=0)


def test_bounded_params_uses_registry_bounds() -> None:
    """bounded_params at the registry bounds maps -inf/+inf style extremes to lo/hi."""
    n = len(PARAMS)
    lo = bounded_params(torch.full((n,), -50.0), PARAM_BOUNDS)
    hi = bounded_params(torch.full((n,), 50.0), PARAM_BOUNDS)
    torch.testing.assert_close(lo, PARAM_BOUNDS[:, 0], rtol=1e-6, atol=1e-12)
    torch.testing.assert_close(hi, PARAM_BOUNDS[:, 1], rtol=1e-6, atol=1e-12)


# --- Cross-module: downstream consumers derive from the same registry ----------


def test_5pft_indices_derived_from_registry() -> None:
    from darwindiff import carroll6_5pft as p5

    got = (
        p5.I_ALPFE, p5.I_SCAV_RAT, p5.I_SMALLGROW,
        p5.I_BIGGROW, p5.I_DIATOMGRAZ, p5.I_R_PICPOC,
    )
    want = tuple(PARAM_INDEX[n] for n in GOLDEN_NAMES)
    assert got == want


def test_2layer_reexports_registry_indices() -> None:
    from darwindiff import carroll6_5pft_2layer as l2

    assert (l2.I_ALPFE, l2.I_SCAV_RAT, l2.I_SMALLGROW) == (0, 1, 2)
    assert (l2.I_BIGGROW, l2.I_DIATOMGRAZ, l2.I_R_PICPOC) == (3, 4, 5)


def test_gating_param_index_is_registry() -> None:
    from darwindiff import gating

    assert gating._PARAM_INDEX == PARAM_INDEX


# --------------------------------------------------------------------------- DD_ALPFE_HI
# The lever exists because `alpfe` rails at its 1.0 bound, so the precision we quote is the
# bound-to-Carroll distance rather than a measurement. These tests pin the two properties that
# make it safe to ship: it is INERT unless set, and when set it moves alpfe and nothing else.
# Each runs in a subprocess because the override is applied at import time.

def _bounds_under(env: dict[str, str] | None) -> list[list[float]]:
    import json
    import os
    import subprocess
    import sys

    child = dict(os.environ)
    child.pop("DD_ALPFE_HI", None)
    child.update(env or {})
    out = subprocess.run(
        [sys.executable, "-c",
         "import json;from darwindiff.carroll6 import PARAM_BOUNDS;"
         "print(json.dumps(PARAM_BOUNDS.tolist()))"],
        capture_output=True, text=True, env=child, check=True,
    )
    return json.loads(out.stdout)


def test_alpfe_hi_lever_is_inert_when_unset() -> None:
    """Absent the env var the registry is byte-for-byte the shipped one."""
    assert _bounds_under(None)[PARAM_INDEX["alpfe"]] == [pytest.approx(0.05), pytest.approx(1.0)]


def test_alpfe_hi_lever_widens_only_alpfe() -> None:
    base = _bounds_under(None)
    wide = _bounds_under({"DD_ALPFE_HI": "1.6"})
    i = PARAM_INDEX["alpfe"]
    assert wide[i] == [pytest.approx(0.05), pytest.approx(1.6)]
    # every other row is untouched -- the lever must not perturb the joint fit it is measured in
    for j, (b, w) in enumerate(zip(base, wide)):
        if j != i:
            assert b == w, f"row {j} moved; the lever is not isolated"


def test_alpfe_hi_lever_rejects_a_bound_below_the_floor() -> None:
    import os
    import subprocess
    import sys

    child = dict(os.environ)
    child["DD_ALPFE_HI"] = "0.01"
    out = subprocess.run(
        [sys.executable, "-c", "import darwindiff.carroll6"],
        capture_output=True, text=True, env=child, check=False,
    )
    assert out.returncode != 0
    assert "must exceed alpfe's lower bound" in out.stderr
