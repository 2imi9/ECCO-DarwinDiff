"""Aggregate executed nb23-family notebooks into a goal-check summary table.

Walks notebooks/ for any 23_*, 26_*, 27_* executed .ipynb, extracts the
"GOAL: DINN baseline recovery vs Carroll's published Green's-functions
optima" table from each, and writes:
- docs/findings/v2.2_overnight_summary.md  (Markdown table for humans)
- docs/findings/v2.2_overnight_summary.csv  (machine-readable)

Idempotent. Run multiple times safely. Skips notebooks with no goal-check
output (i.e. unexecuted).

Usage: python scripts/overnight_summary.py
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"
OUT_DIR = ROOT / "docs" / "findings"


def parse_goal_table(text: str) -> list[dict] | None:
    """Extract the 'GOAL: DINN baseline ...' table rows.

    The table looks like:
        param         recovered    Carroll publ.  |Δ|/Carroll  band
        alpfe         1.5531e-01   9.2831e-01     0.891        Loose
        ...
    Returns list of dicts {param, recovered, carroll, rel_diff, band} or
    None if no GOAL section is present.
    """
    m = re.search(
        r"=== GOAL: DINN baseline recovery vs Carroll's published Green's-functions optima ===\s*\n(.+?)(?=\n  -> DINN baseline|\Z)",
        text,
        re.DOTALL,
    )
    if not m:
        return None
    body = m.group(1)
    rows: list[dict] = []
    for line in body.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        if parts[0] in ("alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"):
            try:
                rows.append({
                    "param": parts[0],
                    "recovered": float(parts[1]),
                    "carroll": float(parts[2]),
                    "rel_diff": float(parts[3]),
                    "band": " ".join(parts[4:]),
                })
            except (ValueError, IndexError):
                pass
    return rows if rows else None


def extract_summary_line(text: str) -> str:
    """The 'X of 6 params at calibration-grade ...' line."""
    m = re.search(r"-> DINN baseline: (\d) of 6 params at calibration-grade or better", text)
    return m.group(0)[3:] if m else ""


def extract_elapsed(text: str) -> int | None:
    """Total training elapsed seconds across both networks if present."""
    matches = re.findall(r"done in (\d+)s", text)
    if not matches:
        return None
    return sum(int(x) for x in matches)


def gather_outputs(nb_path: Path) -> str:
    """Concatenate all stream outputs from a notebook."""
    try:
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    buf: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        for out in cell.get("outputs", []):
            text = out.get("text", "")
            if isinstance(text, list):
                text = "".join(text)
            buf.append(text)
    return "\n".join(buf)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[dict] = []
    for nb_path in sorted(NB_DIR.glob("2[3-9]_*.ipynb")):
        outputs = gather_outputs(nb_path)
        goal_rows = parse_goal_table(outputs)
        if not goal_rows:
            continue
        cal_grade = sum(1 for r in goal_rows if r["rel_diff"] <= 0.40)
        excellent = sum(1 for r in goal_rows if r["rel_diff"] <= 0.10)
        record = {
            "notebook": nb_path.name,
            "cal_grade_count": cal_grade,
            "excellent_count": excellent,
            "elapsed_s": extract_elapsed(outputs) or "",
            "alpfe_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "alpfe"), None),
            "scav_rat_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "scav_rat"), None),
            "Smallgrow_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "Smallgrow"), None),
            "Biggrow_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "Biggrow"), None),
            "diatomgraz_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "diatomgraz"), None),
            "R_PICPOC_rel": next((r["rel_diff"] for r in goal_rows if r["param"] == "R_PICPOC"), None),
            "summary": extract_summary_line(outputs),
        }
        summary.append(record)

    if not summary:
        print("No executed nb23-family notebooks found with goal-check output.")
        return

    # Sort by cal-grade descending, then by alpfe ascending (lower is better)
    summary.sort(key=lambda r: (-r["cal_grade_count"], r.get("alpfe_rel") or 99))

    # CSV
    csv_path = OUT_DIR / "v2.2_overnight_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    # Markdown
    md_path = OUT_DIR / "v2.2_overnight_summary.md"
    md = ["# v2.2 / v2.3 overnight experiment summary",
          "",
          "Generated by `scripts/overnight_summary.py`. Sorted by calibration-grade count descending; ties broken by alpfe distance from Carroll.",
          "",
          "| Notebook | Cal-grade | Excellent | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC | Train (s) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary:
        cells = [
            r["notebook"],
            str(r["cal_grade_count"]),
            str(r["excellent_count"]),
            f"{r['alpfe_rel']:.3f}" if r["alpfe_rel"] is not None else "",
            f"{r['scav_rat_rel']:.3f}" if r["scav_rat_rel"] is not None else "",
            f"{r['Smallgrow_rel']:.3f}" if r["Smallgrow_rel"] is not None else "",
            f"{r['Biggrow_rel']:.3f}" if r["Biggrow_rel"] is not None else "",
            f"{r['diatomgraz_rel']:.3f}" if r["diatomgraz_rel"] is not None else "",
            f"{r['R_PICPOC_rel']:.3f}" if r["R_PICPOC_rel"] is not None else "",
            str(r["elapsed_s"]),
        ]
        md.append("| " + " | ".join(cells) + " |")
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {md_path.relative_to(ROOT)}")
    print(f"  Notebooks summarized: {len(summary)}")
    print(f"  Best: {summary[0]['notebook']} ({summary[0]['cal_grade_count']}/6 cal-grade)")


if __name__ == "__main__":
    main()
