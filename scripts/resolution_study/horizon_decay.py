#!/usr/bin/env python
"""Per-step rollout skill decay from existing JSONs: does resolution help LONGER horizons?
Skill_k = 1 - MSE_model_k / MSE_persist_k (z-space), averaged over seeds. Usage: horizon_decay.py <label> <glob>..."""
import json, sys, glob, statistics as st

def load(g):
    rows = []
    for p in sorted(glob.glob(g)):
        try: d = json.load(open(p))
        except Exception: continue
        r = d.get("rollout", {})
        m = r.get("step_mse_z_model"); pz = r.get("step_mse_z_persistence")
        if m and pz and len(m) == len(pz):
            rows.append([1 - mi/pi if pi > 0 else float("nan") for mi, pi in zip(m, pz)])
    return rows

label = sys.argv[1]
print(f"=== {label} : per-step rollout skill (mean over seeds) ===")
for g in sys.argv[2:]:
    rows = load(g)
    if not rows:
        print(f"  {g}: no rollout data"); continue
    K = min(len(r) for r in rows)
    per_step = [st.mean(r[k] for r in rows) for k in range(K)]
    tag = g.split("/")[-1].replace("_s*.json", "")
    print(f"  {tag:26} n={len(rows)} steps=" + " ".join(f"{s:+.3f}" for s in per_step))
