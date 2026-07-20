#!/usr/bin/env python
"""per_pft_picpoc_experiment.py -- test Jon's per-functional-type calcite
hypothesis (his 2026-06-28 reply) against the observed PIC:POC basin spread.

Jon: only some Darwin PFTs calcify ("other large eukaryotes" = Chl2, the
coccolithophore pool), so bulk PIC:POC SHOULD vary in space; per-functional-type
PIC:POC should be more consistent. The 5-PFT box already has this as the gated
USE_COCCOLITH_ONLY_CALCITE option (carroll6_5pft_2layer.py:465-479).

Mechanism (exact, from the box's calcite source term dPIC = R * calcite_mort):
  - BULK   (current default): calcite_mort = mort_total  -> realized
    bulk PIC:POC = R  (a CONSTANT -- the single-scalar closure limit).
  - PER-PFT (Jon / coccolith-only): calcite_mort = mort_calcifier  -> realized
    bulk PIC:POC = R * f_calc, where f_calc = calcifier share of total mortality
    flux. Now the basin spread is carried by f_calc at a CONSTANT per-calcifier R.

Test: can ONE per-calcifier ratio R reproduce Darwin's observed surface
ratio-of-means {eqpac 0.033, natl 0.676, SO 0.0067} via plausible f_calc?
"""
from __future__ import annotations
import numpy as np

# Darwin v05 surface PIC:POC ratio-of-means per AOI (as emailed to Jon).
OBS = {"eqpac": 0.033, "natl": 0.676, "SO": 0.0067}
R_BULK_CARROLL = 0.04245     # the single bulk Carroll R_PICPOC

print("=" * 68)
print("PER-PFT (COCCOLITH-ONLY) CALCITE vs BULK -- Jon's hypothesis test")
print("=" * 68)

# --- 1. Numerical confirmation that realized bulk PIC:POC = R * f_calc -------
# Minimal steady-flux check: a community whose calcifier biomass fraction is phi.
# Mortality ~ m*P (linear-dominated near the rain-ratio-relevant surface), so the
# calcifier share of total mortality f_calc tracks phi. PIC from calcifier only.
rng = np.random.default_rng(0)
print("\n[1] realized bulk PIC:POC under coccolith-only, swept over calcifier fraction:")
print(f"    (constant per-calcifier R = 1.0)")
for phi in [0.005, 0.05, 0.2, 0.5, 0.8]:
    P = np.array([1 - phi, phi])           # [non-calcifier, calcifier] biomass
    m = np.array([0.15, 0.15])             # shared linear mortality (per day)
    mort = m * P
    f_calc = mort[1] / mort.sum()
    R = 1.0
    realized = R * f_calc                   # bulk PIC:POC
    print(f"    calcifier frac phi={phi:5.3f} -> f_calc={f_calc:5.3f} -> bulk PIC:POC = {realized:6.4f}")
print("    => bulk PIC:POC scales ~linearly with the calcifier fraction (mechanism confirmed).")

# --- 2. BULK single-scalar: structurally constant -> cannot span the basins ---
print("\n[2] BULK single scalar (current default, calcite_mort=mort_total):")
print(f"    bulk PIC:POC = R = {R_BULK_CARROLL} EVERYWHERE.")
span = max(OBS.values()) / min(OBS.values())
print(f"    observed basins span {span:.0f}x ({min(OBS.values())}..{max(OBS.values())}).")
print(f"    -> a single bulk scalar is mathematically incapable of the spread. (closure limit)")

# --- 3. PER-PFT: solve for ONE per-calcifier R that fits all three basins ------
# bulk_basin = R * f_calc_basin, with f_calc in (0,1]. Anchor R so the bloom
# basin (natl) sits at a high-but-physical calcifier fraction, then read off the
# implied f_calc for the others. A realistic coccolithophore PIC:POC is ~0.8-1.2.
print("\n[3] PER-PFT (coccolith-only): does ONE per-calcifier R fit all basins?")
for R in [0.8, 1.0, 1.2]:
    fr = {k: v / R for k, v in OBS.items()}
    ok = all(0 < f <= 1.0 for f in fr.values())
    line = "  ".join(f"{k} f_calc={fr[k]*100:5.1f}%" for k in ("eqpac", "natl", "SO"))
    print(f"    R={R:4.2f}: {line}   {'[all fractions <=100%: OK]' if ok else '[INFEASIBLE: f>100%]'}")

R_pick = 1.0
fr = {k: v / R_pick for k, v in OBS.items()}
print(f"\n    At a single realistic per-calcifier R={R_pick} (coccolithophore PIC:POC ~1):")
print(f"      implied calcifier (Chl2) fraction:  eqpac {fr['eqpac']*100:.1f}%  |  "
      f"natl {fr['natl']*100:.1f}%  |  SO {fr['SO']*100:.1f}%")
print(f"      ->  ~{fr['natl']/fr['SO']:.0f}x calcifier-fraction span, natl >> eqpac >> SO.")

print("\n" + "-" * 68)
print("VERDICT")
print("-" * 68)
print("""A single bulk R_PICPOC is structurally constant (bulk PIC:POC = R) and
CANNOT reproduce the 100x basin spread -- the closure limit we reported.

Moving the ratio onto the calcifier PFT (Jon's per-functional-type idea =
the box's already-built USE_COCCOLITH_ONLY_CALCITE) makes
   bulk PIC:POC = R x calcifier_fraction,
so ONE constant per-calcifier R ~1 (a realistic coccolithophore value)
reproduces all three basins via calcifier fractions of ~3% (eqpac) /
~68% (natl bloom) / ~0.7% (SO) -- matching Darwin's documented biogeography
(eqpac ~no coccolithophores, natl coccolithophore bloom zone, SO diatom-
dominated). Jon's mechanism is quantitatively consistent.

CAVEAT (the Track-2 hook): the 0-D box homogenizes the calcifier field, so it
cannot REALIZE this spread internally -- it needs the SPATIAL Chl2 (calcifier)
field. That is exactly why this is a higher-dimensional-surrogate (Track-2)
payoff, and why USE_COCCOLITH_ONLY_CALCITE was shelved in the 0-D box (ADR 0001).
NEXT: validate against Darwin's REAL per-AOI Chl2 fraction (is observed_bulk /
f_calc actually constant across basins?).""")
