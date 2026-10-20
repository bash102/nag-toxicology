"""Shared helpers for rebuilding the ToxiCity map data layers.

Study area: Brooklyn Community District 1 (BoroCD 301, Greenpoint + Williamsburg)
plus a ~200 m buffer.

Downloads are cached in $NAG_CACHE (default ~/.cache/nag-toxicology) so the
scripts can be re-run cheaply; delete that directory to force fresh downloads.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data")
CACHE_DIR = os.environ.get("NAG_CACHE", os.path.expanduser("~/.cache/nag-toxicology"))
os.makedirs(CACHE_DIR, exist_ok=True)

DCP = "https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services"
CD_SERVICE = DCP + "/NYC_Community_Districts/FeatureServer/0"
BUFFER_M = 200.0

UA = "nag-toxicology-data-rebuild/1.0 (+https://github.com/clhenrick/nag-toxicology)"

# NY State Plane Long Island (US feet) <-> WGS84; and UTM 18N metres for buffering
_to_m = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True).transform
_to_ll = Transformer.from_crs("EPSG:32618", "EPSG:4326", always_xy=True).transform


def to_metric(geom):
    return transform(_to_m, geom)


def to_wgs84(geom):
    return transform(_to_ll, geom)


def fetch(url, params=None, data=None, cache=True, retries=4, timeout=180, binary=False):
    """GET (or POST if data given) with simple on-disk caching and retries."""
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    body = urllib.parse.urlencode(data).encode() if data else None
    key = hashlib.sha1((url + (body.decode() if body else "")).encode()).hexdigest()
    path = os.path.join(CACHE_DIR, key)
    if cache and os.path.exists(path):
        with open(path, "rb") as f:
            raw = f.read()
    else:
        last = None
        for i in range(retries):
            try:
                req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    raw = r.read()
                break
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(2 * (i + 1))
        else:
            raise RuntimeError(f"failed to fetch {url}: {last}")
        if cache:
            with open(path, "wb") as f:
                f.write(raw)
    return raw if binary else raw.decode("utf-8")


def fetch_json(url, params=None, data=None, cache=True):
    return json.loads(fetch(url, params=params, data=data, cache=cache))


def arcgis_query(layer_url, where="1=1", geometry=None, out_fields="*", page=1000, extra=None):
    """Query an ArcGIS FeatureServer/MapServer layer, returning GeoJSON-like
    features (geometry in WGS84). `geometry` may be a shapely geometry in
    WGS84; its bounding envelope is used as the spatial filter."""
    feats = []
    offset = 0
    while True:
        p = {
            "where": where,
            "outFields": out_fields,
            "outSR": 4326,
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page,
            "returnGeometry": "true",
        }
        if geometry is not None:
            minx, miny, maxx, maxy = geometry.bounds
            p.update({
                "geometry": f"{minx},{miny},{maxx},{maxy}",
                "geometryType": "esriGeometryEnvelope",
                "inSR": 4326,
                "spatialRel": "esriSpatialRelIntersects",
            })
        if extra:
            p.update(extra)
        d = fetch_json(layer_url + "/query", data=p)
        if "error" in d:
            raise RuntimeError(f"{layer_url}: {d['error']}")
        got = d.get("features", [])
        feats.extend(got)
        exceeded = d.get("exceededTransferLimit") or d.get("properties", {}).get("exceededTransferLimit")
        if not got or (not exceeded and len(got) < page):
            break
        offset += len(got)
    return feats


def socrata(domain, dataset, where=None, select=None, limit=50000, order=":id"):
    """Fetch all rows from a Socrata SODA endpoint as a list of dicts."""
    rows = []
    offset = 0
    while True:
        p = {"$limit": limit, "$offset": offset, "$order": order}
        if where:
            p["$where"] = where
        if select:
            p["$select"] = select
        d = fetch_json(f"https://{domain}/resource/{dataset}.json", params=p)
        rows.extend(d)
        if len(d) < limit:
            break
        offset += limit
    return rows


_cd1 = None


def cd1():
    """CD1 (BoroCD 301) polygon in WGS84 (DCP 'NYC_Community_Districts', clipped to shoreline)."""
    global _cd1
    if _cd1 is None:
        feats = arcgis_query(CD_SERVICE, where="BoroCD=301")
        assert len(feats) == 1, feats
        _cd1 = shape(feats[0]["geometry"]).buffer(0)
    return _cd1


def study_area(buffer_m=BUFFER_M):
    """CD1 buffered by `buffer_m` metres, in WGS84."""
    return to_wgs84(to_metric(cd1()).buffer(buffer_m))


def round_coords(obj, nd=6):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(v), nd) for v in obj]
        return [round_coords(o, nd) for o in obj]
    return obj


def simplify(geom, tol_m=1.5):
    """Topology-preserving simplification with a tolerance in metres."""
    return to_wgs84(to_metric(geom).simplify(tol_m, preserve_topology=True)).buffer(0)


def feature(geom, props):
    g = mapping(geom)
    g = {"type": g["type"], "coordinates": round_coords(g["coordinates"])}
    return {"type": "Feature", "properties": props, "geometry": g}


def write_fc(name, features, meta=None):
    path = os.path.join(DATA_DIR, name)
    fc = {"type": "FeatureCollection"}
    if meta:
        fc["metadata"] = meta
    fc["features"] = features
    with open(path, "w") as f:
        json.dump(fc, f, separators=(",", ":"), ensure_ascii=False)
    print(f"wrote {path}: {len(features)} features, {os.path.getsize(path)/1024:.1f} KB")
    return path


__all__ = [
    "DATA_DIR", "DCP", "arcgis_query", "cd1", "feature", "fetch", "fetch_json",
    "round_coords", "shape", "simplify", "socrata", "study_area", "to_metric",
    "to_wgs84", "unary_union", "write_fc",
]
