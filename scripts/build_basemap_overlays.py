"""Build the basemap overlays in data/basemap/ for the study area (see common.DISTRICTS),
drawn client side over the base tiles, from current public data:

- truck_routes_through.geojson / truck_routes_local.geojson: NYC DOT "New York City Truck
  Routes" (NYC Open Data jjja-shxy), split on `routetype`, clipped to the study area + 300 m
  and merged per street. Property: `street`.
- zip_boundaries.geojson: lines between the 2020 Census ZIP Code Tabulation Areas (TIGERweb)
  that lie substantially inside the districts, clipped to the districts.
- zip_labels.geojson: one label point per such ZCTA, inside the districts. Property: `zipcode`.
- area_mask.geojson: the districts' bounding box, expanded by 0.1 degrees, minus the districts.

Usage: python3 scripts/build_basemap_overlays.py
Requires: shapely, pyproj
"""
import os

from shapely.geometry import box
from shapely.ops import linemerge

from common import (DATA_DIR, arcgis_query, districts, feature, parts, shape, simplify, socrata,
                    study_area, to_metric, to_wgs84, unary_union, write_fc)

OUT = "basemap"

TRUCK_ROUTES = "jjja-shxy"  # NYC DOT, "New York City Truck Routes"
TRUCK_BUFFER_M = 300.0
ZCTA_LAYER = ("https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
              "PUMA_TAD_TAZ_UGA_ZCTA/MapServer/1")  # 2020 Census ZIP Code Tabulation Areas
# a ZCTA is mapped when at least this share of its land area lies inside the districts
# (the shares fall into two groups: about 0.2 to 1, and under 0.001)
ZCTA_MIN_SHARE = 0.10
EDGE_M = 25.0  # drop ZIP boundary lines within this distance of the districts' outline
MASK_PAD_DEG = 1.0  # wide enough to cover the view at the map's minimum zoom
ACRONYMS = {"Bqe": "BQE", "Lie": "LIE", "Eb": "EB", "Wb": "WB", "Mcguinness": "McGuinness"}


def merge_lines(g):
    """Merge the LineString parts of a metric-space geometry into as few lines as possible."""
    if g.geom_type in ("MultiLineString", "GeometryCollection"):
        g = linemerge([p for p in parts(g) if p.geom_type == "LineString"])
    return g


def lines_metric(geom, tol_m=2.0):
    """Merge, simplify (in metres) and return a WGS84 (Multi)LineString."""
    return to_wgs84(merge_lines(to_metric(geom)).simplify(tol_m, preserve_topology=False))


def truck_routes():
    area = study_area(TRUCK_BUFFER_M)
    where = f"intersects(the_geom, '{box(*area.bounds).wkt}')"
    rows = socrata("data.cityofnewyork.us", TRUCK_ROUTES, where=where)
    by_type = {}
    for r in rows:
        if not r.get("the_geom"):
            continue
        g = shape(r["the_geom"]).intersection(area)
        if g.is_empty:
            continue
        street = " ".join(ACRONYMS.get(w, w) for w in (r.get("street") or "").title().split())
        by_type.setdefault(r["routetype"], {}).setdefault(street, []).append(g)
    assert set(by_type) <= {"Through", "Local"}, set(by_type)
    for kind in ("Through", "Local"):
        feats = []
        for street, geoms in sorted(by_type.get(kind, {}).items()):
            g = lines_metric(unary_union(geoms))
            if not g.is_empty:
                feats.append(feature(g, {"street": street}))
        write_fc(os.path.join(OUT, f"truck_routes_{kind.lower()}.geojson"), feats)


def zip_codes():
    dist = districts()
    dist_m = to_metric(dist)
    zctas = {}
    for f in arcgis_query(ZCTA_LAYER, geometry=dist, out_fields="ZCTA5,AREALAND"):
        g = shape(f["geometry"]).buffer(0)
        inside = to_metric(g).intersection(dist_m).area
        share = inside / max(f["properties"]["AREALAND"], 1)
        if share >= ZCTA_MIN_SHARE:
            zctas[f["properties"]["ZCTA5"]] = g
    print("ZCTAs:", ", ".join(sorted(zctas)))

    # boundary lines between the ZCTAs, inside the districts (the mask draws the outline)
    inner = dist_m.buffer(-EDGE_M)
    edges = unary_union([to_metric(g).boundary for g in zctas.values()]).intersection(inner)
    # drop stubs left where a ZCTA edge wanders in and out of the band along the outline
    edges = [e for e in parts(merge_lines(edges)) if e.length >= 50]
    write_fc(os.path.join(OUT, "zip_boundaries.geojson"),
             [feature(to_wgs84(e.simplify(2.0)), {}) for e in edges])

    # one label per ZCTA on the largest piece of it inside the districts
    labels = []
    for z, g in sorted(zctas.items()):
        part = g.intersection(dist)
        part = max(parts(part), key=lambda p: to_metric(p).area)
        labels.append(feature(part.representative_point(), {"zipcode": z}))
    write_fc(os.path.join(OUT, "zip_labels.geojson"), labels)


def mask():
    dist = simplify(districts(), 1.5)
    minx, miny, maxx, maxy = dist.bounds
    frame = box(minx - MASK_PAD_DEG, miny - MASK_PAD_DEG, maxx + MASK_PAD_DEG, maxy + MASK_PAD_DEG)
    write_fc(os.path.join(OUT, "area_mask.geojson"), [feature(frame.difference(dist), {})])


def main():
    os.makedirs(os.path.join(DATA_DIR, OUT), exist_ok=True)
    truck_routes()
    zip_codes()
    mask()


if __name__ == "__main__":
    main()
