"""Build data/air_pm25.geojson and data/air_no2.geojson: NYCCAS annual-average PM2.5 and NO2,
classified into 5 bands and clipped to the study area (common.DISTRICTS + 200 m).

Source: NYC DOHMH New York City Community Air Survey (NYCCAS), NYC Open Data file asset
"NYCCAS Air Pollution Rasters" (q68s-8qxv). The zip holds ESRI grids at 300 m (984 ft)
resolution in NAD83 / New York Long Island State Plane (US feet), one per pollutant and
NYCCAS year. Year N covers December (2007+N) through December (2008+N), so year 16 is the
2024 annual average (Dec 2023 - Dec 2024). The script uses the latest year in the zip.

Requires rasterio and numpy in addition to the common dependencies.
"""
import json
import os
import re
import zipfile

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import shapes
from rasterio.mask import mask
import shapely
from shapely.geometry import MultiPolygon, mapping, shape
from shapely.ops import unary_union

from common import AREA_NAME, CACHE_DIR, feature, fetch, simplify, study_area, write_fc

VIEW = "https://data.cityofnewyork.us/api/views/q68s-8qxv"
SOURCE = ("NYC DOHMH New York City Community Air Survey (NYCCAS), "
          "NYC Open Data 'NYCCAS Air Pollution Rasters' (q68s-8qxv)")

# Class breaks chosen from the range of cells touching the study area (+ 200 m) in the
# year-16 (2024) surfaces: PM2.5 5.78-8.48 ug/m3, NO2 12.90-20.93 ppb; equal-width
# round-number bands (0.6 ug/m3, 2 ppb). Bands are [lo, hi); the top band includes its upper
# edge. If a newer year falls outside these, the script stops so the breaks can be revisited
# rather than silently dropping cells.
POLLUTANTS = {
    "pm25": {
        "grid": "pm", "units": "µg/m³", "out": "air_pm25.geojson",
        "name": "fine particulate matter (PM2.5)",
        "breaks": [5.6, 6.2, 6.8, 7.4, 8.0, 8.6],
    },
    "no2": {
        "grid": "no2", "units": "ppb", "out": "air_no2.geojson",
        "name": "nitrogen dioxide (NO2)",
        "breaks": [12.0, 14.0, 16.0, 18.0, 20.0, 22.0],
    },
}
SIMPLIFY_M = 5.0


def download():
    meta = json.loads(fetch(VIEW + ".json"))
    blob, fname = meta["blobId"], meta["blobFilename"]
    path = os.path.join(CACHE_DIR, "nyccas_" + fname)
    if not os.path.exists(path):
        raw = fetch(f"{VIEW}/files/{blob}", params={"download": "true", "filename": fname},
                    binary=True, cache=False)
        with open(path, "wb") as f:
            f.write(raw)
    return path, fname


def latest_grid(names, grid):
    """Return (year_number, path-in-zip) of the newest annual-average grid for `grid`."""
    found = {}
    for n in names:
        m = re.search(rf"(?:^|/)(aa(\d+)_{grid}300m)/hdr\.adf$", n)
        if m:
            found[int(m.group(2))] = n[: -len("/hdr.adf")]
    year = max(found)
    return year, found[year]


def reproject(geom, fn):
    return shapely.transform(geom, lambda c: np.column_stack(fn(c[:, 0], c[:, 1])))


def as_multi(geom):
    if geom.geom_type == "Polygon":
        return MultiPolygon([geom])
    if geom.geom_type == "GeometryCollection":
        return MultiPolygon([g for g in geom.geoms if g.geom_type == "Polygon"]
                            + [p for g in geom.geoms if g.geom_type == "MultiPolygon" for p in g.geoms])
    return geom


def fmt(v):
    return f"{v:.1f}"


def build(zpath, names, key, cfg, area_ll):
    yr, inner = latest_grid(names, cfg["grid"])
    cal = 2008 + yr
    period = f"{cal} annual average"
    with rasterio.open(f"/vsizip/{zpath}/{inner}") as src:
        to_src = Transformer.from_crs("EPSG:4326", src.crs, always_xy=True).transform
        to_ll = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform
        area = reproject(area_ll, to_src)
        # every cell that touches the study area, so the clipped polygons have no gaps
        data, tr = mask(src, [mapping(area)], crop=True, all_touched=True, filled=False)
        crs_txt = src.crs.to_wkt().split('"')[1]  # PROJCS name
        res = src.res
    arr = data[0]
    vals = arr.compressed()
    vmin, vmax = float(vals.min()), float(vals.max())
    br = cfg["breaks"]
    if vmin < br[0] or vmax > br[-1]:
        raise RuntimeError(f"{key} year {yr}: values {vmin:.2f}-{vmax:.2f} fall outside breaks {br}")
    cls = np.digitize(arr.filled(np.nan), br[1:-1], right=False) + 1  # 1..5
    cls = np.where(arr.mask, 0, cls).astype("int32")
    print(f"{key}: NYCCAS year {yr} ({period}), {inner}, {vals.size} cells, "
          f"min {vmin:.3f} max {vmax:.3f} {cfg['units']}, counts "
          f"{[int((cls == b).sum()) for b in range(1, 6)]}")

    feats = []
    for b in range(1, 6):
        polys = [shape(g) for g, v in shapes(cls, mask=(cls == b), transform=tr) if v == b]
        if not polys:
            continue
        g = unary_union(polys).intersection(area)
        if g.is_empty:
            continue
        g = as_multi(simplify(reproject(g, to_ll), SIMPLIFY_M))
        lo, hi = br[b - 1], br[b]
        feats.append(feature(g, {
            "pollutant": key,
            "band": b,
            "band_min": lo,
            "band_max": hi,
            "label": f"{fmt(lo)} – {fmt(hi)} {cfg['units']}",
            "units": cfg["units"],
            "period": period,
            "source": SOURCE,
        }))
    write_fc(cfg["out"], feats, meta={
        "description": f"NYCCAS modeled {period} {cfg['name']}, 5 classes, clipped to "
                       f"{AREA_NAME} + 200 m",
        "nyccas_year": yr,
        "nyccas_grid": inner.rsplit("/", 1)[-1],
        "raster_crs": crs_txt,
        "raster_resolution_ft": list(res),
        "breaks": br,
        "study_area_min": round(vmin, 3),
        "study_area_max": round(vmax, 3),
    })


def main():
    zpath, _ = download()
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
    area_ll = study_area()
    for key, cfg in POLLUTANTS.items():
        build(zpath, names, key, cfg, area_ll)


if __name__ == "__main__":
    main()
