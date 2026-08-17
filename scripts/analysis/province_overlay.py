"""Longhurst biogeochemical provinces vs the rectangular DarwinDiff AOI boxes.

Answers the two questions raised on 2026-08-16 about defining AOIs as biogeochemical
provinces (Longhurst) instead of lat/lon rectangles:

  (a) Does the natlsubpolar box straddle province boundaries, and can that explain
      the per-cell dispersion (``per_aoi_log_sd`` = 0.936, job 258713) that moves the
      North Atlantic ``scav_rat`` leg 37 -> 7 between arithmetic and geometric pooling?
  (b) Which Longhurst province contains GEOTRACES GP16 (~12 S, eastern Pacific)?

Everything here is a **lookup plus geometry**, no cluster compute and no model fit.

Polygons: Longhurst v4 via the Marine Regions WFS layer ``MarineRegions:longhurst``.
    Flanders Marine Institute (2009), *Longhurst Provinces*,
    https://www.marineregions.org/, after Longhurst (1998),
    *Ecological Geography of the Sea*.

    ⚠️ The request MUST be WFS **1.0.0**. Version 1.1.0 flips the EPSG:4326 axis
    order to lat,lon and silently returns Indian Ocean provinces for a North
    Atlantic bbox — it does not error, it returns confident nonsense.

Iron coverage: GEOTRACES IDP2025 ``Fe_D_CONC`` at QC 1/2, via
    :mod:`darwindiff.geotraces_loader`.

Usage::

    python scripts/analysis/province_overlay.py                  # all AOIs + GP16
    python scripts/analysis/province_overlay.py --aoi eqpac      # one AOI
    python scripts/analysis/province_overlay.py --no-iron        # skip GEOTRACES
    python scripts/analysis/province_overlay.py --json OUT.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from darwindiff.ecco_darwin_loader import AOI, AOI_BY_KEY  # noqa: E402

WFS = (
    "https://geo.vliz.be/geoserver/MarineRegions/wfs"
    "?service=WFS&version=1.0.0&request=GetFeature"
    "&typeName=MarineRegions:longhurst&outputFormat=application/json"
)
CACHE = Path(
    os.environ.get("PROVINCE_CACHE_DIR", Path(__file__).resolve().parent / ".province_cache")
)

# The GP16 East Pacific Zonal Transect (R/V Thomas G. Thompson, Oct–Dec 2013): Peru
# margin westward to Tahiti along a line falling between 10 and 15 S, crossing the
# East Pacific Rise hydrothermal plume near 12 S.
GP16_CORRIDOR = (-155.0, -16.0, -70.0, -9.0)  # lon_min, lat_min, lon_max, lat_max
GP16_LINE_LAT = -12.0


def fetch(bbox: tuple[float, float, float, float], tag: str) -> list[dict]:
    """Longhurst features whose geometry intersects ``bbox`` (lon_min, lat_min, lon_max, lat_max).

    The WFS bbox filter returns WHOLE features, never clipped geometry, so the cached
    polygons are the full global provinces and are safe to reuse for point-in-polygon.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"longhurst_{tag}.geojson"
    if not path.is_file():
        w, s, e, n = bbox
        with urllib.request.urlopen(f"{WFS}&bbox={w},{s},{e},{n}", timeout=300) as fh:
            path.write_bytes(fh.read())
    return json.loads(path.read_text(encoding="utf-8"))["features"]


def _gdf(features: list[dict]):
    import geopandas as gpd

    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def compose(features: list[dict], aoi: AOI) -> dict:
    """Area-weighted province composition of one rectangular AOI.

    Areas are computed in a Lambert azimuthal equal-area projection centred on the
    box. At 50–65 N a degree of longitude is roughly half a degree of latitude, so
    doing this in raw degrees would overweight the northern (polar-province) rows.
    """
    import geopandas as gpd
    from shapely.geometry import box

    rect = box(aoi.lon_min, aoi.lat_min, aoi.lon_max, aoi.lat_max)
    laea = (
        f"+proj=laea +lat_0={(aoi.lat_min + aoi.lat_max) / 2} "
        f"+lon_0={(aoi.lon_min + aoi.lon_max) / 2} +datum=WGS84 +units=m +no_defs"
    )
    rect_area = gpd.GeoSeries([rect], crs="EPSG:4326").to_crs(laea).iloc[0].area

    rows = []
    for _, feat in _gdf(features).iterrows():
        inter = feat.geometry.intersection(rect)
        if inter.is_empty:
            continue
        area = gpd.GeoSeries([inter], crs="EPSG:4326").to_crs(laea).iloc[0].area
        if area <= 0:
            continue
        rows.append(
            {"code": feat["provcode"], "descr": feat["provdescr"], "share": area / rect_area}
        )
    rows.sort(key=lambda r: -r["share"])

    shares = np.array([r["share"] for r in rows])
    shares = shares / shares.sum()
    # Inverse Simpson index: the effective number of provinces the box mixes. 1.0 means
    # the box IS a province; 3.1 means it is a three-way mixture.
    return {"provinces": rows, "effective_n": float(1.0 / (shares**2).sum())}


