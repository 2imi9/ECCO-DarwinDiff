"""Per-AOI parameter gating for multi-AOI Carroll-6 recovery (Stage 1).

Background
----------
The v3.1 multi-AOI joint training reached a 5/6 recovery ceiling: a single
shared DINN, trained on the *sum* of per-AOI losses, cannot simultaneously
satisfy every regime's preferred Carroll-6 value. Each parameter's identifying
signal lives predominantly in one regime -- ``alpfe`` and ``diatomgraz`` in the
iron-limited Equatorial Pacific, ``Biggrow`` and ``R_PICPOC`` in the
iron-replete North Atlantic Subpolar gyre, ``scav_rat`` in the Southern Ocean.
When all six parameters learn from the summed loss the regimes pull against each
other and the optimiser settles on a compromise.

Stage 1 attacks this *architecturally* by hard-routing each parameter's gradient
to only the AOI loss(es) that carry its signal. The forward parameter values are
unchanged; only the backward pass is masked. For AOI ``k`` we form

    params_gated = params.detach() + gate_k * (params - params.detach())

where ``gate_k[p] == 1`` iff parameter ``p`` is routed to AOI ``k`` and ``0``
otherwise. The straight-through construction leaves the forward value bitwise
identical to ``params`` (so per-AOI losses are unaffected) while zeroing the
gradient AOI ``k``'s loss contributes to the un-routed parameter channels.

This is a *shared-DINN* intervention: it routes gradients into the per-channel
outputs of the one network every AOI shares. It is mutually exclusive with
``PER_AOI_DINN`` (which instead decouples regimes by giving each its own
network); the runner raises if both are requested.

Policies
--------
A policy maps each AOI key to the list of Carroll-6 parameter names that learn
from that AOI's loss. The empty policy (``"ungated"``) is the baseline: every
parameter learns from every AOI, reproducing pre-gating behaviour bitwise.
"""

from __future__ import annotations

import json

import torch

from darwindiff.carroll6 import PARAM_INDEX, PARAM_NAMES

# Registry-derived name -> index map. carroll6.PARAMS is the single source of
# truth; aliased here so the rest of this module keeps its private name.
_PARAM_INDEX: dict[str, int] = PARAM_INDEX

# Named presets. Keys are AOI keys from ecco_darwin_loader.AOI_BY_KEY; values are
# the Carroll-6 parameters routed to that AOI's loss. Each preset covers all six
# parameters across the AOIs it names (validate_policy enforces this at run time
# against the AOIs actually present).
GATING_POLICIES: dict[str, dict[str, list[str]]] = {
    # Baseline: no gating. Every parameter learns from every AOI loss.
    "ungated": {},
    # 2-AOI default (eqpac + natlsubpolar). With no Southern-Ocean regime here,
    # scav_rat + Smallgrow ride with the iron-cycle (eqpac) regime where the
    # scavenging + small-phyto signals are strongest.
    "signal_2aoi": {
        "eqpac": ["alpfe", "scav_rat", "Smallgrow", "diatomgraz"],
        "natlsubpolar": ["Biggrow", "R_PICPOC"],
    },
    # 3-AOI (eqpac + natlsubpolar + southernoceanpac). The canonical Stage-1
    # routing: each parameter to the regime that most identifies it. The
    # assignment of Smallgrow (eqpac) is a researcher-tunable hypothesis.
    "signal_3aoi": {
        "eqpac": ["alpfe", "diatomgraz", "Smallgrow"],
        "natlsubpolar": ["Biggrow", "R_PICPOC"],
        "southernoceanpac": ["scav_rat"],
    },
}


def resolve_policy(spec: str | dict) -> dict[str, list[str]]:
    """Resolve a policy spec into an ``{aoi_key: [param_name, ...]}`` mapping.

    ``spec`` may be:
      - a preset name in :data:`GATING_POLICIES` (e.g. ``"signal_2aoi"``),
      - a JSON object string mapping AOI keys to parameter-name lists,
      - an already-built mapping (shallow-copied and returned).

    Returns the empty dict for the ``"ungated"`` baseline.
    """
    if isinstance(spec, dict):
        return {k: list(v) for k, v in spec.items()}
    if not isinstance(spec, str):
        raise TypeError(f"policy spec must be str or dict, got {type(spec).__name__}")
    s = spec.strip()
    if s in GATING_POLICIES:
        return {k: list(v) for k, v in GATING_POLICIES[s].items()}
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"GATING_POLICY {spec!r} is neither a known preset "
            f"({sorted(GATING_POLICIES)}) nor valid JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            f"GATING_POLICY JSON must be an object mapping AOI->params, "
            f"got {type(parsed).__name__}"
        )
    return {k: list(v) for k, v in parsed.items()}


