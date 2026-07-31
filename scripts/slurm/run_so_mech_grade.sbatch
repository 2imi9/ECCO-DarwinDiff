#!/bin/bash
#SBATCH --job-name=dd-so-mech-grade
#SBATCH --account=p2026_0089_neu
#SBATCH --partition=cpu
#SBATCH --time=01:00:00
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4
#SBATCH --output=/scratch/qi_zim_neu/so_mech/GRADED_%j.log
set -u
PY=/home/qi_zim_neu/dd_venv/bin/python     # NOT bare python: the system one has no torch
cd ~/emulator_poc_pw || exit 1
export PYTHONPATH=~/emulator_poc_pw/src
R=/scratch/qi_zim_neu/so_mech

echo "######## 1. verify_run gate -- every arm MUST be exit 0 or nothing here is reportable"
gate_fail=0
for d in so_surf so_sub prior_so_abl so_repro; do
  echo "--- $d"
  "$PY" scripts/verify_run.py $R/$d 2>&1 | tail -3
  rc=${PIPESTATUS[0]}
  echo "    exit=$rc"
  [ "$rc" -ne 0 ] && gate_fail=1
done
echo "GATE_FAIL=$gate_fail"

echo
echo "######## 2. RUNNER-SYNC CONTROL: so_repro must reproduce parent 238079 bitwise"
echo "         (parent ran an older cluster build; this certifies the sync empirically)"
"$PY" - <<'PYEOF'
import glob, json, os
def vals(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        if "params" not in r: continue
        out[r.get("seed")] = {k: (v.get("per_aoi_recovered") or {}).get("southernoceanpac")
                              for k, v in r["params"].items()}
    return out
a = vals("/scratch/qi_zim_neu/so_only2/so_only")     # parent, older runner
b = vals("/scratch/qi_zim_neu/so_mech/so_repro")     # same config, new runner
shared = sorted(set(a) & set(b))
print("shared seeds:", len(shared))
worst = {}
for s in shared:
    for k in a[s]:
        va, vb = a[s].get(k), b[s].get(k)
        if va is None or vb is None: continue
        worst[k] = max(worst.get(k, 0.0), abs(va - vb) / max(abs(va), 1e-30))
ok = True
for k, v in sorted(worst.items()):
    flag = "IDENTICAL" if v < 1e-9 else "*** DIFFERS ***"
    if v >= 1e-9: ok = False
    print("  %-11s max relative difference %.3e %s" % (k, v, flag))
print("RUNNER_SYNC_INERT=" + ("yes" if ok and shared else "NO"))
PYEOF

echo
echo "######## 3. NULL CONTROL: prior_so_abl must equal prior_so_only (LR=0 cannot see the loss)"
"$PY" - <<'PYEOF'
import glob, json, os
def vals(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        if "params" not in r: continue
        out[r.get("seed")] = {k: (v.get("per_aoi_recovered") or {}).get("southernoceanpac")
                              for k, v in r["params"].items()}
    return out
a = vals("/scratch/qi_zim_neu/so_only2/prior_so_only")
b = vals("/scratch/qi_zim_neu/so_mech/prior_so_abl")
shared = sorted(set(a) & set(b))
worst = 0.0
for s in shared:
    for k in a[s]:
        va, vb = a[s].get(k), b[s].get(k)
        if va is None or vb is None: continue
        worst = max(worst, abs(va - vb) / max(abs(va), 1e-30))
print("shared seeds: %d   max relative difference %.3e  ->  %s"
      % (len(shared), worst, "IDENTICAL" if worst < 1e-9 and shared else "*** DIFFERS ***"))
PYEOF

echo
echo "######## 4. PRE-REGISTERED READ (2026-07-30_prereg_scavrat_mechanism_surface_vs_depth.md)"
"$PY" - <<'PYEOF'
import glob, json, os, math
from darwindiff.carroll6 import PARAMS
from darwindiff.grading import is_recovered_per_aoi

CARROLL = {p.name: p.carroll_value for p in PARAMS}
R = "/scratch/qi_zim_neu/so_mech"

def flags(d):
    """seed -> {param: recovered bool}, via the single-source grading rule."""
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        if "params" not in r: continue
        out[r["seed"]] = {k: is_recovered_per_aoi(v.get("per_aoi_recovered"), CARROLL.get(k))
                          for k, v in r["params"].items()}
    return out

def binom_tail_ge(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))

def fisher_2x2_two_sided(a, b, c, d):
    """P of tables at most as probable as observed, same margins."""
    n = a + b + c + d; r1 = a + b; c1 = a + c
    def pr(x):
        return (math.comb(r1, x) * math.comb(n - r1, c1 - x)) / math.comb(n, c1)
    obs = pr(a)
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= obs * (1 + 1e-9)))

def mcnemar_exact(b, c):
    """Two-sided exact binomial on the discordant pairs."""
    n = b + c
    if n == 0: return 1.0, n
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) * 0.5**n for i in range(0, k + 1))), n

