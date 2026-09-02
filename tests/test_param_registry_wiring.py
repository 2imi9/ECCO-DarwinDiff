"""Registry-driven wiring guards for the Carroll-N parameter set.

The failure mode these tests exist to catch: **a parameter is added to the
``PARAMS`` registry but never wired into the box model's tendency terms.** That
fails *silently* — the network grows an extra output channel, the extra channel
is bounded into a physical range, the value is collapsed per AOI and graded, and
a recovery count is reported for a parameter that cannot possibly have been
constrained by any observation. Nothing raises.

Worse, the reported count is not random: it is whatever fraction of the
parameter's prior range happens to fall inside the +/-40 % Cal-grade band. For
``diatomgraz`` that is ~55 % (its bounds midpoint sits at rel 0.367, inside the
band), so an unwired parameter with generous bounds would report as "recovered"
most of the time.

These tests are deliberately **derived from the registry**, so appending an
entry to ``PARAMS`` automatically extends the coverage. There is no list of
parameter names to keep in sync.

Companion guard: ``tests/test_carroll6_5pft.py`` already asserts gradient flow
for the 10-tracer surface model. These extend the same idea to
(a) the 15-tracer **2-layer model the flagship runner actually integrates**, and
(b) a finite-difference magnitude floor, because a parameter can carry a
gradient that is nonzero but numerically negligible.
"""

from __future__ import annotations

import pytest
import torch

from darwindiff.carroll6 import (
    CARROLL_VALUES,
    N_PARAMS,
    PARAM_BOUNDS,
    PARAM_INDEX,
    PARAM_NAMES,
    PARAMS,
    bounded_params,
    log_mask_from_names,
    prior_midpoint_offset,
)
from darwindiff.carroll6_5pft_2layer import carroll6_5pft_2layer_integrate
from darwindiff.diagnostics import BAND_CAL_GRADE_MAX

# Parameters KNOWN to violate the prior-contamination rule below. This is a
# defect register, not a permission list: every entry is a parameter whose
# recovery counts are partly an artifact of its bounds, and every entry needs a
# reason and a measurement.
#
# diatomgraz: bounds (0.05, 1.0) against Carroll 0.83003 put the Cal-grade band
# at [0.498, 1.0], which is 52.8 % of the range, and the midpoint 0.525 sits
# INSIDE it at rel 0.367. Measured consequence (n=50 untrained, job 227777):
# diatomgraz recovers 32/50 with NO TRAINING. The published 35/50 "non-circular
# handle" result is P = 0.447 against an architecture-matched untrained control,
# i.e. one seed better than nothing.
#
# Fixing it means changing bounds, which breaks bitwise reproduction of every
# prior run (CONTRIBUTING: "values are frozen"). So it is recorded here until
# that change is made deliberately.
KNOWN_PRIOR_CONTAMINATED = {"diatomgraz"}

# Every tracer non-zero so no parameter is dormant for want of a substrate:
# R_PICPOC needs calcifiers, diatomgraz needs diatoms, scav_rat needs iron.
# A zero in the wrong slot would make a correctly-wired parameter look unwired.
_STATE0 = torch.tensor(
    [
        0.6e-3,  # 0  DFe_1
        0.30,    # 1  P_diatom
        0.20,    # 2  P_lge
        0.15,    # 3  P_syn
        0.10,    # 4  P_proLL
        0.10,    # 5  P_proHL
        1.50,    # 6  POC_1
        0.10,    # 7  PIC_1
        2000.0,  # 8  DIC_1
        2300.0,  # 9  ALK_1
        0.8e-3,  # 10 DFe_2
        1.00,    # 11 POC_2
        0.08,    # 12 PIC_2
        2100.0,  # 13 DIC_2
        2350.0,  # 14 ALK_2
    ],
    dtype=torch.float32,
)

_DT = 0.25
_N_STEPS = 60


def _rollout(params: torch.Tensor) -> torch.Tensor:
    return carroll6_5pft_2layer_integrate(
        state0=_STATE0, params=params, dt=_DT, n_steps=_N_STEPS
    )


def test_registry_derived_layout_is_self_consistent() -> None:
    """The derived views cannot drift from PARAMS."""
    assert N_PARAMS == len(PARAMS) == len(PARAM_NAMES)
    assert PARAM_BOUNDS.shape == (N_PARAMS, 2)
    assert CARROLL_VALUES.shape == (N_PARAMS,)
    assert {p.name: i for i, p in enumerate(PARAMS)} == PARAM_INDEX
    for p in PARAMS:
        lo, hi = p.bounds
        assert lo < hi, f"{p.name}: bounds must be increasing"
        assert p.scale in ("linear", "log"), f"{p.name}: bad scale {p.scale!r}"
        if p.scale == "log":
            assert lo > 0, f"{p.name}: log scale needs a positive lower bound"


