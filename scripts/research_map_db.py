#!/usr/bin/env python3
r"""Make the research map queryable: a real relational database over what the project knows.

WHY THIS EXISTS. The research map is the index a session trusts to decide what is already known.
Prose you must read and remember is a weak guarantee; a query you run is a strong one. On 2026-07-30
one session re-derived work the repo already contained FOUR times, once at 1.52M tokens, because
nothing made "has this been settled?" a one-command question. This makes it one, and then goes
further: claims are JOINED to the evidence and the parameters they rest on, so an unsupported or
retracted claim is findable by query rather than by memory.

SOURCES. The database is assembled from five places, so no relation has to be maintained by hand
twice:

    docs/research_map.md            settled, claim, hypothesis, supersedes, trap, derives
    docs/findings/research_map_corpus.json  the SAME rows, untruncated -- see TEXT below
    src/darwindiff/carroll6.py      parameter  (the registry is the single source of truth)
    docs/findings/citation_audit.json   citation  (written by the citation-verification workflow)
    docs/findings/*.md              document   (existence and supersession banners)

The document source matters: it lets a query ask "does this claim cite a file that exists, and does
that file carry a RETRACTED banner?" without anybody remembering to cross-check.

TEXT. The markdown is a READING view and `gen_research_map.cell()` cuts every cell in it -- settled
answers at 240 characters, claim statements at 230, traps at 220. This module parses that markdown,
so until 2026-08-04 the database held the CUT text and `settled` searched it: 87% of settled answers
were truncated, 35% of the corpus (83,957 of 242,118 characters) was unsearchable, and a miss
printed "This may be genuinely new work" -- a false negative indistinguishable from a true one, in
the tool built to prevent exactly that. `_rehydrate()` now widens every prose column back to the
corpus text after the parse. The markdown keeps its truncation; the database does not. Issue #228.

USAGE

    python scripts/research_map_db.py settled daily      # <- RUN THIS BEFORE STARTING WORK
    python scripts/research_map_db.py check              # integrity constraints, exit 1 on violation
    python scripts/research_map_db.py trace D1           # what a claim rests on, and what rests on it
    python scripts/research_map_db.py param scav_rat     # everything known about one parameter
    python scripts/research_map_db.py superseded 0.408   # is this number dead?
    python scripts/research_map_db.py dangerous          # live claims resting on weak ground
    python scripts/research_map_db.py sql "SELECT ..."   # arbitrary read-only SQL

ENFORCED (`check` exits 1). Relational algebra, written in SQL in CONSTRAINTS below:

    pi_cl(sigma_{live}(CLAIM)) INTERSECT pi_old(SUPERSEDES)   = {}   on normalised PROSE, not ids
    sigma_{mode=inductive AND numbers IS NULL}(CLAIM)         = {}   presence only, see caveat
    sigma_{doc NOT IN DOCUMENT}(CLAIM)                        = {}   DOCUMENT is the REPO, not disk
    sigma_{verdict=RESOLVES_MISMATCH}(CITATION)               = {}
    sigma_{verdict IN (DEAD, FABRICATED)}(CITATION)           = {}
    sigma_{doc IS NULL}(SETTLED)                              = {}
    sigma_{status IS NULL}(CLAIM)                             = {}
    sigma_{prose ENDS WITH ellipsis}(SETTLED u CLAIM u ...)   = {}   no markdown cut leaked in

REPORTED BUT NOT ENFORCED (`check` prints, never fails). These are real properties that currently
have violations; gating on them would fail every run and train readers to ignore the gate:

    sigma_{live}(CLAIM) |><| sigma_{local_only}(DOCUMENT), sole cite       -- 2 rows
    CLAIM |><| SUPPORTS |><| sigma_{gate != exit0}(EVIDENCE) where live     -- 39 rows
    sigma_{live}(CLAIM) |><| sigma_{retracted}(DOCUMENT)                    -- 26 rows
    CLAIM - pi_cl(SUPPORTS)                                                 -- 291 rows

THREE CAVEATS, stated because a passing `check` otherwise reads stronger than it is:
  * "carries its untrained null" is a PRESENCE check on the merged `n / null` column. The corpus
    has no separate null field, so no constraint here can verify a matched baseline exists.
  * the citation constraints run over the audit's EXCEPTION rows only (1 of 130). `check` prints
    its own coverage line for this reason.
  * DOCUMENT is built from `git ls-files` plus the declared LOCAL_ONLY_DOCS, never from a disk
    walk. Enumerating from disk made the orphan constraint pass on the author's machine and fail
    in CI, where the seven gitignored notes do not exist. The mirror is now byte-identical from a
    tracked-files-only checkout, which is the negative control ADR-0004 asks for.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path

# Windows consoles default to cp1252 and the map contains typographic minus signs and arrows.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-reconfigurable stream
        pass

REPO = Path(__file__).resolve().parents[1]
MAP = REPO / "docs" / "research_map.md"
CITATION_AUDIT = REPO / "docs" / "findings" / "citation_audit.json"
CORPUS = REPO / "docs" / "findings" / "research_map_corpus.json"

#: The character `gen_research_map.cell()` appends when it cuts a cell. Its presence in the
#: database after `_rehydrate` means a row failed to match the corpus and is still truncated.
ELLIPSIS = "…"

SCHEMA = """
-- ---------------------------------------------------------------- core entities
CREATE TABLE document (
    path       TEXT PRIMARY KEY,
    name       TEXT,
    date       TEXT,
    retracted  INTEGER DEFAULT 0,   -- carries a SUPERSEDED / RETRACTED / CORRECTED banner
    words      INTEGER,
    local_only INTEGER DEFAULT 0    -- 1 = deliberately gitignored; on disk here, absent for a reader
);

CREATE TABLE parameter (
    name          TEXT PRIMARY KEY,
    carroll_value REAL,
    bounds_lo     REAL,
    bounds_hi     REAL,
    scale         TEXT,
    in_denominator INTEGER          -- one of the 4 observables, vs the excluded growth pair
);

CREATE TABLE evidence (
    ev_id   TEXT PRIMARY KEY,
    kind    TEXT,                   -- run | ablation | audit | source-read | literature | osse
    locator TEXT,                   -- artifact path or run dir
    job     TEXT,
    gate    TEXT,                   -- exit0 | exit2 | ungated | n/a
    n       INTEGER,
    date    TEXT
);

