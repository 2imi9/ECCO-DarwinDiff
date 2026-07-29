#!/usr/bin/env python3
r"""Print the identifiability contract for every observable, from REAL artifacts.

This is the reusable front-end for :mod:`darwindiff.contract` (issue #210). It
declares each Carroll-N parameter as an :class:`Unknown` -- naming the real
observable claimed to identify it -- then fills the four clauses from artifacts
already on disk:

  structural     <- the GN-Fisher JSONs written by identifiability_sloppiness.py
                    (contract_gnfisher_{realiron,realbsi,realdaniels}.json)
  measured_null  <- an untrained run directory + a trained run directory, graded
                    per-AOI >=2-of-3 exactly as verify_run does
  prior_contam.  <- computed from the registry bounds alone, no run needed
  practical      <- CRLB from the same Fisher JSONs

Nothing is hardcoded from memory. A clause with no artifact reads UNAVAILABLE,
which is a real verdict and deliberately not a soft pass.

Usage:
    python scripts/analysis/contract_report.py --fisher-dir /scratch/.../identif
    python scripts/analysis/contract_report.py --fisher-dir DIR \
        --run /scratch/.../ctrl_n50 --baseline /scratch/.../prior_ctrl_n50
    python scripts/analysis/contract_report.py --fisher-dir DIR --json

Exit code is the WORST across all unknowns, mirroring verify_run:
    0 every contract identifiable
    1 at least one clause failed
    7 at least one clause unavailable (and none failed)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from darwindiff.carroll6 import PARAMS  # noqa: E402
from darwindiff.contract import (  # noqa: E402
    EXIT_FAIL,
    EXIT_INCOMPLETE,
    EXIT_OK,
    Evidence,
    Unknown,
    contract,
)
from darwindiff.diagnostics import band_of  # noqa: E402

CAL_PLUS = {"Excellent", "Cal-grade"}

#: Which REAL observable is claimed to identify each parameter, and which
#: GN-Fisher artifact carries the evidence for that claim.
#:
#: The growth pair maps to an EMPTY tuple deliberately. No real observable
#: constrains a phytoplankton growth rate under time-mean fitting, and the
#: contract is supposed to say so rather than leave the clause blank.
IDENTIFIED_BY: dict[str, tuple[tuple[str, ...], str | None]] = {
    "alpfe":      (("geotraces_dfe_surf", "geotraces_dfe_sub"), "realiron"),
    "scav_rat":   (("geotraces_dfe_surf", "geotraces_dfe_sub"), "realiron"),
    "diatomgraz": (("geotraces_bsi",), "realbsi"),
    "R_PICPOC":   (("daniels_cp_pp",), "realdaniels"),
    "Smallgrow":  ((), None),
    "Biggrow":    ((), None),
}


def _load_fisher(fisher_dir: Path) -> dict[str, dict]:
    """Load whichever GN-Fisher artifacts exist. Missing ones stay missing."""
    out: dict[str, dict] = {}
    for tag in ("realiron", "realbsi", "realdaniels"):
        p = fisher_dir / f"contract_gnfisher_{tag}.json"
        if p.is_file():
            try:
                out[tag] = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  [warn] {p.name} unreadable ({exc}); treating as absent")
    return out


def _dig(obj, key):
    """Find ``key`` anywhere in a nested dict. The artifact schema is not flat."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _dig(v, key)
            if r is not None:
                return r
    return None


