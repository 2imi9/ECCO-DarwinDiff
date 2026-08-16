"""Fail fast when the research-map mirror is stale, before the commit rather than in CI.

WHY. The DOCUMENT table is built from `git ls-files` over docs/findings/ and
docs/research_notes/, so ADDING, RENAMING or DELETING any file there changes
docs/research_map.json and docs/tools/darwindiff_evidence_navigator.html — even when the corpus
itself is untouched. A docs-only commit therefore turns `test_research_map_json_mirror_is_current`
red without anything scientific having changed.

That happened twice in two days (2026-08-13 and again 2026-08-14, the latter across three
consecutive commits) and each time it was found by CI, minutes later, on a branch that had
already been pushed. The rule was documented in the test's own failure message; what was missing
was a check that runs at the point the mistake is made.

Usage:
    python scripts/check_map_mirror_current.py          # exit 1 if regeneration is needed
    python scripts/check_map_mirror_current.py --fix    # regenerate, then report what changed

Wire as a pre-commit hook:
    printf '#!/bin/sh\\nexec python scripts/check_map_mirror_current.py\\n' > .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GEN = [
    ("docs/research_map.md", [sys.executable, "scripts/gen_research_map.py"]),
    ("docs/research_map.json", [sys.executable, "scripts/research_map_db.py", "export-json"]),
    ("docs/tools/darwindiff_evidence_navigator.html",
     [sys.executable, "scripts/build_evidence_navigator.py"]),
]


def snapshot(paths: list[str]) -> dict[str, bytes]:
    out = {}
    for p in paths:
        f = REPO / p
        out[p] = f.read_bytes() if f.exists() else b""
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true",
                    help="regenerate in place instead of only reporting")
    args = ap.parse_args()

    paths = [p for p, _ in GEN]
    before = snapshot(paths)

    for _p, cmd in GEN:
        r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"regeneration command failed: {' '.join(cmd)}\n{r.stderr[-600:]}",
                  file=sys.stderr)
            return 2

    after = snapshot(paths)
    stale = [p for p in paths if before[p] != after[p]]

    if not stale:
        print("map mirror is current")
        return 0

    if args.fix:
        print("regenerated (now current):")
        for p in stale:
            print(f"  {p}")
        print("\nstage these with your commit.")
        return 0

    # restore, so a bare check never leaves the tree modified
    for p in stale:
        (REPO / p).write_bytes(before[p])
    print("MAP MIRROR IS STALE — these would change on a fresh build:", file=sys.stderr)
    for p in stale:
        print(f"  {p}", file=sys.stderr)
    print("\nAdding or renaming anything under docs/findings/ or docs/research_notes/ does this,\n"
          "even with no corpus edit. Fix with:\n"
          "  python scripts/check_map_mirror_current.py --fix\n"
          "then stage the regenerated files.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