CREATE TABLE claim (
    cl_id         TEXT PRIMARY KEY,
    statement     TEXT,
    mode          TEXT,             -- deductive | inductive | abductive
    status        TEXT,             -- live | retracted | superseded | pending | unverified
    detail        TEXT,             -- derivation, or what prompted it, or the evidence summary
    n             TEXT,
    null_baseline TEXT,
    doc           TEXT,
    parameter     TEXT,             -- FK-ish into parameter.name when the claim is about one
    track         TEXT              -- track1 | track2 | method | data
);

-- ---------------------------------------------------------------- relationships
CREATE TABLE supports (              -- claim <- evidence, many to many
    cl_id    TEXT,
    ev_id    TEXT,
    relation TEXT                    -- establishes | qualifies | refutes
);

CREATE TABLE derives (               -- deductive dependency edges: to_cl follows FROM from_cl
    from_cl TEXT,
    to_cl   TEXT,
    rule    TEXT
);

CREATE TABLE supersedes (
    old    TEXT,
    new    TEXT,
    reason TEXT,
    doc    TEXT                       -- where the retraction is recorded; the chain needs a cite
);

CREATE TABLE hypothesis (
    hy_id     TEXT PRIMARY KEY,
    statement TEXT,
    predicts  TEXT,
    falsifier TEXT,
    status    TEXT,                  -- open | tested-confirmed | tested-refuted | abandoned
    prereg    TEXT
);

CREATE TABLE settled (
    question TEXT,
    answer   TEXT,
    doc      TEXT,
    dont     TEXT
);

CREATE TABLE citation (
    doi        TEXT,
    verdict    TEXT,                 -- RESOLVES_MATCHES | RESOLVES_MISMATCH | DEAD | SUSPECT_FABRICATED
    claimed    TEXT,
    actual     TEXT,
    doc        TEXT,
    deliberate INTEGER DEFAULT 0     -- 1 = cites a known-bad DOI on purpose, to record that it is bad
);

CREATE TABLE trap (
    trap     TEXT,
    doc      TEXT,
    category TEXT
);

-- ---------------------------------------------------------------- derived views
CREATE VIEW v_live AS
    SELECT * FROM claim WHERE lower(coalesce(status,'')) LIKE '%live%';

CREATE VIEW v_unsupported AS         -- a claim with no evidence edge at all
    SELECT c.* FROM claim c
    LEFT JOIN supports s ON s.cl_id = c.cl_id
    WHERE s.cl_id IS NULL;

CREATE VIEW v_claim_evidence AS      -- the join a human would otherwise do by hand
    SELECT c.cl_id, c.mode, c.status, c.statement,
           e.ev_id, e.kind, e.gate, e.n AS ev_n, e.job
    FROM claim c
    LEFT JOIN supports s ON s.cl_id = c.cl_id
    LEFT JOIN evidence e ON e.ev_id = s.ev_id;

CREATE VIEW v_dangerous AS           -- live claims resting on ungated evidence
    SELECT DISTINCT c.cl_id, c.statement, e.ev_id, e.gate
    FROM claim c JOIN supports s ON s.cl_id = c.cl_id
                 JOIN evidence e ON e.ev_id = s.ev_id
    WHERE lower(coalesce(c.status,'')) LIKE '%live%'
      AND lower(coalesce(e.gate,'')) NOT IN ('exit0', 'n/a', '');

CREATE VIEW v_orphan_doc AS          -- a claim citing a file that is not in the repo
    -- A claim cell may name SEVERAL documents ("a.md, b.md"), so an equality test on the whole
    -- cell reports a false orphan. Match if ANY known document name appears inside the cell.
    SELECT c.cl_id, c.doc FROM claim c
    WHERE trim(coalesce(c.doc,'')) <> ''
      AND NOT EXISTS (SELECT 1 FROM document d WHERE instr(c.doc, d.name) > 0);

CREATE VIEW v_local_only_cite AS     -- a live claim whose only backing is a file the reader cannot open
    SELECT DISTINCT c.cl_id, d.name, substr(c.statement,1,70) AS statement
    FROM claim c JOIN document d ON instr(c.doc, d.name) > 0
    WHERE d.local_only = 1
      AND lower(coalesce(c.status,'')) LIKE '%live%'
      AND NOT EXISTS (SELECT 1 FROM document t
                      WHERE t.local_only = 0 AND instr(c.doc, t.name) > 0);
