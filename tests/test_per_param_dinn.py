"""The missing rung: a parameterisation that does not share representation across parameters.

The ladder (GLOBAL_SCALAR > POINTWISE > PER_AOI_DINN > DINN) varies SPATIAL sharing at every
rung and PARAMETER sharing at none. `PerParamDINN` adds that rung, to test whether the 3-of-4
observable frontier is a parameter-sharing artifact -- the Fisher rank is 4/4, so the
information is present, and the documented conflict (MLD helps diatomgraz, breaks scav_rat) is
representational rather than informational.

The capacity test is the load-bearing one. Independent trunks have ~N_PARAMS times the weights
of one shared trunk, and "a bigger network fits better" is the confound that made the
2026-07-12 resolution result null. If the matched control is not really matched, any lift this
architecture shows is uninterpretable.
"""
from __future__ import annotations

import torch

from darwindiff.carroll6 import N_PARAMS, PARAM_BOUNDS, bounded_params
from darwindiff.networks import DINN, PerParamDINN


def _n(m) -> int:
    return sum(p.numel() for p in m.parameters())


def test_shape_matches_dinn_unbatched_and_batched():
    """Drop-in for DINN: same in, same out, so bounded_params applies unchanged."""
    for shape, axis in (((3, 5, 7), 0), ((2, 3, 5, 7), 1)):
        env = torch.randn(*shape)
        out = PerParamDINN(n_input_channels=3)(env)
        ref = DINN(n_input_channels=3)(env)
        assert out.shape == ref.shape
        assert bounded_params(out, PARAM_BOUNDS, param_axis=axis).shape == out.shape


def test_parameters_are_genuinely_independent_across_outputs():
    """The whole point: no weight is shared between two parameters' predictions.

    Perturbing head j must move output j and NOTHING else. If any other output moves, the
    representation is still shared and this rung does not test what it claims to.
    """
    m = PerParamDINN(n_input_channels=3)
    env = torch.randn(3, 4, 4)
    before = m(env).detach().clone()
    with torch.no_grad():
        for p in m.heads[2].parameters():
            p.add_(0.5)
    after = m(env).detach()
    moved = [bool((after[i] - before[i]).abs().max() > 0) for i in range(N_PARAMS)]
    assert moved[2], "perturbing head 2 must move output 2"
    assert sum(moved) == 1, f"exactly one output may move, got {moved}"


def test_gradients_do_not_cross_between_parameters():
    """A loss on one parameter leaves every other head's gradient exactly None/zero."""
    m = PerParamDINN(n_input_channels=3)
    m(torch.randn(3, 4, 4))[0].pow(2).sum().backward()
    assert any(p.grad is not None and p.grad.abs().sum() > 0 for p in m.heads[0].parameters())
    for j in range(1, N_PARAMS):
        for p in m.heads[j].parameters():
            assert p.grad is None or float(p.grad.abs().sum()) == 0.0, (
                f"head {j} received gradient from a loss on parameter 0 -- representations "
                "are still coupled and the arm is confounded"
            )


def test_matched_control_never_exceeds_the_per_param_budget():
    """The capacity-matched shared trunk must not be ADVANTAGED, or a lift is just capacity."""
    for ch in (1, 2, 3):
        for hd in (8, 16, 32):
            pp = _n(PerParamDINN(n_input_channels=ch, hidden_dim=hd))
            w = PerParamDINN.matched_hidden_dim(n_input_channels=ch, hidden_dim=hd)
            ctrl = _n(DINN(n_input_channels=ch, hidden_dim=w))
            assert ctrl <= pp, f"matched control {ctrl} exceeds budget {pp} (ch={ch}, hd={hd})"
            bigger = _n(DINN(n_input_channels=ch, hidden_dim=w + 1))
            assert bigger > pp, f"matched width {w} is not maximal (ch={ch}, hd={hd})"


def test_matched_control_is_wider_than_the_default_trunk():
    """Sanity: the control must actually be widened, else the comparison is against the old net."""
    w = PerParamDINN.matched_hidden_dim(n_input_channels=1, hidden_dim=16)
    assert w > 16, f"matched width {w} should exceed the shared-trunk default 16"


def test_deterministic_under_manual_seed():
    """Two builds at one seed agree bitwise, so arm-to-arm differences are not init noise."""
    env = torch.randn(3, 4, 4)
    torch.manual_seed(0); a = PerParamDINN(n_input_channels=3)(env)
    torch.manual_seed(0); b = PerParamDINN(n_input_channels=3)(env)
    assert torch.equal(a, b)
