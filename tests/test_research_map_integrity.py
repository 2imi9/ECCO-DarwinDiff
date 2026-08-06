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
# An answer whose only source is a gitignored local-only note. This IS a location -- it names
# the file -- it is simply one a reader cannot open, and gen_research_map.docref() marks it
# explicitly rather than dropping the row and silently deleting an answered question.
_LOCAL_ONLY = re.compile(r"LOCAL-ONLY source, not in the repo: [A-Za-z0-9_.\-]+\.md")

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


def _tracked_files() -> set[str]:
    """Files that exist IN THE REPOSITORY, not merely on this disk.

    This distinction is the whole point. `Path.exists()` is local state: seven
    docs/research_notes files are gitignored by name as deliberately local-only working
    notes, so a disk check passed on the author's machine for weeks while the committed map
    cited seven files nobody who cloned the repo could open. CI caught it; the author's
    suite never could. Same absent-is-not-equal shape the repo keeps hitting, one level up.
    """
    import subprocess
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True)
    return {line.strip().replace("\\", "/") for line in out.stdout.splitlines() if line.strip()}


def test_every_referenced_file_is_tracked_in_the_repo():
    """A pointer that does not resolve FOR A READER is the failure that makes a map dangerous.

    Checked against `git ls-files`, deliberately NOT against the filesystem, so this fails on
    the machine that introduced it rather than only in CI.
    """
    text = _map_text()
    refs = set(_DOC_REF.findall(text))
    tracked = _tracked_files()
    missing = sorted(r for r in refs if r not in tracked)
    assert not missing, (
        "research map references files that are not tracked in the repo:\n  "
        + "\n  ".join(missing)
        + "\nThese may exist on your disk and still be invisible to every other reader "
          "(e.g. gitignored local-only notes). Either track them or drop the citation; "
          "regenerate with: python scripts/gen_research_map.py"
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
    bad = [ln.strip()[:100] for ln in rows
           if not (_DOC_REF.search(ln) or _BARE_FINDING.search(ln) or _LOCAL_ONLY.search(ln))]
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

    # Snapshot BEFORE regenerating. This test used to run export-json -- which WRITES this file --
    # and only then read it, so it compared the freshly generated bytes against themselves and
    # could never fail on a stale committed mirror. Verified 2026-08-04 by setting
    # counts.settled = 99999 and truncating the rows to 3: the test passed. That is the same
    # inert-gate shape as the truncated-prose search and the disk-vs-repo citation check, in the
    # one test standing between the repo and a mirror that disagrees with the corpus.
    committed = mirror.read_bytes()

    out = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "research_map_db.py"), "export-json"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert out.returncode == 0, f"export-json failed:\n{out.stdout}\n{out.stderr}"

    regenerated = mirror.read_bytes()
    if committed != regenerated:
        mirror.write_bytes(committed)          # leave the tree as we found it
        raise AssertionError(
            f"docs/research_map.json is STALE: committed {len(committed):,} bytes, "
            f"build produces {len(regenerated):,}. The committed mirror does not match what "
            "the current corpus generates.\n"
            "Regenerate and commit it with the change that caused it:\n"
            "    python scripts/gen_research_map.py\n"
            "    python scripts/research_map_db.py export-json"
        )

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


# --------------------------------------------------------------------- #228: no truncated prose
#
# `gen_research_map.cell()` cuts every markdown cell (settled answers at 240 characters), and
# research_map_db.py parses that markdown. So the database -- and `settled`, the check CLAUDE.md
# makes mandatory before starting work -- searched CUT prose. Measured 2026-08-04 before the fix:
# 87% of settled answers truncated, 35% of the corpus unsearchable, and a miss printed "may be
# genuinely new work", which reads exactly like a true negative.


def _db():
    sys.path.insert(0, str(REPO / "scripts"))
    import research_map_db as rmdb
    return rmdb


def test_database_holds_the_corpus_full_text_not_the_truncated_markdown():
    """Every rehydrated column must match the corpus length, not the markdown's cut length."""
    import json

    rmdb = _db()
    con = rmdb.build()
    corpus = json.loads(rmdb.CORPUS.read_text(encoding="utf-8"))

    longest = max(len(rmdb._flat(r.get("answer"))) for r in corpus["settled"])
    db_longest = con.execute("SELECT max(length(answer)) FROM settled").fetchone()[0]
    assert db_longest == longest, (
        f"settled.answer in the DB tops out at {db_longest} but the corpus has {longest}; "
        "the markdown truncation is leaking into the database (#228)"
    )
    assert longest > 240, (
        "this test is vacuous unless the corpus actually contains an answer longer than the "
        f"240-char markdown cut; longest is {longest}"
    )