"""

_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_BACKTICK = re.compile(r"`([^`]*)`")
_BANNER = re.compile(r"\b(SUPERSEDED|RETRACTED|CORRECTED|PARTLY SUPERSEDED)\b")


def _has_banner(text: str) -> bool:
    """A retraction banner, not a document that merely discusses retractions.

    Scanning the first 4000 characters for the word flagged every audit and index doc, whose whole
    job is to catalogue other documents' corrections. The convention in this repo is a blockquote or
    bold line in the opening lines, so require that shape and that position.
    """
    for line in text.splitlines()[:12]:
        s = line.strip()
        if not _BANNER.search(s):
            continue
        if s.startswith(">") or s.startswith("**") or s.startswith("#"):
            return True
    return False
_PARAM_WORDS = ("alpfe", "scav_rat", "diatomgraz", "r_picpoc", "smallgrow", "biggrow")


def _clean(cell: str) -> str:
    cell = _LINK.sub(r"\1", cell)
    cell = _BACKTICK.sub(r"\1", cell)
    return cell.replace("**", "").replace("*", "").strip()


def _tables(text: str):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and set(
            lines[i + 1].strip()
        ) <= set("|-: "):
            header = [_clean(c) for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = [_clean(c) for c in lines[j].strip().strip("|").split("|")]
                if any(cells):
                    rows.append(cells)
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


SIGNATURES = [
    ("settled", {"question", "answer"}),
    ("claim_deductive", {"statement", "derivation"}),
    ("claim_inductive", {"statement", "null"}),
    ("claim_abductive", {"statement", "tested"}),
    ("hypothesis", {"statement", "falsifier"}),
    ("supersedes", {"old", "new"}),
    ("trap", {"trap"}),
    ("evidence", {"evidence", "gate"}),
]


def _kind(header: list[str]) -> str | None:
    words = {w for h in header for w in re.split(r"[^a-z0-9]+", h.lower()) if w}
    for name, sig in SIGNATURES:
        if sig <= words:
            return name
    return None


def _get(row: list[str], header: list[str], *names: str) -> str:
    """Fetch a cell by header name; '' when the column is absent.

    Short names are matched EXACTLY. A substring match on a one- or two-letter name like "n"
    hits "statement" and silently returns the wrong column, which is how the seed count ended up
    echoing the claim text.
    """
    low = [h.lower().strip() for h in header]
    for name in names:
        exact = len(name) <= 2
        for k, h in enumerate(low):
            if k >= len(row):
                continue
            if (h == name) if exact else (name in h):
                return row[k]
    return ""


def _infer_parameter(text: str) -> str:
    low = text.lower()
    for p in _PARAM_WORDS:
        if p in low:
            return "R_PICPOC" if p == "r_picpoc" else p
    return ""


def _infer_track(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ("emulator", "ar(1)", "persistence", "rollout", "fno")):
        return "track2"
    if any(w in low for w in _PARAM_WORDS) or "recover" in low or "identifiab" in low:
        return "track1"
    if any(w in low for w in ("gate", "verify_run", "grading", "null", "prereg")):
        return "method"
    return "data"


# Seven research notes are gitignored BY NAME (.gitignore:100-106) at the author's direction, so
# they exist on this machine and nowhere a reader can reach. Enumerating documents from the DISK
# let them into the table here and only here: the orphan constraint passed locally and failed in
# CI, where 8 claims (2 of them live) cite no document that a fresh checkout contains. Measured
# with the v_orphan_doc predicate restricted to local_only=0; an earlier note said 31, which was
# a count of filename occurrences in the corpus file, not of claims. Enumerate from the REPO and
# declare the seven, so
# both environments build the same table. Same shape as citation.deliberate -- an exemption that is
# written down and counted, not a silent pass. An eighth undeclared local citation still fails.
LOCAL_ONLY_DOCS = (
    "docs/research_notes/2026-05-03_overnight.md",
    "docs/research_notes/2026-05-21_jon_meeting_brief.md",
    "docs/research_notes/2026-05-23_cleanup_audit.md",
    "docs/research_notes/2026-05-23_compute_ladder.md",
    "docs/research_notes/2026-05-23_overnight_diff_full_darwin.md",
    "docs/research_notes/2026-05-23_overnight_executed.md",
    "docs/research_notes/2026-06-06_daily_data_defer.md",
)


def _tracked_doc_paths() -> list[str] | None:
    """Repo-relative doc paths git knows about, or None if git cannot answer.

    None is NOT the same as "no documents": falling through to an empty list would empty the
    document table and make every claim an orphan at once.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "docs/findings", "docs/research_notes"],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.splitlines() if out.returncode == 0 else None


def _load_documents(con: sqlite3.Connection) -> None:
    tracked = _tracked_doc_paths()
    if tracked is None:
        print("WARNING: git could not list files, falling back to disk. Untracked notes may enter "
              "the document table, and this run will not match CI.", file=sys.stderr)

    for sub in ("findings", "research_notes"):
        d = REPO / "docs" / sub
        if not d.is_dir():
            continue
        prefix = f"docs/{sub}/"
        if tracked is None:
            names = sorted(p.name for p in d.glob("*.md"))
        else:
            # Direct children only, matching the glob("*.md") this replaced -- ls-files also
            # returns nested paths such as research_notes/art/.
            names = sorted(r[len(prefix):] for r in tracked
                           if r.startswith(prefix) and r.endswith(".md") and "/" not in r[len(prefix):])
        for name in names:
            p = d / name
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = re.match(r"(20\d\d-\d\d-\d\d)", name)
            con.execute(
                "INSERT OR REPLACE INTO document VALUES (?,?,?,?,?,?)",
                # Repo-relative. This was p.as_posix(), an ABSOLUTE path, so the exported mirror
                # carried 196 "C:/Users/Frank/..." strings and could not byte-match a rebuild
                # anywhere else -- the mirror test could never have passed in CI.
                (prefix + name, name, m.group(1) if m else "",
                 1 if _has_banner(text) else 0, len(text.split()), 0),
            )

    # Declared local-only notes. Written from the constant, never read from disk, so the row is
    # identical whether or not the file happens to be present. All seven are banner-free (checked
    # 2026-08-04), so retracted=0 is the measured value and not a convenient default.
    for rel in LOCAL_ONLY_DOCS:
        name = rel.rsplit("/", 1)[1]
        m = re.match(r"(20\d\d-\d\d-\d\d)", name)
        con.execute(
            "INSERT OR REPLACE INTO document VALUES (?,?,?,?,?,?)",
            (rel, name, m.group(1) if m else "", 0, 0, 1),
        )


def _load_parameters(con: sqlite3.Connection) -> None:
    """The Carroll-N registry is the single source of truth; join to it rather than restating it."""
    src = REPO / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from darwindiff.carroll6 import PARAMS  # noqa: PLC0415
    except Exception:  # torch missing, or registry moved. Not fatal for the rest of the map.
        return
    denominator = {"alpfe", "scav_rat", "diatomgraz", "R_PICPOC"}
    for p in PARAMS:
        lo, hi = p.bounds
        con.execute(
            "INSERT OR REPLACE INTO parameter VALUES (?,?,?,?,?,?)",
            (p.name, float(p.carroll_value), float(lo), float(hi),
             getattr(p, "scale", ""), 1 if p.name in denominator else 0),
        )