@pytest.mark.parametrize("name", PARAM_NAMES)
def test_bounds_do_not_put_the_prior_inside_the_cal_grade_band(name: str) -> None:
    """A parameter's bounds must not hand it a recovery it did not earn.

    "Recovered" means ``rel <= 0.40`` from Carroll. An untrained network's
    outputs sit near zero, so ``bounded_params`` places it near the MIDPOINT of
    ``bounds``. If that midpoint is already inside the band, the parameter scores
    as recovered from a network that has learned nothing, and the count measures
    the bounds rather than the observations.

    This guard exists because it already happened. ``diatomgraz`` scores 32/50
    untrained, and a 35/50 trained result was reported as a finding before the
    control was run.
    """
    spec = PARAMS[PARAM_INDEX[name]]
    offset = prior_midpoint_offset(spec)

    if name in KNOWN_PRIOR_CONTAMINATED:
        # Pin the defect so it cannot silently get worse, and so that fixing the
        # bounds forces this list to be updated.
        assert offset <= BAND_CAL_GRADE_MAX, (
            f"{name} is in KNOWN_PRIOR_CONTAMINATED but its midpoint offset "
            f"{offset:.3f} is now OUTSIDE the {BAND_CAL_GRADE_MAX} band. If the "
            f"bounds were fixed, remove it from that set."
        )
        pytest.xfail(
            f"{name}: prior midpoint sits at rel {offset:.3f}, inside the "
            f"{BAND_CAL_GRADE_MAX} Cal-grade band. Recovery counts for this "
            f"parameter are partly an artifact of its bounds (32/50 measured "
            f"untrained). Known defect, see KNOWN_PRIOR_CONTAMINATED."
        )

    assert offset > BAND_CAL_GRADE_MAX, (
        f"{name!r}: the midpoint of bounds {spec.bounds} sits at relative offset "
        f"{offset:.3f} from Carroll {spec.carroll_value}, INSIDE the "
        f"{BAND_CAL_GRADE_MAX} Cal-grade band. An untrained network would score "
        f"this parameter as 'recovered' most of the time, so any recovery count "
        f"you report would measure your choice of bounds, not the observations. "
        f"Widen the bounds, or re-centre them so the midpoint falls outside the "
        f"band, or grade this parameter with a different metric."
    )


@pytest.mark.parametrize("name", PARAM_NAMES)
def test_model_value_matches_carroll_or_is_declared(name: str) -> None:
    """If the GCM runs a different number than the published optimum, say so.

    Recovery is graded against ``carroll_value``. Where ECCO-Darwin v05 actually
    integrates something else, ``model_value`` must record it so the gap is
    visible rather than silently absorbed into the tolerance.
    """
    spec = PARAMS[PARAM_INDEX[name]]
    if spec.model_value is None:
        return
    gap = abs(spec.model_value - spec.carroll_value) / abs(spec.carroll_value)
    # Declared gaps must be small enough not to move a verdict on their own.
    assert gap < BAND_CAL_GRADE_MAX, (
        f"{name}: model_value {spec.model_value} differs from carroll_value "
        f"{spec.carroll_value} by {gap:.1%}, which is large enough to change a "
        f"recovery verdict. Decide which one is the target."
    )
    assert gap > 0, f"{name}: model_value equals carroll_value; set it to None"


@pytest.mark.parametrize("name", PARAM_NAMES)
def test_every_registered_parameter_reaches_the_2layer_model(name: str) -> None:
    """Each learned parameter must move the 15-tracer state it is declared to affect.

    This is the anti-silent-no-op guard. If it fails for a newly added
    parameter, that parameter is in the registry but not in the physics, and any
    recovery count reported for it is meaningless.
    """
    spec = PARAMS[PARAM_INDEX[name]]
    if not spec.learned:
        pytest.skip(f"{name} is not learned")

    base = CARROLL_VALUES.clone()
    ref = _rollout(base)
    assert torch.isfinite(ref).all(), "reference rollout must be finite"

    # Central difference at +/-2 % of the Carroll value.
    i = PARAM_INDEX[name]
    hi_p = base.clone()
    hi_p[i] = base[i] * 1.02
    lo_p = base.clone()
    lo_p[i] = base[i] * 0.98
    d = (_rollout(hi_p) - _rollout(lo_p)).abs()

    scale = ref.abs().clamp(min=1e-12)
    rel = float((d / scale).max())

    assert rel > 1e-8, (
        f"{name!r} is REGISTERED but does not measurably change the 2-layer box "
        f"state (max relative response {rel:.2e} to a +/-2 % perturbation). "
        f"Either wire it into a tendency term in carroll6_5pft_2layer.py, or "
        f"set learned=False. Leaving it registered-but-unwired means the "
        f"pipeline will still report a recovery count for it, and that count "
        f"reflects only how much of its prior range falls inside the Cal-grade "
        f"band -- not any observational constraint."
    )


