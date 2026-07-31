import glob, json, os, re
from collections import defaultdict
import numpy as np
OUT = "/work/neu/p2026_0089_neu/monthly_logfull"
arms = defaultdict(dict)
for f in sorted(glob.glob(os.path.join(OUT, "*.json"))):
    b = os.path.basename(f)
    if "_fields" in b or "matrix" in b:
        continue
    tag = b[:-5]
    arm, seed = tag.rsplit("_s", 1)
    d = json.load(open(f))
    pt = d["metrics"]["per_tracer"]
    arms[arm][seed] = {"overall": d["metrics"]["overall_skill_vs_persistence"],
                       "per": {k: v["skill_vs_persistence"] for k, v in pt.items()},
                       "logged": d["config"].get("log_tracers"),
                       "neg": d["rollout"].get("max_frac_negative"),
                       "drift": d["rollout"].get("max_abs_relative_mass_drift")}
for arm in sorted(arms):
    seeds = arms[arm]
    ov = [s["overall"] for s in seeds.values()]
    any_s = next(iter(seeds.values()))
    print("=== %-9s n=%d  logged=%s" % (arm, len(seeds), any_s["logged"]))
    print("    overall skill vs persistence: %s   mean %+.4f" % ([round(x,4) for x in ov], float(np.mean(ov))))
    print("    max frac negative in rollout: %s" % [round(s["neg"],4) for s in seeds.values()])
    # group per-tracer by stem
    stems = defaultdict(list)
    for s in seeds.values():
        for k, v in s["per"].items():
            stems[k.split("_k")[0]].append(v)
    print("    per-tracer (mean over levels and seeds):")
    for st in sorted(stems):
        print("       %-6s %+8.4f" % (st, float(np.mean(stems[st]))))
    print()
if len(arms) == 2:
    a, b = sorted(arms)
    sa = defaultdict(list); sb = defaultdict(list)
    for s in arms[a].values():
        for k, v in s["per"].items(): sa[k.split("_k")[0]].append(v)
    for s in arms[b].values():
        for k, v in s["per"].items(): sb[k.split("_k")[0]].append(v)
    print("=== DELTA  %s minus %s  (positive = logging PIC/POC/FeT helped) ===" % (b, a))
    for st in sorted(set(sa) & set(sb)):
        d = float(np.mean(sb[st]) - np.mean(sa[st]))
        mark = "  <== logged in logfull only" if st in ("PIC","POC","FeT") else ""
        print("   %-6s %+8.4f%s" % (st, d, mark))
