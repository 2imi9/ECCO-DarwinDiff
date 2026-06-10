"""Build the v3.1 per-(config, seed) recovery manifest from the committed aggregation.

Reads docs/paper/figures/aggregated_v3.1.json (the canonical aggregation of the
v3.1 sweep: total_seeds=856, total_configs=86) and writes a flat CSV manifest so
every rate cited in STATUS.md / README / findings is a filterable column rather
than a prose count. Run from the repo root:

    python scripts/build_v3.1_manifest.py

Output: docs/findings/v3.1_seed_manifest.csv  (one row per seed; 1=Cal-grade).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "paper" / "figures" / "aggregated_v3.1.json"
OUT = ROOT / "docs" / "findings" / "v3.1_seed_manifest.csv"


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    seeds = data["seeds"]
    rows = sorted(seeds, key=lambda s: (s["config"], s["seed"]))
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["config", "seed", *[f"{p}_cal" for p in PARAMS], "k_of_6"])
        for s in rows:
            cg = s["cal_grade"]
            w.writerow([s["config"], s["seed"], *[int(cg[p]) for p in PARAMS], sum(cg.values())])
    print(f"wrote {OUT.relative_to(ROOT)} ({len(rows)} rows; "
          f"{data['total_seeds']} seeds / {data['total_configs']} configs)")


if __name__ == "__main__":
    main()
