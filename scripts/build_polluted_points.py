"""Build data/polluted_points.geojson.

category = highly_regulated | e_designation | spill_major | spill_minor

highly_regulated  U.S. EPA ECHO (Enforcement and Compliance History Online) facility search,
                  active facilities within the study area (Brooklyn CDs 1, 2 and 4) + 200 m
                  that are any of:
                  - Clean Air Act major source (Title V, "Major Emissions")
                  - Clean Water Act major NPDES discharger
                  - current Toxics Release Inventory (TRI) reporter
                  - RCRA hazardous-waste treatment/storage/disposal facility (TSDF)
                  - RCRA Large Quantity Generator with an industrial NAICS code (221 utilities
                    excl. 22131 water supply, 31-33 manufacturing, 42 wholesale, 49319 petroleum
                    storage, 562 waste management excl. 56291 remediation). LQG records that are
                    only construction, real-estate, school, transit, bridge/road-work, remediation
                    or Con Edison manhole/vault jobs (mostly one-time generators) are excluded.
e_designation     NYC DCP (E) Designations (nyedesignations feature service) on tax lots in
                  Brooklyn CDs 1, 2 and 4 (MapPLUTO CD in DISTRICTS: 301, 302, 304) with a
                  hazardous-materials or air-quality requirement (noise-only E-designations
                  excluded). Point = MapPLUTO lot centroid (DCP Latitude/Longitude).
spill_*           NYS DEC Spill Incidents (data.ny.gov u44d-k5fk), Kings County, spill date
                  2011-01-01 or later, geocoded with NYC GeoSearch (no coordinates in source)
                  and kept if inside the boundary of CDs 1, 2 and 4 (no buffer). spill_major =
                  total reported quantity >= 100 gallons; everything else (smaller, unknown, or
                  non-gallon units) is spill_minor.
"""
import collections
import json
import os
import re
import sys
import time
import urllib.parse

from shapely.geometry import Point

from common import CACHE_DIR, DCP, DISTRICTS_SQL, arcgis_query, districts, fetch_json, socrata, study_area, write_fc

ECHO = "https://echodata.epa.gov/echo/echo_rest_services"
ECHO_COLS = "1,2,3,5,6,16,17,19,20,21,23,24,28,32,33,34,38,62,75,97,104,105"
EDES = DCP + "/nyedesignations/FeatureServer/0"
MAPPLUTO = DCP + "/MAPPLUTO/FeatureServer/0"
GEOSEARCH = "https://geosearch.planninglabs.nyc/v2/search"
SPILL_START = "2011-01-01"
GEOCODE_DELAY = 0.15  # seconds between GeoSearch requests (sequential)

NOISE_ONLY = {
    "window wall attenuation & alternate ventilation",
    "double glazed windows",
    "double glazed windows & alternate ventilation",
    "n2 ambient noise zone levels",
}
INDUSTRIAL_NAICS = ("221", "31", "32", "33", "42", "49319", "562")
NON_INDUSTRIAL_NAICS = ("22131", "56291")  # water supply works, remediation services
ONE_TIME_NAME = r"MANHOLE|VAULT|SERVICE BOX|\bBIN\b|BRIDGE|SHAFT"


def pt_feature(lon, lat, props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}}


def title(s):
    s = (s or "").strip()
    return s.title() if s.isupper() else s


