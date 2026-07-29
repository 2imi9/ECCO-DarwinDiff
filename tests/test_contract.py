"""Tests for the declarative identifiability contract (issue #210).

The load-bearing behaviour is negative: a clause with no evidence must read
UNAVAILABLE and must NOT read PASS. Silently treating absent evidence as satisfied
evidence is the failure mode that let a coin-flip result (`diatomgraz` 35/50
against an untrained 34/50, P=0.447) sit in an abstract draft for six days.

Every numeric case here is a real project number, so the tests double as a
regression net on the verdicts themselves.
"""
from __future__ import annotations

import json

import pytest

from darwindiff.carroll6 import PARAMS
from darwindiff.contract import (
    ALIASING_GATE,
    CAL_GRADE_BAND,
    EXIT_FAIL,
    EXIT_INCOMPLETE,
    EXIT_OK,
    ClauseStatus,
    ContractReport,
    Evidence,
    Unknown,
    contract,
)

# --- real declarations -------------------------------------------------------

ALPFE = Unknown(
    name="alpfe", kind="field", scope="per_cell",
    enters="dFe/dt += alpfe * dust_flux",
    identified_by=("geotraces_surf", "geotraces_sub"),
    bounds=(0.05, 1.0), reference=0.92831, conditioned_on=("sst",),
)
SCAV_RAT = Unknown(
    name="scav_rat", kind="field", scope="per_cell",
    enters="dFe/dt -= scav_rat * DFe * POC",
    identified_by=("geotraces_surf", "geotraces_sub"),
    bounds=(3e-8, 3e-6), reference=10.41124 * 0.005 / 86400.0, scale="log",
)
DIATOMGRAZ = Unknown(
    name="diatomgraz", kind="field", scope="per_cell",
    enters="PALAT, diatom grazing palatability",
    identified_by=("geotraces_bsi",),
    bounds=(0.05, 1.0), reference=0.83003,
)
R_PICPOC = Unknown(
    name="R_PICPOC", kind="field", scope="per_cell",
    enters="PIC production rain ratio",
    identified_by=("daniels_cp_pp",),
    bounds=(0.005, 1.5), reference=0.04245,
)
BIGGROW = Unknown(  # the point: no real observable exists
    name="Biggrow", kind="field", scope="per_cell",
    enters="PCMAX, large-eukaryote max growth rate",
    identified_by=(), bounds=(0.10, 2.0), reference=0.43148,
)
SCAV_CLOSURE = Unknown(
    name="ScavClosure", kind="relation", scope="per_cell",
    enters="dFe/dt -= f(DFe, POC) replacing the scav_rat scalar",
    identified_by=("geotraces_surf",), conditioned_on=("DFe", "POC"),
)


# --- the rule the module exists to enforce -----------------------------------

def test_absent_evidence_is_unavailable_and_never_pass() -> None:
    r = contract(ALPFE)
    assert r.verdict == "INCOMPLETE"
    assert r.exit_code() == EXIT_INCOMPLETE
    for name in ("measured_null", "structural", "practical"):
        assert r.clause(name).status == ClauseStatus.UNAVAILABLE
    assert not any(c.status == ClauseStatus.PASS for c in r.clauses
                   if c.name != "prior_contamination")


def test_incomplete_is_distinct_from_both_pass_and_fail() -> None:
    """Three-valued logic. Collapsing UNAVAILABLE into either is the bug."""
    assert EXIT_OK != EXIT_INCOMPLETE != EXIT_FAIL
    full = contract(ALPFE, Evidence(untrained_rate=0.20, untrained_n=50,
                                    recovered_count=49, recovered_n=50,
                                    fisher_info=0.26, crlb=68.5, profile="CURVED"))
    assert full.verdict == "IDENTIFIABLE" and full.exit_code() == EXIT_OK


# --- clause: prior contamination ---------------------------------------------

def test_diatomgraz_prior_contamination_fails_by_construction() -> None:
    """Bounds (0.05, 1.0) vs Carroll 0.83003 put the midpoint INSIDE the band.

    This is why an untrained network scores it 32/50 and why the 35/50 count was
    retired at P=0.447. The contract must catch it from the declaration alone,
    with no run at all.
    """
    c = contract(DIATOMGRAZ).clause("prior_contamination")
    assert c.status == ClauseStatus.FAIL
    assert c.evidence["midpoint_rel_offset"] == pytest.approx(0.367, abs=0.002)
    assert c.evidence["band_fraction_of_range"] == pytest.approx(0.528, abs=0.002)


