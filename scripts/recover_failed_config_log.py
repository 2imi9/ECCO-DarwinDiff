"""Recover per-seed JSON from a failed run's log (MAX_PATH crash).

The runner succeeded at training but failed at JSON write due to Windows
MAX_PATH=260 chars. All per-seed recovery values ARE in the .log file
(printed before the write). This script parses them and emits compatible
JSONs at a short path so downstream aggregation sees the data.

Usage:
  python scripts/recover_failed_config_log.py <log_path> <out_dir> [env_kv ...]

The env_kv are space-separated KEY=VALUE pairs that get embedded in each
JSON's top-level keys (pic_abs_w=0.05, poc_abs_w=0.025, etc.) so aggregation
sees the same fields it would from a clean run.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PARAM_NAMES = ['alpfe', 'scav_rat', 'Smallgrow', 'Biggrow', 'diatomgraz', 'R_PICPOC']
BAND_RE = re.compile(r"joint=(\w+(?:-\w+)?)\s*\(([^)]+)\)")
SUMMARY_RE = re.compile(r"->\s*joint\s+(\d+)/6\s+cal-grade\s+\((\d+)\s+Excellent\)")
PARAM_LINE_RE = re.compile(
    r"^(\S+)\s+"          # param name
    r"([\d.e+-]+)\s+"      # eqpac value
    r"([\d.e+-]+)\s+"      # natlsubpolar
    r"([\d.e+-]+)\s+"      # southern
    r"([\d.e+-]+)\s+"      # JOINT
    r"([\d.e+-]+)\s+"      # Carroll
    r"joint=(\w+(?:-\w+)?)\s*\(([^)]+)\)"
)


def parse_log(log_path: Path) -> list[dict]:
    """Parse seed sections from a runner log. Returns list of seed dicts."""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    # Split on "=== Seed N recovery ===" markers
    chunks = re.split(r"=== Seed (\d+) recovery ===", text)
    seeds = []
    # chunks = [before-first-seed, "0", body0, "1", body1, ...]
    for i in range(1, len(chunks), 2):
        try:
            seed_num = int(chunks[i])
            body = chunks[i + 1]
        except (ValueError, IndexError):
            continue

        params = {}
        for line in body.splitlines():
            m = PARAM_LINE_RE.match(line.strip())
            if not m:
                continue
            param, eqp, nat, sou, jt, car, band, dist = m.groups()
            if param not in PARAM_NAMES:
                continue
            params[param] = {
                "eqpac_value": float(eqp),
                "natlsubpolar_value": float(nat),
                "southernoceanpac_value": float(sou),
                "joint_value": float(jt),
                "carroll_value": float(car),
                "joint_band": band,
                "joint_distance": float(dist),
            }

        # n_cal_grade and n_excellent from summary line
        sm = SUMMARY_RE.search(body)
        if not sm:
            print(f"  warning: seed {seed_num} no summary line", file=sys.stderr)
            continue
        n_cal_grade = int(sm.group(1))
        n_excellent = int(sm.group(2))

        seeds.append({
            "seed": seed_num,
            "n_cal_grade": n_cal_grade,
            "n_excellent": n_excellent,
            "params": params,
            "recovered_from_log": True,  # flag that this is reconstructed
        })

    return seeds


def main():
    if len(sys.argv) < 3:
        print("usage: python recover_failed_config_log.py <log> <out_dir> [k=v ...]")
        sys.exit(2)
    log_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    extras = {}
    for kv in sys.argv[3:]:
        if "=" in kv:
            k, v = kv.split("=", 1)
            try:
                extras[k] = float(v)
            except ValueError:
                extras[k] = v

    if not log_path.is_file():
        print(f"log not found: {log_path}")
        sys.exit(1)

    seeds = parse_log(log_path)
    if not seeds:
        print("no seed sections parsed; nothing to write")
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    for s in seeds:
        s.update(extras)
        # Use a minimal short filename so we stay under MAX_PATH for the
        # entire <out_dir>/<filename> path. Filename only needs to be unique
        # per seed within the config dir.
        fname = f"recovered_seed{s['seed']}.json"
        path = out_dir / fname
        with path.open("w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, allow_nan=False)
        print(f"  wrote {path}")
    print(f"\nRecovered {len(seeds)} seeds from {log_path.name}")


if __name__ == "__main__":
    main()
