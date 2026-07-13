#!/usr/bin/env python
"""Aggregate emulator_poc JSON results into config groups and diagnostic tables.

Groups runs by (grid, modes, width, forcing, k, epochs), aggregates skill across
seeds, and — crucially for the resolution-sharpening claim — decomposes skill into
MODEL vs PERSISTENCE absolute physical RMSE per tracer (the "denominator trap"
check). Persistence physical RMSE is recovered exactly from saved fields:
    skill = 1 - SSE_model/SSE_persist  =>  rmse_persist = rmse_model / sqrt(1 - skill).

Usage: analyze_grid.py <glob...>
"""
import json, sys, glob, math, statistics as st
from collections import defaultdict

paths = []
for a in sys.argv[1:]:
    paths.extend(sorted(glob.glob(a)))
if not paths:
    print("no files matched", file=sys.stderr); sys.exit(1)

TRACERS = ["DIC", "ALK", "PIC", "POC", "FeT", "Chl1"]
groups = defaultdict(list)   # key -> list of run dicts

for p in paths:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f"SKIP {p}: {e}", file=sys.stderr); continue
    cfg = d.get("config", {}); m = d["metrics"]; r = d.get("rollout", {})
    gs = tuple(cfg.get("grid_shape", []))
    forcing = cfg.get("forcing", [])
    forc = "+".join(forcing) if forcing else "none"
    key = (gs, cfg.get("modes"), cfg.get("width"), forc, cfg.get("rollout_train_k"), cfg.get("epochs"))
    pt = m["per_tracer"]
    per = {}
    for t, dd in pt.items():
        sk = dd["skill_vs_persistence"]; rm = dd["rmse_physical"]
        rp = rm / math.sqrt(1.0 - sk) if sk < 1.0 else float("nan")  # persistence phys RMSE
        per[t] = {"skill": sk, "rmse_model": rm, "rmse_persist": rp}
    groups[key].append({
        "skill": d["headline_overall_skill_vs_persistence"],
        "anomR2": m["overall_anomaly_r2_vs_climatology"],
        "persist_vs_clim": m.get("persistence_skill_vs_climatology"),
        "n_cells": m.get("n_metric_cells"),
        "stable": r.get("stable"), "beats_final": r.get("beats_persistence_at_final_step"),
        "per": per, "file": p.split("/")[-1],
    })

def agg(vals):
    vals = [v for v in vals if v is not None and (isinstance(v, bool) or math.isfinite(v))]
    if not vals: return (float("nan"), float("nan"), 0)
    if isinstance(vals[0], bool):
        return (sum(vals)/len(vals), None, len(vals))
    return (st.mean(vals), st.pstdev(vals) if len(vals) > 1 else 0.0, len(vals))

print(f"# {len(paths)} runs -> {len(groups)} config groups\n")
hdr = f"{'grid':>10} {'mod':>3} {'wid':>3} {'forcing':>8} {'k':>2} {'ep':>5} {'n':>2} {'skill':>16} {'cells':>6} {'stable':>6} {'beats@f':>7}"
print(hdr); print("-"*len(hdr))
for key in sorted(groups, key=lambda k: (-(k[0][0]*k[0][1] if k[0] else 0), k[1] or 0, k[2] or 0, k[3], k[4] or 0, k[5] or 0)):
    gs, modes, width, forc, k, ep = key
    runs = groups[key]
    sm, ss, sn = agg([x["skill"] for x in runs])
    stb, _, _ = agg([x["stable"] for x in runs])
    bf, _, _ = agg([x["beats_final"] for x in runs])
    gstr = f"{gs[0]}x{gs[1]}" if gs else "?"
    print(f"{gstr:>10} {modes:>3} {width:>3} {forc:>8} {k:>2} {ep:>5} {sn:>2} "
          f"{sm:+.4f}±{ss:.4f} {runs[0]['n_cells'] or 0:>6} {stb:>6.2f} {bf:>7.2f}")

# --- per-tracer skill + RMSE decomposition, grouped ---
print("\n\n# PER-TRACER: skill / model-RMSE / persistence-RMSE (mean over seeds)")
print("# denominator-trap check: is higher skill from LOWER model RMSE or HIGHER persistence RMSE?")
for key in sorted(groups, key=lambda k: (-(k[0][0]*k[0][1] if k[0] else 0), k[1] or 0, k[2] or 0, k[3])):
    gs, modes, width, forc, k, ep = key
    runs = groups[key]
    gstr = f"{gs[0]}x{gs[1]}" if gs else "?"
    print(f"\n[{gstr} m{modes} w{width} f={forc} k{k} ep{ep} n={len(runs)}]")
    for t in TRACERS:
        sk = agg([x["per"].get(t, {}).get("skill") for x in runs])[0]
        rm = agg([x["per"].get(t, {}).get("rmse_model") for x in runs])[0]
        rp = agg([x["per"].get(t, {}).get("rmse_persist") for x in runs])[0]
        print(f"    {t:<5} skill={sk:+.3f}  rmse_model={rm:.4g}  rmse_persist={rp:.4g}")
