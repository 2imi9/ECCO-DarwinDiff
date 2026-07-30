"""Declarative identifiability contract for DarwinDiff unknowns (issue #210).

A scientist declares an :class:`Unknown` and gets back a :class:`ContractReport`: a
machine-readable statement of what is inferable about it from the declared
observables, computed BEFORE a fit is trusted.

Why this exists
---------------
ADCME (Xu & Darve) gives a four-way taxonomy of inverse problems and **no
identifiability column**. Their own neural-network full-waveform-inversion slide
shows two visibly different velocity models *at the same loss function value* and
never names the phenomenon. DarwinDiff already computes every ingredient of that
missing column -- Fisher information, CRLB, profile likelihood, prior
contamination, a measured untrained baseline -- and none of it sat behind a
declaration. This module is the declaration.

The taxonomy, and where our objects sit in it::

    parameter inverse   c constant          Carroll's Green's functions; GlobalScalarNet
    function inverse    f(x), NN of coords  the per-cell DINN            <- Track 1
    relation inverse    f(u), NN of state   ScavClosure/EnvCalciteClosure <- Track 2
    stochastic inverse  PhysGNN             the diffusion emulator (a null for us)

Track 1 and Track 2 are different ROWS, not the same method at different scales,
and the relation row is the harder one.

The one rule this module exists to enforce
------------------------------------------
**A missing clause reads as UNAVAILABLE, never as PASS.** The project's whole
methodological posture is that a gap you name is not a gap that gets used against
you, and the alternative -- silently treating absent evidence as satisfied
evidence -- is exactly the failure mode that let a coin-flip result (`diatomgraz`
35/50 against an untrained 34/50, P=0.447) sit in an abstract draft.

Design note: this module CONSUMES evidence rather than computing it. The Fisher
computation needs torch, the box model, real observations and a GPU; making the
contract depend on that would make it untestable and unimportable. The scripts
that already produce those numbers populate an :class:`Evidence` object. What
needs pinning down here is the VERDICT LOGIC, and that is what is tested.

See ``docs/spec/identifiability_contract_spec.md``.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = [
    "Unknown",
    "Evidence",
    "Clause",
    "ContractReport",
    "ClauseStatus",
    "contract",
    "CAL_GRADE_BAND",
    "ALIASING_GATE",
    "EXIT_OK",
    "EXIT_FAIL",
    "EXIT_INCOMPLETE",
]

# ---------------------------------------------------------------------------
# Defaults, all traceable to measured project facts rather than taste.
# ---------------------------------------------------------------------------

#: Recovery band. "Recovered" means rel = |v - reference| / |reference| <= this.
CAL_GRADE_BAND = 0.40

#: Aliasing gate for the RELATION row. Deliberately NOT a dex-span threshold: the
#: 0.30-dex figure widely quoted internally is a ``distill_powerlaw`` default from
#: the calcite branch, and 0.311 dex has already FAILED at aliasing 0.9908 with a
#: held-out R^2 of 0.99999999. Perfect fit, failed verdict. The calibrated pass
#: was near 1.8 dex at aliasing ~0.81. So gate on aliasing, not span.
ALIASING_GATE = 0.95

#: Above this untrained pass probability the prior is doing the work, not the data.
#: `diatomgraz` sits at 0.64 measured, which is why its 35/50 was retired.
PRIOR_CONTAMINATION_LIMIT = 0.25

#: Significance level for "clears its measured null".
ALPHA = 0.05

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_INCOMPLETE = 7

_KINDS = ("scalar", "field", "relation", "stochastic")
_SCOPES = ("global", "per_aoi", "per_cell")


class ClauseStatus:
    """Not an enum, so a report round-trips through JSON as plain strings."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class Unknown:
    """A declared unknown quantity in an inverse problem.

    Args:
        name: identifier, matching the registry name where one exists.
        kind: which row of the inverse-problem taxonomy this sits in.
        scope: what the unknown is resolved over.
        enters: the equation term it appears in. Documentation, but required,
            because an unknown that cannot be pointed at a term in the model is
            not wired to anything -- the silent-failure mode the registry-driven
            finite-difference guard exists to catch.
        identified_by: the observables claimed to identify it. An EMPTY tuple is
            a legitimate and important declaration: it is how the growth pair is
            expressed, and it forces the structural clause to FAIL rather than
            sit unavailable.
        bounds: ``(lo, hi)`` for the sigmoid bounding map. Scalars and fields only.
        scale: the bounding geometry the registry DECLARES it would prefer.
            Metadata only. See ``bounding_map``.
        reference: the published value recovery is graded against, when the study
            is a consistency check. ``None`` for the relation row, where there is
            no reference FUNCTION and therefore no relative band.
        conditioned_on: covariates (field row) or state variables (relation row).
        bounding_map: the geometry ACTUALLY IN USE for the run being described,
            ``"linear"`` (default) or ``"log"``. This is deliberately separate
            from ``scale`` and it is the one the prior clause uses.

            The distinction is load-bearing and easy to get wrong. ``Param.scale``
            is registry metadata; the map a run actually applies is set by the
            ``PARAM_LOG_SCALE`` environment variable, which defaults to empty and
            therefore to LINEAR. So ``scav_rat`` is declared ``scale="log"`` while
            **every published run bounds it linearly**, and its untrained prior
            sits at the linear midpoint 1.515e-6 (2.5x Carroll), not the geometric
            midpoint 3.0e-7 (0.5x Carroll). Reading the registry here would
            misstate where an untrained network starts by a factor of five, which
            is exactly the quantity the measured prior control exists to settle.
    """

    name: str
    kind: str
    scope: str
    enters: str
    identified_by: tuple[str, ...] = ()
    bounds: tuple[float, float] | None = None
    scale: str = "linear"
    reference: float | None = None
    conditioned_on: tuple[str, ...] = ()
    bounding_map: str = "linear"

    def __post_init__(self) -> None:
        if self.kind not in _KINDS:
            raise ValueError(f"kind must be one of {_KINDS}, got {self.kind!r}")
        if self.scope not in _SCOPES:
            raise ValueError(f"scope must be one of {_SCOPES}, got {self.scope!r}")
        if self.scale not in ("linear", "log"):
            raise ValueError(f"scale must be 'linear' or 'log', got {self.scale!r}")
        if self.bounding_map not in ("linear", "log"):
            raise ValueError(
                f"bounding_map must be 'linear' or 'log', got {self.bounding_map!r}")
        if not self.enters.strip():
            raise ValueError(
                f"{self.name}: 'enters' must name the equation term. An unknown that "
                "cannot be pointed at a term in the model is not wired to anything.")
        if self.bounds is not None:
            lo, hi = self.bounds
            if not (lo < hi):
                raise ValueError(f"{self.name}: bounds must satisfy lo < hi, got {self.bounds}")
            if self.scale == "log" and lo <= 0:
                raise ValueError(
                    f"{self.name}: log scale needs a strictly positive lower bound, got {lo}")
        if self.kind == "relation" and self.reference is not None:
            raise ValueError(
                f"{self.name}: a relation unknown is a learned FUNCTION and has no scalar "
                "reference. Relative bands, per-AOI 2-of-3 and the binomial P are all "
                "inapplicable to it; declare reference=None and use the aliasing gate.")

    @property
    def uses_relative_band(self) -> bool:
        """Whether ``rel = |v - ref| / |ref|`` grading applies at all."""
        return self.kind in ("scalar", "field") and self.reference is not None


