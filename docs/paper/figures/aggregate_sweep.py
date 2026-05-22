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
def _find_params_dict(obj: Any) -> dict | None:
    """Depth-first search for any dict whose keys include all six Carroll-6
    param names. Returns the dict itself (not its values)."""
    if isinstance(obj, dict):
        if all(k in obj for k in PARAM_NAMES):
            return obj
        for v in obj.values():
            found = _find_params_dict(v)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_params_dict(v)
            if found is not None:
                return found
    return None


# Candidate sub-keys for the recovered value when the params dict uses a
# nested-per-param layout. v3.x JSONs use ``joint_recovered`` as the
# canonical aggregated recovery; older waves may use ``recovered`` or
# ``value``.
_RECOVERED_SUBKEYS = (
    "joint_recovered",
    "joint_cellweighted_recovered",
    "joint_aoiweighted_recovered",
    "recovered",
    "value",
)

# Candidate sub-keys for the recovery-band classification string.
_BAND_SUBKEYS = (
    "joint_band",
    "joint_cellweighted_band",
    "joint_aoiweighted_band",
    "band",
    "cal_grade_band",
)

# Bands that count as Cal-grade per STATUS.md ``Recovery scoring`` block.
_CAL_GRADE_BANDS = {"Excellent", "Cal-grade"}


def compute_cal_grade_from_threshold(recovered: dict[str, float]) -> dict[str, bool]:
    """Apply the ±40% threshold definition when no band is present."""
    return {
        k: abs(recovered[k] - CARROLL_OPTIMA[k]) / CARROLL_OPTIMA[k] <= CAL_GRADE_TOL
        for k in PARAM_NAMES
    }


def extract_carroll6(obj: Any) -> tuple[dict[str, float], dict[str, bool]] | None:
    """Find a Carroll-6 params dict and return (recovered_values, cal_grade).

    Handles two common layouts:
    - flat:   {alpfe: 0.92, scav_rat: 6e-7, ...}
    - nested: {alpfe: {joint_recovered: 0.92, joint_band: "Cal-grade", ...}, ...}

    For nested layouts, Cal-grade is taken from the band field if present,
    otherwise computed from the ±40% threshold.
    """
    params_dict = _find_params_dict(obj)
    if params_dict is None:
        return None

    recovered: dict[str, float] = {}
    cal_grade: dict[str, bool] = {}
    for p in PARAM_NAMES:
        val = params_dict[p]

        # flat layout — value is a number
        if isinstance(val, (int, float)):
            recovered[p] = float(val)
            cal_grade[p] = (
                abs(val - CARROLL_OPTIMA[p]) / CARROLL_OPTIMA[p] <= CAL_GRADE_TOL
            )
            continue

        # nested layout — value is a sub-dict with joint_recovered / joint_band
        if isinstance(val, dict):
            rec_val: float | None = None
            for key in _RECOVERED_SUBKEYS:
                if key in val:
                    try:
                        rec_val = float(val[key])
                        break
                    except (TypeError, ValueError):
                        continue
            if rec_val is None:
                return None  # unsupported nested layout
            recovered[p] = rec_val

            band: str | None = None
            for key in _BAND_SUBKEYS:
                if key in val and isinstance(val[key], str):
                    band = val[key]
                    break
            if band is not None:
                cal_grade[p] = band in _CAL_GRADE_BANDS
            else:
                cal_grade[p] = (
                    abs(rec_val - CARROLL_OPTIMA[p]) / CARROLL_OPTIMA[p] <= CAL_GRADE_TOL
                )
            continue

        # something else — unsupported
        return None

    return recovered, cal_grade


# legacy alias kept for callers that imported the old name
def find_carroll6_in_json(obj: Any) -> dict[str, float] | None:
    result = extract_carroll6(obj)
    return result[0] if result is not None else None


def compute_cal_grade(recovered: dict[str, float]) -> dict[str, bool]:
    """Apply the ±40% Cal-grade definition from STATUS.md."""
    return compute_cal_grade_from_threshold(recovered)


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
            <top_level>/           # e.g. bcr_<wave>_<stamp> or sweep_d4_F2_*
                [<config_name>/]   # optional intermediate config dir
                    [<batch>/]     # optional seedsN-M batch dir
                    <seed>.json

    We prefer the intermediate config dir if present (skipping any
    ``seedsN-M`` batch dirs). Otherwise we fall back to the top-level dir
    name itself (e.g. for sweeps where each top-level dir IS the config).
    """
    try:
        rel = path.relative_to(runs_root)
    except ValueError:
        return path.parent.name

    parts = rel.parts
    if not parts:
        return "unknown"

    # parts[0] = top-level dir; parts[1:-1] = intermediate dirs; parts[-1] = file
    intermediates = list(parts[1:-1])
    while intermediates and _SEED_BATCH_RE.match(intermediates[-1]):
        intermediates.pop()
    if intermediates:
        return intermediates[-1]
    # no intermediate config dir — the top-level dir IS the config scope
    return parts[0]


# ----------------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------------
def aggregate(
    runs_root: Path,
    output: Path,
    verbose: bool = False,
    top_level_pattern: str = "*",
) -> None:
    seeds: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    total_files = 0

    # Accept comma-separated patterns so callers can scope to multiple
    # top-level dirs (e.g. ``bcr_*,sweep_d4_F2_*``).
    patterns = [p.strip() for p in top_level_pattern.split(",") if p.strip()]
    seen: set[Path] = set()
    top_dirs: list[Path] = []
    for pat in patterns:
        for p in runs_root.glob(pat):
            if p.is_dir() and p not in seen:
                seen.add(p)
                top_dirs.append(p)
    top_dirs.sort()
    if not top_dirs:
        print(f"WARN: no top-level dirs matching {top_level_pattern!r} under {runs_root}")
        return

    print(f"Scanning {len(top_dirs)} top-level dirs matching {top_level_pattern!r}:")
    for d in top_dirs:
        print(f"  - {d.name}")

    json_paths: list[Path] = []
    for top in top_dirs:
        json_paths.extend(top.rglob("*.json"))
    json_paths.sort()
    print(f"Scanning {len(json_paths)} JSON files ...")

    for json_path in json_paths:
        total_files += 1
        try:
            with open(json_path, encoding="utf-8") as f:
                content = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            skipped.append((str(json_path), f"unreadable: {exc}"))
            continue

        extracted = extract_carroll6(content)
        if extracted is None:
            skipped.append((str(json_path), "no Carroll-6 dict found"))
            continue
        recovered, cal_grade = extracted

        seed = extract_seed(json_path, content)
        if seed is None:
            skipped.append((str(json_path), "no seed identifiable"))
            continue

        config = extract_config(json_path, runs_root)

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
    parser.add_argument(
        "--include", default="bcr_*",
        help="Top-level dir glob pattern to include under runs-root "
             "(default: 'bcr_*' which restricts to v3.1 sweep waves; use '*' for everything)",
    )
    args = parser.parse_args()

    if not args.runs_root.exists():
        sys.exit(f"ERROR: runs-root does not exist: {args.runs_root}")

    aggregate(args.runs_root, args.output, args.verbose, args.include)


if __name__ == "__main__":
    main()
