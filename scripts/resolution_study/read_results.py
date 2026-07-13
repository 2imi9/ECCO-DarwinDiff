#!/usr/bin/env python
"""Summarize emulator_poc JSON result files. Usage: read_results.py <glob-or-files...>"""
import json, sys, glob, statistics as st

paths = []
for a in sys.argv[1:]:
    paths.extend(sorted(glob.glob(a)))
if not paths:
    print("no files matched", file=sys.stderr); sys.exit(1)

skills = []
for p in paths:
    try:
        d = json.load(open(p))
    except Exception as e:
        print(f"{p}: ERR {e}"); continue
    m = d["metrics"]; r = d.get("rollout", {})
    cfg = d.get("config", {})
    pt = m["per_tracer"]
    sk = d["headline_overall_skill_vs_persistence"]
    skills.append(sk)
    name = p.split("/")[-1]
    per = " ".join(f"{k}={pt[k]['skill_vs_persistence']:+.3f}" for k in pt)
    gs = cfg.get("grid_shape")
    print(f"{name:<34} {d['verdict']:<8} skill={sk:+.4f} anomR2={m['overall_anomaly_r2_vs_climatology']:+.4f} "
          f"grid={gs} modes={cfg.get('modes')} width={cfg.get('width')} k={cfg.get('rollout_train_k')} "
          f"forcing={cfg.get('forcing')} rollout[stable={r.get('stable')},beats@final={r.get('beats_persistence_at_final_step')}]")
    print(f"    per-tracer: {per}")
if len(skills) > 1:
    print(f"\nAGG n={len(skills)} mean_skill={st.mean(skills):+.4f} "
          f"std={st.pstdev(skills):.4f} min={min(skills):+.4f} max={max(skills):+.4f} "
          f"all_beat={all(s>0 for s in skills)}")