def test_gradient_reaches_every_parameter_through_the_2layer_model() -> None:
    """Autograd path check, the differentiable-programming counterpart of the FD test."""
    theta = torch.zeros(N_PARAMS, requires_grad=True)
    params = bounded_params(theta, PARAM_BOUNDS)
    _rollout(params).sum().backward()

    assert theta.grad is not None
    assert torch.isfinite(theta.grad).all(), "non-finite parameter gradient"
    dead = [PARAM_NAMES[i] for i in range(N_PARAMS) if theta.grad[i].abs() == 0]
    assert not dead, f"parameters with exactly zero gradient (unwired?): {dead}"


def test_default_bounding_is_unchanged_by_the_log_scale_feature() -> None:
    """Regression lock: log-scale support must not alter the historical map.

    Every published recovery count was produced with the linear map. If this
    fails, prior results are no longer reproducible by the current code.
    """
    torch.manual_seed(0)
    theta = torch.randn(N_PARAMS, 5, 7)
    lo = PARAM_BOUNDS[:, 0].reshape(N_PARAMS, 1, 1)
    hi = PARAM_BOUNDS[:, 1].reshape(N_PARAMS, 1, 1)
    historical = lo + (hi - lo) * torch.sigmoid(theta)

    assert torch.equal(historical, bounded_params(theta, PARAM_BOUNDS))
    assert torch.equal(
        historical, bounded_params(theta, PARAM_BOUNDS, log_mask=log_mask_from_names(""))
    )


def test_log_mask_touches_only_the_named_parameter() -> None:
    """Opting one parameter into log space must not perturb the others."""
    torch.manual_seed(0)
    theta = torch.randn(N_PARAMS, 4, 4)
    linear = bounded_params(theta, PARAM_BOUNDS)
    logged = bounded_params(
        theta, PARAM_BOUNDS, log_mask=log_mask_from_names("scav_rat")
    )
    changed = [
        PARAM_NAMES[i]
        for i in range(N_PARAMS)
        if not torch.equal(linear[i], logged[i])
    ]
    assert changed == ["scav_rat"], f"log mask leaked into {changed}"


def test_log_map_midpoint_is_the_geometric_mean() -> None:
    """theta=0 must land on sqrt(lo*hi), not the arithmetic midpoint.

    Pins that the log map's CENTRE is outside the Cal-grade band: at theta=0
    scav_rat sits at rel 0.502 against the 0.40 threshold.

    .. warning::

        This is a statement about theta=0 ONLY, and it must not be read as "the
        log map does not affect the chance rate". Real initialisation has
        spread, and the measured untrained control (job 227876, n=50) shows the
        log map moves scav_rat's chance rate from **0/50 to 8/50 (16 %)** --
        median start 2.46x Carroll with 0 % in-band under the linear map, versus
        0.48x with 18 % in-band under the log map. So a log-map arm MUST be
        graded against its own prior control, never against the linear arm's.
    """
    i = PARAM_INDEX["scav_rat"]
    lo, hi = (float(x) for x in PARAM_BOUNDS[i])
    got = bounded_params(
        torch.zeros(N_PARAMS), PARAM_BOUNDS, log_mask=log_mask_from_names("scav_rat")
    )[i]
    assert got == pytest.approx((lo * hi) ** 0.5, rel=1e-6)

    carroll = float(CARROLL_VALUES[i])
    rel = abs(float(got) - carroll) / carroll
    assert rel > 0.40, (
        f"log-map init sits at rel {rel:.3f}, INSIDE the Cal-grade band -- that "
        f"would hand scav_rat a free recovery at initialisation"
    )


def test_log_mask_rejects_bad_input() -> None:
    """Unknown names and wrong-length masks must fail loudly, not silently no-op."""
    with pytest.raises(KeyError):
        log_mask_from_names("not_a_parameter")
    with pytest.raises(ValueError):
        bounded_params(
            torch.zeros(N_PARAMS), PARAM_BOUNDS,
            log_mask=torch.ones(N_PARAMS + 1, dtype=torch.bool),
        )
