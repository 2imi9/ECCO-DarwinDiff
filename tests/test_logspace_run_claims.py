"""Guards on what the global log-space run (AICR job 204877) actually shows.

Why this exists. `docs/index.md` and `README.md` both stated that this run achieved
"mass ratio 1.000". Its own committed artifact records a +129.7% relative mass drift in
Chl1. The claim was wrong in two public documents for three days.

Positivity and mass conservation are DIFFERENT properties. The log-space fix delivered the
first and not the second, and the prose collapsed them into "physically valid". These tests
read the artifact and refuse to let that happen again.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ARTIFACT = REPO / "docs" / "findings" / "track2_runs" / "global_fields_logspace.json"

pytestmark = pytest.mark.skipif(not ARTIFACT.is_file(), reason="log-space artifact not committed")


@pytest.fixture(scope="module")
def run():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_positivity_does_hold(run):
    """The half of the claim that is true: zero negative output on every tracer."""
    pos = run["rollout"]["positivity"]
    assert pos, "no positivity block"
    for tracer, d in pos.items():
        assert d["frac_negative"] == 0.0, f"{tracer} has negative output"
    assert run["rollout"]["max_frac_negative"] == 0.0


def test_mass_is_not_conserved_in_this_run(run):
    """The half that is false. Pinned so nobody re-asserts conservation from prose.

    If a future run genuinely conserves mass, this test SHOULD fail -- that is the
    signal to update the documents, having checked the artifact rather than assumed.
    """
    drift = {k: abs(v["relative_drift"]) for k, v in run["rollout"]["mass_drift"].items()}
    assert drift["Chl1"] > 1.0, f"Chl1 drift {drift['Chl1']:.3f} no longer >100%; re-check the docs"
    assert run["rollout"]["mass_conserve_enforced"] is False
    # DIC/ALK are the only tracers that hold, and the prose generalised from them.
    assert drift["DIC"] < 0.01 and drift["ALK"] < 0.01


def _tracked_docs() -> list[Path]:
    import subprocess
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=REPO,
                         capture_output=True, text=True, check=False)
    return [REPO / p for p in out.stdout.split("\n")
            if p.strip() and "docs/archive/" not in p and (REPO / p).exists()]


_MASS_CLAIM = re.compile(r"mass\s+ratio\s+1\.000|mass\s+1\.000", re.IGNORECASE)
_THIS_RUN = re.compile(r"204877|log-?space", re.IGNORECASE)


def test_no_doc_credits_this_run_with_mass_conservation():
    """A line may say 'mass ratio 1.000' only if it is NOT about the log-space run."""
    offenders: list[str] = []
    for path in _tracked_docs():
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        for n, line in enumerate(lines, 1):
            if _MASS_CLAIM.search(line) and _THIS_RUN.search(line):
                offenders.append(f"{path.relative_to(REPO).as_posix()}:{n}: {line.strip()[:110]}")
    assert not offenders, (
        "mass conservation credited to the log-space run, which drifts Chl1 +129.7%:\n  "
        + "\n  ".join(offenders)
    )