def validate_policy(policy: dict[str, list[str]], aoi_keys: list[str]) -> None:
    """Validate a resolved policy against the AOIs present in the run.

    Raises ``ValueError`` if a policy AOI key is absent from ``aoi_keys``, a
    parameter name is not a Carroll-6 name, or the routed parameters (over the
    present AOIs) do not cover all six -- an un-routed parameter would receive
    no gradient from any AOI and stay at its initialisation.

    The empty policy (ungated) passes trivially: every parameter learns from
    every AOI.
    """
    if not policy:
        return
    aoi_set = set(aoi_keys)
    routed: set[str] = set()
    for k, params in policy.items():
        if k not in aoi_set:
            raise ValueError(
                f"GATING_POLICY references AOI {k!r} not in this run's AOIS "
                f"({sorted(aoi_set)}). Add it to AOIS or fix the policy."
            )
        for p in params:
            if p not in _PARAM_INDEX:
                raise ValueError(
                    f"GATING_POLICY routes unknown parameter {p!r}; "
                    f"valid names: {PARAM_NAMES}"
                )
            routed.add(p)
    missing = [p for p in PARAM_NAMES if p not in routed]
    if missing:
        raise ValueError(
            f"GATING_POLICY leaves {missing} un-routed: those parameters would "
            f"receive no gradient from any AOI and stay at initialisation. "
            f"Route every Carroll-6 parameter to at least one AOI in the run."
        )


def build_gate_vectors(
    policy: dict[str, list[str]],
    aoi_keys: list[str],
    device: str | torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> dict[str, torch.Tensor]:
    """Build per-AOI gate vectors of shape ``[6]`` (1.0 routed, 0.0 not).

    For the ungated baseline (empty policy) every AOI gets an all-ones vector so
    :func:`apply_gate` is an exact no-op.
    """
    n = len(PARAM_NAMES)
    vectors: dict[str, torch.Tensor] = {}
    for k in aoi_keys:
        vec = torch.zeros(n, dtype=dtype, device=device)
        if not policy:
            vec[:] = 1.0
        else:
            for p in policy.get(k, []):
                vec[_PARAM_INDEX[p]] = 1.0
        vectors[k] = vec
    return vectors


def apply_gate(params: torch.Tensor, gate_vec: torch.Tensor) -> torch.Tensor:
    """Straight-through per-parameter gradient mask.

    ``params`` has the parameter axis first (shape ``[6, ...]``); ``gate_vec``
    is shape ``[6]``. The returned tensor has values **identical** to ``params``
    (forward unchanged) but its gradient w.r.t. ``params`` equals ``gate_vec``
    broadcast over the trailing dims: 1 lets the gradient flow, 0 blocks it.
    """
    if params.shape[0] != gate_vec.shape[0]:
        raise ValueError(
            f"params param-axis ({params.shape[0]}) != gate length "
            f"({gate_vec.shape[0]})"
        )
    shape = (gate_vec.shape[0],) + (1,) * (params.ndim - 1)
    g = gate_vec.reshape(shape).to(dtype=params.dtype, device=params.device)
    detached = params.detach()
    return detached + g * (params - detached)


def build_weight_vectors_from_rule(
    rule: dict,
    aoi_keys: list[str],
    aoi_loss_weights: dict[str, float],
    device: str | torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> dict[str, torch.Tensor]:
    """Soft per-(parameter, AOI) gradient weights from a derived routing rule.

    :func:`apply_gate` is a straight-through mask -- ``detached + g * (params - detached)`` --
    whose forward value is ``params`` for **any** ``g`` and whose backward scales the gradient
    by ``g``. Nothing about it requires ``g`` to be binary, so soft weighting needs no change
    there: only the vectors differ.

    ``rule`` is the JSON emitted by ``scripts/analysis/emit_routing_rule.py``: per parameter, a
    distribution over AOIs proportional to the Fisher information that AOI's observations carry
    about that parameter, evaluated at the prior midpoint. It never reads Carroll's values, so
    routing by it is not selection on the answer.

    TOTAL GRADIENT IS HELD FIXED, AND THIS IS THE POINT.
    ---------------------------------------------------
    The runner already multiplies each AOI's loss by ``aoi_loss_weights`` (the flagship's
    ``{1, 2, 2}``). If the rule's weights were applied on top, the *total* gradient reaching each
    parameter would change as well as its distribution across basins -- and a change in total
    gradient is a change in effective learning rate. On 2026-08-03 an unpinned learning rate
    (5e-3 vs 1e-3) moved ``scav_rat`` from 26/50 to 1/50, so an experiment that varies routing and
    effective LR together would be uninterpretable in exactly the way that cost two arrays.

    So the returned gate satisfies, for every parameter ``j``::

        sum_a  aoi_loss_weights[a] * gate[a][j]  ==  sum_a aoi_loss_weights[a]

    i.e. the same total as ungated. Only the *distribution* over AOIs changes. Verified by
    ``tests/test_gating_weights.py``.
    """
    n = len(PARAM_NAMES)
    weights = rule.get("weights", rule)
    total = float(sum(aoi_loss_weights[a] for a in aoi_keys))
    vectors: dict[str, torch.Tensor] = {}
    for a in aoi_keys:
        vec = torch.zeros(n, dtype=dtype, device=device)
        w_a = float(aoi_loss_weights[a])
        for name, idx in _PARAM_INDEX.items():
            share = float(weights.get(name, {}).get(a, 1.0 / len(aoi_keys)))
            # gate = share * total / aoi_weight, so that aoi_weight * gate == share * total
            # and the per-parameter sum over AOIs is `total`, matching ungated exactly.
            vec[idx] = 0.0 if w_a == 0.0 else share * total / w_a
        vectors[a] = vec
    return vectors
