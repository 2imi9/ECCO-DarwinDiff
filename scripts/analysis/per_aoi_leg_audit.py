"""Is R_PICPOC's headline 50/50 secretly a 2-AOI result?

Daniels CP:PP covers eqpac (34 cells) and natlsubpolar (26 cells) and has ZERO
southernoceanpac coverage -- the loss term auto-gates off there. If the per-AOI
>=2-of-3 majority were always formed by the two ANCHORED AOIs, the largest count
in the manuscript would be a 2-AOI result reported as a 3-AOI one.
"""
import json, glob, sys
sys.path.insert(0, "src")
from darwindiff.diagnostics import band_of

CAL = {"Excellent", "Cal-grade"}
AOIS = ["eqpac", "natlsubpolar", "southernoceanpac"]
COV = {"eqpac": 34, "natlsubpolar": 26, "southernoceanpac": 0}

for run in sys.argv[1:]:
    fs = sorted(glob.glob(run + "/*.json"))
    if not fs:
        print(f"{run}: NO DATA"); continue
    print(f"\n=== {run}  n={len(fs)} ===")
    for param in ("R_PICPOC", "alpfe", "scav_rat"):
        legs = {a: 0 for a in AOIS}; maj = 0; both_anchored = 0; needed_so = 0
        for f in fs:
            pp = json.load(open(f))["params"][param]
            pub = pp["joint_carroll_published"]
            ok = {a: band_of(abs(pp["per_aoi_recovered"][a] - pub) / abs(pub)) in CAL
                  for a in AOIS}
            for a in AOIS:
                legs[a] += ok[a]
            if sum(ok.values()) >= 2:
                maj += 1
                if ok["eqpac"] and ok["natlsubpolar"]:
                    both_anchored += 1
                else:
                    needed_so += 1          # majority REQUIRED the unanchored SO leg
        n = len(fs)
        print(f"  {param:<10} per-AOI>=2of3 = {maj}/{n}")
        for a in AOIS:
            print(f"      {a:<18} {legs[a]:>3}/{n}   (daniels cells: {COV[a]})")
        if param == "R_PICPOC":
            print(f"      majorities formed by the two ANCHORED AOIs : {both_anchored}/{maj}")
            print(f"      majorities that REQUIRED the unanchored SO : {needed_so}/{maj}")
            print(f"      -> SO leg passes {legs['southernoceanpac']}/{n} with ZERO local anchor.")
            print("         A free per-cell field cannot do this: with no Daniels residual in SO,")
            print("         its SO values are untouched by the anchor. Only a SHARED network can")
            print("         carry the anchored AOIs' magnitude into SO. This is the pooling")
            print("         mechanism, measured on the flagship.")