@pytest.mark.parametrize("u", [ALPFE, R_PICPOC, BIGGROW])
def test_uncontaminated_priors_pass(u: Unknown) -> None:
    assert contract(u).clause("prior_contamination").status == ClauseStatus.PASS


def test_log_scale_uses_the_geometric_midpoint() -> None:
    """A log-scaled parameter's prior sits at the GEOMETRIC midpoint of its bounds.

    scav_rat's linear midpoint is ~1.5e-6 (2.5x Carroll) while its geometric
    midpoint is ~3.0e-7 (0.5x Carroll). Using the wrong one misstates where an
    untrained network starts, which is precisely what the measured prior control
    was built to settle.
    """
    c = contract(SCAV_RAT).clause("prior_contamination")
    assert c.evidence["midpoint"] == pytest.approx(3.0e-7, rel=0.02)
    assert c.status == ClauseStatus.PASS      # 0.5x Carroll is rel 0.50, outside 0.40

    linear = Unknown(name="scav_rat_linear", kind="field", scope="per_cell",
                     enters="x", identified_by=("a",), bounds=SCAV_RAT.bounds,
                     reference=SCAV_RAT.reference, scale="linear")
    assert contract(linear).clause("prior_contamination").evidence["midpoint"] == \
        pytest.approx(1.515e-6, rel=0.02)


# --- clause: measured null ----------------------------------------------------

def test_measured_null_passes_on_the_real_alpfe_numbers() -> None:
    c = contract(ALPFE, Evidence(untrained_rate=0.20, untrained_n=50,
                                 recovered_count=49, recovered_n=50)).clause("measured_null")
    assert c.status == ClauseStatus.PASS
    assert c.evidence["P_ge"] < 1e-20


def test_measured_null_fails_the_retired_diatomgraz_count() -> None:
    """35/50 against an architecture-matched untrained 34/50 is P=0.447."""
    c = contract(DIATOMGRAZ, Evidence(untrained_rate=0.68, untrained_n=50,
                                      recovered_count=35, recovered_n=50)).clause("measured_null")
    assert c.status == ClauseStatus.FAIL
    assert c.evidence["P_ge"] == pytest.approx(0.447, abs=0.01)


def test_zero_event_baseline_is_floored_by_the_rule_of_three() -> None:
    """A literal p=0 makes any nonzero count infinitely significant.

    This exact bug was found and fixed in the project's own grader, where Biggrow
    6/50 was first reported as "decisive, P=1.6e-17" against a 0/50 baseline.
    """
    c = contract(R_PICPOC, Evidence(untrained_rate=0.0, untrained_n=50,
                                    recovered_count=6, recovered_n=50)).clause("measured_null")
    assert c.evidence["null_p_used"] == pytest.approx(0.06)
    assert c.evidence["P_ge"] == pytest.approx(0.078, abs=0.005)
    assert c.status == ClauseStatus.FAIL          # 6/50 is chance-level, not decisive

    good = contract(R_PICPOC, Evidence(untrained_rate=0.0, untrained_n=50,
                                       recovered_count=50, recovered_n=50)).clause("measured_null")
    assert good.status == ClauseStatus.PASS


def test_baseline_without_a_count_is_unavailable_not_pass() -> None:
    c = contract(ALPFE, Evidence(untrained_rate=0.20, untrained_n=50)).clause("measured_null")
    assert c.status == ClauseStatus.UNAVAILABLE


# --- clause: structural -------------------------------------------------------

def test_no_declared_observable_fails_structurally() -> None:
    """The growth pair. Unidentifiable by DECLARATION, which is the finding."""
    c = contract(BIGGROW).clause("structural")
    assert c.status == ClauseStatus.FAIL
    assert "observing system" in c.detail


def test_zero_fisher_information_is_a_null_space_failure() -> None:
    """R_PICPOC has Fisher info identically 0.00e+00 under realiron and realbsi.

    Measured, job 233265. Exactly zero, not small. That is the formal statement
    behind the 50/50-versus-6/50 anchor contrast.
    """
    mis_declared = Unknown(name="R_PICPOC", kind="field", scope="per_cell",
                           enters="rain ratio", identified_by=("geotraces_surf",),
                           bounds=(0.005, 1.5), reference=0.04245)
    c = contract(mis_declared, Evidence(fisher_info=0.0)).clause("structural")
    assert c.status == ClauseStatus.FAIL
    assert "NULL SPACE" in c.detail

    ok = contract(R_PICPOC, Evidence(fisher_info=1.2e-2)).clause("structural")
    assert ok.status == ClauseStatus.PASS


