"""Aggregate every sweep run today and produce a master comparison table.

Walks D:\\runs\\v3.0_maxlever_<stamp>, D:\\runs\\sweep_modis_pic_<stamp>,
and D:\\runs\\sweep_modis_pic_lowW_<stamp> to produce a single Markdown
ranking across all configs.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

CARROLL = {
    'alpfe': 0.92831, 'scav_rat': 6.0250e-7, 'Smallgrow': 0.66098,
    'Biggrow': 0.43148, 'diatomgraz': 0.83003, 'R_PICPOC': 0.04245,
}

SWEEPS = [
    ("max-lever", r"D:\runs\v3.0_maxlever_*"),
    ("modis-W1", r"D:\runs\sweep_modis_pic_2*"),
    ("modis-lowW", r"D:\runs\sweep_modis_pic_lowW_*"),
]


def parse_config(filename: str) -> dict:
    """Extract the env-var config from a JSON filename."""
    cfg = {}
    name = Path(filename).stem
    for piece in name.split("_"):
        if piece.startswith("seed"):
            try:
                cfg["seed"] = int(piece[4:])
            except ValueError:
                pass
        elif piece.startswith("surf"):
            cfg["surf"] = piece[4:]
        elif piece.startswith("sub") and piece[3:].replace(".", "").isdigit():
            cfg["sub"] = piece[3:]
        elif piece.startswith("pinn"):
            cfg["pinn"] = piece[4:]
        elif piece.startswith("pocsubW"):
            cfg["pocsubW"] = piece[7:]
        elif piece.startswith("geopocW"):
            cfg["geopocW"] = piece[7:]
        elif piece.startswith("hd"):
            cfg["hd"] = piece[2:]
        elif piece.startswith("w-natlsubpolar"):
            cfg["natl"] = piece[14:]
        elif piece.startswith("picabsW"):
            cfg["picabs"] = piece[7:]
        elif piece.startswith("pocabsW"):
            cfg["pocabs"] = piece[7:]
        elif piece.startswith("posiW"):
            cfg["posi"] = piece[5:]
        elif piece.startswith("fco2absW"):
            cfg["fco2"] = piece[8:]
        elif piece.startswith("modispicW"):
            cfg["modis"] = piece[9:]
        elif piece in ("mehrbach", "cocco", "aoiid", "mld"):
            cfg[piece] = True
        elif piece.startswith("chl1W"):
            cfg["chl1W"] = piece[5:]
    return cfg


def config_signature(cfg: dict) -> str:
    """Short label for a config, excluding seed."""
    keys = []
    for k in ["picabs", "pocabs", "posi", "fco2", "modis", "chl1W"]:
        if k in cfg:
            keys.append(f"{k}={cfg[k]}")
    for k in ["mehrbach", "cocco", "mld"]:
        if k in cfg:
            keys.append(k)
    return ", ".join(keys) if keys else "baseline"


def aggregate_group(files: list[str]) -> dict | None:
    if not files:
        return None
    runs = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                runs.append(json.load(fh))
        except Exception:
            pass
    if not runs:
        return None
    cal = [r["n_cal_grade"] for r in runs]
    exc = [r["n_excellent"] for r in runs]
    pcal = {p: 0 for p in CARROLL}
    pexc = {p: 0 for p in CARROLL}
    rpicpoc_values = []
    alpfe_values = []
    for r in runs:
        for p in CARROLL:
            b = r["params"][p]["joint_band"]
            if b in ("Cal-grade", "Excellent"):
                pcal[p] += 1
            if b == "Excellent":
                pexc[p] += 1
        rpicpoc_values.append(r["params"]["R_PICPOC"]["joint_recovered"])
        alpfe_values.append(r["params"]["alpfe"]["joint_recovered"])
    return {
        "n": len(runs),
        "n_at_6": sum(c >= 6 for c in cal),
        "n_at_5": sum(c >= 5 for c in cal),
        "n_at_4": sum(c >= 4 for c in cal),
        "mean_cal": sum(cal) / len(cal),
        "excellents": sum(exc),
        "pcal": pcal,
        "rpicpoc_mean": mean(rpicpoc_values),
        "rpicpoc_min": min(rpicpoc_values),
        "rpicpoc_max": max(rpicpoc_values),
        "alpfe_mean": mean(alpfe_values),
    }


def main() -> None:
    # Group every JSON across all sweeps by config-signature.
    groups: dict[str, list[str]] = defaultdict(list)
    sweep_of: dict[str, str] = {}
    for sweep_label, glob_root in SWEEPS:
        for sweep_dir in glob.glob(glob_root):
            for f in glob.glob(str(Path(sweep_dir) / "run_v3.0_joint_*.json")):
                cfg = parse_config(f)
                sig = config_signature(cfg)
                # Differentiate by sweep label so seeds in different sweeps don't merge.
                key = f"[{sweep_label}] {sig}"
                groups[key].append(f)
                sweep_of[key] = sweep_label

    rows = []
    for key, files in groups.items():
        a = aggregate_group(files)
        if a:
            rows.append((key, a))

    # Sort by (n_at_5 desc, mean_cal desc, excellents desc) so the most
    # promising configs surface at the top.
    rows.sort(key=lambda kv: (kv[1]["n_at_5"], kv[1]["mean_cal"], kv[1]["excellents"]),
              reverse=True)

    print("# Master comparison across all overnight sweeps\n")
    print(f"**Total config-groups:** {len(rows)}")
    print(f"**Carroll-published R_PICPOC target:** {CARROLL['R_PICPOC']:.4f}\n")
    print("## Ranked by (at_5, mean_cal, excellents)\n")
    hdr = ("| Config | n | at6 | at5 | at4 | mean | excs "
           "| alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC "
           "| R_PIC mean | R_PIC range |")
    sep = "|:---|" + "---:|" * 13 + ":---|"
    print(hdr); print(sep)
    for key, a in rows:
        c = a["pcal"]
        rng = f"{a['rpicpoc_min']:.4f}–{a['rpicpoc_max']:.4f}"
        print(f"| `{key}` | {a['n']} | {a['n_at_6']} | {a['n_at_5']} | {a['n_at_4']} | "
              f"{a['mean_cal']:.2f} | {a['excellents']} | "
              f"{c['alpfe']} | {c['scav_rat']} | {c['Smallgrow']} | {c['Biggrow']} | "
              f"{c['diatomgraz']} | {c['R_PICPOC']} | "
              f"{a['rpicpoc_mean']:.4f} | {rng} |")
    print()
    print("## Notes\n")
    print("- `R_PIC mean` is the mean joint-recovered R_PICPOC across seeds. "
          f"Carroll target = {CARROLL['R_PICPOC']:.4f}.")
    print("- Per-parameter columns are #seeds at Cal-grade or Excellent out of n.")
    print("- Sweep labels: max-lever (Darwin v05 PIC), modis-W1 (MODIS PIC weight=1.0), "
          "modis-lowW (MODIS PIC weight ∈ {0.01, 0.1, 0.3}).")


if __name__ == "__main__":
    main()