def _load_citations(con: sqlite3.Connection) -> None:
    if not CITATION_AUDIT.is_file():
        return
    try:
        rows = json.loads(CITATION_AUDIT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    for r in rows if isinstance(rows, list) else rows.get("rows", []):
        for doc in (r.get("citing_docs") or [""]):
            con.execute(
                "INSERT INTO citation VALUES (?,?,?,?,?,?)",
                (r.get("doi", ""), r.get("verdict", ""), r.get("claimed_as", ""),
                 f'{r.get("actual_first_author","")} {r.get("actual_year","")} {r.get("actual_title","")}'.strip(),
                 doc, 1 if r.get("deliberate") else 0),
            )


def _flat(s) -> str:
    """Single-line form. Matches gen_research_map.cell()'s whitespace handling, minus the cut."""
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _key_full(s) -> str:
    """Normalised text, uncut. Used to break key collisions by prefix containment."""
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _key(s) -> str:
    """The same normalised 60-char prefix gen_research_map.py dedups its tables on."""
    return _key_full(s)[:60]


#: (db table, key column, corpus section, ((db column, corpus fields in fallback order), ...)).
#: The key column is named identically in both, which is what makes the join possible at all.
_REHYDRATE = (
    ("settled", "question", "settled",
     (("question", ("question",)), ("answer", ("answer",)))),
    ("trap", "trap", "traps",
     (("trap", ("trap",)),)),
    ("supersedes", "old", "supersedes",
     (("old", ("old",)), ("new", ("new",)), ("reason", ("reason",)))),
    ("claim", "statement", "claims",
     (("statement", ("statement",)), ("detail", ("why_this_mode", "numbers")),
      ("null_baseline", ("numbers",)))),
    ("hypothesis", "statement", "hypotheses",
     (("statement", ("statement",)), ("predicts", ("predicts",)),
      ("falsifier", ("falsifier",)), ("status", ("status",)))),
)

_MISSING = object()

#: Counters from the most recent build(), so `check` can report coverage instead of asserting it.
LAST_REHYDRATION: dict = {}


def _rehydrate(con: sqlite3.Connection) -> dict:
    """Widen markdown-truncated prose back to the corpus's full text. -> counters.

    WHY. `gen_research_map.cell()` cuts every cell when it renders the markdown -- settled answers
    at 240 characters, claim statements at 230, traps at 220. This module parses that markdown, so
    before this step the database held the CUT text, and `settled` -- the check CLAUDE.md makes
    mandatory before starting work -- searched it. Measured 2026-08-04: 87% of settled answers were
    truncated and 35% of the corpus (83,957 of 242,118 characters) was unsearchable. A miss printed
    "This may be genuinely new work", which reads as a clean negative rather than "your term may be
    past character 240" -- the exact failure the map exists to prevent, in the tool built to prevent
    it. See issue #228.

    The markdown stays a READING view and keeps its truncation; only the database is widened.

    This runs AFTER the parse and only ever rewrites text columns of rows that already exist. It
    cannot change row counts or the synthesised `cl_id` / `hy_id` values, which #227 makes
    load-bearing -- claim ids are positional, so a step that added or dropped a row here would
    renumber hundreds of citations.

    Collisions are resolved EXACTLY, not guessed. Two claims really do share a normalised
    60-character key here (`ded110` and `ded111`, both opening "The alpfe/scav_rat degeneracy is a
    one-parameter multiplicative gauge symmetry..."), which is the same shape of collision that
    once silently destroyed 7 of 99 hypotheses through INSERT OR REPLACE. Because the cut text is
    by construction a PREFIX of the full text, a tie is broken by asking which candidate the
    database's own value actually prefixes. If that still leaves more than one, neither is used and
    the row is counted as ambiguous rather than resolved by position.
    """
    counts = {"widened": 0, "ambiguous": 0, "unmatched": 0, "corpus": 0}
    if not CORPUS.is_file():
        counts["no_corpus"] = 1
        return counts
    try:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        counts["no_corpus"] = 1
        return counts

    for table, keycol, section, cols in _REHYDRATE:
        index: dict = {}
        for row in corpus.get(section, []) or []:
            k = _key(row.get(keycol))
            if k:
                index.setdefault(k, []).append(row)
        counts["corpus"] += sum(len(v) for v in index.values())

        # table/keycol come from the _REHYDRATE literal above, never from input.
        for rowid, keyval in con.execute(
                f"SELECT rowid, {keycol} FROM {table}").fetchall():
            cands = index.get(_key(keyval))
            if not cands:
                counts["unmatched"] += 1
                continue
            if len(cands) > 1:
                # The rendered cell is a prefix of the corpus text, so ask which candidate the
                # database's own value actually prefixes. Compare normalised, because cell()
                # rewrites "|" and drops "\" on the way into the markdown.
                stem = _key_full(str(keyval).rstrip(ELLIPSIS))
                cands = [c for c in cands if _key_full(c.get(keycol)).startswith(stem)] or cands
            if len(cands) != 1:
                counts["ambiguous"] += 1
                continue
            row = cands[0]
            sets, vals = [], []
            for dbcol, fields in cols:
                val = ""
                for f in fields:
                    if row.get(f):
                        val = row[f]
                        break
                val = _flat(val)
                if val:                       # never blank a column the parse already filled
                    sets.append(f"{dbcol}=?")
                    vals.append(val)
            if sets:
                con.execute(
                    f"UPDATE {table} SET {', '.join(sets)} WHERE rowid=?",
                    (*vals, rowid))
                counts["widened"] += 1
    return counts


def build(map_path: Path = MAP) -> sqlite3.Connection:
    if not map_path.is_file():
        raise SystemExit(f"{map_path} not found. CLAUDE.md tells every session to read it.")
    con = sqlite3.connect(":memory:")
    # nrm() lets a constraint compare PROSE across tables. Claim IDs are synthetic (ded40) while
    # supersedes.old holds the retracted sentence, so any join on the id can never match.
    con.create_function("nrm", 1, lambda s: re.sub(r"[^a-z0-9]+", "", (s or "").lower()))
    con.executescript(SCHEMA)
    _load_documents(con)
    _load_parameters(con)
    _load_citations(con)

    text = map_path.read_text(encoding="utf-8")
    # Legacy claim ids are positional. Explicit semantic ids do not consume
    # this counter, so adding a new semantic claim cannot renumber old rows.
    legacy_claim_index = 0
    for header, rows in _tables(text):
        kind = _kind(header)
        if kind is None:
            continue
        for r in rows:
            if kind == "settled":
                con.execute("INSERT INTO settled VALUES (?,?,?,?)",
                            (_get(r, header, "question"), _get(r, header, "answer"),
                             _get(r, header, "where", "doc"), _get(r, header, "do not", "dont")))
            elif kind.startswith("claim_"):
                mode = kind.split("_", 1)[1]
                explicit_cl_id = _get(r, header, "cl_id", "claim id", "id")
                if explicit_cl_id:
                    cl_id = explicit_cl_id
                else:
                    cl_id = f"{mode[:3]}{legacy_claim_index}"
                    legacy_claim_index += 1
                stmt = _get(r, header, "statement")
                detail = _get(r, header, "derivation", "prompted", "evidence")
                con.execute(
                    "INSERT INTO claim VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (cl_id, stmt, mode, _get(r, header, "status"), detail,
                     _get(r, header, "n"), _get(r, header, "null"), _get(r, header, "doc"),
                     _infer_parameter(stmt + " " + detail), _infer_track(stmt + " " + detail)),
                )
                # every claim that names an artifact gets an evidence row and a supports edge,
                # so the join in v_claim_evidence is populated without a second hand-maintained table
                # A blank explicit-evidence column must not mask the legacy
                # derivation/prompted evidence carried by older claim tables.
                ev = _get(r, header, "evidence")
                if not ev:
                    ev = _get(r, header, "n", "derivation", "prompted")
                if ev:
                    ev_id = f"ev_{cl_id}"
                    gate = "exit0" if "exit 0" in ev.lower() else ("ungated" if mode != "deductive" else "n/a")
                    con.execute("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?)",
                                (ev_id, mode, _get(r, header, "doc"), "", gate, None, ""))
                    con.execute("INSERT INTO supports VALUES (?,?,?)", (cl_id, ev_id, "establishes"))
            elif kind == "evidence":
                con.execute("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?)",
                            (_get(r, header, "ev_id", "id", "ev"), _get(r, header, "kind"),
                             _get(r, header, "locator", "artifact", "path"), _get(r, header, "job"),
                             _get(r, header, "gate"), None, _get(r, header, "date")))
            elif kind == "hypothesis":
                # The key must be UNIQUE PER ROW. It used to fall back to statement[:12], which
                # with INSERT OR REPLACE silently destroyed 7 of 99 hypotheses whose statements
                # merely began alike -- including two RIVAL explanations of the same Southern
                # Ocean result ("...comes from DEPTH STRUCTURE" vs "...because scavenging is
                # ~79.7% of the surface sink"), so the map lost the competing hypothesis it
                # exists to keep visible. Fall back to a row counter instead.
                hy_id = (_get(r, header, "hy_id", "hyp id", "id")
                         or f"hy{con.execute('SELECT count(*) FROM hypothesis').fetchone()[0]:03d}")
                con.execute("INSERT OR REPLACE INTO hypothesis VALUES (?,?,?,?,?,?)",
                            (hy_id,
                             _get(r, header, "statement"), _get(r, header, "predict"),
                             _get(r, header, "falsifier"), _get(r, header, "status"),
                             _get(r, header, "prereg", "doc")))
            elif kind == "supersedes":
                con.execute("INSERT INTO supersedes VALUES (?,?,?,?)",
                            (_get(r, header, "old"), _get(r, header, "new"),
                             _get(r, header, "reason"), _get(r, header, "doc")))
            elif kind == "trap":
                con.execute("INSERT INTO trap VALUES (?,?,?)",
                            (_get(r, header, "trap"), _get(r, header, "doc"), _get(r, header, "category")))
    # The markdown is a reading view and is truncated by design; the database must not be. #228.
    LAST_REHYDRATION.clear()
    LAST_REHYDRATION.update(_rehydrate(con))
    con.commit()
    return con


