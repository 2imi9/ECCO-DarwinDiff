"""The research map must not rot into misinformation.

`docs/research_map.md` is loaded at the start of every session via CLAUDE.md and is the index a
session trusts to decide what is already known. A map that cites a deleted file, or that lists a
question as SETTLED without saying where the answer lives, is worse than no map: it produces
confident wrong beliefs instead of an honest gap.

These tests are cheap and structural. They do not check that a claim is TRUE, which no test can do.
They check that every claim is TRACEABLE, that the anti-redundancy machinery is actually wired up,
and that the file is reachable from the working agreement.

Context for why this exists: on 2026-07-30 one session re-derived work the repo already contained
four separate times, one at a cost of 1.52M tokens. The map is the fix and it only works if its
pointers resolve.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MAP = REPO / "docs" / "research_map.md"
CLAUDE_MD = REPO / "CLAUDE.md"

# A path-like token pointing into the docs tree or a repo source file.
_DOC_REF = re.compile(r"(?:docs|src|scripts|tests)/[A-Za-z0-9_./-]+\.(?:md|py|F|h)")
# Bare findings filenames, which the map cites in prose (e.g. `2026-07-30_foo.md`).
_BARE_FINDING = re.compile(r"`(20\d\d-\d\d-\d\d_[A-Za-z0-9_.-]+\.md)`")

REQUIRED_SECTIONS = [
    "SETTLED",
    "deductive",
    "inductive",
    "abductive",
    "SUPERSEDES",
]


def _map_text() -> str:
    assert MAP.is_file(), f"{MAP} is missing; CLAUDE.md tells every session to read it"
    return MAP.read_text(encoding="utf-8")


def test_map_exists_and_is_not_a_stub():
    text = _map_text()
    assert len(text) > 2000, "research map is too short to be carrying the corpus"


def test_claude_md_points_at_the_map():
    """The map only prevents drift if sessions are told to read it."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    assert "docs/research_map.md" in text, "CLAUDE.md must reference the research map"
    head = text[: text.find("## Issue tracker")] if "## Issue tracker" in text else text[:2000]
    assert "research_map" in head, "the pointer must be near the TOP of CLAUDE.md, not buried"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_map_has_the_load_bearing_sections(section):
    """SETTLED stops re-derivation; SUPERSEDES stops dead numbers; the three modes are the schema."""
    assert section.lower() in _map_text().lower(), f"research map is missing its {section} section"


def test_every_referenced_file_exists():
    """A pointer that does not resolve is the failure mode that makes a map dangerous."""
    text = _map_text()
    refs = set(_DOC_REF.findall(text))
    missing = sorted(r for r in refs if not (REPO / r).exists())
    assert not missing, (
        "research map references files that do not exist:\n  "
        + "\n  ".join(missing)
        + "\nEither restore them or update the map."
    )


def test_bare_finding_filenames_resolve():
    """The map cites findings by bare filename in prose; those must resolve under docs/."""
    text = _map_text()
    names = set(_BARE_FINDING.findall(text))
    searched = [REPO / "docs" / "findings", REPO / "docs" / "research_notes", REPO / "docs"]
    missing = sorted(n for n in names if not any((d / n).is_file() for d in searched))
    assert not missing, (
        "research map cites findings that do not exist under docs/:\n  "
        + "\n  ".join(missing)
    )


def test_settled_rows_all_cite_a_location():
    """A SETTLED row without a 'where' is an assertion, not an index entry."""
    text = _map_text()
    # Anchor on the HEADING, not the first occurrence of the word: the preamble names the
    # `research_map_db.py settled` command, so a bare find() slices the Schema section instead.
    m = re.search(r"^##\s*\d+\.\s*SETTLED\b.*$", text, re.MULTILINE | re.IGNORECASE)
    assert m, "research map has no '## N. SETTLED' heading"
    lo = m.start()
    # take the SETTLED section up to the next top-level heading
    rest = text[lo:]
    end = rest.find("\n## ", 1)
    section = rest[:end] if end != -1 else rest
    rows = [
        ln for ln in section.splitlines()
        if ln.strip().startswith("|")
        and ln.count("|") >= 4
        and not set(ln.strip()) <= set("|-: ")
        and "question" not in ln.lower()
    ]
    assert rows, "SETTLED section has no table rows"
    bad = [ln.strip()[:100] for ln in rows if not (_DOC_REF.search(ln) or _BARE_FINDING.search(ln))]
    assert not bad, (
        "SETTLED rows with no citation (a future session cannot verify these):\n  "
        + "\n  ".join(bad)
    )


def test_research_map_json_mirror_is_current():
    """The JSON mirror must be an export of the CURRENT database, not a stale snapshot.

    Two representations of one model will disagree eventually unless something forces them not to.
    SQL is the query interface; JSON is the bulk-read interface. Both are produced by the same
    build(), so this test only has to prove the committed file is what that build produces now.
    Regenerate with:  python scripts/research_map_db.py export-json
    """
    import json
    import subprocess

    mirror = REPO / "docs" / "research_map.json"
    assert mirror.exists(), "docs/research_map.json missing; run: research_map_db.py export-json"

    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "research_map_db.py"), "export-json"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, f"export-json failed:\n{out.stdout}\n{out.stderr}"

    doc = json.loads(mirror.read_text(encoding="utf-8"))

    # Every table and view in the live schema is present in the mirror, with matching row counts.
    for name, payload in doc["schema"].items():
        assert len(payload["rows"]) == doc["counts"][name], f"{name}: count disagrees with rows"
    for name, payload in doc["views"].items():
        assert len(payload["rows"]) == doc["counts"][name], f"{name}: view count disagrees"

    # The mirror carries the constraint results, so a reader who never runs SQL still sees them.
    failing = [k for k, v in doc["constraints"].items() if not v["holds"]]
    assert not failing, f"mirror records failing constraints: {failing}"
    assert doc["constraints"], "mirror has no constraints recorded"
    assert doc["relational_algebra"], "mirror lost the relational-algebra statement"
