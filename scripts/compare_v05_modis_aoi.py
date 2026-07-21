"""v05 vs MODIS-Aqua surface chlorophyll, per-AOI, 2003-2018.

Generalises the 2026-07-19 subpolar-N.-Atlantic comparison (the first evaluation of
ECCO-Darwin chlorophyll against real observations) to any AOI in ``AOI_BY_KEY``.

Run:
    python scripts/compare_v05_modis_aoi.py --aoi eqpac        --data-dir C:/Users/Frank/dd_chl_val
    python scripts/compare_v05_modis_aoi.py --aoi natlsubpolar --data-dir C:/Users/Frank/dd_chl_val

Method notes (each is a trap that produces a wrong answer if skipped):
  * log10 throughout. The linear mean runs ~86% above the geometric mean in the
    subpolar N. Atlantic.
  * v05 is MASKED TO MODIS-VALID PIXELS per month, per cell, BEFORE any aggregate.
    Ocean colour has zero coverage under cloud/ice/polar night and the sampling is
    latitude-structured, so an all-weather model mean vs a fair-weather satellite
    mean is meaningless.
  * MODIS 4 km is binned to the v05 grid with a GEOMETRIC mean (mean of logs); an
    arithmetic one would reintroduce the linear bias at the binning step.
  * v05 negatives are clipped to MODIS valid_min (0.001) and the count reported.
    Clipping RAISES v05, so a reported low bias is conservative.
  * Time comes from the CORRECTED calendar (delta_t = 1200 s, not 900 s). Inputs
    are the ``*_monthly_fixed.npz`` extracts, which already carry ``cal_ratio``.

THE CORRELATION STATISTIC. The headline Pearson r across all months is dominated by
the seasonal cycle, which both fields trivially share -- it measures agreement on the
*existence* of a seasonal cycle, not on which years were productive. We therefore
report three r's, and the headline one must never be quoted alone:

  r_all       - all months, seasonal-cycle-dominated. NOT a skill number.
  r_anomaly   - month-of-year climatology removed from BOTH series first. This is
                the interannual-skill number and is the one to lead with. It is
                regime-independent, unlike a growing-season window.
  r_season    - restricted to a growing-season window (May-Sep in the subpolar N.
                Atlantic). Kept for continuity with the 2026-07-19 result; it is
                not meaningful at the equator, where there is no bloom season.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import netCDF4 as nc
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from darwindiff.ecco_darwin_loader import AOI_BY_KEY  # noqa: E402

VALID_MIN, VALID_MAX = 0.001, 100.0
NOISE_FLOOR_DEX = 0.130  # MODIS retrieval +/-35%
N_BOOT = 2000

# MODIS download filename stem per AOI key (the download script's own convention).
MODIS_STEM = {"eqpac": "eqpac", "natlsubpolar": "natl"}
# Growing-season window per AOI. None => not meaningful for this regime.
GROWING_SEASON = {"natlsubpolar": (5, 9), "eqpac": None}


def bin_geo(field, ilat, ilon, nlat, nlon, mlat, mlon):
    """MODIS 4 km -> v05 grid, geometric mean (mean of logs), NaN-safe."""
    lg = np.log10(np.clip(field, VALID_MIN, VALID_MAX))
    lg[~np.isfinite(field)] = np.nan
    out = np.full((nlat, nlon), np.nan)
    cnt = np.zeros((nlat, nlon))
    acc = np.zeros((nlat, nlon))
    ok = np.isfinite(lg)
    ii = ilat[:, None].repeat(len(mlon), 1)[ok]
    jj = ilon[None, :].repeat(len(mlat), 0)[ok]
    np.add.at(acc, (ii, jj), lg[ok])
    np.add.at(cnt, (ii, jj), 1.0)
    good = cnt > 0
    out[good] = acc[good] / cnt[good]
    return out  # log10 units


def deseasonalize(vals, moy):
    """Remove the month-of-year mean. Returns anomalies in the same units."""
    out = np.array(vals, dtype=float)
    for m in range(1, 13):
        sel = moy == m
        if sel.sum() >= 2:
            out[sel] = out[sel] - out[sel].mean()
        elif sel.sum() == 1:
            out[sel] = 0.0  # a single sample carries no anomaly information
    return out


def safe_r(a, b):
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def boot_ci(x, n_boot=N_BOOT, seed=0):
    """Percentile bootstrap CI of the mean."""
    rng = np.random.default_rng(seed)
    if len(x) < 3:
        return (float("nan"), float("nan"))
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = np.asarray(x)[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aoi", required=True, choices=sorted(MODIS_STEM))
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    aoi = AOI_BY_KEY[args.aoi]
    d = args.data_dir

    # ---- v05 (already on the corrected calendar) ----------------------------
    npz = os.path.join(d, f"{args.aoi}_monthly_fixed.npz")
    z = np.load(npz, allow_pickle=True)
    v05 = z["chl"].astype(np.float64)
    months = [str(m) for m in z["months"]]
    omask = z["valid_mask"]
    H, W = omask.shape
    cal_ratio = float(z["cal_ratio"]) if "cal_ratio" in z.files else float("nan")

    # ---- MODIS --------------------------------------------------------------
    stem = MODIS_STEM[args.aoi]
    files = sorted(glob.glob(os.path.join(d, f"{stem}_[0-9][0-9][0-9][0-9].nc")))
    if not files:
        raise SystemExit(f"no MODIS files matching {stem}_YYYY.nc in {d}")
    mod = {}
    mlat = mlon = None
    for f in files:
        ds = nc.Dataset(f)
        t = nc.num2date(ds.variables["time"][:], ds.variables["time"].units)
        mlat = ds.variables["latitude"][:]
        mlon = ds.variables["longitude"][:]
        ch = ds.variables["chlorophyll"][:]
        for i, tt in enumerate(t):
            mod["%04d-%02d" % (tt.year, tt.month)] = np.ma.filled(ch[i], np.nan)
        ds.close()

    # The v05 AOI grid cells are CENTERED on [lat_min, lat_max] (H centers span the
    # inclusive bounds; cf. daniels_loader/geotraces_loader `arange(lat_min, lat_max+res/2, res)`),
    # so the H+1 bin edges must bracket those centers by half a cell on each side.
    # Using the centers themselves as edges packs H bins into (lat_max-lat_min) deg —
    # a half-cell shift that clips MODIS pixels into the edge bins and biases the map.
    lat_res = (aoi.lat_max - aoi.lat_min) / max(H - 1, 1)
    lon_res = (aoi.lon_max - aoi.lon_min) / max(W - 1, 1)
    lat_edges = np.linspace(aoi.lat_min - lat_res / 2.0, aoi.lat_max + lat_res / 2.0, H + 1)
    lon_edges = np.linspace(aoi.lon_min - lon_res / 2.0, aoi.lon_max + lon_res / 2.0, W + 1)
    ilat = np.clip(np.digitize(mlat, lat_edges) - 1, 0, H - 1)
    ilon = np.clip(np.digitize(mlon, lon_edges) - 1, 0, W - 1)

    rows, clipped, n_used = [], 0, 0
    for k, mm in enumerate(months):
        if mm not in mod:
            continue
        sat_lg = bin_geo(mod[mm], ilat, ilon, H, W, mlat, mlon)
        mdl = v05[k]
        clipped += int(np.sum((mdl < VALID_MIN) & omask))
        mdl_lg = np.log10(np.clip(mdl, VALID_MIN, VALID_MAX))
        m = omask & np.isfinite(sat_lg)
        if m.sum() < 50:
            continue
        n_used += 1
        rows.append(
            dict(
                month=mm,
                model=float(np.nanmean(mdl_lg[m])),
                sat=float(np.nanmean(sat_lg[m])),
                cover=float(m.sum() / omask.sum()),
                bias_map_n=int(m.sum()),
            )
        )

    if not rows:
        raise SystemExit("no months survived the >=50-valid-cell filter")

    moy = np.array([int(r["month"][5:7]) for r in rows])
    md = np.array([r["model"] for r in rows])
    st = np.array([r["sat"] for r in rows])
    cov = np.array([r["cover"] for r in rows])
    dif = md - st

    bias = float(dif.mean())
    lo, hi = boot_ci(dif)
    rmse = float(np.sqrt((dif**2).mean()))

    r_all = safe_r(md, st)
    md_a, st_a = deseasonalize(md, moy), deseasonalize(st, moy)
    r_anom = safe_r(md_a, st_a)

    gs = GROWING_SEASON.get(args.aoi)
    if gs is not None:
        sel = (moy >= gs[0]) & (moy <= gs[1])
        r_season = safe_r(md[sel], st[sel])
        n_season = int(sel.sum())
    else:
        r_season, n_season = float("nan"), 0

    # coverage-threshold robustness
    robust = []
    for thr in (0.0, 0.3, 0.5, 0.7, 0.9):
        s = cov >= thr
        if s.sum() >= 3:
            robust.append(
                dict(
                    thr=thr,
                    n=int(s.sum()),
                    bias_dex=float(dif[s].mean()),
                    r_all=safe_r(md[s], st[s]),
                    r_anomaly=safe_r(deseasonalize(md[s], moy[s]), deseasonalize(st[s], moy[s])),
                )
            )

    cl_m = np.array([md[moy == i].mean() if (moy == i).any() else np.nan for i in range(1, 13)])
    cl_s = np.array([st[moy == i].mean() if (moy == i).any() else np.nan for i in range(1, 13)])

    out = dict(
        aoi=args.aoi,
        aoi_name=aoi.name,
        bounds=dict(
            lat_min=aoi.lat_min, lat_max=aoi.lat_max, lon_min=aoi.lon_min, lon_max=aoi.lon_max
        ),
        grid=[H, W],
        calendar=dict(cal_ratio=cal_ratio, delta_t_s=1200, note="corrected calendar; delta_t=1200s"),
        satellite="NOAA CoastWatch ERDDAP erdMH1chlamday (MODIS-Aqua), processing_version 2018.1QL",
        n_months=n_used,
        span=[rows[0]["month"], rows[-1]["month"]],
        bias_dex=bias,
        bias_ci95_dex=[lo, hi],
        bias_factor=float(10**bias),
        rmse_dex=rmse,
        pearson_r_all=r_all,
        pearson_r_anomaly=r_anom,
        pearson_r_growing_season=r_season,
        n_growing_season=n_season,
        growing_season_window=gs,
        noise_floor_dex=NOISE_FLOOR_DEX,
        bias_exceeds_noise_floor=bool(abs(bias) > NOISE_FLOOR_DEX),
        mean_satellite_coverage=float(cov.mean()),
        min_satellite_coverage=float(cov.min()),
        v05_cells_below_valid_min=clipped,
        coverage_robustness=robust,
        clim_model_log10=cl_m.tolist(),
        clim_sat_log10=cl_s.tolist(),
        monthly=rows,
    )

    dest = args.out or os.path.join(d, f"v05_vs_modis_{args.aoi}.json")
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=1)

    names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    print(f"=== v05 vs MODIS-Aqua chlorophyll — {aoi.name} ===")
    print(f"months compared: {n_used}   span {rows[0]['month']} -> {rows[-1]['month']}")
    print(f"satellite coverage: mean {100*cov.mean():.1f}%  min {100*cov.min():.1f}%")
    print(f"v05 cells below MODIS valid_min: {clipped}")
    print()
    print(
        "BIAS   %+.4f dex  = %.3fx  (v05 %s)   95%% CI [%+.4f, %+.4f]"
        % (bias, 10**bias, "LOWER" if bias < 0 else "HIGHER", lo, hi)
    )
    print("RMSE    %.4f dex" % rmse)
    print(
        "noise floor %.3f dex -> bias %s the floor"
        % (NOISE_FLOOR_DEX, "EXCEEDS" if abs(bias) > NOISE_FLOOR_DEX else "is INSIDE")
    )
    print()
    print("r(all months)      %+.4f   <- seasonal cycle; NOT a skill number" % r_all)
    print("r(ANOMALY)         %+.4f   <- interannual skill; lead with this" % r_anom)
    if gs is not None:
        print("r(growing %02d-%02d)    %+.4f  (n=%d)" % (gs[0], gs[1], r_season, n_season))
    else:
        print("r(growing season)  n/a — no bloom season in this regime")
    print()
    print("=== seasonal climatology (log10 mg/m3) ===")
    print("%5s %9s %9s %9s" % ("mon", "v05", "MODIS", "diff"))
    for i in range(12):
        if np.isfinite(cl_m[i]):
            print("%5s %9.3f %9.3f %+9.3f" % (names[i], cl_m[i], cl_s[i], cl_m[i] - cl_s[i]))
    print()
    print(
        "peak month  v05: %s   MODIS: %s"
        % (names[int(np.nanargmax(cl_m))], names[int(np.nanargmax(cl_s))])
    )
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
