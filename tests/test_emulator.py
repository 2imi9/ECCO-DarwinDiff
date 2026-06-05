"""Tests for darwindiff.emulator: Track-2 PhysicsNeMo / Earth-2 scaffold.

CPU-only, tiny grids. Verifies the FNO operator plumbing and the Earth-2
prognostic interface. Does NOT require physicsnemo (import-guarded) and never
touches a GPU -- the actual training run is a cluster-phase activity.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pytest
import torch

from darwindiff import emulator as emu
from darwindiff.emulator import FNO2d, build_emulator


def _tiny() -> emu.DarwinEmulator:
    return build_emulator(
        variables=["DFe", "POC", "PIC"], grid_shape=(16, 16), modes=4, width=8, n_layers=2
    )


def test_module_imports_without_physicsnemo() -> None:
    # The mere fact this test runs proves the import-guard works on a laptop.
    assert isinstance(emu.HAS_PHYSICSNEMO, bool)


def test_forward_shape_and_finite() -> None:
    m = _tiny()
    y = m(torch.randn(2, 3, 16, 16))
    assert y.shape == (2, 3, 16, 16)
    assert torch.isfinite(y).all()


def test_autograd_flows_to_all_params() -> None:
    m = _tiny()
    m(torch.randn(1, 3, 16, 16)).pow(2).sum().backward()
    missing = [n for n, p in m.named_parameters() if p.grad is None]
    assert not missing, f"no gradient for: {missing}"


def test_operator_couples_cells() -> None:
    """FNO mixes globally: perturbing one input cell changes other cells -- the
    opposite of the per-cell DINN. Confirms this is a genuine operator."""
    torch.manual_seed(0)
    m = _tiny()
    x = torch.randn(1, 3, 16, 16)
    y0 = m(x)
    xp = x.clone()
    xp[0, :, 8, 8] += 3.0
    diff = (y0 - m(xp)).abs()
    mask = torch.ones(16, 16, dtype=torch.bool)
    mask[8, 8] = False
    assert diff[0, :, mask].max() > 1e-6, "operator should couple distant cells"


def test_param_count_small() -> None:
    n = sum(p.numel() for p in _tiny().parameters())
    assert 0 < n < 2_000_000, f"unexpected param count {n}"


def test_input_output_coords_schema() -> None:
    m = _tiny()
    ic = m.input_coords()
    assert isinstance(ic, OrderedDict)
    assert [str(v) for v in ic["variable"]] == ["DFe", "POC", "PIC"]
    assert len(ic["lat"]) == 16 and len(ic["lon"]) == 16
    oc = m.output_coords(ic)
    assert [str(v) for v in oc["variable"]] == ["DFe", "POC", "PIC"]
    assert oc["lead_time_h"][0] == pytest.approx(m.dt_hours)


def test_step_preserves_shape_and_advances_time() -> None:
    m = _tiny()
    x = torch.randn(1, 3, 16, 16)
    x1, c1 = m.step(x, m.input_coords())
    assert x1.shape == x.shape
    assert c1["lead_time_h"][0] == pytest.approx(m.dt_hours)
    _, c2 = m.step(x1, c1)
    assert c2["lead_time_h"][0] == pytest.approx(2 * m.dt_hours)


def test_create_iterator_rollout_length_and_shapes() -> None:
    m = _tiny()
    steps = list(m.create_iterator(torch.randn(1, 3, 16, 16), m.input_coords(), n_steps=3))
    assert len(steps) == 4  # initial condition + 3 steps
    for xi, _ in steps:
        assert xi.shape == (1, 3, 16, 16)
    assert steps[-1][1]["lead_time_h"][0] == pytest.approx(3 * m.dt_hours)


def test_step_rejects_mismatched_variables() -> None:
    m = _tiny()
    bad = OrderedDict(
        [
            ("variable", np.array(["A", "B", "C"])),
            ("lat", np.linspace(-90, 90, 16)),
            ("lon", np.linspace(0, 360, 16, endpoint=False)),
        ]
    )
    with pytest.raises(ValueError):
        m.step(torch.randn(1, 3, 16, 16), bad)


def test_fno2d_standalone_shape() -> None:
    op = FNO2d(2, 5, modes1=4, modes2=4, width=6, n_layers=2)
    assert op(torch.randn(3, 2, 12, 12)).shape == (3, 5, 12, 12)
