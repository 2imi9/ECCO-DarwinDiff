import glob, os
import numpy as np
import torch

C = "/home/qi_zim_neu/dd_data/ecco_darwin_v5/cache"
# measured per-AOI R_PICPOC bias in obsonly_mld_litic, n=50, every seed same side, tight IQR
BIAS = {"Equatorial Pacific": 1.518,
        "Southern Ocean Pacific": 1.268,
        "North Atlantic Subpolar": 1.029}

rows = []
for f in sorted(glob.glob(os.path.join(C, "*.pt"))):
    d = torch.load(f, map_location="cpu", weights_only=False)
    name = d["aoi_name"]
    cpp = d["chl_per_pft"]
    keys = list(cpp.keys())
    means = {}
    for k in keys:
        v = np.asarray(cpp[k], dtype=float)
        means[k] = float(np.nanmean(v[np.isfinite(v)]))
    tot = sum(means.values())
    fr = {k: means[k] / tot for k in keys} if tot else {}
    pic = np.asarray(d["pic_binned"], dtype=float)
    poc = np.asarray(d["poc_binned"], dtype=float)
    g = np.isfinite(pic) & np.isfinite(poc) & (poc > 0)
    obs = float(np.nanmedian(pic[g] / poc[g])) if g.any() else float("nan")
    b = BIAS.get(name, float("nan"))
    print("===", name)
    print("   pft keys   :", keys)
    print("   fractions  :", {k: round(v, 4) for k, v in fr.items()})
    print("   observed PIC:POC median = %.5f    bias(recovered/Carroll) = %.3f" % (obs, b))
    print()
    rows.append((name, fr, keys, obs, b))

print("=== TEST: does 1/f_large predict the bias? ===")
for label, ntop in (("largest PFT only", 1), ("two largest PFTs", 2)):
    xs, bs, ns = [], [], []
    for name, fr, keys, obs, b in rows:
        if not np.isfinite(b) or len(keys) < ntop:
            continue
        f = sum(fr[k] for k in keys[:ntop])
        xs.append(1.0 / f); bs.append(b); ns.append(name.split()[0])
    if len(xs) >= 3:
        r = float(np.corrcoef(xs, bs)[0, 1])
        print("  %-18s aois=%s" % (label, ns))
        print("  %-18s 1/f =%s" % ("", [round(x, 3) for x in xs]))
        print("  %-18s bias=%s" % ("", [round(x, 3) for x in bs]))
        print("  %-18s corr=%+.3f   spread(1/f)=%.3fx   spread(bias)=%.3fx" % (
            "", r, max(xs) / min(xs), max(bs) / min(bs)))
        print()
