#!/usr/bin/env python3
"""Aggregate raw per-seed JSON outputs from the v3.1 sweep into the
single aggregated JSON consumed by ``make_figures.py``.

What this does
--------------
1. Walks ``D:\\runs\\bcr_*\\`` (or whatever ``--runs-root`` you point at).
2. Recursively finds every ``.json`` file.
3. Searches each JSON for a Carroll-6-shaped dict — any dict that contains
   all six param names (alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz,
   R_PICPOC) as keys. Defensive against varying JSON layouts across the
   five sweep waves.
4. Identifies the seed (from JSON content or filename) and the config
   (from path).
5. Computes Cal-grade flags per the project definition: |recovered −
   Carroll| / |Carroll| ≤ 0.40 (matches STATUS.md "Recovery scoring").
6. Dedupes by ``(config, seed)`` — keeps the first match per pair.
7. Writes ``aggregated_v3.1.json`` in the schema ``make_figures.py``
   expects (see its module docstring).

Treats this as a best-effort aggregation: any JSON it can't parse, or
that doesn't contain a Carroll-6 dict, is skipped with a logged reason.
Run with ``--verbose`` to see the first 20 skips.

Sanity expectation
------------------
After running on a complete v3.1 sweep tree (5 waves + Wave 6
composition), you should see roughly:

    Scanned: ... JSON files
    Parsed Carroll-6 from: ~857 files
    After dedup: 857 seeds
    Unique configs: 86

If you see substantially fewer, run with ``--verbose`` and inspect the
skipped-reason log — the per-seed JSON layout may have a field name
this script doesn't recognise yet, in which case extend
``find_carroll6_in_json``.

Usage
-----
    python aggregate_sweep.py                     # defaults to D:/runs
    python aggregate_sweep.py --runs-root D:/runs --verbose
    python aggregate_sweep.py --output other.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


# Carroll-6 published optima (from docs/ecco_darwin_parameter_inventory.md;
# verified bit-for-bit between Carroll 2020 v04 and Carroll 2022 v05).
CARROLL_OPTIMA: dict[str, float] = {
    "alpfe": 0.92831,
    "scav_rat": 10.41124 * 0.005 / 86400,  # ≈ 6.026e-7 s^-1
    "Smallgrow": 0.66098,
    "Biggrow": 0.43148,
    "diatomgraz": 0.83003,
    "R_PICPOC": 0.04245,
}

PARAM_NAMES = list(CARROLL_OPTIMA.keys())

# Project Cal-grade definition: |recovered − Carroll| / Carroll ≤ 0.40
CAL_GRADE_TOL = 0.40


# ----------------------------------------------------------------------------
# JSON scanning
# ----------------------------------------------------------------------------
def find_carroll6_in_json(obj: Any) -> dict[str, float] | None:
    """Recursively search a parsed JSON tree for a Carroll-6 dict.

    Returns the first dict (depth-first) whose keys include all six Carroll-6
    param names. Values are coerced to float.
    """
    if isinstance(obj, dict):
        if all(k in obj for k in PARAM_NAMES):
            try:
                return {k: float(obj[k]) for k in PARAM_NAMES}
            except (TypeError, ValueError):
                pass  # fall through and continue searching children
        for v in obj.values():
            found = find_carroll6_in_json(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_carroll6_in_json(v)
            if found is not None:
                return found
    return None


def compute_cal_grade(recovered: dict[str, float]) -> dict[str, bool]:
    """Apply the ±40% Cal-grade definition from STATUS.md."""
    return {
        k: abs(recovered[k] - CARROLL_OPTIMA[k]) / CARROLL_OPTIMA[k] <= CAL_GRADE_TOL
        for k in PARAM_NAMES
    }


# ----------------------------------------------------------------------------
# Seed + config extraction
# ----------------------------------------------------------------------------
_SEED_RE = re.compile(r"seed[_\-]?(\d+)", re.IGNORECASE)
_SEED_BATCH_RE = re.compile(r"^seeds?\d+([-_]\d+)?$", re.IGNORECASE)


def extract_seed(path: Path, content: Any) -> int | None:
    """Try to identify the seed from JSON content first, then from the
    filename. Returns None if no signal is available."""
    if isinstance(content, dict):
        for key in ("seed", "rng_seed", "torch_seed", "SEED"):
            if key in content:
                try:
                    return int(content[key])
                except (TypeError, ValueError):
                    pass
    m = _SEED_RE.search(path.stem)
    if m:
        return int(m.group(1))
    # last-ditch: parent dir might be named e.g. "seed_5"
    m = _SEED_RE.search(path.parent.name)
    if m:
        return int(m.group(1))
    return None


def extract_config(path: Path, runs_root: Path) -> str:
    """Identify the config name from the file's path.

    Layout assumption::

        runs_root/
            bcr_<wave>_<stamp>/
                <config_name>/
                    (optional batch dir like seeds10-19/)
                    <seed>.json

    We walk up the path skipping any ``seedsN-M`` style batch directories
    until we land on the config name (one level under bcr_*).
    """
    try:
        rel = path.relative_to(runs_root)
    except ValueError:
        return path.parent.name

    parts = rel.parts
    if len(parts) < 2:
        return "unknown"

    # parts[0] = bcr_<...>
    # parts[1] onwards = config / optional batch / file
    # walk from the immediate parent upward, skipping batch dirs
    parents = list(parts[1:-1])
    while parents and _SEED_BATCH_RE.match(parents[-1]):
        parents.pop()
    if parents:
        return parents[-1]
    # if we ate everything, use parts[1] (the direct child of bcr_*)
    return parts[1] if len(parts) > 1 else "unknown"


# ----------------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------------
def aggregate(runs_root: Path, output: Path, verbose: bool = False) -> None:
    seeds: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    total_files = 0

    json_paths = sorted(runs_root.rglob("*.json"))
    print(f"Scanning {len(json_paths)} JSON files under {runs_root} ...")

    for json_path in json_paths:
        total_files += 1
        try:
            with open(json_path, encoding="utf-8") as f:
                content = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            skipped.append((str(json_path), f"unreadable: {exc}"))
            continue

        recovered = find_carroll6_in_json(content)
        if recovered is None:
            skipped.append((str(json_path), "no Carroll-6 dict found"))
            continue

        seed = extract_seed(json_path, content)
        if seed is None:
            skipped.append((str(json_path), "no seed identifiable"))
            continue

        config = extract_config(json_path, runs_root)

        try:
            cal_grade = compute_cal_grade(recovered)
        except (ZeroDivisionError, KeyError) as exc:
            skipped.append((str(json_path), f"cal_grade compute failed: {exc}"))
            continue

        seeds.append({
            "config": config,
            "seed": seed,
            "recovered": recovered,
            "cal_grade": cal_grade,
            "source": str(json_path.relative_to(runs_root)).replace("\\", "/"),
        })

    # ---- dedupe by (config, seed); keep first ----
    seen: set[tuple[str, int]] = set()
    deduped: list[dict[str, Any]] = []
    for s in seeds:
        key = (s["config"], s["seed"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    # ---- summary ----
    unique_configs = sorted({s["config"] for s in deduped})
    cal_count_distribution: dict[int, int] = {k: 0 for k in range(7)}
    for s in deduped:
        cal_count_distribution[sum(s["cal_grade"].values())] += 1

    print()
    print(f"Total files scanned:    {total_files}")
    print(f"Parsed Carroll-6 from:  {len(seeds)}")
    print(f"After dedup:            {len(deduped)} seeds")
    print(f"Unique configs:         {len(unique_configs)}")
    print(f"Skipped:                {len(skipped)} files")
    print()
    print("Cal-grade distribution across deduped seeds:")
    for k in range(7):
        marker = "  <-- 5/6" if k == 5 else ("  <-- 6/6" if k == 6 else "")
        print(f"  {k}/6: {cal_count_distribution[k]} seeds{marker}")
    print()

    if verbose and skipped:
        print(f"First {min(20, len(skipped))} skips:")
        for path, reason in skipped[:20]:
            print(f"  - {path}: {reason}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more (run with --verbose-all to see all)")

    if verbose:
        print()
        print(f"First {min(15, len(unique_configs))} unique config names:")
        for c in unique_configs[:15]:
            print(f"  - {c}")
        if len(unique_configs) > 15:
            print(f"  ... and {len(unique_configs) - 15} more")

    out_data = {
        "schema_version": 1,
        "carroll_optima": CARROLL_OPTIMA,
        "cal_grade_tolerance": CAL_GRADE_TOL,
        "total_seeds": len(deduped),
        "total_configs": len(unique_configs),
        "seeds": deduped,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)
    print(f"Wrote {output}")
    print()
    print("Next step:")
    print(f"  python make_figures.py --aggregated {output}")


# ----------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--runs-root", type=Path, default=Path("D:/runs"),
        help="Root directory containing bcr_<stamp>/<config>/<seed>.json (default: D:/runs)",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).parent / "aggregated_v3.1.json",
        help="Output aggregated JSON path (default: ./aggregated_v3.1.json)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print first 20 skipped files and first 15 config names",
    )
    args = parser.parse_args()

    if not args.runs_root.exists():
        sys.exit(f"ERROR: runs-root does not exist: {args.runs_root}")

    aggregate(args.runs_root, args.output, args.verbose)


if __name__ == "__main__":
    main()