CONSTRAINTS = [
    # This compared claim.cl_id (synthetic, "ded40") against supersedes.old (the retracted
    # SENTENCE), so the join had zero possible matches and the constraint passed vacuously from
    # the day it was written. It now compares the normalised prose: a live claim that restates
    # the first 60 significant characters of a retracted statement is the failure it was meant
    # to catch. 60 is long enough that an incidental shared opening does not trip it.
    ("no live claim restates a superseded statement",
     """SELECT c.cl_id, substr(c.statement,1,70) FROM claim c JOIN supersedes s
        ON length(nrm(s.old)) >= 60
       AND instr(nrm(c.statement), substr(nrm(s.old), 1, 60)) > 0
        WHERE lower(coalesce(c.status,'')) LIKE '%live%'"""),
    ("every inductive claim carries a numbers cell (NOT a verified untrained null -- the corpus "
     "has no separate null field, so this checks presence, not that a matched baseline exists)",
     """SELECT cl_id, statement FROM claim
        WHERE mode='inductive' AND trim(coalesce(null_baseline,''))=''"""),
    ("every settled answer says where it lives",
     """SELECT question, answer FROM settled WHERE trim(coalesce(doc,''))=''"""),
    ("no claim or rendered hypothesis has an empty status",
     """SELECT cl_id AS id, statement FROM claim
        WHERE trim(coalesce(status,''))=''
        UNION ALL
        SELECT hy_id AS id, statement FROM hypothesis
        WHERE trim(coalesce(status,''))=''"""),
    # The seven LOCAL_ONLY_DOCS are inside `document`, so claims citing them are not orphans here.
    # That exemption is deliberate and is COUNTED by the advisory below rather than hidden: the
    # files are gitignored by the author, so gating on them would fail forever and teach readers to
    # ignore the gate. Any OTHER missing file is still a hard failure.
    ("no claim cites a document that is neither in the repo nor a declared local-only note",
     """SELECT cl_id, doc FROM v_orphan_doc"""),
    # `deliberate` marks a site that cites a known-bad DOI ON PURPOSE, to record that it is bad.
    # Without this exemption the constraint would fail forever and readers would learn to ignore it,
    # which is precisely the failure mode the citation audit warned about.
    ("no citation resolves to the wrong paper (excluding declared-deliberate sites)",
     """SELECT doi, claimed, actual FROM citation
        WHERE verdict='RESOLVES_MISMATCH' AND deliberate = 0"""),
    ("no citation is fabricated or dead",
     """SELECT doi, verdict, doc FROM citation
        WHERE verdict IN ('DEAD','SUSPECT_FABRICATED') AND deliberate = 0"""),
    # The markdown truncates every cell; this module parses the markdown; so without _rehydrate
    # the DB -- and `settled`, the mandatory pre-work check -- searched cut prose. 87% of settled
    # answers were affected and 35% of the corpus was unsearchable (#228). char(8230) is the U+2026
    # ellipsis gen_research_map.cell() appends when it cuts, so a row still carrying it here failed
    # to match the corpus and is still truncated.
    ("no prose is left truncated by the markdown rendering (#228)",
     """SELECT 'settled.answer' AS col, substr(answer,1,60) AS text FROM settled
          WHERE answer LIKE '%' || char(8230)
        UNION ALL SELECT 'settled.question', substr(question,1,60) FROM settled
          WHERE question LIKE '%' || char(8230)
        UNION ALL SELECT 'claim.statement', substr(statement,1,60) FROM claim
          WHERE statement LIKE '%' || char(8230)
        UNION ALL SELECT 'trap.trap', substr(trap,1,60) FROM trap
          WHERE trap LIKE '%' || char(8230)
        UNION ALL SELECT 'supersedes.old', substr(old,1,60) FROM supersedes
          WHERE old LIKE '%' || char(8230)
        UNION ALL SELECT 'hypothesis.statement', substr(statement,1,60) FROM hypothesis
          WHERE statement LIKE '%' || char(8230)"""),
]


