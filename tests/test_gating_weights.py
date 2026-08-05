"""Soft per-(parameter, AOI) gradient weights must redistribute gradient, not change its total.

`apply_gate` is a straight-through mask whose forward value is `params` for ANY gate and whose
backward scales the gradient by the gate. Nothing requires the gate to be binary, so soft
weighting is a change of vectors only.

The property that makes the experiment interpretable: for every parameter, the sum over AOIs of
`aoi_loss_weight * gate` must equal the ungated sum. If it did not, the arm would vary routing
AND effective learning rate together -- and on 2026-08-03 the learning rate alone moved
`scav_rat` from 26/50 to 1/50, so a confounded arm would be worthless.
"""
from __future__ import annotations

import torch

from darwindiff.gating import (
    PARAM_NAMES,
    apply_gate,
    build_weight_vectors_from_rule,
)

AOIS = ["eqpac", "natlsubpolar", "southernoceanpac"]
LOSS_W = {"eqpac": 1.0, "natlsubpolar": 2.0, "southernoceanpac": 2.0}


def _rule(**per_param) -> dict:
    uniform = {a: 1.0 / len(AOIS) for a in AOIS}
    return {"weights": {n: per_param.get(n, dict(uniform)) for n in PARAM_NAMES}}


def test_total_gradient_per_parameter_is_preserved() -> None:
    """The invariant the whole experiment rests on."""
    rule = _rule(scav_rat={"eqpac": 0.1, "natlsubpolar": 0.1, "southernoceanpac": 0.8},
                 R_PICPOC={"eqpac": 0.6, "natlsubpolar": 0.4, "southernoceanpac": 0.0})
    vec = build_weight_vectors_from_rule(rule, AOIS, LOSS_W)
    want = sum(LOSS_W.values())
    for j, name in enumerate(PARAM_NAMES):
        got = sum(LOSS_W[a] * float(vec[a][j]) for a in AOIS)
        assert abs(got - want) < 1e-6, (
            f"{name}: total effective weight {got} != ungated {want}; this arm would vary "
            "routing and effective learning rate together and could not be interpreted"
        )


def test_a_uniform_rule_reproduces_the_ungated_gate() -> None:
    """With equal information everywhere the soft gate must be the ungated baseline."""
    vec = build_weight_vectors_from_rule(_rule(), AOIS, LOSS_W)
    want = sum(LOSS_W.values()) / len(AOIS)
    for a in AOIS:
        for j in range(len(PARAM_NAMES)):
            assert abs(float(vec[a][j]) * LOSS_W[a] - want) < 1e-6


def test_zero_information_gives_exactly_zero_gradient() -> None:
    """southernoceanpac has NO Daniels cells, so R_PICPOC must get exactly nothing from it.

    Not a small number: zero. A basin with no observations of a quantity carries no information
    about it, and letting a floor leak gradient there would train the parameter on nothing.
    """
    rule = _rule(R_PICPOC={"eqpac": 0.6, "natlsubpolar": 0.4, "southernoceanpac": 0.0})
    vec = build_weight_vectors_from_rule(rule, AOIS, LOSS_W)
    j = PARAM_NAMES.index("R_PICPOC")
    assert float(vec["southernoceanpac"][j]) == 0.0


def test_forward_is_unchanged_and_backward_is_scaled() -> None:
    """The straight-through property, at a non-binary gate."""
    params = torch.arange(1.0, 1 + len(PARAM_NAMES)).reshape(-1, 1, 1).requires_grad_(True)
    gate = torch.full((len(PARAM_NAMES),), 0.37)
    out = apply_gate(params, gate)
    assert torch.equal(out.detach(), params.detach()), "forward must be identical to ungated"
    out.sum().backward()
    assert torch.allclose(params.grad, torch.full_like(params, 0.37))


def test_gradient_ratio_between_aois_matches_the_rule() -> None:
    """The distribution actually delivered must be the distribution the rule asked for."""
    rule = _rule(scav_rat={"eqpac": 0.2, "natlsubpolar": 0.1, "southernoceanpac": 0.7})
    vec = build_weight_vectors_from_rule(rule, AOIS, LOSS_W)
    j = PARAM_NAMES.index("scav_rat")
    eff = {a: LOSS_W[a] * float(vec[a][j]) for a in AOIS}
    tot = sum(eff.values())
    for a, want in rule["weights"]["scav_rat"].items():
        assert abs(eff[a] / tot - want) < 1e-6, f"{a}: delivered {eff[a]/tot:.4f}, asked {want}"
