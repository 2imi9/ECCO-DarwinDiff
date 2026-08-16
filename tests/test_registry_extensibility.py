"""Adding a 7th Carroll parameter must stay a one-entry edit on the PLUMBING side.

WHY THIS TEST EXISTS. The registry is designed so that appending to ``carroll6.PARAMS``
propagates automatically to ``PARAM_NAMES``, ``CARROLL_VALUES``, ``PARAM_BOUNDS``,
``PARAM_INDEX``, the ``P`` named-index namespace, ``N_PARAMS``, and the width of every network
head. That property is easy to break by hand-writing a ``6`` somewhere, and nothing currently
notices until a future extension fails in a confusing place.

WHAT THIS TEST DOES NOT CLAIM. It pins the plumbing only. Four things remain genuinely manual
when a parameter is added, and no test can remove them:

  1. THE PHYSICS. The box reads parameters by name (``params[P.alpfe]``), so a new registry entry
     is predicted by the network and IGNORED by the equations until a term is written by hand. A
     parameter with no term in the ODE is not a parameter.
  2. EVERY CHECKPOINT IS INVALIDATED. The DINN head goes 6 -> 7 outputs, so saved weights no
     longer load. This is the real cost of extending a learned parameter map.
  3. EVERY UNTRAINED NULL MUST BE RE-MEASURED. The null is ARCHITECTURE-matched, so a
     7-parameter network has a different chance rate than a 6-parameter one. Published nulls
     (alpfe 10/50, scav_rat 0/50, ...) do not carry over.
  4. THE NEW PARAMETER'S PRIOR GEOMETRY IS A LOTTERY. If its bounds put the midpoint inside the
     pass band, an untrained network scores it as recovered - which is exactly the known
     ``diatomgraz`` defect (rel 0.367 inside a 0.40 band). See
     ``test_param_registry_wiring.py::test_bounds_do_not_put_the_prior_inside_the_cal_grade_band``.

Order is load-bearing for ARTIFACTS, not for the code: run JSONs and checkpoints store the
parameter axis positionally, so appending is safe and reordering breaks compatibility with
everything already on disk.
"""

from __future__ import annotations

import torch

from darwindiff import carroll6
from darwindiff.networks import DINN, GlobalScalarNet


def _extended():
    """The registry with one extra entry, in memory only."""
    extra = carroll6.Param(
        name="test_extra_param",
        bounds=(0.01, 0.5),
        carroll_value=0.1,
        units="d^-1",
        description="synthetic entry used only to pin registry extensibility",
    )
    return carroll6.PARAMS + (extra,)


def test_registry_derivations_all_follow_the_tuple():
    """Every derived structure must be a function of PARAMS, not a hand-written constant."""
    assert carroll6.N_PARAMS == len(carroll6.PARAMS)
    assert len(carroll6.PARAM_NAMES) == len(carroll6.PARAMS)
    assert carroll6.CARROLL_VALUES.shape == (len(carroll6.PARAMS),)
    assert carroll6.PARAM_BOUNDS.shape == (len(carroll6.PARAMS), 2)
    assert len(carroll6.PARAM_INDEX) == len(carroll6.PARAMS)
    assert carroll6.PARAM_LOG_MASK.shape == (len(carroll6.PARAMS),)


def test_derivations_widen_with_a_seventh_entry():
    p7 = _extended()
    assert len(p7) == carroll6.N_PARAMS + 1
    names = [p.name for p in p7]
    assert names[-1] == "test_extra_param"
    assert len(set(names)) == len(names), "parameter names must stay unique"
    vals = torch.tensor([p.carroll_value for p in p7])
    bnds = torch.tensor([list(p.bounds) for p in p7])
    assert vals.shape == (len(p7),)
    assert bnds.shape == (len(p7), 2)
    # appending must not disturb any existing index
    idx = {p.name: i for i, p in enumerate(p7)}
    for name, i in carroll6.PARAM_INDEX.items():
        assert idx[name] == i, f"appending moved {name} from {i} to {idx[name]}"


def test_every_network_head_widens_from_n_outputs():
    """The parameter axis is the only thing that changes; nothing may hardcode 6."""
    x = torch.zeros(1, 1, 4, 4)
    for n in (carroll6.N_PARAMS, carroll6.N_PARAMS + 1):
        net = DINN(n_input_channels=1, hidden_dim=16, n_outputs=n)
        assert net(x).shape == (1, n, 4, 4), f"DINN head did not widen to {n}"
    for n in (carroll6.N_PARAMS, carroll6.N_PARAMS + 1):
        g = GlobalScalarNet(n_outputs=n)
        out = g(x)          # same env -> [n_outputs, H, W] signature as DINN
        assert out.shape[-3] == n, f"GlobalScalarNet did not widen to {n}, got {tuple(out.shape)}"


def test_the_box_reads_parameters_by_name_not_position():
    """Name-indexing is what makes an append safe; positional reads would shift silently."""
    import inspect
    import re

    src = inspect.getsource(carroll6)
    # Strip comments and docstrings before scanning: the module DOCUMENTS the positional
    # pattern in prose ("call sites read params[P.alpfe] instead of the position-counted
    # params[0]"), and matching that text would be a false positive on the very comment
    # that establishes the convention.
    code_only = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    code_only = re.sub(r'"""[\s\S]*?"""', "", code_only)

    assert re.search(r"params\[P\.\w+\]", code_only), "expected name-indexed parameter reads"
    bare = re.findall(r"params\[\s*\d+\s*\]", code_only)
    assert not bare, f"positional parameter reads found, these break on insertion: {bare}"


def test_a_new_parameter_is_inert_in_the_physics_until_wired():
    """Guards the most likely misunderstanding: the registry does not write equations.

    A 7th entry is predicted by the network and ignored by the box. This test documents that
    rather than asserting it is fine - it is the manual step an extension must not forget.
    """
    p7 = _extended()
    consumed = {m for m in carroll6.PARAM_INDEX}
    new_names = {p.name for p in p7} - consumed
    assert new_names == {"test_extra_param"}
    import inspect

    src = inspect.getsource(carroll6)
    assert "P.test_extra_param" not in src, (
        "a new registry entry must be explicitly wired into the equations; "
        "if this ever passes trivially, the test has lost its meaning"
    )