# --------------------------------------------------------------------------- EPA ECHO
def highly_regulated(area):
    b = area.bounds
    q = fetch_json(ECHO + ".get_facilities", params={
        "output": "JSON", "p_c1lat": b[3], "p_c1lon": b[0], "p_c2lat": b[1], "p_c2lon": b[2], "p_act": "Y"},
        cache=False)["Results"]
    rows, page = [], 1
    while True:
        r = fetch_json(ECHO + ".get_qid", params={
            "output": "JSON", "qid": q["QueryID"], "pageno": page, "qcolumns": ECHO_COLS}, cache=False)["Results"]
        rows.extend(r.get("Facilities", []))
        if len(rows) >= int(q["QueryRows"]) or not r.get("Facilities"):
            break
        page += 1
    feats = []
    for x in rows:
        if not x.get("FacLat"):
            continue
        lon, lat = float(x["FacLong"]), float(x["FacLat"])
        if not area.contains(Point(lon, lat)):
            continue
        caa, cwa, rcra = x.get("CAAPermitTypes") or "", x.get("CWAPermitTypes") or "", x.get("RCRAPermitTypes") or ""
        naics = (x.get("FacNAICSCodes") or "").split()
        reasons = []
        if "Major Emissions" in caa:
            reasons.append("Clean Air Act major source (Title V)")
        if re.search(r"\bMajor\b", cwa):
            reasons.append("Clean Water Act major NPDES discharger")
        if x.get("TRIFlag") == "Y":
            reasons.append("Toxics Release Inventory reporter")
        if "TSD" in rcra:
            reasons.append("RCRA hazardous waste treatment/storage/disposal facility")
        if "LQG" in rcra:
            industrial = any(n.startswith(INDUSTRIAL_NAICS) and not n.startswith(NON_INDUSTRIAL_NAICS) for n in naics)
            if industrial and not re.search(ONE_TIME_NAME, x["FacName"] or "", re.I):
                reasons.append("RCRA Large Quantity Generator of hazardous waste")
        if not reasons:
            continue
        progs = []
        if caa:
            progs.append(f"CAA: {caa}")
        if cwa:
            progs.append(f"CWA/NPDES: {cwa}")
        if rcra:
            progs.append(f"RCRA: {rcra}")
        if x.get("TRIFlag") == "Y":
            progs.append("TRI")
        desc = "; ".join(reasons)
        if x.get("FacSICDescs"):
            desc += f". Industry: {x['FacSICDescs']}"
        if x.get("FacComplianceStatus"):
            desc += f". Compliance status: {x['FacComplianceStatus']}"
        feats.append(pt_feature(lon, lat, {
            "category": "highly_regulated",
            "name": title(x["FacName"]),
            "address": f"{title(x.get('FacStreet'))}, {title(x.get('FacCity'))}, NY {x.get('FacZip') or ''}".strip(),
            "description": desc,
            "program": "; ".join(progs),
            "date": "",
            "link": f"https://echo.epa.gov/detailed-facility-report?fid={x['RegistryID']}",
            "source": "U.S. EPA ECHO facility search (FRS registry ID %s), active facilities" % x["RegistryID"],
        }))
    return feats


# --------------------------------------------------------------------------- (E) designations
def e_designations():
    lots = {}
    for f in arcgis_query(MAPPLUTO, where=f"CD IN ({DISTRICTS_SQL}) AND EDesigNum IS NOT NULL",
                          out_fields="BBL,Address,Latitude,Longitude,EDesigNum,LandUse",
                          extra={"returnGeometry": "false"}):
        p = f["properties"]
        lots[str(int(float(p["BBL"])))] = p
    recs = collections.defaultdict(list)
    bbls = sorted(lots)
    for i in range(0, len(bbls), 150):
        for f in arcgis_query(EDES, where=f"BBL in ({','.join(bbls[i:i + 150])})", extra={"returnGeometry": "false"}):
            p = f["properties"]
            recs[str(int(p["BBL"]))].append(p)
    feats = []
    for bbl, rs in sorted(recs.items()):
        reqs = []
        for r in rs:
            for part in (r.get("DESCRIPTION") or "").split(";"):
                part = part.replace("\xa0", " ").strip()
                if part and part not in reqs:
                    reqs.append(part)
        relevant = [q for q in reqs if q.lower() not in NOISE_ONLY]
        if not relevant:
            continue
        types = []
        if any(re.search(r"hazard|gasoline storage|restrictive declaration", q, re.I) for q in relevant):
            types.append("Hazardous Materials")
        if any(not re.search(r"hazard|gasoline storage|restrictive declaration", q, re.I) for q in relevant):
            types.append("Air Quality")
        lot = lots[bbl]
        if lot.get("Latitude") is None:
            continue
        enums = sorted({r["ENUMBER"] for r in rs if r.get("ENUMBER")})
        ceqr = sorted({r["CEQR_NUM"] for r in rs if r.get("CEQR_NUM")})
        feats.append(pt_feature(float(lot["Longitude"]), float(lot["Latitude"]), {
            "category": "e_designation",
            "name": f"(E) designation {', '.join(enums)}",
            "address": f"{title(lot.get('Address'))}, Brooklyn" if lot.get("Address") else "",
            "description": f"{' and '.join(types)} (E) designation. Requirements: " + "; ".join(reqs),
            "program": "NYC (E) Designation - " + " / ".join(types),
            "date": "",
            "link": "",
            "bbl": bbl,
            "ceqr_number": ", ".join(ceqr),
            "source": "NYC DCP (E) Designations + MapPLUTO lot centroid",
        }))
    return feats


# --------------------------------------------------------------------------- spills
_gc_path = os.path.join(CACHE_DIR, "geosearch_cache.json")


