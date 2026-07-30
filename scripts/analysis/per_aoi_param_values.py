import glob, json, os, sys
import numpy as np
AOIS = ["eqpac", "natlsubpolar", "southernoceanpac"]
PARAM = sys.argv[1] if len(sys.argv) > 1 else "R_PICPOC"

def vals(d, param):
    out = {a: [] for a in AOIS}
    pub = None
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        if "params" not in r or param not in r["params"]:
            continue
        pv = r["params"][param]
        pub = pv["joint_carroll_published"]
        pa = pv.get("per_aoi_recovered") or {}
        for a in AOIS:
            if a in pa:
                out[a].append(pa[a])
    return out, pub

for arm in sys.argv[2:]:
    v, pub = vals(arm, PARAM)
    if pub is None:
        print(f"=== {os.path.basename(arm)}: no data"); continue
    print("=== %-22s %s  Carroll=%.5g" % (os.path.basename(arm), PARAM, pub))
    for a in AOIS:
        x = np.array(v[a], dtype=float)
        if not x.size:
            continue
        rel = np.abs(x - pub) / abs(pub)
        print("    %-18s n=%2d median=%10.5g  x_Carroll=%7.3f  median_rel=%6.3f  frac_below=%.2f  IQR=[%.4g, %.4g]"
              % (a, x.size, np.median(x), np.median(x) / pub, np.median(rel),
                 float(np.mean(x < pub)), np.percentile(x, 25), np.percentile(x, 75)))
    print()