ADVISORIES = [
    # The price of the local-only exemption above, stated in rows. These live claims rest on a
    # file no reader outside this machine can open, which is a provenance defect even though it is
    # not a build failure. Shrinking this list means publishing the note or re-citing the claim.
    ("live claims whose ONLY cited document is a declared local-only note -- a reader cannot check them",
     """SELECT cl_id, name, statement FROM v_local_only_cite"""),
    # Reported, never gated. A banner supersedes part of a document, not every claim in it, so
    # failing on this would fire on rows that are mostly fine and teach readers to ignore the gate.
    # Same reasoning as the STRADDLE guard in verify_run: keep the failure channel sharp.
    ("live claims sourced from a document that carries a retraction banner -- review each",
     """SELECT c.cl_id, d.name, substr(c.statement,1,70) FROM claim c JOIN document d
        ON instr(c.doc, d.name) > 0
        WHERE d.retracted = 1 AND lower(coalesce(c.status,'')) LIKE '%live%'"""),
    ("live claims resting on UNGATED evidence (advertised as a constraint, never enforced; "
     "run `dangerous` for the full list)",
     """SELECT cl_id, gate, substr(statement,1,60) FROM v_dangerous"""),
    ("claims with no evidence edge at all",
     """SELECT cl_id, substr(statement,1,80) FROM v_unsupported"""),
]


def cmd_check(con) -> int:
    # State the citation coverage up front. The audit JSON stores only the EXCEPTION rows, so the
    # two citation constraints below run over a handful of records, not the whole corpus. Without
    # this line a clean run reads as "every DOI was verified just now", which is not what happened.
    stored = con.execute("SELECT count(*) FROM citation").fetchone()[0]
    if CITATION_AUDIT.exists():
        try:
            meta = json.loads(CITATION_AUDIT.read_text(encoding="utf-8"))
            print(f"citation coverage: {meta.get('clean', '?')} of {meta.get('total', '?')} DOIs "
                  f"verified on {meta.get('date', '?')}; {stored} exception row(s) stored and "
                  f"re-tested here. Newer DOIs are NOT covered -- re-run the audit to extend it.\n")
        except (json.JSONDecodeError, OSError):
            print(f"citation coverage: unreadable audit file; {stored} row(s) in table\n")
    else:
        print("citation coverage: NO audit file; the citation constraints below are vacuous\n")

    # State the text coverage too. The markdown this DB is parsed from truncates every cell, so
    # without rehydration `settled` searches cut prose (#228). Report it rather than assume it.
    rh = LAST_REHYDRATION
    if rh.get("no_corpus"):
        print(f"text coverage: corpus {CORPUS.name} NOT FOUND -- prose is TRUNCATED as rendered "
              f"(settled answers at 240 chars). Searches will miss text past the cut.\n")
    elif rh:
        note = ""
        if rh.get("ambiguous") or rh.get("unmatched"):
            note = (f"; {rh.get('ambiguous', 0)} ambiguous and {rh.get('unmatched', 0)} unmatched "
                    f"rows LEFT TRUNCATED")
        print(f"text coverage: {rh.get('widened', 0)} rows rehydrated to full corpus text{note}. "
              f"The markdown stays truncated by design; the database does not.\n")

    bad = 0
    for name, sql in CONSTRAINTS:
        try:
            rows = con.execute(sql).fetchall()
        except sqlite3.Error as exc:
            print(f"ERROR   {name}: {exc}")
            bad += 1
            continue
        if rows:
            bad += 1
            print(f"VIOLATED  {name}  ({len(rows)})")
            for r in rows[:6]:
                print(f"     {' | '.join(str(x)[:80] for x in r)}")
        else:
            print(f"ok        {name}")

    print()
    for name, sql in ADVISORIES:
        try:
            rows = con.execute(sql).fetchall()
        except sqlite3.Error as exc:
            print(f"advisory error  {name}: {exc}")
            continue
        if rows:
            print(f"ADVISORY  {name}  ({len(rows)})")
            for r in rows[:8]:
                print(f"     {' | '.join(str(x)[:70] for x in r)}")
            if len(rows) > 8:
                print(f"     ... and {len(rows) - 8} more")

    print("\nCONSTRAINTS_FAILED" if bad else "\nALL CONSTRAINTS HOLD (advisories above are not failures)")
    return 1 if bad else 0