def _load_gc():
    try:
        with open(_gc_path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def geocode(text, cache):
    if text in cache:
        return cache[text]
    url = GEOSEARCH + "?" + urllib.parse.urlencode({"text": text, "size": 1})
    try:
        d = fetch_json(url, cache=False)
        feats = d.get("features") or []
        res = None
        if feats:
            f = feats[0]
            p = f["properties"]
            res = {"lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1],
                   "label": p.get("label"), "borough": p.get("borough"), "layer": p.get("layer"),
                   "housenumber": p.get("housenumber"), "confidence": p.get("confidence"),
                   "match_type": p.get("match_type")}
    except Exception as e:  # noqa: BLE001
        print("geocode failed:", text, e, file=sys.stderr)
        return None
    cache[text] = res
    time.sleep(GEOCODE_DELAY)
    return res


def usable(res, street):
    """Accept only Brooklyn address-level matches whose house number agrees with the input."""
    if not res or res.get("borough") != "Brooklyn":
        return False
    m = re.match(r"\s*(\d+[-\d]*)", street)
    if not m or not res.get("housenumber"):
        return False
    return res["housenumber"].split("-")[0] == m.group(1).split("-")[0]


def spills(area):
    rows = socrata("data.ny.gov", "u44d-k5fk",
                   where=f"county='Kings' and spill_date >= '{SPILL_START}T00:00:00'")
    by_num = collections.defaultdict(list)
    for r in rows:
        by_num[r["spill_number"]].append(r)
    cache = _load_gc()
    feats, n_geo, n_fail = [], 0, 0
    try:
        for i, (num, rs) in enumerate(sorted(by_num.items())):
            r0 = rs[0]
            street = (r0.get("street_1") or "").strip()
            if not street:
                n_fail += 1
                continue
            text = f"{street}, Brooklyn, NY {r0.get('zip_code') or ''}".strip()
            res = geocode(text, cache)
            if i % 200 == 0:
                print(f"  spills geocoded {i}/{len(by_num)}", flush=True)
                with open(_gc_path, "w") as f:
                    json.dump(cache, f)
            if not usable(res, street):
                n_fail += 1
                continue
            n_geo += 1
            pt = Point(res["lon"], res["lat"])
            if not area.contains(pt):
                continue
            gallons, mats, other_units = 0.0, [], []
            for r in rs:
                q = float(r.get("quantity") or 0)
                u = (r.get("units") or "").strip()
                if u.lower() == "gallons":
                    gallons += q
                elif q:
                    other_units.append(f"{q:g} {u}".strip())
                m = (r.get("material_name") or "").strip()
                if m and m not in mats:
                    mats.append(m)
            qty = []
            if gallons:
                qty.append(f"{gallons:g} gallons")
            qty += other_units
            desc = f"Material: {', '.join(mats) or 'unknown'}. Quantity: {', '.join(qty) or 'not reported'}."
            if r0.get("contributing_factor"):
                desc += f" Cause: {r0['contributing_factor']}."
            if r0.get("source"):
                desc += f" Source: {r0['source']}."
            if r0.get("waterbody"):
                desc += f" Waterbody: {r0['waterbody']}."
            if r0.get("close_date"):
                desc += f" Closed {r0['close_date'][:10]}."
            feats.append(pt_feature(res["lon"], res["lat"], {
                "category": "spill_major" if gallons >= 100 else "spill_minor",
                "name": title(r0.get("program_facility_name")) or f"Spill {num}",
                "address": f"{title(street)}, Brooklyn, NY {r0.get('zip_code') or ''}".strip(),
                "description": desc,
                "program": "NYS DEC Spill Response Program",
                "date": (r0.get("spill_date") or "")[:10],
                "link": "",
                "spill_number": num,
                "quantity_gallons": round(gallons, 2),
                "geocode_label": res.get("label"),
                "source": "NYS DEC Spill Incidents (data.ny.gov u44d-k5fk), geocoded with NYC GeoSearch",
            }))
    finally:
        with open(_gc_path, "w") as f:
            json.dump(cache, f)
    print(f"spills: {len(by_num)} Kings spills since {SPILL_START}; {n_geo} geocoded to an address, "
          f"{n_fail} without a usable address; {len(feats)} inside the districts")
    return feats


def main():
    area = study_area()
    feats = []
    hr = highly_regulated(area)
    print("highly_regulated:", len(hr))
    ed = e_designations()
    print("e_designation:", len(ed))
    sp = spills(districts())
    feats = hr + ed + sp
    write_fc("polluted_points.geojson", feats)
    print(collections.Counter(f["properties"]["category"] for f in feats))


if __name__ == "__main__":
    main()