def test_settled_search_finds_text_past_the_markdown_cut():
    """A term that appears only after character 240 of an answer must still be findable."""
    import json

    rmdb = _db()
    con = rmdb.build()
    corpus = json.loads(rmdb.CORPUS.read_text(encoding="utf-8"))

    probe = None
    for r in corpus["settled"]:
        flat = rmdb._flat(r.get("answer"))
        if len(flat) > 400:
            for word in re.findall(r"[A-Za-z]{8,}", flat[320:]):
                if word.lower() not in flat[:240].lower():
                    probe = word.lower()
                    break
        if probe:
            break
    assert probe, "no corpus answer carries a distinctive word past char 320; cannot probe"

    hits = con.execute(
        "SELECT count(*) FROM settled WHERE lower(answer) LIKE ?", (f"%{probe}%",)).fetchone()[0]
    assert hits, f"{probe!r} appears past the 240-char cut and settled cannot find it (#228)"


def test_truncation_constraint_is_not_vacuous():
    """Negative control: with the corpus unavailable the constraint MUST fire.

    A check that cannot fail teaches readers to ignore the gate -- the exact reasoning recorded
    for the vacuous supersedes join and for STRADDLE staying advisory in verify_run.
    """
    import pathlib

    rmdb = _db()
    sql = next(sql for name, sql in rmdb.CONSTRAINTS if "#228" in name)

    con = rmdb.build()
    assert not con.execute(sql).fetchall(), "prose is truncated with the corpus present"

    real = rmdb.CORPUS
    try:
        rmdb.CORPUS = pathlib.Path("no_such_research_map_corpus.json")
        degraded = rmdb.build()
        assert degraded.execute(sql).fetchall(), (
            "constraint found nothing even with rehydration disabled -- it is vacuous"
        )
    finally:
        rmdb.CORPUS = real


def test_rehydration_leaves_no_row_unmatched_or_ambiguous():
    """Silent partial coverage is the failure mode; require the join to be total.

    Ambiguity is real here: ded110 and ded111 share their first 60 normalised characters. The
    tie is broken by prefix containment, not by position, so both resolve.
    """
    rmdb = _db()
    rmdb.build()
    counts = rmdb.LAST_REHYDRATION
    assert counts.get("widened", 0) > 1000, f"suspiciously few rows rehydrated: {counts}"
    assert counts.get("unmatched", 0) == 0, f"rows the corpus could not match: {counts}"
    assert counts.get("ambiguous", 0) == 0, f"rows left truncated by key collision: {counts}"


def test_rehydration_does_not_change_row_counts_or_ids():
    """#227 makes claim ids positional, so a step that added or dropped a row would renumber
    hundreds of citations. Rehydration may only ever widen text in place."""
    import pathlib

    rmdb = _db()
    con = rmdb.build()
    with_corpus = {
        t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]  # - literal names
        for t in ("settled", "claim", "trap", "supersedes", "hypothesis")
    }
    ids = [r[0] for r in con.execute("SELECT cl_id FROM claim ORDER BY cl_id").fetchall()]

    real = rmdb.CORPUS
    try:
        rmdb.CORPUS = pathlib.Path("no_such_research_map_corpus.json")
        bare = rmdb.build()
        without = {
            t: bare.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in with_corpus
        }
        bare_ids = [r[0] for r in bare.execute("SELECT cl_id FROM claim ORDER BY cl_id").fetchall()]
    finally:
        rmdb.CORPUS = real

    assert with_corpus == without, f"rehydration changed row counts: {with_corpus} vs {without}"
    assert ids == bare_ids, "rehydration changed claim ids; #227 makes those positional"


def test_settled_search_matches_terms_not_only_contiguous_phrases():
    """The mandatory pre-work check must not report a false negative on a multi-word query.

    Until 2026-08-05 `cmd_settled` ran ONE `LIKE` over the whole query string, so a multi-word
    search only hit when those words were adjacent in the prose. Measured on the corpus that day,
    5 of 7 plausible queries printed "This may be genuinely new work" while the answer was
    present; "R_PICPOC anchor Daniels" returned nothing against 22 rows containing all three
    words. That is the same false-negative shape #228 fixed for truncation, in the one command
    CLAUDE.md tells every session to run before starting.

    NEGATIVE CONTROL is built in: the last assertion pins that a genuinely absent term still
    reports absent, so this test fails if the fix is "match everything".
    """
    import subprocess
    import sys

    def settled(term):
        out = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "research_map_db.py"), "settled", term],
            cwd=REPO, capture_output=True, text=True, check=False,
        )
        assert out.returncode == 0, out.stderr
        return out.stdout

    # scattered terms, all present in the corpus, none adjacent
    scattered = settled("R_PICPOC anchor Daniels")
    assert "ALREADY SETTLED" in scattered, "scattered terms must still find the answer"
    assert "not necessarily adjacent" in scattered, "the match mode should be stated"

    # a single term must behave exactly as before, as an exact-phrase hit
    single = settled("alpfe")
    assert "ALREADY SETTLED" in single and "exact phrase" in single

    # NEGATIVE CONTROL: something genuinely absent must still read absent
    absent = settled("zzzz quixotic nonexistent tokens")
    assert "nothing settled" in absent
    assert "may be genuinely new work" in absent
