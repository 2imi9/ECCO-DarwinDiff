#!/usr/bin/env python3
r"""Make the research map queryable: a real relational database over what the project knows.

WHY THIS EXISTS. The research map is the index a session trusts to decide what is already known.
Prose you must read and remember is a weak guarantee; a query you run is a strong one. On 2026-07-30
one session re-derived work the repo already contained FOUR times, once at 1.52M tokens, because
nothing made "has this been settled?" a one-command question. This makes it one, and then goes
further: claims are JOINED to the evidence and the parameters they rest on, so an unsupported or
retracted claim is findable by query rather than by memory.

SOURCES. The database is assembled from four places, so no relation has to be maintained by hand
twice:

    docs/research_map.md            settled, claim, hypothesis, supersedes, trap, derives
    src/darwindiff/carroll6.py      parameter  (the registry is the single source of truth)
    docs/findings/citation_audit.json   citation  (written by the citation-verification workflow)
    docs/findings/*.md              document   (existence and supersession banners)

That last one matters: it lets a query ask "does this claim cite a file that exists, and does that
file carry a RETRACTED banner?" without anybody remembering to cross-check.

USAGE

    python scripts/research_map_db.py settled daily      # <- RUN THIS BEFORE STARTING WORK
    python scripts/research_map_db.py check              # integrity constraints, exit 1 on violation
    python scripts/research_map_db.py trace D1           # what a claim rests on, and what rests on it
    python scripts/research_map_db.py param scav_rat     # everything known about one parameter
    python scripts/research_map_db.py superseded 0.408   # is this number dead?
    python scripts/research_map_db.py dangerous          # live claims resting on weak ground
    python scripts/research_map_db.py sql "SELECT ..."   # arbitrary read-only SQL

THE CONSTRAINTS, as relational algebra written in SQL (see CONSTRAINTS below):

    pi_cl(sigma_{status=live}(CLAIM)) INTERSECT pi_old(SUPERSEDES)          = {}
    sigma_{mode=inductive AND null IS NULL}(CLAIM)                          = {}
    CLAIM |><| SUPPORTS |><| sigma_{gate != exit0}(EVIDENCE) where live     = {}
    sigma_{doc NOT IN DOCUMENT}(CLAIM)                                      = {}
    sigma_{verdict=RESOLVES_MISMATCH}(CITATION)                             = {}
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
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

SCHEMA = """
-- ---------------------------------------------------------------- core entities
CREATE TABLE document (
    path      TEXT PRIMARY KEY,
    name      TEXT,
    date      TEXT,
    retracted INTEGER DEFAULT 0,   -- carries a SUPERSEDED / RETRACTED / CORRECTED banner
    words     INTEGER
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
    reason TEXT
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


def _load_documents(con: sqlite3.Connection) -> None:
    for sub in ("findings", "research_notes"):
        d = REPO / "docs" / sub
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            m = re.match(r"(20\d\d-\d\d-\d\d)", p.name)
            con.execute(
                "INSERT OR REPLACE INTO document VALUES (?,?,?,?,?)",
                (p.as_posix(), p.name, m.group(1) if m else "",
                 1 if _has_banner(text) else 0, len(text.split())),
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


def build(map_path: Path = MAP) -> sqlite3.Connection:
    if not map_path.is_file():
        raise SystemExit(f"{map_path} not found. CLAUDE.md tells every session to read it.")
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    _load_documents(con)
    _load_parameters(con)
    _load_citations(con)

    text = map_path.read_text(encoding="utf-8")
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
                cl_id = _get(r, header, "cl_id", "claim id", "id") or f"{mode[:3]}{con.execute('SELECT count(*) FROM claim').fetchone()[0]}"
                stmt = _get(r, header, "statement")
                detail = _get(r, header, "derivation", "prompted", "evidence")
                con.execute(
                    "INSERT OR REPLACE INTO claim VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (cl_id, stmt, mode, _get(r, header, "status"), detail,
                     _get(r, header, "n"), _get(r, header, "null"), _get(r, header, "doc"),
                     _infer_parameter(stmt + " " + detail), _infer_track(stmt + " " + detail)),
                )
                # every claim that names an artifact gets an evidence row and a supports edge,
                # so the join in v_claim_evidence is populated without a second hand-maintained table
                ev = _get(r, header, "evidence", "n", "derivation", "prompted")
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
                con.execute("INSERT OR REPLACE INTO hypothesis VALUES (?,?,?,?,?,?)",
                            (_get(r, header, "hy_id", "hyp id", "id") or _get(r, header, "statement")[:12],
                             _get(r, header, "statement"), _get(r, header, "predict"),
                             _get(r, header, "falsifier"), _get(r, header, "status"),
                             _get(r, header, "prereg", "doc")))
            elif kind == "supersedes":
                con.execute("INSERT INTO supersedes VALUES (?,?,?)",
                            (_get(r, header, "old"), _get(r, header, "new"), _get(r, header, "reason")))
            elif kind == "trap":
                con.execute("INSERT INTO trap VALUES (?,?,?)",
                            (_get(r, header, "trap"), _get(r, header, "doc"), _get(r, header, "category")))
    con.commit()
    return con


CONSTRAINTS = [
    ("no live claim is also superseded",
     """SELECT c.cl_id, c.statement FROM claim c JOIN supersedes s
        ON length(c.cl_id) > 1 AND lower(s.old) LIKE '%' || lower(c.cl_id) || '%'
        WHERE lower(coalesce(c.status,'')) LIKE '%live%'"""),
    ("every inductive claim carries its untrained null",
     """SELECT cl_id, statement FROM claim
        WHERE mode='inductive' AND trim(coalesce(null_baseline,''))=''"""),
    ("every settled answer says where it lives",
     """SELECT question, answer FROM settled WHERE trim(coalesce(doc,''))=''"""),
    ("no claim has an empty status",
     """SELECT cl_id, statement FROM claim WHERE trim(coalesce(status,''))=''"""),
    ("no claim cites a document that is not in the repo",
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
]


ADVISORIES = [
    # Reported, never gated. A banner supersedes part of a document, not every claim in it, so
    # failing on this would fire on rows that are mostly fine and teach readers to ignore the gate.
    # Same reasoning as the STRADDLE guard in verify_run: keep the failure channel sharp.
    ("live claims sourced from a document that carries a retraction banner -- review each",
     """SELECT c.cl_id, d.name, substr(c.statement,1,70) FROM claim c JOIN document d
        ON instr(c.doc, d.name) > 0
        WHERE d.retracted = 1 AND lower(coalesce(c.status,'')) LIKE '%live%'"""),
    ("claims with no evidence edge",
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
    q = f"%{term.lower()}%"
    rows = con.execute("SELECT question, answer, doc, dont FROM settled "
                       "WHERE lower(question) LIKE ? OR lower(answer) LIKE ?", (q, q)).fetchall()
    if not rows:
        print(f"nothing settled matching {term!r}. This may be genuinely new work.")
        return 0
    print(f"ALREADY SETTLED matching {term!r} ({len(rows)}). Do not re-derive:\n")
    for question, answer, doc, dont in rows:
        print(f"  Q: {question}\n  A: {answer}\n  -> {doc}")
        if dont:
            print(f"  do not: {dont}")
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="integrity constraints; exit 1 on violation")
    sub.add_parser("stats", help="row counts per relation")
    sub.add_parser("open", help="open hypotheses with falsifiers")
    sub.add_parser("dangerous", help="live claims on ungated or missing evidence")
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
        "settled": lambda: cmd_settled(con, a.term),
        "superseded": lambda: cmd_superseded(con, a.term),
        "trace": lambda: cmd_trace(con, a.term),
        "param": lambda: cmd_param(con, a.term),
        "sql": lambda: cmd_sql(con, a.query),
    }[a.cmd]()


if __name__ == "__main__":
    sys.exit(main())