def cmd_settled(con, term) -> int:
    # MATCHING IS PER-TERM, NOT WHOLE-PHRASE. This was a single LIKE on the entire query until
    # 2026-08-05, which meant a multi-word search only hit when the words were CONTIGUOUS in the
    # prose. Measured on the corpus that day: 5 of 7 plausible queries printed "may be genuinely
    # new work" while the answer was present. "R_PICPOC anchor Daniels" returned nothing against
    # 22 rows that contain all three words.
    #
    # That is the same false-negative shape #228 fixed for truncation, and it is worse, because
    # this is the MANDATORY pre-work check. A session that searches before starting and is told
    # its question is new will re-derive. CLAUDE.md opens with that happening four times.
    #
    # Exact phrase is still tried first and reported, since a contiguous hit is stronger evidence
    # than a scatter of terms across a long answer.
    terms = [t for t in term.lower().split() if t]
    phrase = f"%{term.lower()}%"

    def _run(sql, args):
        return con.execute("SELECT question, answer, doc, dont FROM settled WHERE " + sql,
                           args).fetchall()

    rows = _run("lower(question) LIKE ? OR lower(answer) LIKE ?", (phrase, phrase))
    how = "exact phrase"
    if not rows and len(terms) > 1:
        clause = " AND ".join(["(lower(question) LIKE ? OR lower(answer) LIKE ?)"] * len(terms))
        args = [x for t in terms for x in (f"%{t}%", f"%{t}%")]
        rows = _run(clause, args)
        how = f"all {len(terms)} terms, not necessarily adjacent"

    if not rows:
        # Say what was actually searched. Until #228 this line was printed over TRUNCATED prose,
        # so "nothing settled" could mean "your term sits past character 240 of an answer" -- a
        # false negative that reads exactly like a true one.
        n_rows, n_chars = con.execute(
            "SELECT count(*), coalesce(sum(length(question) + length(answer)), 0) "
            "FROM settled").fetchone()
        print(f"nothing settled matching {term!r}. This may be genuinely new work.")
        print(f"  (searched {n_rows} settled rows, {n_chars:,} characters, untruncated; "
              f"tried exact phrase then all {len(terms)} term(s) separately)")
        return 0
    print(f"ALREADY SETTLED matching {term!r} ({len(rows)}, matched on {how}). "
          f"Do not re-derive:\n")
    for question, answer, doc, dont in rows:
        print(f"  Q: {question}")
        # Answers run past 1,500 characters now that they are not cut, so wrap rather than
        # emit one unreadable line.
        for i, line in enumerate(textwrap.wrap(answer, 96) or [""]):
            print(f"  {'A:' if i == 0 else '  '} {line}")
        print(f"  -> {doc}")
        if dont:
            for i, line in enumerate(textwrap.wrap(dont, 96)):
                print(f"  {'do not:' if i == 0 else '       '} {line}")
        print()
    return 0


def cmd_trace(con, cl_id) -> int:
    """What a claim rests on, what rests on it, and whether any of it is dead."""
    row = con.execute("SELECT cl_id, mode, status, statement, detail, doc, parameter, track "
                      "FROM claim WHERE lower(cl_id)=lower(?)", (cl_id,)).fetchone()
    if not row:
        print(f"no claim {cl_id!r}")
        return 1
    print(f"{row[0]}  [{row[1]}]  status={row[2]}  track={row[7]}  param={row[6] or '-'}")
    print(f"  {row[3]}")
    if row[4]:
        print(f"  detail: {row[4]}")
    print(f"  doc: {row[5]}")
    for ev_id, kind, gate, job in con.execute(
            "SELECT e.ev_id, e.kind, e.gate, e.job FROM supports s JOIN evidence e ON e.ev_id=s.ev_id "
            "WHERE s.cl_id=?", (row[0],)):
        print(f"  rests on: {ev_id} kind={kind} gate={gate} job={job or '-'}")
    for f, r in con.execute("SELECT from_cl, rule FROM derives WHERE to_cl=?", (row[0],)):
        print(f"  follows from: {f} ({r})")
    for t, r in con.execute("SELECT to_cl, rule FROM derives WHERE from_cl=?", (row[0],)):
        print(f"  implies: {t} ({r})")
    for old, new, reason in con.execute(
            "SELECT old,new,reason FROM supersedes WHERE lower(old) LIKE ?", (f"%{row[0].lower()}%",)):
        print(f"  SUPERSEDED: {old} -> {new} ({reason})")
    return 0


def cmd_param(con, name) -> int:
    p = con.execute("SELECT * FROM parameter WHERE lower(name)=lower(?)", (name,)).fetchone()
    if p:
        print(f"{p[0]}  carroll={p[1]:.6g}  bounds=({p[2]:.4g}, {p[3]:.4g})  scale={p[4]}  "
              f"{'IN' if p[5] else 'NOT IN'} the 4-observable denominator")
    else:
        print(f"{name}: not in the registry")
    print()
    for cl_id, mode, status, stmt, n, nb in con.execute(
            "SELECT cl_id, mode, status, statement, n, null_baseline FROM claim "
            "WHERE lower(parameter)=lower(?) ORDER BY mode", (name,)):
        print(f"  [{mode[:3]}] {cl_id:<5} {status:<10} {stmt[:100]}")
        if n or nb:
            print(f"        n={n or '-'}  null={nb or '-'}")
    return 0


def cmd_dangerous(con) -> int:
    rows = con.execute("SELECT * FROM v_dangerous").fetchall()
    unsupported = con.execute("SELECT cl_id, statement FROM v_unsupported").fetchall()
    if rows:
        print("LIVE claims resting on ungated evidence:")
        for cl_id, stmt, ev, gate in rows:
            print(f"  {cl_id:<5} gate={gate:<8} {stmt[:90]}")
    if unsupported:
        print("\nClaims with NO evidence edge:")
        for cl_id, stmt in unsupported:
            print(f"  {cl_id:<5} {stmt[:100]}")
    if not rows and not unsupported:
        print("no live claim is resting on weak ground")
    return 0


def cmd_superseded(con, term) -> int:
    q = f"%{term.lower()}%"
    rows = con.execute("SELECT old,new,reason FROM supersedes "
                       "WHERE lower(old) LIKE ? OR lower(new) LIKE ?", (q, q)).fetchall()
    if not rows:
        print(f"no supersession recorded for {term!r}.")
        return 0
    print(f"RETRACTED OR SUPERSEDED matching {term!r}. Do not quote the old value:\n")
    for old, new, reason in rows:
        print(f"  {old}\n    -> {new}\n    because {reason}\n")
    return 0


def cmd_open(con) -> int:
    for hy_id, s, p, f, st in con.execute(
            "SELECT hy_id,statement,predicts,falsifier,status FROM hypothesis "
            "WHERE lower(coalesce(status,'')) LIKE '%open%'"):
        print(f"  {hy_id}: {s}")
        print(f"      status:    {st}")
        if p:
            print(f"      predicts:  {p}")
        if f:
            print(f"      falsifier: {f}")
    return 0


