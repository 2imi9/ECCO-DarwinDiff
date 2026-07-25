"""Remin-fidelity gate: v05 vs GEOTRACES dissolved-iron VERTICAL PROFILE shape.

Question this answers
---------------------
For a planned 1-D iron-column parameter fit we want to *prescribe*
remineralization from ECCO-Darwin v05 and recover the scavenging rate from the
resulting DFe column. That only works if v05 reproduces the SHAPE of the
observed DFe vertical profile. If v05's profile shape is biased, the column
route inherits that bias. This script builds the gate:

  1. Load v05 native LLC270 FeT (TRAC06, 50 depth levels) for a small handful of
     mid-record monthly iterations and average them into a pseudo-climatology
     water-column field (mmol Fe / m^3).
  2. Select GEOTRACES IDP2025 stations with a genuine full-depth Fe_D profile
     (>= 5 QC-good samples, surface (<100 m) to deep (>500 m)).
  3. For each station find the nearest v05 OCEAN column (nearest XC/YC cell) and
     extract the v05 FeT profile at that column's 50 depth levels.
  4. Interpolate obs and model onto a common depth axis and compare, per station:
       - ABSOLUTE offset vs depth (ratio obs/model) -- constant factor vs
         depth-dependent.
       - SHAPE agreement -- Pearson correlation of the co-located profiles,
         subsurface-maximum depth, surface-to-deep gradient.
  5. Aggregate globally and split by three study regions.

Units. v05 FeT is mmol Fe / m^3. GEOTRACES Fe_D_CONC is nmol/kg; converted with
rho_sw = 1025 kg/m^3 (-> * 1.025e-3). Darwin FeT is total DISSOLVED iron;
GEOTRACES Fe_D may include colloidal iron, so a modest constant obs>model offset
is expected and is *rescalable* -- the gate is about SHAPE, not absolute level.

Run:
  PYTHONPATH=src DARWIN_DATA_ROOT=D:\\ecco_darwin_v5 \\
      uv run python scripts/analysis/v05_geotraces_iron_profile_fidelity.py

Writes a JSON result to the scratchpad (path printed at the end).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from darwindiff.geotraces_loader import (
    _NMOL_PER_KG_TO_MMOL_PER_M3,
    open_geotraces_bottle,
)
from darwindiff.llc270_loader import list_available_iterations, open_llc270_tracer

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
MONTHLY_ROOT = DATA_ROOT / "output" / "monthly"
GRID_DIR = DATA_ROOT / "grid"
GEOTRACES_PATH = Path(r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")

VARIABLE = "FeT"
N_ITERS = 12            # handful of monthly snapshots -> pseudo-climatology
QC_GOOD = (49.0, 50.0)  # SeaDataNet good + probably-good (ASCII codes, float)
MIN_GOOD_SAMPLES = 5
SURFACE_MAX_M = 100.0   # station must sample shallower than this
DEEP_MIN_M = 500.0      # station must sample deeper than this
MAX_MATCH_KM = 100.0    # reject a station if nearest v05 ocean cell is farther

COMMON_DEPTHS = np.array([0.0, 50.0, 100.0, 200.0, 400.0, 600.0, 1000.0, 1500.0])

REGIONS = {
    # eqpac ~ lat -5..15 lon -160..-110
    "eqpac": dict(lat=(-5.0, 15.0), lon=(-160.0, -110.0)),
    # N Atlantic subpolar
    "natl_subpolar": dict(lat=(45.0, 65.0), lon=(-60.0, -10.0)),
    # Southern Ocean, Pacific sector
    "so_pacific": dict(lat=(-75.0, -50.0), lon=(-180.0, -90.0)),
}

SCRATCH = Path(
    r"C:\Users\Frank\AppData\Local\Temp\claude"
    r"\C--Users-Frank-OneDrive-Desktop-Github-ecco-darwindiff"
    r"\f720edb2-1006-4242-a5c9-774bc13137b2\scratchpad"
)
OUT_JSON = SCRATCH / "v05_geotraces_iron_profile_fidelity.json"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def latlon_to_xyz(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    """Unit-sphere Cartesian coords for a nearest-neighbour (chord) search."""
    la = np.radians(lat_deg)
    lo = np.radians(lon_deg)
    return np.stack(
        [np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1
    )


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def interp_to_axis(depths, values, targets, allow_shallow_clamp=True):
    """Interp (depth, value) onto targets. No deep extrapolation (targets past
    the deepest sample -> NaN). Shallow clamp for the near-surface target."""
    d = np.asarray(depths, float)
    v = np.asarray(values, float)
    ok = np.isfinite(d) & np.isfinite(v)
    d, v = d[ok], v[ok]
    if d.size < 2:
        return np.full(targets.shape, np.nan)
    order = np.argsort(d)
    d, v = d[order], v[order]
    out = np.interp(targets, d, v)  # np.interp clamps outside range
    dmin, dmax = d[0], d[-1]
    out[targets > dmax] = np.nan
    if not allow_shallow_clamp:
        out[targets < dmin] = np.nan
    return out


def region_of(lat, lon):
    for name, box in REGIONS.items():
        if box["lat"][0] <= lat <= box["lat"][1] and box["lon"][0] <= lon <= box["lon"][1]:
            return name
    return "other"


def _median(x):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    return float(np.median(x)) if x.size else None


# ----------------------------------------------------------------------------
# 1. v05 FeT pseudo-climatology water-column field
# ----------------------------------------------------------------------------
def load_v05_field():
    all_iters = list_available_iterations(MONTHLY_ROOT, VARIABLE)
    idx = np.unique(np.linspace(0, len(all_iters) - 1, N_ITERS).round().astype(int))
    chosen = [all_iters[i] for i in idx]
    print(f"[v05] {len(all_iters)} iters available; averaging {len(chosen)}: {chosen}")

    # Grid + Z from the first chosen iteration.
    ds0 = open_llc270_tracer(MONTHLY_ROOT, GRID_DIR, VARIABLE, iters=chosen[0])
    Z = np.abs(np.asarray(ds0.Z.values))           # (50,) positive depths (m)
    XC = np.asarray(ds0.XC.values).ravel()         # (Ncells,)
    YC = np.asarray(ds0.YC.values).ravel()
    ncells = XC.size

    fld0 = np.asarray(ds0[VARIABLE].isel(time=0).values).reshape(len(Z), ncells)
    fld0 = np.where(fld0 > 0, fld0, np.nan)
    ssum = np.where(np.isfinite(fld0), fld0, 0.0)
    scnt = np.isfinite(fld0).astype(np.int32)
    ds0.close()

    for it in chosen[1:]:
        ds = open_llc270_tracer(MONTHLY_ROOT, GRID_DIR, VARIABLE, iters=it)
        fld = np.asarray(ds[VARIABLE].isel(time=0).values).reshape(len(Z), ncells)
        fld = np.where(fld > 0, fld, np.nan)
        ssum += np.where(np.isfinite(fld), fld, 0.0)
        scnt += np.isfinite(fld).astype(np.int32)
        ds.close()

    with np.errstate(invalid="ignore"):
        field = np.where(scnt > 0, ssum / scnt, np.nan)  # (50, Ncells) mmol/m^3
    surf_ocean = np.isfinite(field[0])                   # ocean = finite surface
    print(f"[v05] field {field.shape}; ocean surface cells: {int(surf_ocean.sum())}")
    return Z, XC, YC, field, surf_ocean


# ----------------------------------------------------------------------------
# 2. GEOTRACES qualifying full-depth stations
# ----------------------------------------------------------------------------
def load_geotraces_stations():
    ds = open_geotraces_bottle(GEOTRACES_PATH)
    fe = ds["Fe_D_CONC"].values            # (Nsta, Nsamp) nmol/kg
    qc = ds["Fe_D_CONC_qc"].values
    dep = ds["DEPTH"].values
    lat = ds["latitude"].values
    lon = ds["longitude"].values

    good = np.isin(qc, np.array(QC_GOOD, dtype=qc.dtype)) & np.isfinite(fe) & np.isfinite(dep)
    n_good = good.sum(axis=1)
    dmax = np.nanmax(np.where(good, dep, -np.inf), axis=1)
    dmin = np.nanmin(np.where(good, dep, np.inf), axis=1)
    qual = (n_good >= MIN_GOOD_SAMPLES) & (dmax > DEEP_MIN_M) & (dmin < SURFACE_MAX_M)

    stations = []
    for si in np.where(qual)[0]:
        m = good[si]
        d = dep[si, m].astype(float)
        v = fe[si, m].astype(float) * _NMOL_PER_KG_TO_MMOL_PER_M3  # -> mmol/m^3
        o = np.argsort(d)
        stations.append(
            dict(sidx=int(si), lat=float(lat[si]), lon=float(lon[si]),
                 depth=d[o], obs=v[o])
        )
    print(f"[geotraces] {fe.shape[0]} stations; {len(stations)} qualify "
          f"(>= {MIN_GOOD_SAMPLES} good, surf<{SURFACE_MAX_M} m, deep>{DEEP_MIN_M} m)")
    ds.close()
    return stations


# ----------------------------------------------------------------------------
# 3-4. Match, extract, compare
# ----------------------------------------------------------------------------
def main():
    Z, XC, YC, field, surf_ocean = load_v05_field()
    stations = load_geotraces_stations()

    # KD-tree over ocean columns only.
    from scipy.spatial import cKDTree

    ocean_idx = np.where(surf_ocean)[0]
    tree = cKDTree(latlon_to_xyz(YC[ocean_idx], XC[ocean_idx]))

    per_station = []
    for st in stations:
        q = latlon_to_xyz(np.array([st["lat"]]), np.array([st["lon"]]))
        _, pos = tree.query(q, k=1)
        full = int(ocean_idx[int(pos[0])])
        mlat, mlon = float(YC[full]), float(XC[full])
        dkm = float(haversine_km(st["lat"], st["lon"], mlat, mlon))
        if dkm > MAX_MATCH_KM:
            continue

        model_col = field[:, full]                       # (50,) mmol/m^3
        mok = np.isfinite(model_col)
        if mok.sum() < 3:
            continue
        mdepth, mval = Z[mok], model_col[mok]

        obs_i = interp_to_axis(st["depth"], st["obs"], COMMON_DEPTHS)
        mod_i = interp_to_axis(mdepth, mval, COMMON_DEPTHS)
        both = np.isfinite(obs_i) & np.isfinite(mod_i) & (obs_i > 0) & (mod_i > 0)
        if both.sum() < 4:
            continue

        xo, xm = obs_i[both], mod_i[both]
        dsub = COMMON_DEPTHS[both]

        # Shape correlation (Pearson) of the co-located profiles.
        r = float(np.corrcoef(xo, xm)[0, 1]) if xo.size >= 2 else np.nan
        # Log-space correlation (iron spans orders of magnitude).
        r_log = float(np.corrcoef(np.log(xo), np.log(xm))[0, 1]) if xo.size >= 2 else np.nan

        # Offset ratio obs/model per depth.
        ratio = xo / xm

        # Subsurface-max depth (depth of max concentration), obs & model full col.
        obs_maxdepth = float(st["depth"][int(np.argmax(st["obs"]))])
        mod_maxdepth = float(mdepth[int(np.argmax(mval))])

        # Surface-to-deep gradient: deep/surface ratio on the common axis.
        obs_grad = float(xo[-1] / xo[0])
        mod_grad = float(xm[-1] / xm[0])

        per_station.append(dict(
            sidx=st["sidx"], lat=st["lat"], lon=st["lon"],
            region=region_of(st["lat"], st["lon"]),
            match_km=dkm, n_common=int(both.sum()),
            r=r, r_log=r_log,
            depths=[float(x) for x in dsub],
            ratio=[float(x) for x in ratio],
            obs_maxdepth=obs_maxdepth, mod_maxdepth=mod_maxdepth,
            obs_grad=obs_grad, mod_grad=mod_grad,
        ))

    print(f"[match] {len(per_station)} stations compared "
          f"(median match dist {_median([p['match_km'] for p in per_station]):.1f} km)")

    # ------------------------------------------------------------------
    # Aggregate
    # ------------------------------------------------------------------
    def band(dep):
        return "surface" if dep <= 100 else ("mid" if dep <= 500 else "deep")

    def aggregate(subset):
        if not subset:
            return None
        rs = [p["r"] for p in subset]
        rlogs = [p["r_log"] for p in subset]
        # Offset ratio pooled by depth band.
        bands = {"surface": [], "mid": [], "deep": []}
        for p in subset:
            for d, rr in zip(p["depths"], p["ratio"]):
                bands[band(d)].append(rr)
        band_med = {k: _median(v) for k, v in bands.items()}
        # Per-depth median ratio.
        depth_ratio = {}
        for dtarget in COMMON_DEPTHS:
            vals = [rr for p in subset for d, rr in zip(p["depths"], p["ratio"])
                    if abs(d - dtarget) < 1e-6]
            depth_ratio[str(dtarget)] = _median(vals)
        # Depth-dependence of the offset: deep-band median ratio / surface-band.
        dd = None
        if band_med["surface"] and band_med["deep"]:
            dd = band_med["deep"] / band_med["surface"]
        return dict(
            n=len(subset),
            median_r=_median(rs),
            median_r_log=_median(rlogs),
            median_match_km=_median([p["match_km"] for p in subset]),
            offset_ratio_by_band=band_med,
            offset_ratio_by_depth=depth_ratio,
            offset_depth_dependence_deep_over_surface=dd,
            median_obs_subsurface_max_m=_median([p["obs_maxdepth"] for p in subset]),
            median_model_subsurface_max_m=_median([p["mod_maxdepth"] for p in subset]),
            median_obs_deep_over_surface_gradient=_median([p["obs_grad"] for p in subset]),
            median_model_deep_over_surface_gradient=_median([p["mod_grad"] for p in subset]),
        )

    result = {"global": aggregate(per_station)}
    for rname in REGIONS:
        result[rname] = aggregate([p for p in per_station if p["region"] == rname])

    # ------------------------------------------------------------------
    # Verdict. Two independent tests must both pass for GOOD:
    #   (1) SHAPE: median profile correlation is high (nutrient-like increase
    #       with depth is reproduced).
    #   (2) OFFSET is a rescalable ~constant factor, tested two ways:
    #        - depth-dependence of obs/model ratio (deep-band / surface-band)
    #          should sit near 1;
    #        - model's surface->deep gradient should match the observed one
    #          (gradient_ratio = model_gradient / obs_gradient near 1).
    #   A depth-dependent offset (ratio drifts with depth, or the model's
    #   vertical gradient is materially weaker/stronger than observed) is a
    #   real profile-SHAPE bias that a single global rescale cannot remove ->
    #   the column route would inherit it.
    # ------------------------------------------------------------------
    g = result["global"]
    mr = g["median_r"]
    dd = g["offset_depth_dependence_deep_over_surface"]
    grad_ratio = None
    if g["median_model_deep_over_surface_gradient"] and g["median_obs_deep_over_surface_gradient"]:
        grad_ratio = (g["median_model_deep_over_surface_gradient"]
                      / g["median_obs_deep_over_surface_gradient"])
    g["gradient_ratio_model_over_obs"] = grad_ratio

    constant_offset = dd is not None and 0.8 <= dd <= 1.25
    gradient_ok = grad_ratio is not None and 0.7 <= grad_ratio <= 1.4
    if mr is not None and mr >= 0.6 and constant_offset and gradient_ok:
        verdict = "GOOD"
    elif mr is not None and mr < 0.35:
        verdict = "POOR"
    else:
        verdict = "MIXED"
    reason = (
        f"median shape-corr r={mr:.2f} (log r={g['median_r_log']:.2f}) is decent, "
        f"but the offset is DEPTH-DEPENDENT: obs/model ratio drifts "
        f"deep/surface={dd:.2f} and the model's surface->deep gradient is only "
        f"{grad_ratio:.2f}x the observed (obs {g['median_obs_deep_over_surface_gradient']:.2f}x "
        f"vs model {g['median_model_deep_over_surface_gradient']:.2f}x). "
        f"Profile shape broadly tracks but is not a constant rescalable offset. "
        f"N={g['n']} stations."
    ) if verdict == "MIXED" else (
        f"median shape-corr r={mr:.2f}; offset deep/surface={dd:.2f}, "
        f"gradient_ratio={grad_ratio}; N={g['n']} stations."
    )

    out = dict(
        meta=dict(
            variable=VARIABLE,
            n_iters_averaged=int(N_ITERS),
            common_depths_m=[float(x) for x in COMMON_DEPTHS],
            qc_flags=list(QC_GOOD),
            selection=dict(min_good_samples=MIN_GOOD_SAMPLES,
                           surface_max_m=SURFACE_MAX_M, deep_min_m=DEEP_MIN_M),
            max_match_km=MAX_MATCH_KM,
            obs_unit="mmol/m^3 (GEOTRACES nmol/kg * 1.025e-3)",
            model_unit="mmol/m^3 (v05 FeT / TRAC06)",
            note=("Darwin FeT = total dissolved Fe; GEOTRACES Fe_D may include "
                  "colloidal Fe, so a constant obs>model offset is expected."),
        ),
        verdict=verdict,
        verdict_reason=reason,
        aggregate=result,
        n_stations_compared=len(per_station),
    )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))
    print("\n" + "=" * 70)
    print(f"VERDICT: {verdict}")
    print(reason)
    print("=" * 70)
    for k, v in result.items():
        if v is None:
            print(f"{k:16s}: (no stations)")
            continue
        print(f"{k:16s}: N={v['n']:4d}  median_r={v['median_r']}  "
              f"r_log={v['median_r_log']}  offset(surf/mid/deep)="
              f"{v['offset_ratio_by_band']}  deep/surf_dd="
              f"{v['offset_depth_dependence_deep_over_surface']}")
    print(f"\nJSON -> {OUT_JSON}")
    return out


if __name__ == "__main__":
    main()
