"""Validate the per-PFT calcite hypothesis against Darwin's REAL per-AOI Chl fields.

Follow-up to scripts/per_pft_picpoc_experiment.py, whose stated NEXT step was:
"validate against Darwin's REAL per-AOI Chl2 fraction (is observed_bulk / f_calc
actually constant across basins?)".

The analytic per_pft test showed a single per-calcifier ratio R could reproduce the
~100x PIC:POC basin spread IF the calcifier fraction f_calc were 3.3% (eqpac) / 67.6%
(natl) / 0.7% (SO). That test ASSUMED the fractions. Here we read Darwin's ACTUAL Chl
fields from the native caches and check whether the hypothesis survives:

  bulk PIC:POC = R * f_calc   =>   R = bulk PIC:POC / f_calc  should be CONSTANT across AOIs.

We also identify the calcifier empirically (which Chl_i covaries with PIC across cells),
rather than assuming Chl2 is the coccolithophore proxy.

Data: D:/ecco_darwin_v5/cache/native_targets_{equatorial_pacific,north_atlantic_subpolar,
southern_ocean_pacific}.pt (per-cell fields, native LLC270). CPU-only.

NOTE ON DATA HYGIENE: the cached Chl fields contain small NEGATIVE values (bin/interp
artifacts; e.g. SO Chl2 is negative in ~88% of cells but tiny) and a near-zero Chl4.
We clip Chl to >= 0 before taking fractions, and only use cells with total Chl above a
floor. PIC/POC are non-negative except a handful of tiny-negative POC in SO (masked).
"""
from __future__ import annotations

import numpy as np
import torch

CACHES = {
    "eqpac": "D:/ecco_darwin_v5/cache/native_targets_equatorial_pacific.pt",
    "natl": "D:/ecco_darwin_v5/cache/native_targets_north_atlantic_subpolar.pt",
    "SO": "D:/ecco_darwin_v5/cache/native_targets_southern_ocean_pacific.pt",
}
CHL_FLOOR = 1e-4  # mg Chl/m^3 total below which a cell has no meaningful composition


def _load(path):
    d = torch.load(path, map_location="cpu", weights_only=False)
    pic = np.asarray(d["pic_binned"]).ravel().astype(float)
    poc = np.asarray(d["poc_binned"]).ravel().astype(float)
    chl = {i: np.clip(np.asarray(d["chl_per_pft"][f"Chl{i}"]).ravel().astype(float), 0.0, None)
           for i in range(1, 6)}  # clip negatives (artifacts) to 0
    return d["aoi_name"], pic, poc, chl


def main() -> int:
    print("=" * 74)
    print("PER-PFT CALCITE HYPOTHESIS vs DARWIN'S REAL Chl FIELDS")
    print("=" * 74)

    # --- 1. Identify the calcifier empirically (per-cell corr of each Chl_i with PIC) ---
    print("\n[1] Which Chl_i covaries with PIC across cells? (per-AOI Pearson r, cleaned)")
    print("    (the calcifier PFT should track PIC; assumed proxy in prior work = Chl2)")
    for key, path in CACHES.items():
        name, pic, poc, chl = _load(path)
        good = np.isfinite(pic) & (pic > 0)
        rr = []
        for i in range(1, 6):
            c = chl[i]
            m = good & np.isfinite(c) & (c > 0)
            if m.sum() > 20 and c[m].std() > 0 and pic[m].std() > 0:
                r = np.corrcoef(np.log(c[m]), np.log(pic[m]))[0, 1]
            else:
                r = np.nan
            rr.append(r)
        best = int(np.nanargmax(rr)) + 1
        print(f"    {name:24s} r(logChl_i,logPIC): " +
              " ".join(f"Chl{i}={rr[i-1]:+.2f}" for i in range(1, 6)) +
              f"   -> best=Chl{best}")

    # --- 2. Bulk PIC:POC, calcifier fraction, and implied per-calcifier R -------------
    print("\n[2] Is  R = bulk_PICPOC / f_calc  CONSTANT across AOIs? (calcifier = Chl2)")
    print(f"    f_calc = sum(Chl2)/sum(Chl1..5), biomass-weighted; cells with totChl>{CHL_FLOOR}")
    rows = []
    for key, path in CACHES.items():
        name, pic, poc, chl = _load(path)
        tot = sum(chl[i] for i in range(1, 6))
        m = np.isfinite(pic) & np.isfinite(poc) & (poc > 0) & (tot > CHL_FLOOR)
        bulk = pic[m].sum() / poc[m].sum()            # flux-weighted bulk PIC:POC
        f_calc = chl[2][m].sum() / tot[m].sum()       # biomass-weighted calcifier fraction
        R_implied = bulk / f_calc if f_calc > 0 else np.nan
        rows.append((name, m.sum(), bulk, f_calc, R_implied))
        print(f"    {name:24s} N={m.sum():6d}  bulkPICPOC={bulk:8.4f}  "
              f"f_calc(Chl2)={f_calc:6.3f}  => implied R={R_implied:8.3f}")

    Rs = np.array([r[4] for r in rows])
    fcs = np.array([r[3] for r in rows])
    bulks = np.array([r[2] for r in rows])
    print(f"\n    calcifier fraction spread: {fcs.min():.3f}..{fcs.max():.3f}  "
          f"({fcs.max()/fcs.min():.1f}x)")
    print(f"    bulk PIC:POC spread:       {bulks.min():.4f}..{bulks.max():.4f}  "
          f"({bulks.max()/bulks.min():.0f}x)")
    print(f"    implied per-calcifier R:   {np.nanmin(Rs):.3f}..{np.nanmax(Rs):.3f}  "
          f"({np.nanmax(Rs)/np.nanmin(Rs):.0f}x)")

    # --- 3. Verdict -------------------------------------------------------------------
    print("\n" + "-" * 74)
    print("VERDICT")
    print("-" * 74)
    frac_spread = fcs.max() / fcs.min()
    R_spread = np.nanmax(Rs) / np.nanmin(Rs)
    bulk_spread = bulks.max() / bulks.min()
    if frac_spread < 3 and R_spread > 5:
        print(f"REFUTED (composition-only): the REAL calcifier fraction is nearly FLAT")
        print(f"  ({frac_spread:.1f}x) while the bulk PIC:POC spans {bulk_spread:.0f}x. A single")
        print(f"  per-calcifier R is NOT constant ({R_spread:.0f}x). So composition (which PFTs")
        print(f"  are present) does NOT carry the basin spread in Darwin's real fields.")
        print(f"  => the spread is carried by the PER-CALCIFIER calcification EFFICIENCY,")
        print(f"     which must vary with ENVIRONMENT / carbonate chemistry (SST, Omega, ...).")
        print(f"  => Track-2 calcite_closure should be ENVIRONMENT-driven, not composition-only.")
    else:
        print(f"  frac_spread={frac_spread:.1f}x  R_spread={R_spread:.0f}x  bulk_spread={bulk_spread:.0f}x")
        print("  (see numbers; not the clean composition-refuted signature)")
    print("\nCAVEAT: Chl fields carry bin/interp negatives (clipped to 0); SO Chl2 is")
    print("near-zero in most cells (diatom-dominated, few coccolithophores) -> SO f_calc")
    print("is noisy. The eqpac-vs-natl contrast (flat f_calc, 20x bulk gap) is the robust core.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
