#!/usr/bin/env python
"""banner_notebooks.py -- doc-audit bucket #3: prepend a 'SUPERSEDED FRAMING'
banner cell to point-in-time notebooks so a reader lands on the canonical
identifiability framing first.

Idempotent: skips a notebook whose first markdown cell is already a banner.
Skips notebooks listed in CURRENT (their framing is canonical, not stale).
Dry-run by default; pass --apply to write.
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys

# Notebooks whose framing is CURRENT -- never banner these.
CURRENT = {"demo_colab.ipynb"}

BANNER_DATE = "2026-06-28"
BANNER_ID = "supersede-banner"

CANON = (
    "the surrogate-to-model **identifiability study** that is now canonical "
    "(four observable parameters {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; "
    "the growth pair {`Smallgrow`, `Biggrow`} is unobservable by construction; "
    "`R_PICPOC` is recoverable via a real calcite anchor; per-cell prediction is "
    "load-bearing for the {`alpfe`, `scav_rat`, `R_PICPOC`} trio, 7/10 vs 0/10 global-scalar). "
    "The 0-D surrogate gap is dimensional (the box homogenizes spatial structure)."
)


def is_banner(cell) -> bool:
    if not cell or cell.get("cell_type") != "markdown":
        return False
    src = "".join(cell.get("source", []))
    s = src.strip().lower()
    return s.startswith(">") and any(m in s for m in ("superseded", "point-in-time", "historical", "⚠"))


def descriptor(path: str, title: str) -> str:
    """A short, accurate self-identifier. Trust the title unless it is the known
    broken copy-paste ('Notebook 23 ...' on the 26-29 sweep family); else use the
    filename stem."""
    stem = os.path.splitext(os.path.basename(path))[0]
    broken = stem[:2] not in ("23",) and title.lstrip("# ").startswith("Notebook 23")
    if broken or not title.strip():
        return f"`{stem}`"
    # strip leading '# ' and the project prefix for compactness
    t = title.lstrip("# ").strip()
    t = re.sub(r"^ECCO-DarwinDiff\s*[—\-]\s*", "", t)
    return t


def make_banner(path: str, title: str) -> dict:
    desc = descriptor(path, title)
    text = (
        f"> **⚠ SUPERSEDED FRAMING ({BANNER_DATE}).** This notebook is a "
        f"point-in-time record ({desc}); its framing predates {CANON} "
        f"Treat its numbers and claims as historical. "
        f"Canonical results: `STATUS.md` / `README.md`."
    )
    return {"cell_type": "markdown", "metadata": {}, "id": BANNER_ID, "source": [text]}


def first_title(nb) -> str:
    c = next((c for c in nb.get("cells", []) if c.get("cell_type") == "markdown"), None)
    if not c:
        return ""
    src = "".join(c.get("source", []))
    return next((ln for ln in src.splitlines() if ln.strip()), "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--preview", type=int, default=3, help="dry-run: print N banners")
    args = ap.parse_args()

    nbs = sorted(glob.glob("notebooks/**/*.ipynb", recursive=True))
    bannered, skipped_current, already, written = [], [], [], []
    previews = []
    for p in nbs:
        base = os.path.basename(p)
        nb = json.load(open(p, encoding="utf-8"))
        cells = nb.get("cells", [])
        first_md = next((c for c in cells if c.get("cell_type") == "markdown"), None)
        if base in CURRENT:
            skipped_current.append(p); continue
        if is_banner(first_md):
            already.append(p); continue
        banner = make_banner(p, first_title(nb))
        previews.append((p, "".join(banner["source"])))
        if args.apply:
            cells.insert(0, banner)
            nb["cells"] = cells
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
                f.write("\n")
            written.append(p)
        bannered.append(p)

    print(f"total={len(nbs)} | to-banner={len(bannered)} | already={len(already)} "
          f"| current-skip={len(skipped_current)} | written={len(written)}")
    print(f"current-skip: {[os.path.basename(p) for p in skipped_current]}")
    print(f"already: {[os.path.basename(p) for p in already]}")
    if not args.apply:
        for p, txt in previews[:args.preview]:
            print("\n" + "=" * 70 + f"\n{p}\n" + "-" * 70 + f"\n{txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