@dataclass
class Evidence:
    """Measured inputs to the clauses. Every field defaults to absent.

    Absent means UNAVAILABLE, which is a real verdict and not a soft PASS.
    """

    #: Measured untrained pass rate for the MATCHING architecture, in [0, 1].
    untrained_rate: float | None = None
    #: Seeds the untrained rate was measured over. Needed for the rule-of-three floor.
    untrained_n: int | None = None
    #: Trained count and n, per-AOI >=2-of-3.
    recovered_count: int | None = None
    recovered_n: int | None = None
    #: Fisher information for THIS unknown under its identifying observable,
    #: dimensionless (scaled by |theta|). Exactly 0 means it is in the null space.
    fisher_info: float | None = None
    #: Cramer-Rao lower bound, relative-variance. Lower is better constrained.
    crlb: float | None = None
    #: Profile-likelihood verdict, if one was computed: "CURVED" or "FLAT".
    profile: str | None = None
    #: Relation row only: correlation between the candidate law and its
    #: linearisation on the VISITED support. Above the gate means aliased.
    aliasing_corr: float | None = None
    #: Free-parameter count, for the relation row. Context, not a gate.
    n_free_parameters: int | None = None
    #: Anything else worth carrying into the report.
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Clause:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def blocks(self) -> bool:
        return self.status == ClauseStatus.FAIL

    @property
    def missing(self) -> bool:
        return self.status == ClauseStatus.UNAVAILABLE