arms = {name: flags(os.path.join(R, name))
        for name in ("so_surf", "so_sub", "so_repro", "prior_so_abl")}
parent = flags("/scratch/qi_zim_neu/so_only2/so_only")
null = arms["prior_so_abl"]

print("n seeds per arm:", {k: len(v) for k, v in arms.items()}, " parent:", len(parent))
print()
print("%-12s %-11s %-9s %-9s %-11s %s" % ("arm", "param", "recovered", "null", "P(>=k)", "verdict"))
counts = {}
for arm in ("so_surf", "so_sub"):
    for prm in ("scav_rat", "alpfe", "R_PICPOC", "diatomgraz"):
        k = sum(1 for s, f in arms[arm].items() if f.get(prm))
        n = len(arms[arm])
        kn = sum(1 for s, f in null.items() if f.get(prm))
        p = max(kn / max(len(null), 1), 3.0 / 50.0)
        P = binom_tail_ge(k, n, p)
        rec = (k >= 25 and P < 0.01)
        counts[(arm, prm)] = (k, n, P, rec)
        print("%-12s %-11s %-9s %-9s %-11.3e %s"
              % (arm, prm, f"{k}/{n}", f"{kn}/{len(null)}", P,
                 "RECOVERS" if rec else "not above chance"))
    print()

ks, ns, _, rs = counts[("so_surf", "scav_rat")]
kb, nb, _, rb = counts[("so_sub",  "scav_rat")]

print("---- PRIMARY (volume-matched head-to-head, 13 surface bins vs 14 subsurface bins)")
pf = fisher_2x2_two_sided(ks, ns - ks, kb, nb - kb)
print("  so_surf %d/%d  vs  so_sub %d/%d   Fisher exact two-sided P = %.4g  -> %s"
      % (ks, ns, kb, nb, pf, "DIFFERENT" if pf < 0.05 else "not distinguishable"))

print()
print("---- SECONDARY (paired vs parent so_only, confounded by data volume 27 -> 13/14 bins)")
for arm, k, n in (("so_surf", ks, ns), ("so_sub", kb, nb)):
    shared = sorted(set(arms[arm]) & set(parent))
    b = sum(1 for s in shared if parent[s].get("scav_rat") and not arms[arm][s].get("scav_rat"))
    c = sum(1 for s in shared if arms[arm][s].get("scav_rat") and not parent[s].get("scav_rat"))
    P, nd = mcnemar_exact(b, c)
    kp = sum(1 for s in shared if parent[s].get("scav_rat"))
    print("  %-8s %d/%d vs parent %d/%d on %d shared seeds | discordant %d lost / %d gained"
          " | McNemar exact P = %.4g %s"
          % (arm, k, n, kp, len(shared), len(shared), b, c, P,
             "(differs)" if P < 0.05 else "(not distinguishable)"))

print()
print("---- PRE-REGISTERED VERDICT")
if rs and not rb:   v = "CURVATURE  (surface alone suffices; depth not necessary)"
elif rb and not rs: v = "DEPTH  (subsurface alone suffices; surface not sufficient)"
elif rs and rb:     v = "BOTH CHANNELS CARRY IT  (neither level necessary alone)"
else:               v = "SYNERGY / JOINT-ONLY  (individually insufficient, jointly sufficient)"
print(" ", v)

ka = counts[("so_surf", "alpfe")][0]
print()
print("---- FALSIFIER CHECK (pre-registered)")
if (not rs) and (not rb) and ka < 25:
    print("  TRIPPED: both arms collapsed AND alpfe collapsed in so_surf (%d/50)." % ka)
    print("  A single iron term is too data-poor at 13-14 bins. This run does NOT separate")
    print("  the mechanisms and must NOT be read as evidence for H_depth.")
else:
    print("  clear: alpfe in so_surf = %d/50 (control holds -> the arm can fit)" % ka)
PYEOF

echo
echo "######## 5. per-AOI vs own null (reference tool, both arms)"
for d in so_surf so_sub; do
  echo "--- $d"
  "$PY" scripts/analysis/per_aoi_vs_null.py $R/$d $R/prior_so_abl \
    /work/neu/p2026_0089_neu/coverage/so_mech_$d.json 2>&1 | tail -12
done

echo
echo "######## 6. iron-coverage provenance, now recorded in the artifact"
"$PY" - <<'PYEOF'
import glob, json
for arm in ("so_surf", "so_sub", "so_repro"):
    fs = sorted(glob.glob(f"/scratch/qi_zim_neu/so_mech/{arm}/*.json"))
    if not fs: continue
    d = json.load(open(fs[0]))
    print("  %-9s geotraces_w=%-4s surf_cells=%s | geotraces_sub_w=%-4s sub_cells=%s"
          % (arm, d.get("geotraces_w"), d.get("n_geo_surf_cells_per_aoi"),
             d.get("geotraces_sub_w"), d.get("n_geo_sub_cells_per_aoi")))
PYEOF