def cmd_sql(con, query) -> int:
    if re.search(r"\b(insert|update|delete|drop|alter)\b", query, re.I):
        print("read-only: refusing a mutating statement")
        return 1
    try:
        cur = con.execute(query)
    except sqlite3.Error as exc:
        print(f"SQL error: {exc}")
        return 1
    if cur.description:
        print(" | ".join(d[0] for d in cur.description))
    for row in cur.fetchall():
        print(" | ".join(str(x)[:90] for x in row))
    return 0


def cmd_stats(con) -> int:
    for t in ("document", "parameter", "evidence", "claim", "supports", "derives",
              "supersedes", "hypothesis", "settled", "citation", "trap"):
        print(f"  {t:<12}{con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>6}")
    print()
    for mode, n in con.execute("SELECT mode, count(*) FROM claim GROUP BY mode ORDER BY mode"):
        print(f"    claim.{mode:<11}{n:>4}")
    for track, n in con.execute("SELECT track, count(*) FROM claim GROUP BY track ORDER BY track"):
        print(f"    track.{track:<11}{n:>4}")
    r = con.execute("SELECT count(*) FROM document WHERE retracted=1").fetchone()[0]
    print(f"\n  documents carrying a retraction banner: {r}")
    return 0


JSON_MIRROR = REPO / "docs" / "research_map.json"


def export_json(con: sqlite3.Connection) -> dict:
    """The whole relational model as one JSON document.

    WHY BOTH. SQL is the better interface for ASKING -- joins, the constraints, `settled <term>`
    in one command. JSON is the better interface for READING IN BULK, because the entire structure
    arrives in a single file read instead of one shell round-trip per question. The risk of keeping
    two representations is that they disagree, so this is not a second source: it is an export of
    the same in-memory database the SQL commands run against, produced by the same build(). Schema
    changes propagate automatically, and test_research_map_json_mirror_is_current fails if the
    committed file falls behind.
    """
    tables, views = [], []
    for name, kind, sql in con.execute(
        "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name"
    ).fetchall():
        (views if kind == "view" else tables).append((name, sql))

    def rows_of(name):
        cur = con.execute(f"SELECT * FROM {name}")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        # CANONICAL ORDER, not scan order. `SELECT *` returns rows in rowid order, and
        # `INSERT OR REPLACE` deletes-then-reinserts, so a replaced row moves to the end and the
        # scan order encodes how many replacements happened rather than anything about the data.
        # That is stable for one machine and not guaranteed across two, which is exactly the shape
        # of a mirror that byte-matches locally and fails in CI. Sorting on the serialised row
        # makes the export independent of insert history.
        rows.sort(key=lambda d: json.dumps(d, sort_keys=True, ensure_ascii=False, default=str))
        return cols, rows

    out = {
        "_readme": "Generated by scripts/research_map_db.py export-json. Do not hand-edit; "
                   "it is an export of the same database the SQL commands query. "
                   "Regenerate after changing the map, the schema, or the corpus.",
        "relational_algebra": [c.strip() for c in __doc__.split("SQL (see CONSTRAINTS below):")[-1]
                               .strip().splitlines() if c.strip()],
        "schema": {}, "views": {}, "constraints": {}, "advisories": {}, "counts": {},
    }
    for name, sql in tables:
        cols, rows = rows_of(name)
        out["schema"][name] = {"ddl": sql, "columns": cols, "rows": rows}
        out["counts"][name] = len(rows)
    for name, sql in views:
        cols, rows = rows_of(name)
        out["views"][name] = {"ddl": sql, "columns": cols, "rows": rows}
        out["counts"][name] = len(rows)
    for label, sql in CONSTRAINTS:
        violations = con.execute(sql).fetchall()
        out["constraints"][label] = {"sql": sql, "holds": not violations,
                                     "violations": [list(map(_jsonable, v)) for v in violations]}
    for label, sql in ADVISORIES:
        rows = con.execute(sql).fetchall()
        out["advisories"][label] = {"sql": sql, "count": len(rows),
                                    "rows": [list(map(_jsonable, r)) for r in rows]}
    return out


def _jsonable(v):
    return v if v is None or isinstance(v, (str, int, float, bool)) else str(v)


def cmd_export_json(con) -> int:
    doc = export_json(con)
    # newline="\n" EXPLICITLY. Path.write_text opens in text mode, which on Windows translates
    # every \n to \r\n, so the same build produced a different artifact per platform and the
    # mirror could only ever byte-match on the OS that last wrote it.
    JSON_MIRROR.write_text(
        json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n"
    )
    failed = [k for k, v in doc["constraints"].items() if not v["holds"]]
    print(f"wrote {JSON_MIRROR.relative_to(REPO).as_posix()}  "
          f"{JSON_MIRROR.stat().st_size:,} bytes")
    print(f"  {len(doc['schema'])} tables, {len(doc['views'])} views, "
          f"{len(doc['constraints'])} constraints ({len(failed)} failing), "
          f"{len(doc['advisories'])} advisories")
    return 1 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="integrity constraints; exit 1 on violation")
    sub.add_parser("stats", help="row counts per relation")
    sub.add_parser("open", help="open hypotheses with falsifiers")
    sub.add_parser("dangerous", help="live claims on ungated or missing evidence")
    sub.add_parser("export-json", help="write docs/research_map.json (mirror of this DB)")
    for name, helptext in (("settled", "has this been answered? RUN BEFORE STARTING WORK"),
                           ("superseded", "is this number or claim retracted?"),
                           ("trace", "what a claim rests on and implies"),
                           ("param", "everything known about one Carroll-N parameter"),
                           ("sql", "arbitrary read-only SQL")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("term" if name != "sql" else "query")
    a = ap.parse_args(argv)

    con = build()
    return {
        "check": lambda: cmd_check(con),
        "stats": lambda: cmd_stats(con),
        "open": lambda: cmd_open(con),
        "dangerous": lambda: cmd_dangerous(con),
        "export-json": lambda: cmd_export_json(con),
        "settled": lambda: cmd_settled(con, a.term),
        "superseded": lambda: cmd_superseded(con, a.term),
        "trace": lambda: cmd_trace(con, a.term),
        "param": lambda: cmd_param(con, a.term),
        "sql": lambda: cmd_sql(con, a.query),
    }[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