@dataclass(frozen=True)
class ContractReport:
    unknown: str
    kind: str
    scope: str
    clauses: tuple[Clause, ...]

    @property
    def verdict(self) -> str:
        if any(c.blocks for c in self.clauses):
            return "NOT_IDENTIFIABLE"
        if any(c.missing for c in self.clauses):
            return "INCOMPLETE"
        return "IDENTIFIABLE"

    def exit_code(self) -> int:
        """Mirrors ``verify_run``'s discipline: nonzero means do not trust a number."""
        return {
            "IDENTIFIABLE": EXIT_OK,
            "NOT_IDENTIFIABLE": EXIT_FAIL,
            "INCOMPLETE": EXIT_INCOMPLETE,
        }[self.verdict]

    def clause(self, name: str) -> Clause:
        for c in self.clauses:
            if c.name == name:
                return c
        raise KeyError(f"no clause named {name!r}; have {[c.name for c in self.clauses]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "unknown": self.unknown,
            "kind": self.kind,
            "scope": self.scope,
            "verdict": self.verdict,
            "exit_code": self.exit_code(),
            "clauses": [asdict(c) for c in self.clauses],
        }

    def to_json(self, **kw: Any) -> str:
        return json.dumps(self.to_dict(), **kw)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ContractReport":
        return ContractReport(
            unknown=d["unknown"], kind=d["kind"], scope=d["scope"],
            clauses=tuple(Clause(**c) for c in d["clauses"]),
        )

    def format(self) -> str:
        w = max((len(c.name) for c in self.clauses), default=0)
        head = f"IDENTIFIABILITY CONTRACT for {self.unknown}  [{self.kind}/{self.scope}]"
        rows = [f"  {c.name:<{w}}  {c.status:<15} {c.detail}" for c in self.clauses]
        return "\n".join([head, *rows, f"  => {self.verdict} (exit {self.exit_code()})"])


# ---------------------------------------------------------------------------
# Clause computation
# ---------------------------------------------------------------------------

def _binom_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if n <= 0:
        return float("nan")
    p = min(max(p, 1e-12), 1.0 - 1e-12)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _rule_of_three_floor(rate: float | None, n: int | None) -> tuple[float, str]:
    """Floor a zero-event baseline at 3/n.

    With 0 events in n trials the point estimate is 0, against which ANY nonzero
    count is infinitely significant. 3/n is the standard 95% upper bound and is
    close to the exact Clopper-Pearson value 1 - 0.05**(1/n). Using an UPPER bound
    for the null makes the resulting P CONSERVATIVE, because the binomial tail
    P(X >= k) is increasing in p.
    """
    if rate is None:
        return 0.0, ""
    if rate > 0 or not n:
        return rate, ""
    return 3.0 / n, f" (0/{n} measured, floored at rule-of-three 3/{n}={3.0 / n:.3f})"


