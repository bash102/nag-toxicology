"""Convert the basemap shapefiles in basemap/data/ to WGS84 GeoJSON for Leaflet.

The original basemap was a custom Mapbox Studio Classic style whose hosted
tiles are no longer available. The same overlay data (truck routes, ZIP code
boundaries and labels, Community District 1 mask) is drawn client side instead.

Usage: python3 scripts/build_basemap_overlays.py
Requires: pyshp, shapely, pyproj
"""
import io
import json
import os
import zipfile

import numpy as np
import shapefile
import shapely
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "basemap", "data")
OUT = os.path.join(ROOT, "data", "basemap")

_transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)


def to_wgs84(coords):
    return np.column_stack(_transformer.transform(coords[:, 0], coords[:, 1]))


def read_zip(name):
    """Yield (geometry, record dict) for the single shapefile inside a zip."""
    with zipfile.ZipFile(os.path.join(SRC, name)) as z:
        base = [n for n in z.namelist() if n.endswith(".shp")][0][:-4]
        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(base + ".shp")),
            shx=io.BytesIO(z.read(base + ".shx")),
            dbf=io.BytesIO(z.read(base + ".dbf")),
        )
        for sr in reader.shapeRecords():
            yield shapely.transform(shape(sr.shape.__geo_interface__), to_wgs84), sr.record.as_dict()


def round_coords(obj, nd=6):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(c, nd) for c in obj]
        return [round_coords(o, nd) for o in obj]
    return obj


def write(name, features):
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": props,
                "geometry": {
                    "type": mapping(geom)["type"],
                    "coordinates": round_coords(mapping(geom)["coordinates"]),
                },
            }
            for geom, props in features
            if not geom.is_empty
        ],
    }
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        json.dump(fc, f, separators=(",", ":"))
    print("wrote %s (%d features, %d KB)" % (path, len(fc["features"]), os.path.getsize(path) // 1024))


def truck_routes(zip_name):
    # merge segments per street so the file stays small
    streets = {}
    for geom, rec in read_zip(zip_name):
        streets.setdefault(rec.get("Street") or "", []).append(geom)
    return [
        (unary_union(geoms).simplify(0.00001), {"street": street.title()})
        for street, geoms in sorted(streets.items())
    ]


def main():
    os.makedirs(OUT, exist_ok=True)
    write("truck_routes_through.geojson", truck_routes("truck_routes_through_joined_3857.zip"))
    write("truck_routes_local.geojson", truck_routes("truck_routes_local_joined_3857.zip"))
    write("zip_boundaries.geojson", [(g.simplify(0.00001), {}) for g, _ in read_zip("cd1_zip_boundaries_3857.zip")])
    write("zip_labels.geojson", [(g, {"zipcode": r["ZipCode"]}) for g, r in read_zip("cd1_zip_labels_3857.zip")])
    write("cd1_mask.geojson", [(g.simplify(0.00005), {}) for g, _ in read_zip("cd1_mask_3857.zip")])


if __name__ == "__main__":
    main()
