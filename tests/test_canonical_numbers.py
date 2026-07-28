"""The verified result set, as executable constants that documentation cannot contradict.

Why this exists. On 2026-07-25 the flagship `scav_rat` count drifted to 26/50 across twelve
tracked documents. Two independent audits then "corrected" the correct value *back* to the
wrong one, each reasoning from the fact that many documents agreed. The canonical grader
settled it in a single run.

Verified results in this repo are stored as English sentences, and English does not fail
CI. These tests give the numbers a mechanical guard. Documentation is a deliverable here,
so it gets tested like one.

Source of truth (do NOT edit these without re-running the grader):

    uv run python scripts/grade_recovery.py <run-dir> --expect-seeds 50 \
        --params alpfe,scav_rat,diatomgraz,R_PICPOC

    [n50e2k_percell_trio]  n=50/50   gate: VERIFIED (exit 0)
      param       per-AOI>=2/3  joint(cw)  straddle   AOI Cal+ tally
      alpfe              49/50      49/50             eqpa:43 natl:49 sout:49
      scav_rat           25/50      36/50    +11 <<   eqpa:7  natl:20 sout:49
      diatomgraz          3/50       6/50     +3 <<   eqpa:37 natl:1  sout:3
      R_PICPOC           50/50      46/50             eqpa:46 natl:50 sout:40
      iron_pair (per-AOI honest): 25/50   rho(alpfe,scav_rat) = -0.65

RE-DERIVED 2026-07-26. The 50 per-seed JSONs were pulled from Explorer
(/projects/schultz/qi.zim/runs/n50e2k_percell_trio) and re-graded from scratch. Every
value above reproduced exactly, gate exit 0. This matters because the constants below
were previously only asserted -- a guard whose expected values came from the same
documents it polices is circular. They now come from the grader, independently re-run.

The re-grade also settled the per-AOI legs: eqpac 7 / natl 20 / sopac 49. STATUS.md had
carried 8 / 19, which are the subW=1 arm's legs attached to the flagship's joint.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- canonical facts
FLAGSHIP_RUN = "n50e2k_percell_trio"
FLAGSHIP = {                      # per-AOI >=2-of-3 Cal+, n=50, 2000 epochs
    "alpfe": 49,
    "scav_rat": 25,
    "diatomgraz": 3,
    "R_PICPOC": 50,
}
TRIO_PER_AOI = 25                 # equals scav_rat: it is the sole binding leg
TRIO_CELL_WEIGHTED = 33
GLOBAL_SCALAR_TRIO = 0

# Two anchor-off runs exist and differ only in epoch budget. Quoting the 1500-epoch one
# against the 2000-epoch flagship overstates the calcite-anchor effect.
ANCHOR_OFF = {"n50e2k_anchor_off": (2000, 6), "n50_anchor_off": (1500, 4)}
EPOCH_MATCHED_ANCHOR_OFF = 6

# A genuinely different run that legitimately reads 26/50. Any doc mentioning 26/50 must be
# talking about this, not the flagship.
SUBW1_ARM_SCAV_RAT = 26


def test_trio_equals_its_binding_leg():
    """The trio cannot exceed its weakest member, and here it exactly equals it."""
    assert TRIO_PER_AOI == FLAGSHIP["scav_rat"]
    assert TRIO_PER_AOI <= min(FLAGSHIP[p] for p in ("alpfe", "scav_rat", "R_PICPOC"))


def test_cell_weighted_overstates_the_honest_metric():
    """The straddle is the reason per-AOI is the reported metric, not cell-weighted."""
    assert TRIO_CELL_WEIGHTED > TRIO_PER_AOI
    assert GLOBAL_SCALAR_TRIO == 0


def test_anchor_off_controls_are_distinguished_by_epoch():
    assert ANCHOR_OFF["n50e2k_anchor_off"][1] == EPOCH_MATCHED_ANCHOR_OFF
    assert ANCHOR_OFF["n50_anchor_off"][1] != EPOCH_MATCHED_ANCHOR_OFF
    # the flagship is 2000 epochs, so the matched control must be too
    assert ANCHOR_OFF["n50e2k_anchor_off"][0] == 2000


# ---------------------------------------------------------------- documentation guard
def _tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO, capture_output=True, text=True, check=False
    )
    files = [REPO / p for p in out.stdout.split("\n") if p.strip()]
    # The archive is a deliberate historical record and may contain superseded claims.
    return [p for p in files if p.exists() and "docs/archive/" not in p.as_posix()]


#: A line may say 26/50 only if it also identifies the separate arm it belongs to.
_SUBW1_MARKERS = ("subw", "188532", "separate", "not the flagship", "essentially identical")


def test_no_tracked_doc_binds_26_of_50_to_the_flagship():
    """The exact drift that cost hours: 26/50 presented as the flagship scav_rat count."""
    offenders: list[str] = []
    for path in _tracked_markdown():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if "26/50" not in line:
                continue
            low = line.lower()
            if any(m in low for m in _SUBW1_MARKERS):
                continue  # correctly attributed to the subW=1 arm
            if "flagship" in low or "geo1" in low or FLAGSHIP_RUN in low:
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "26/50 is bound to the flagship in:\n  " + "\n  ".join(offenders)
        + f"\n\nThe flagship scav_rat count is {FLAGSHIP['scav_rat']}/50 "
        f"({FLAGSHIP_RUN}, verify_run exit 0). 26/50 is the separate subW=1 arm."
    )


#: The flagship's per-AOI Cal+ legs. The joint 25/50 is set by how often eqpac/natl
#: join the always-recovering Southern Ocean, so quoting the wrong legs beside 25/50
#: misattributes a different run's decomposition to the flagship.
FLAGSHIP_SCAV_RAT_LEGS = {"eqpac": 7, "natl": 20, "sopac": 49}
#: At 4000 epochs (ep4k_n50) scav_rat rises 25 -> 41; the natl leg goes 20 -> 40.
EP4K_SCAV_RAT = (25, 41)
EP4K_NATL_LEG = (20, 40)


def test_flagship_legs_are_consistent_with_the_joint_count():
    """The joint cannot exceed its weakest leg, and 25/50 is set by eqpac+natl."""
    assert FLAGSHIP_SCAV_RAT_LEGS["sopac"] == 49
    assert FLAGSHIP["scav_rat"] == 25
    assert min(FLAGSHIP_SCAV_RAT_LEGS.values()) == FLAGSHIP_SCAV_RAT_LEGS["eqpac"] == 7


#: 26/50 also drifted in RANGE form ("26->41/50"), which the literal "26/50" check
#: below never saw. Same for the natl leg, which drifted as "19->40". Both forms are
#: matched here so the guard covers how the numbers are actually written in prose.
_ARROW = r"(?:->|-->|→|–>|\s+to\s+)"
_RANGE_DRIFTS = (
    (re.compile(rf"\b26\s*{_ARROW}\s*41\b"), "scav_rat 26->41 (flagship is 25->41 at 4000ep)"),
    (re.compile(rf"\bnatl\s+19\s*{_ARROW}\s*40\b", re.IGNORECASE),
     "natl leg 19->40 (flagship natl leg is 20->40)"),
    (re.compile(rf"\b19\s*{_ARROW}\s*40/50\b"), "natl leg 19->40/50 (should be 20->40/50)"),
)


@pytest.mark.parametrize("pattern,label", _RANGE_DRIFTS,
                         ids=[d[1].split()[0] + "-range" for d in _RANGE_DRIFTS])
def test_no_tracked_doc_carries_the_range_form_drift(pattern, label):
    """The exact hole that let two wrong numbers propagate to 13 files.

    The literal-"26/50" check below matched only the bare fraction, so "26->41/50"
    sailed through it into STATUS.md, ONBOARDING.md, the AGU abstract and nine
    findings docs. A guard that only catches one spelling of a number is not a guard.
    """
    offenders: list[str] = []
    for path in _tracked_markdown():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, f"{label} in:\n  " + "\n  ".join(offenders)


#: The two emulator baseline comparisons have DIFFERENT seed spreads, and swapping them
#: understates the AR(1) result's stability. Source: 2026-07-23_emulator_multiseed.md:9,32.
EMULATOR_VS_PERSISTENCE = (0.055, 0.013)
EMULATOR_VS_SEASONAL_AR1 = (-0.161, 0.015)

_AR1_WRONG_SPREAD = re.compile(r"0\.161\s*(?:±|\+/-)\s*0\.013")


#: The 4000-epoch confirmation run, re-graded 2026-07-28 from the 50 per-seed JSONs on
#: AICR (/scratch/qi_zim_neu/confirm/ep4k_n50), gate exit 0. Until then this was the last
#: document-only Track-1 headline -- and it is quoted in the AGU abstract draft.
#:
#:   [ep4k] n=50/50  alpfe 49/50 | scav_rat 41/50 | diatomgraz 8/50 | R_PICPOC 50/50
#:          scav_rat legs  eqpac 6 / natl 40 / sopac 48
EP4K = {"alpfe": 49, "scav_rat": 41, "diatomgraz": 8, "R_PICPOC": 50}
EP4K_SCAV_RAT_LEGS = {"eqpac": 6, "natl": 40, "sopac": 48}


def test_ep4k_is_the_optimisation_limited_arm():
    """2000 -> 4000 epochs moves scav_rat 25 -> 41 while eqpac barely moves.

    That contrast is the whole 'closeable optimisation component plus a residual
    information component' argument: natl 20 -> 40 is optimisation, eqpac 7 -> 6 is not.
    """
    assert EP4K["scav_rat"] == EP4K_SCAV_RAT[1] == 41
    assert FLAGSHIP["scav_rat"] == EP4K_SCAV_RAT[0] == 25
    assert EP4K_SCAV_RAT_LEGS["natl"] == EP4K_NATL_LEG[1] == 40
    # eqpac does NOT improve with 2x the epochs -- it is information-limited
    assert EP4K_SCAV_RAT_LEGS["eqpac"] <= FLAGSHIP_SCAV_RAT_LEGS["eqpac"]
    # alpfe and R_PICPOC are already saturated and stay there
    assert EP4K["alpfe"] == FLAGSHIP["alpfe"] == 49
    assert EP4K["R_PICPOC"] == FLAGSHIP["R_PICPOC"] == 50


def test_ar1_and_persistence_spreads_are_not_swapped():
    """+/-0.013 belongs to persistence; +/-0.015 belongs to seasonal AR(1).

    Caught by Greptile on PR #202 after -0.161 +/- 0.013 had propagated to ten files,
    including STATUS.md and the README. STATUS.md carried BOTH spellings -- 0.015 at
    L79 and 0.013 at L115 -- so a reader copying from the canonical doc had even odds
    of taking the wrong one. That is how it spread.
    """
    assert EMULATOR_VS_SEASONAL_AR1[1] != EMULATOR_VS_PERSISTENCE[1]
    offenders: list[str] = []
    for path in _tracked_markdown():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if _AR1_WRONG_SPREAD.search(line):
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "seasonal-AR(1) skill quoted with persistence's spread (should be "
        f"{EMULATOR_VS_SEASONAL_AR1[0]} +/- {EMULATOR_VS_SEASONAL_AR1[1]}) in:\n  "
        + "\n  ".join(offenders)
    )


def test_no_tracked_doc_quotes_the_unmatched_anchor_off_against_the_flagship():
    """4/50 is the 1500-epoch control; quoting it beside the 2000-epoch flagship
    overstates how much the real calcite anchor is doing."""
    offenders: list[str] = []
    pat = re.compile(r"anchor[- ]off[^.\n]{0,80}4/50", re.IGNORECASE)
    for path in _tracked_markdown():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            if not pat.search(line):
                continue
            if "1500" in line or "n50_anchor_off" in line:
                continue  # correctly labelled as the 1500-epoch run
            offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "unlabelled anchor-off 4/50 (the 1500-epoch control) in:\n  " + "\n  ".join(offenders)
        + f"\n\nThe epoch-matched control is {EPOCH_MATCHED_ANCHOR_OFF}/50 (n50e2k_anchor_off, 2000 ep)."
    )


@pytest.mark.parametrize("retracted", [
    "beats persistence",
    "9-month horizon",
    "~9-month",
])
def test_retracted_emulator_claims_stay_retracted(retracted):
    """Both were withdrawn: 'beats persistence' used a weak baseline, and the ~9-month
    horizon was a delta_t calendar artifact. A doc may discuss them only as retracted."""
    offenders: list[str] = []
    for path in _tracked_markdown():
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        # A document-level retraction banner near the top exempts the whole file. That is
        # the correct scholarly form for a dated findings note: keep the original text as
        # the record of what was believed, and mark it superseded once at the head.
        head = "\n".join(lines[:15]).lower()
        if any(w in head for w in ("superseded", "retracted", "deflation")):
            continue
        for n, line in enumerate(lines, 1):
            if retracted.lower() not in line.lower():
                continue
            # Look at a WINDOW, not one line. Hand-wrapped prose routinely splits a
            # sentence like "...quoted a ~9-month horizon ... all three of which have been
            # retracted" across two lines, and a line-local check calls that an offender.
            # A paragraph-scale window is needed: a retractions LIST puts its header
            # several lines above the entries, and a metric definition may be justified
            # a few lines below where it is introduced.
            window = "\n".join(lines[max(0, n - 8):n + 6]).lower()
            if any(w in window for w in ("retract", "superseded", "no longer", "withdraw",
                                         "wrong", "artifact", "corrected", "deflat",
                                         "does not", "did not", "cannot",
                                         "not significant", "weak baseline",
                                         "persistence is weak", "seasonal ar(1)",
                                         "retire", "open, testable")):
                continue
            offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        f"'{retracted}' asserted without a retraction marker in:\n  " + "\n  ".join(offenders)
    )
