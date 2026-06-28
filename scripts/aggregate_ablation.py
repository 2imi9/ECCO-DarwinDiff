import json, glob, os, statistics
PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
HOLD3 = ["alpfe", "scav_rat", "R_PICPOC"]

def cal(b):
    return b in ("Cal-grade", "Excellent")

def load(d):
    rows = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        j = json.load(open(f))
        rp = j.get("params", {})
        rows.append({
            "seed": j.get("seed"),
            "loss": j.get("loss_final"),
            "n": j.get("n_cal_grade"),
            "b": {p: rp.get(p, {}).get("joint_band", "") for p in PARAMS},
        })
    return rows

def summ(name, rows):
    if not rows:
        print(name, "NO DATA")
        return
    pp = {p: sum(cal(r["b"][p]) for r in rows) for p in PARAMS}
    h3 = sum(all(cal(r["b"][p]) for p in HOLD3) for r in rows)
    ml = statistics.mean(r["loss"] for r in rows)
    mn = statistics.mean(r["n"] for r in rows)
    print()
    print("=== %s  (n=%d) ===" % (name, len(rows)))
    print("  per-param Cal-grade+:  " + "  ".join("%s=%d" % (p, pp[p]) for p in PARAMS))
    print("  {alpfe,scav_rat,R_PICPOC} JOINT hold: %d/%d" % (h3, len(rows)))
    print("  mean n_cal/6: %.2f   mean loss_final: %.1f" % (mn, ml))
    return pp, h3, mn, ml

base = "/projects/schultz/qi.zim/runs"
g = load(base + "/abl_global")
pcdir = base + "/abl_percell" if len(glob.glob(base + "/abl_percell/*.json")) >= 10 \
    else base + "/sweep_holdtogether_20260626_1119/geo1_dan1"
pc = load(pcdir)
print("per-cell source:", os.path.basename(pcdir))
summ("PER-CELL (DINN)", pc)
summ("GLOBAL-SCALAR", g)