# --- the relation row ---------------------------------------------------------

def test_relation_unknown_cannot_declare_a_scalar_reference() -> None:
    with pytest.raises(ValueError, match="learned FUNCTION"):
        Unknown(name="bad", kind="relation", scope="per_cell", enters="f(u)",
                reference=1.0)


def test_relation_row_marks_band_clauses_not_applicable() -> None:
    r = contract(SCAV_CLOSURE)
    assert r.clause("prior_contamination").status == ClauseStatus.NOT_APPLICABLE
    assert "no relative pass band" in r.clause("prior_contamination").detail


def test_relation_row_is_gated_on_aliasing_not_on_span() -> None:
    """0.311 dex FAILED at aliasing 0.9908 with a held-out R^2 of 0.99999999.

    Perfect fit, failed verdict. So the gate is aliasing, never a dex span. The
    calibrated pass was near 1.8 dex at aliasing ~0.81.
    """
    failed = contract(SCAV_CLOSURE, Evidence(aliasing_corr=0.9908,
                                             n_free_parameters=67)).clause("structural")
    assert failed.status == ClauseStatus.FAIL
    assert failed.evidence["gate"] == ALIASING_GATE

    passed = contract(SCAV_CLOSURE, Evidence(aliasing_corr=0.81)).clause("structural")
    assert passed.status == ClauseStatus.PASS


def test_relation_row_null_is_unavailable_and_says_why() -> None:
    c = contract(SCAV_CLOSURE, Evidence(aliasing_corr=0.5)).clause("measured_null")
    assert c.status == ClauseStatus.UNAVAILABLE
    assert "permutation" in c.detail


# --- practical ----------------------------------------------------------------

def test_flat_profile_fails_but_the_detail_records_our_own_counterexample() -> None:
    c = contract(ALPFE, Evidence(profile="FLAT")).clause("practical")
    assert c.status == ClauseStatus.FAIL
    assert "alpfe is" in c.detail and "9-10/10" in c.detail


def test_curved_profile_passes() -> None:
    assert contract(SCAV_RAT, Evidence(profile="CURVED", crlb=78.2)) \
        .clause("practical").status == ClauseStatus.PASS


# --- schema completeness ------------------------------------------------------

def test_every_registry_parameter_is_expressible_with_no_loss() -> None:
    """Success criterion 1: the schema must carry the existing registry."""
    for p in PARAMS:
        u = Unknown(name=p.name, kind="field", scope="per_cell",
                    enters=p.description or p.name,
                    identified_by=("some_observable",),
                    bounds=p.bounds, reference=p.carroll_value, scale=p.scale)
        assert u.name == p.name
        assert u.bounds == p.bounds
        assert u.reference == p.carroll_value
        assert u.scale == p.scale


def test_report_round_trips_through_json() -> None:
    r = contract(SCAV_RAT, Evidence(untrained_rate=0.0, untrained_n=50,
                                    recovered_count=25, recovered_n=50,
                                    fisher_info=0.54, crlb=78.2, profile="CURVED"))
    back = ContractReport.from_dict(json.loads(r.to_json()))
    assert back.verdict == r.verdict
    assert back.exit_code() == r.exit_code()
    assert [c.status for c in back.clauses] == [c.status for c in r.clauses]


def test_format_is_readable_and_names_the_verdict() -> None:
    text = contract(ALPFE).format()
    assert "IDENTIFIABILITY CONTRACT for alpfe" in text
    assert "INCOMPLETE" in text


# --- declaration validation ---------------------------------------------------

def test_bad_declarations_raise() -> None:
    with pytest.raises(ValueError, match="kind must be"):
        Unknown(name="x", kind="nonsense", scope="global", enters="t")
    with pytest.raises(ValueError, match="scope must be"):
        Unknown(name="x", kind="scalar", scope="nonsense", enters="t")
    with pytest.raises(ValueError, match="must name the equation term"):
        Unknown(name="x", kind="scalar", scope="global", enters="   ")
    with pytest.raises(ValueError, match="lo < hi"):
        Unknown(name="x", kind="scalar", scope="global", enters="t", bounds=(2.0, 1.0))
    with pytest.raises(ValueError, match="strictly positive lower bound"):
        Unknown(name="x", kind="scalar", scope="global", enters="t",
                bounds=(0.0, 1.0), scale="log")


def test_cal_grade_band_matches_the_project_definition() -> None:
    assert CAL_GRADE_BAND == 0.40