def _prior_contamination_clause(u: Unknown, ev: Evidence) -> Clause:
    name = "prior_contamination"
    if not u.uses_relative_band:
        return Clause(
            name, ClauseStatus.NOT_APPLICABLE,
            "no scalar reference, so there is no relative pass band for a prior to fall inside",
        )
    if u.bounds is None:
        return Clause(name, ClauseStatus.UNAVAILABLE, "bounds not declared")

    lo, hi = u.bounds
    ref = float(u.reference)  # type: ignore[arg-type]
    # The map ACTUALLY IN USE, not the registry's declared preference. See the
    # Unknown.bounding_map docstring: PARAM_LOG_SCALE defaults to empty, so every
    # published run is linear even where the registry declares scale="log".
    log_map = u.bounding_map == "log"
    mid = math.sqrt(lo * hi) if log_map else 0.5 * (lo + hi)
    mid_rel = abs(mid - ref) / abs(ref)
    band_lo, band_hi = ref * (1 - CAL_GRADE_BAND), ref * (1 + CAL_GRADE_BAND)
    inside_lo, inside_hi = max(lo, band_lo), min(hi, band_hi)
    if log_map:
        # Under a log map the sigmoid is uniform in log p, so the fraction of the
        # prior that passes is a fraction of the LOG range, not the linear range.
        frac = (max(0.0, math.log(max(inside_hi, lo)) - math.log(max(inside_lo, lo)))
                / (math.log(hi) - math.log(lo)))
    else:
        frac = max(0.0, (inside_hi - inside_lo)) / (hi - lo)
    ev_d = {
        "bounds": [lo, hi], "reference": ref, "midpoint": mid,
        "midpoint_rel_offset": mid_rel, "band_fraction_of_range": frac,
        "declared_scale": u.scale, "bounding_map_in_use": u.bounding_map,
    }
    if u.scale != u.bounding_map:
        ev_d["note"] = (
            f"registry declares scale={u.scale!r} but the run bounds it "
            f"{u.bounding_map!r}; the clause uses the map in use")
    if mid_rel <= CAL_GRADE_BAND:
        return Clause(
            name, ClauseStatus.FAIL,
            f"prior midpoint sits at rel {mid_rel:.3f}, INSIDE the {CAL_GRADE_BAND} band "
            f"({frac:.1%} of the range is a pass); counts measure the bounds, not the data",
            ev_d,
        )
    return Clause(
        name, ClauseStatus.PASS,
        f"prior midpoint at rel {mid_rel:.3f}, outside the {CAL_GRADE_BAND} band "
        f"({frac:.1%} of the range is a pass)",
        ev_d,
    )


def _measured_null_clause(u: Unknown, ev: Evidence) -> Clause:
    name = "measured_null"
    if ev.untrained_rate is None:
        extra = ""
        if u.kind == "relation":
            extra = (" A relation unknown needs a permutation-through-the-rollout null, "
                     "which does not exist in this repo yet.")
        return Clause(
            name, ClauseStatus.UNAVAILABLE,
            "no measured untrained baseline supplied; a count without one is not "
            "interpretable as recovery." + extra,
        )
    p, note = _rule_of_three_floor(ev.untrained_rate, ev.untrained_n)
    ev_d = {"untrained_rate": ev.untrained_rate, "untrained_n": ev.untrained_n,
            "null_p_used": p}
    if ev.untrained_rate > PRIOR_CONTAMINATION_LIMIT:
        ev_d["limit"] = PRIOR_CONTAMINATION_LIMIT
        # Not a FAIL on its own: a high null can still be cleared by a large enough
        # count. It is a FAIL only if the count does not clear it, handled below.
    if ev.recovered_count is None or not ev.recovered_n:
        return Clause(
            name, ClauseStatus.UNAVAILABLE,
            f"baseline is {ev.untrained_rate:.3f}{note} but no trained count supplied "
            "to compare against it",
            ev_d,
        )
    pv = _binom_ge(ev.recovered_count, ev.recovered_n, p)
    ev_d.update({"recovered": f"{ev.recovered_count}/{ev.recovered_n}", "P_ge": pv,
                 "alpha": ALPHA})
    if pv < ALPHA:
        return Clause(
            name, ClauseStatus.PASS,
            f"{ev.recovered_count}/{ev.recovered_n} vs measured null "
            f"{ev.untrained_rate:.3f}{note}, P = {pv:.3g}",
            ev_d,
        )
    return Clause(
        name, ClauseStatus.FAIL,
        f"{ev.recovered_count}/{ev.recovered_n} does NOT clear its measured null "
        f"{ev.untrained_rate:.3f}{note}, P = {pv:.3g}",
        ev_d,
    )


