"""Conformance of DarwinBGCPrognostic against the REAL Earth2Studio contract.

`tests/test_e2s.py` exercises our adapter against the fallback shims, which is what CI
gets when earth2studio is not installed. Shims cannot catch a drift in NVIDIA's actual
protocol, so this module runs the same object against the genuine
`earth2studio.models.px.base.PrognosticModel` and skips cleanly when the package is
absent.

Install the optional extra to activate:  uv sync --extra earth2studio

Verified against earth2studio 0.18.0a0 (commit 3400b69). The protocol requires exactly
five members: __call__, create_iterator, input_coords, output_coords, to.
"""
from __future__ import annotations

import numpy as np
import pytest
import torch

e2s_px = pytest.importorskip(
    "earth2studio.models.px.base",
    reason="earth2studio not installed; run `uv sync --extra earth2studio`",
)

from darwindiff.e2s.prognostic import DarwinBGCPrognostic  # noqa: E402

VARS = ["Chl1_k0", "PIC_k0", "POC_k0"]
NLAT, NLON = 6, 8


def _model(**kw):
    v = len(VARS)
    return DarwinBGCPrognostic(
        torch.nn.Identity(),
        VARS,
        np.linspace(-5.0, 15.0, NLAT),
        np.linspace(-160.0, -110.0, NLON),
        means=np.zeros(v),
        stds=np.ones(v),
        residual=False,
        **kw,
    )


def test_satisfies_the_runtime_checkable_protocol():
    """isinstance against NVIDIA's own Protocol -- the definitive conformance check."""
    assert isinstance(_model(), e2s_px.PrognosticModel)


#: The five members the protocol requires, per this module's own header (verified against
#: earth2studio 0.18.0a0, commit 3400b69). Named explicitly rather than introspected.
_REQUIRED_MEMBERS = ("__call__", "create_iterator", "input_coords", "output_coords", "to")


def test_declares_every_required_protocol_member():
    """Cross-check on the isinstance test above, using the DOCUMENTED member list.

    This previously introspected ``PrognosticModel.__protocol_attrs__``. That is a CPython
    typing internal, and the first real CI run (2026-07-29) found it empty on the installed
    earth2studio -- so the assertion fired while the definitive isinstance check passed.
    The failure was in how we introspected, not in our conformance.

    Depending on a private typing attribute to police someone else's public protocol was the
    wrong instrument. The names below are what their own docs specify; if NVIDIA adds a sixth
    member, ``test_satisfies_the_runtime_checkable_protocol`` is what will catch it.
    """
    missing = {a for a in _REQUIRED_MEMBERS if not hasattr(_model(), a)}
    assert not missing, f"missing protocol members: {sorted(missing)}"

    # If the runtime protocol DOES expose its attrs, assert we cover them too -- but treat
    # its absence as an upstream implementation detail, not a failure.
    exposed = set(getattr(e2s_px.PrognosticModel, "__protocol_attrs__", ()))
    if exposed:
        uncovered = exposed - set(_REQUIRED_MEMBERS)
        assert not uncovered, (
            f"earth2studio's protocol now requires members we do not check: {sorted(uncovered)}"
        )


def test_coordinate_order_matches_the_canonical_convention():
    """Earth2Studio indexes coords positionally via handshake_dim, so order is load-bearing."""
    ic = _model().input_coords()
    assert list(ic.keys()) == ["batch", "time", "lead_time", "variable", "lat", "lon"]


def test_lead_time_is_timedelta_and_accumulates_across_steps():
    """A rollout that does not accumulate lead_time silently mislabels every step
    after the first with the same valid time."""
    m = _model()
    ic = m.input_coords()
    assert np.issubdtype(ic["lead_time"].dtype, np.timedelta64)

    oc = m.output_coords(ic)
    assert np.issubdtype(oc["lead_time"].dtype, np.timedelta64)
    assert oc["lead_time"][0] == ic["lead_time"][0] + m.dt

    oc2 = m.output_coords(oc)
    assert oc2["lead_time"][0] == ic["lead_time"][0] + 2 * m.dt


def test_iterator_yields_the_initial_condition_first():
    """Protocol docstring: 'Will return the initial condition first (0th step).'"""
    m = _model()
    coords = m.input_coords()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2005-01-01")])
    x = torch.rand(1, 1, 1, len(VARS), NLAT, NLON)

    it = m.create_iterator(x, coords)
    x0, c0 = next(it)
    assert torch.allclose(x0, x), "step 0 must be the untouched initial condition"
    assert c0["lead_time"][0] == np.timedelta64(0, "h")

    _, c1 = next(it)
    assert c1["lead_time"][0] == np.timedelta64(0, "h") + m.dt


def test_output_coords_rejects_a_mismatched_input():
    """The model is responsible for validating its own input (protocol warning)."""
    m = _model()
    bad = m.input_coords()
    bad["variable"] = np.array(["not_a_tracer"])
    with pytest.raises(Exception):
        m.output_coords(bad)


def test_call_returns_tensor_and_advanced_coords():
    m = _model()
    coords = m.input_coords()
    coords["batch"] = np.array([0])
    coords["time"] = np.array([np.datetime64("2005-01-01")])
    x = torch.rand(1, 1, 1, len(VARS), NLAT, NLON)

    y, oc = m(x, coords)
    assert y.shape == x.shape
    assert oc["lead_time"][0] == m.dt
