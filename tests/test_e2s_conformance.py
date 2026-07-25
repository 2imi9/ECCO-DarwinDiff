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


def test_declares_every_required_protocol_member():
    required = set(getattr(e2s_px.PrognosticModel, "__protocol_attrs__", ()))
    assert required, "protocol exposes no __protocol_attrs__; earth2studio API changed"
    missing = {a for a in required if not hasattr(_model(), a)}
    assert not missing, f"missing protocol members: {sorted(missing)}"


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
