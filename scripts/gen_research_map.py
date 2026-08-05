#!/usr/bin/env python3
"""Generate docs/research_map.md from the extracted corpus.

The map is a RENDERING of docs/findings/research_map_corpus.json, not a hand-maintained file.
Regenerate it rather than editing it, or it drifts from the documents it indexes:

    python scripts/gen_research_map.py

The corpus was produced by 25 agents reading all 169 documents under docs/findings and
docs/research_notes (12 extracting, 12 adversarially verifying). To extend it after new findings
land, append rows to the corpus JSON and re-run this script.
"""
import json
import pathlib
import re
import subprocess
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "research_map.md"
M = json.loads((REPO / "docs" / "findings" / "research_map_corpus.json").read_text(encoding="utf-8"))

# The doc index is built from what is TRACKED, not from what is on this disk. Seven
# docs/research_notes files are gitignored by name as deliberately local-only working notes;
# globbing the filesystem let the rendered map cite them, so the committed map pointed at
# seven files no other reader could open and the integrity test passed locally anyway.
# `git ls-files` makes the renderer see the repository the way a reader sees it.
def _tracked_docs() -> set:
    try:
        out = subprocess.run(["git", "ls-files", "docs"], cwd=REPO,
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return set()          # not a git checkout: fall back to the filesystem below
    return {p.strip().replace("\\", "/") for p in out.stdout.splitlines() if p.strip()}


_TRACKED = _tracked_docs()
DOCS = {}
for _sub in ("findings", "research_notes"):
    for _p in (REPO / "docs" / _sub).glob("*.md"):
        _rel = f"docs/{_sub}/{_p.name}"
        if _TRACKED and _rel not in _TRACKED:
            continue          # local-only note: real on this disk, invisible to every reader
        DOCS[_p.name] = _rel


def cell(s, n=210):
    """Markdown-table-safe single line."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = s.replace("|", "/").replace("\\", "")
    return (s[: n - 1] + "…") if len(s) > n else s


def docref(d):
    """Keep only doc references that actually resolve, so the integrity test stays meaningful.

    A citation whose ONLY source is a gitignored local-only note is not dropped: a row with no
    doc is filtered out entirely by the callers, which would silently delete answered questions
    from the index and hand back the re-derivation risk the map exists to remove. Instead the
    row survives carrying an explicit unverifiable-source marker. Deliberately emitted WITHOUT
    backticks and WITHOUT a docs/ prefix so neither integrity test mistakes it for a resolvable
    pointer.
    """
    if not d:
        return ""
    names = re.findall(r"[A-Za-z0-9_.\-]+\.md", str(d))
    keep = list(dict.fromkeys(n for n in names if n in DOCS))[:3]
    if keep:
        return ", ".join(f"`{DOCS[n]}`" for n in keep)
    if names:
        return f"LOCAL-ONLY source, not in the repo: {names[0]}"
    return ""


def norm(s):
    return re.sub(r"\W+", "", str(s or "").lower())


# ---------------------------------------------------------------- SETTLED
settled, seen = [], set()
for r in M["settled"]:
    q, a = cell(r.get("question"), 150), cell(r.get("answer"), 240)
    d = docref(r.get("doc"))
    if not q or not a or not d:
        continue
    k = norm(q)[:60]
    if k in seen:
        continue
    seen.add(k)
    settled.append((q, a, d))
settled.sort(key=lambda t: t[0].lower())

# ---------------------------------------------------------------- CLAIMS
by_mode = defaultdict(list)
for r in M["claims"]:
    stmt = cell(r.get("statement"), 230)
    if not stmt:
        continue
    by_mode[r.get("mode", "inductive")].append({
        "s": stmt,
        "detail": cell(r.get("why_this_mode") or r.get("numbers"), 190),
        "num": cell(r.get("numbers"), 150),
        "status": cell(r.get("status") or "live", 22),
        "doc": docref(r.get("doc")),
    })

order = {"live": 0, "pending": 1, "unverified": 2, "superseded": 3, "superseded-in-part": 3, "retracted": 4}
for m in by_mode:
    by_mode[m].sort(key=lambda c: (order.get(c["status"], 5), c["s"].lower()))

# ---------------------------------------------------------------- others
sups = []
seen = set()
for r in M["supersedes"]:
    o, n = cell(r.get("old"), 170), cell(r.get("new"), 170)
    if not o or norm(o)[:60] in seen:
        continue
    seen.add(norm(o)[:60])
    sups.append((o, n, cell(r.get("reason"), 170), docref(r.get("doc"))))

hyps, seen = [], set()
for r in M["hypotheses"]:
    if "open" not in str(r.get("status", "")).lower():
        continue
    s = cell(r.get("statement"), 200)
    if not s or norm(s)[:60] in seen:
        continue
    seen.add(norm(s)[:60])
    hyps.append((s, cell(r.get("predicts"), 160), cell(r.get("falsifier"), 160), docref(r.get("doc"))))

traps, seen = [], set()
for r in M["traps"]:
    t = cell(r.get("trap"), 220)
    if not t or norm(t)[:60] in seen:
        continue
    seen.add(norm(t)[:60])
    traps.append((t, docref(r.get("doc"))))

L = []
w = L.append
w("# ECCO-DarwinDiff — research map")
w("")
w("**Read this before proposing, designing or launching anything.** It is the index of what the")
w("project already knows and how strongly, organised by inference mode over evidence, claims and")
w("open hypotheses.")
w("")
w("**Why it exists.** On 2026-07-30 one session re-derived work the repo already contained **four")
w("separate times** (the GHG Center assessment twice, the rain-ratio precedence, the 1-D column")
w("study), one at a cost of 1.52M tokens. Nothing indexed *questions already answered*. §1 is the fix.")
w("")
w("**How it was built.** 25 agents over all 169 documents in `docs/findings` and")
w("`docs/research_notes`: 12 extracted structured rows, 12 adversarially re-read the cited documents")
w("to refute bad ones, and the result was merged and deduplicated. **Chunk 5's verifier died on a")
w("connection error**, so rows sourced only from")
w("`2026-07-10_iron_partitioning_breaks_the_wall`, `2026-07-19_v05_chlorophyll_vs_modis`,")
w("`2026-07-22_column_osse_result`, `2026-07-22_two_anchor_redteam`,")
w("`2026-07-23_observable_frontier_config_analysis`, `2026-07-24_bgc_operator_lineage_synthesis`,")
w("`2026-07-28_bling_comparability`, `2026-07-29_contract_prior_art`,")
w("`2026-07-30_daily_emulator_artifact_is_contaminated` and")
w("`2026-07-30_scavrat_is_locally_identifiable_in_the_southern_ocean` are **extract-only, not")
w("independently verified**. Treat them with the same caution as an unverified claim.")
w("")
w("**Query it, do not just read it:** `python scripts/research_map_db.py settled <term>`. See")
w("CLAUDE.md for the full harness.")
w("")
w("---")
w("")
w("## 0. Schema")
w("")
w("```")
w("EVIDENCE   (ev_id, kind, locator, job, gate, n, date)")
w("CLAIM      (cl_id, statement, mode, status, doc, parameter, track)")
w("SUPPORTS   (cl_id, ev_id, relation)        relation ∈ {establishes, qualifies, refutes}")
w("HYPOTHESIS (hy_id, statement, predicts, falsifier, prereg, status)")
w("SUPERSEDES (old_cl, new_cl, reason)")
w("```")
w("")
w("| mode | answers | strong when | fails when |")
w("|---|---|---|---|")
w("| **deductive** | what *must* follow from structure | the derivation is checkable by inspection | a premise is wrong |")
w("| **inductive** | what *does* happen, repeatedly | it has n **and** a matched untrained null | no null, small n, or selection over configs |")
w("| **abductive** | what best *explains* a surprise | it predicts something it was not built to explain | it explains only what prompted it |")
w("")
w("The working loop is **abduction → deduction → pre-registration → induction**. §8 is a worked")
w("example that completed on 2026-07-31.")
w("")
w("---")
w("")
w(f"## 1. SETTLED — do not re-derive ({len(settled)} questions)")
w("")
w("**Check here first.** Each row is a question with an answer already on disk. If your task is in")
w("this table, it is done: say so and move on.")
w("")
w("| question | answer | where |")
w("|---|---|---|")
for q, a, d in settled:
    w(f"| {q} | {a} | {d} |")
w("")
w("---")
w("")

TITLES = {
    "deductive": ("2. CLAIM — deductive",
                  "Follows from structure. Checkable without new data. **These are the strongest things "
                  "the project has** and should carry the manuscript's load-bearing arguments.",
                  "| statement | derivation | status | doc |"),
    "inductive": ("3. CLAIM — inductive",
                  "Measured. **Every row needs its untrained baseline quoted with it.** Standing weakness "
                  "for the whole section: there is still **no config-selection null**, so each row measures "
                  "chance for a *fixed* pipeline while the flagship was chosen from a sweep.",
                  "| statement | n / null | status | doc |"),
    "abductive": ("4. CLAIM — abductive",
                  "Inference to the best explanation. **Not a result until it predicts something it was not "
                  "built to explain and that prediction is tested.** Displaced and weakened rows are kept "
                  "visible on purpose: they are the record of how the project reasons.",
                  "| statement | tested / prompted by | status | doc |"),
}
for mode in ("deductive", "inductive", "abductive"):
    rows = by_mode.get(mode, [])
    title, blurb, header = TITLES[mode]
    w(f"## {title} ({len(rows)})")
    w("")
    w(blurb)
    w("")
    w(header)
    w("|---|---|---|---|")
    for c in rows:
        mid = c["num"] if mode == "inductive" else c["detail"]
        w(f"| {c['s']} | {mid} | {c['status']} | {c['doc']} |")
    w("")
    w("---")
    w("")

w(f"## 5. HYPOTHESIS — open, with falsifiers ({len(hyps)})")
w("")
w("| statement | predicts | falsifier | doc |")
w("|---|---|---|---|")
for s, p, f, d in hyps:
    w(f"| {s} | {p} | {f} | {d} |")
w("")
w("---")
w("")
w(f"## 6. SUPERSEDES — the retraction chain ({len(sups)})")
w("")
w("**This is what stops a dead number coming back.** Before quoting any figure from an older")
w("document, check it here.")
w("")
w("| old | new | reason | doc |")
w("|---|---|---|---|")
for o, n, r, d in sups:
    w(f"| {o} | {n} | {r} | {d} |")
w("")
w("---")
w("")
w(f"## 7. TRAPS — process failures that cost time ({len(traps)})")
w("")
w("| trap | doc |")
w("|---|---|")
for t, d in traps:
    w(f"| {t} | {d} |")
w("")
w("---")
w("")
w("## 8. Worked example: the loop that closed on 2026-07-31")
w("")
w("1. **Abduction** (2026-07-22). A 0-D box cannot identify `scav_rat`, CRLB(log scav) = 4.2e6.")
w("   *Best explanation:* the vertical profile carries it, `alpfe` sets the profile **amplitude**")
w("   and `scav_rat` sets its **shape**. Recorded on **synthetic** self-twin data.")
w("2. **Deduction.** If that holds then surface-only iron must fail for `scav_rat` and succeed for")
w("   `alpfe`, and subsurface-only must do the reverse. Forced, not guessed.")
w("3. **Pre-registration** (2026-07-30). Decision rule and falsifier fixed with zero JSONs on disk.")
w("4. **Induction** (2026-07-31). `so_surf` 14/50 against `so_sub` 33/50, Fisher exact")
w("   P = 2.68e-4, `verify_run` exit 0, and the falsifier cleared (`alpfe` 49/50 in `so_surf`).")
w("")
w("**Repeat this pattern.** The strength came from step 2 producing a prediction the mechanism was")
w("*not* built to explain, and from step 3 happening before step 4.")
w("")

OUT.write_text("\n".join(L), encoding="utf-8")
print(f"wrote {OUT}  {OUT.stat().st_size:,} bytes")
print(f"  settled {len(settled)}  deductive {len(by_mode['deductive'])}  "
      f"inductive {len(by_mode['inductive'])}  abductive {len(by_mode['abductive'])}  "
      f"supersedes {len(sups)}  hypotheses {len(hyps)}  traps {len(traps)}")