def _per_aoi_counts(run_dir: Path, names: list[str]) -> tuple[dict[str, int], int]:
    """Per-AOI >=2-of-3 Cal+ counts, recomputed from raw values.

    Deliberately the SAME metric verify_run leads with. Cell-weighted counts are
    not computed here at all: on the observations-only run scav_rat reads 40/50
    cell-weighted and 0/50 per-AOI, so a cell-weighted number is not evidence.
    """
    counts = {n: 0 for n in names}
    files = sorted(run_dir.glob("*.json"))
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        params = d.get("params") or {}
        for n in names:
            pp = params.get(n)
            if not isinstance(pp, dict):
                continue
            per_aoi = pp.get("per_aoi_recovered")
            pub = pp.get("joint_carroll_published")
            if not isinstance(per_aoi, dict) or pub in (None, 0):
                continue
            good = sum(1 for v in per_aoi.values()
                       if band_of(abs(v - pub) / abs(pub)) in CAL_PLUS)
            if good >= 2:
                counts[n] += 1
    return counts, len(files)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fisher-dir", type=Path, default=None,
                    help="directory holding contract_gnfisher_*.json")
    ap.add_argument("--run", type=Path, default=None, help="trained run directory")
    ap.add_argument("--baseline", type=Path, default=None,
                    help="architecture-matched UNTRAINED run directory")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--param-log-scale", default="",
                    help="comma-separated names the RUN bounded logarithmically. Mirrors the "
                         "runner's PARAM_LOG_SCALE, which defaults to EMPTY, so the default "
                         "here is linear for every parameter. Registry Param.scale is metadata "
                         "and is deliberately NOT used: scav_rat declares scale='log' while "
                         "every published run bounds it linearly, and reading the registry "
                         "would misstate its untrained prior by a factor of five.")
    args = ap.parse_args()
    log_scaled = {s.strip() for s in args.param_log_scale.split(",") if s.strip()}

    fisher = _load_fisher(args.fisher_dir) if args.fisher_dir else {}
    names = [p.name for p in PARAMS]

    trained, n_trained = ({}, 0)
    untrained, n_untrained = ({}, 0)
    if args.run:
        trained, n_trained = _per_aoi_counts(args.run, names)
    if args.baseline:
        untrained, n_untrained = _per_aoi_counts(args.baseline, names)

    if not args.json:
        print("=" * 78)
        print("IDENTIFIABILITY CONTRACTS")
        print(f"  fisher artifacts : {sorted(fisher) or 'NONE'}")
        print(f"  trained run      : {args.run or 'NONE'} ({n_trained} seeds)")
        print(f"  untrained null   : {args.baseline or 'NONE'} ({n_untrained} seeds)")
        print("=" * 78)

    reports = []
    for p in PARAMS:
        obs, tag = IDENTIFIED_BY.get(p.name, ((), None))
        u = Unknown(
            name=p.name, kind="field", scope="per_cell",
            enters=p.description or p.name,
            identified_by=obs, bounds=p.bounds,
            reference=p.carroll_value, scale=p.scale,
            bounding_map="log" if p.name in log_scaled else "linear",
        )
        ev = Evidence()
        art = fisher.get(tag) if tag else None
        if art is not None:
            # The artifact schema writes the diagonal as `fisher_info_diag`.
            # `fisher_info` is checked as a fallback only; a silent miss here
            # would report structural as UNAVAILABLE when the evidence exists,
            # which is the wrong kind of wrong for a tool whose whole point is
            # to distinguish absent evidence from failed evidence.
            fi = _dig(art, "fisher_info_diag")
            if fi is None:
                fi = _dig(art, "fisher_info")
            crlb = _dig(art, "crlb")
            if isinstance(fi, dict) and p.name in fi:
                ev.fisher_info = float(fi[p.name])
            elif isinstance(fi, list) and len(fi) == len(names):
                ev.fisher_info = float(fi[names.index(p.name)])
            if isinstance(crlb, dict) and p.name in crlb:
                ev.crlb = float(crlb[p.name])
            elif isinstance(crlb, list) and len(crlb) == len(names):
                ev.crlb = float(crlb[names.index(p.name)])
        if n_untrained:
            ev.untrained_rate = untrained.get(p.name, 0) / n_untrained
            ev.untrained_n = n_untrained
        if n_trained:
            ev.recovered_count = trained.get(p.name)
            ev.recovered_n = n_trained

        r = contract(u, ev)
        reports.append(r)
        if not args.json:
            print()
            print(r.format())

    worst = EXIT_OK
    if any(r.exit_code() == EXIT_FAIL for r in reports):
        worst = EXIT_FAIL
    elif any(r.exit_code() == EXIT_INCOMPLETE for r in reports):
        worst = EXIT_INCOMPLETE

    if args.json:
        print(json.dumps({"reports": [r.to_dict() for r in reports],
                          "exit_code": worst}, indent=2))
    else:
        print()
        print("=" * 78)
        for r in reports:
            print(f"  {r.unknown:<12} {r.verdict}")
        print(f"==> exit {worst}")
        if worst == EXIT_INCOMPLETE:
            print("    INCOMPLETE means a clause has no artifact behind it. That is a")
            print("    named gap, not a pass. Supply --fisher-dir/--run/--baseline.")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