def province_at(features: list[dict], lon: float, lat: float) -> str | None:
    from shapely.geometry import Point

    pt = Point(lon, lat)
    for _, feat in _gdf(features).iterrows():
        if feat.geometry.contains(pt):
            return feat["provcode"]
    return None


def iron_counts(features: list[dict], geoms: dict) -> dict:
    """GEOTRACES IDP2025 dissolved-Fe stations and samples inside each geometry."""
    from shapely.geometry import Point
    from shapely.prepared import prep

    from darwindiff.geotraces_loader import QC_GOOD, open_geotraces_bottle

    idp = os.environ.get("GEOTRACES_IDP", r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")
    ds = open_geotraces_bottle(idp)
    good = np.isfinite(ds["Fe_D_CONC"].values) & np.isin(
        ds["Fe_D_CONC_qc"].values, list(QC_GOOD)
    )
    n_per_station = good.sum(axis=1)
    lat, lon = ds["latitude"].values, ds["longitude"].values
    live = np.where(n_per_station > 0)[0]

    out = {}
    for name, geom in geoms.items():
        p = prep(geom)
        st = sm = 0
        for i in live:
            if p.contains(Point(float(lon[i]), float(lat[i]))):
                st += 1
                sm += int(n_per_station[i])
        out[name] = {"stations": st, "samples": sm}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", action="append", help="AOI key; repeatable. Default: the flagship three.")
    ap.add_argument("--no-iron", action="store_true", help="skip the GEOTRACES coverage count")
    ap.add_argument("--json", help="write the full result to this path")
    args = ap.parse_args()

    keys = args.aoi or ["natlsubpolar", "eqpac", "southernoceanpac"]
    result: dict = {"aois": {}, "gp16": {}}

    all_geoms = {}
    for key in keys:
        aoi = AOI_BY_KEY[key]
        feats = fetch((aoi.lon_min, aoi.lat_min, aoi.lon_max, aoi.lat_max), key)
        comp = compose(feats, aoi)
        result["aois"][key] = comp

        print(f"\n=== {key}  lon[{aoi.lon_min},{aoi.lon_max}] lat[{aoi.lat_min},{aoi.lat_max}] ===")
        for r in comp["provinces"]:
            print(f"  {r['code']:6s} {r['share'] * 100:6.2f}%   {r['descr']}")
        print(f"  effective number of provinces = {comp['effective_n']:.2f}")

        from shapely.geometry import box as _box

        all_geoms[f"{key} (box)"] = _box(aoi.lon_min, aoi.lat_min, aoi.lon_max, aoi.lat_max)
        for _, feat in _gdf(feats).iterrows():
            if any(r["code"] == feat["provcode"] for r in comp["provinces"]):
                all_geoms[f"{feat['provcode']} (province)"] = feat.geometry

    # (b) GP16.
    gfeats = fetch(GP16_CORRIDOR, "gp16")
    print(f"\n=== GP16 corridor: province along {abs(GP16_LINE_LAT)} S ===")
    prev, changes = "<start>", []
    for lon in np.arange(-155.0, -74.0, 0.5):
        code = province_at(gfeats, float(lon), GP16_LINE_LAT) or "<land/none>"
        if code != prev:
            changes.append({"lon": float(lon), "from": prev, "to": code})
            print(f"  change at lon {lon:7.1f}: {prev} -> {code}")
            prev = code
    result["gp16"]["transitions_along_12S"] = changes

    print("\n--- PEQD southern limit vs longitude ---")
    limits = {}
    for lon in np.arange(-140.0, -76.0, 4.0):
        south = None
        for lat in np.arange(2.0, -20.0, -0.25):
            if province_at(gfeats, float(lon), float(lat)) == "PEQD":
                south = float(lat)
        limits[float(lon)] = south
        print(f"  lon {lon:7.1f}  PEQD extends south to {south}")
    result["gp16"]["peqd_southern_limit"] = limits

    if not args.no_iron:
        from shapely.geometry import box as _box

        all_geoms["GP16 corridor"] = _box(*GP16_CORRIDOR)
        for _, feat in _gdf(gfeats).iterrows():
            all_geoms.setdefault(f"{feat['provcode']} (province)", feat.geometry)
        print("\n=== GEOTRACES IDP2025 dissolved Fe (QC 1/2): box vs province ===")
        counts = iron_counts(gfeats, all_geoms)
        result["iron"] = counts
        for name, c in sorted(counts.items(), key=lambda kv: -kv[1]["stations"]):
            print(f"  {name:34s} {c['stations']:5d} stations {c['samples']:6d} samples")

    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
