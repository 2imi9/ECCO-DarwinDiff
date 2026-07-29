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

# A SECOND legitimate context for 26/50 appeared on 2026-07-29: the independent
# reproduction of the flagship on different hardware, compiler and torch build,
# which landed scav_rat at 26/50 against the published 25/50. Prose describing that
# necessarily mentions both "flagship" and "26/50" in one line, e.g.
#   "the flagship's independent reproduction (scav_rat 26/50 versus published 25/50)"
# and that is correct usage, not the drift this guard exists to catch.
#
# The exemption is deliberately NARROW. The drift is "the flagship recovers 26/50"
# stated flatly; the legitimate form always names the act of reproducing, or cites
# the published 25/50 in the same breath. Requiring one of those markers keeps the
# guard sharp while allowing the true sentence.
_REPRODUCTION_MARKERS = (
    "reproduc",        # reproduces / reproduced / reproduction
    "re-run",
    "rerun",
    "published 25/50",
    "vs 25/50",
    "versus 25/50",
    "falsification condition",
)


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
            if any(m in low for m in _REPRODUCTION_MARKERS):
                continue  # correctly attributed to the independent reproduction
            if "flagship" in low or "geo1" in low or FLAGSHIP_RUN in low:
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "26/50 is bound to the flagship in:\n  " + "\n  ".join(offenders)
        + f"\n\nThe flagship scav_rat count is {FLAGSHIP['scav_rat']}/50 "
        f"({FLAGSHIP_RUN}, verify_run exit 0). 26/50 is the separate subW=1 arm."
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


def test_the_26_of_50_guard_still_catches_real_drift(tmp_path, monkeypatch):
    """The reproduction exemption must NOT blunt the guard it was added to.

    Added 2026-07-29 alongside _REPRODUCTION_MARKERS. The exemption lets through
    prose that names the act of reproducing; it must still catch the flat claim
    "the flagship recovers scav_rat 26/50", which is the drift that cost hours.
    """
    drift = "The flagship recovers scav_rat 26/50 per-AOI."
    legit = "The flagship's independent reproduction gave scav_rat 26/50 vs published 25/50."
    subw = "The separate subW=1 arm gives scav_rat 26/50."

    def offends(line: str) -> bool:
        low = line.lower()
        if "26/50" not in line:
            return False
        if any(m in low for m in _SUBW1_MARKERS):
            return False
        if any(m in low for m in _REPRODUCTION_MARKERS):
            return False
        return "flagship" in low or "geo1" in low or FLAGSHIP_RUN in low

    assert offends(drift), "the guard stopped catching the drift it exists for"
    assert not offends(legit), "the guard rejects correct reproduction prose"
    assert not offends(subw), "the guard rejects correct subW=1 attribution"