def _structural_clause(u: Unknown, ev: Evidence) -> Clause:
    name = "structural"
    if not u.identified_by:
        return Clause(
            name, ClauseStatus.FAIL,
            "no observable is claimed to identify this unknown, so it is unidentifiable "
            "by declaration; this is a statement about the observing system, not a bug",
            {"identified_by": []},
        )
    if u.kind == "relation":
        if ev.aliasing_corr is None:
            return Clause(
                name, ClauseStatus.UNAVAILABLE,
                "relation unknowns are gated on the ALIASING correlation on the visited "
                f"support (< {ALIASING_GATE}), which was not supplied",
                {"gate": ALIASING_GATE},
            )
        d = {"aliasing_corr": ev.aliasing_corr, "gate": ALIASING_GATE,
             "n_free_parameters": ev.n_free_parameters}
        if ev.aliasing_corr >= ALIASING_GATE:
            return Clause(
                name, ClauseStatus.FAIL,
                f"aliasing {ev.aliasing_corr:.4f} >= {ALIASING_GATE}: the candidate law is "
                "indistinguishable from its linearisation on the states the trajectory "
                "actually visits, so a good fit carries no information about the law",
                d,
            )
        return Clause(
            name, ClauseStatus.PASS,
            f"aliasing {ev.aliasing_corr:.4f} < {ALIASING_GATE} on the visited support", d,
        )
    if ev.fisher_info is None:
        return Clause(name, ClauseStatus.UNAVAILABLE,
                      f"no Fisher information supplied under {list(u.identified_by)}")
    d = {"fisher_info": ev.fisher_info, "identified_by": list(u.identified_by)}
    if ev.fisher_info <= 0.0:
        return Clause(
            name, ClauseStatus.FAIL,
            f"Fisher information is {ev.fisher_info:.3g} under {list(u.identified_by)}: the "
            "unknown lies in the NULL SPACE of the declared observable, so no amount of "
            "that data constrains it",
            d,
        )
    return Clause(
        name, ClauseStatus.PASS,
        f"Fisher information {ev.fisher_info:.3g} > 0 under {list(u.identified_by)}", d,
    )


def _practical_clause(u: Unknown, ev: Evidence) -> Clause:
    name = "practical"
    if ev.profile is None and ev.crlb is None:
        return Clause(name, ClauseStatus.UNAVAILABLE,
                      "neither a CRLB nor a profile-likelihood verdict was supplied")
    d: dict[str, Any] = {}
    if ev.profile is not None:
        d["profile"] = ev.profile
        if ev.profile.upper() == "FLAT":
            return Clause(
                name, ClauseStatus.FAIL,
                "profile likelihood is FLAT. Note this alone is weak evidence: alpfe is "
                "FLAT (0.0235) in this project and recovers 9-10/10, so FLAT-implies-"
                "unrecoverable is falsified by our own data",
                d,
            )
        d["note"] = "profile CURVED => practical, not structural, non-identifiability"
    if ev.crlb is not None:
        d["crlb"] = ev.crlb
    return Clause(name, ClauseStatus.PASS,
                  "; ".join(f"{k}={v}" for k, v in d.items()), d)


def contract(u: Unknown, ev: Evidence | None = None) -> ContractReport:
    """Compute the four-clause identifiability contract for a declared unknown.

    Args:
        u: the declared unknown.
        ev: measured evidence. Omitted entirely means every computable clause is
            ``UNAVAILABLE``, which is the correct verdict for an undeclared study
            and is deliberately NOT the same as passing.

    Returns:
        A :class:`ContractReport` whose ``exit_code`` mirrors ``verify_run``:
        0 identifiable, 1 not identifiable, 7 incomplete.
    """
    ev = ev or Evidence()
    return ContractReport(
        unknown=u.name, kind=u.kind, scope=u.scope,
        clauses=(
            _prior_contamination_clause(u, ev),
            _measured_null_clause(u, ev),
            _structural_clause(u, ev),
            _practical_clause(u, ev),
        ),
    )
