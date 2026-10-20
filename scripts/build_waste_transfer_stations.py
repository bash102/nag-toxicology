"""Build data/waste_transfer_stations.geojson: waste transfer stations, C&D / recyclables
handling, scrap-metal facilities and the Newtown Creek wastewater plant in CD1 + 200 m.

Sources
1. NYS DEC "Solid Waste Management Facilities" (data.ny.gov 2fni-raj8; active facilities,
   with DEC coordinates). Rows are per authorization; we merge rows sharing name+address.
2. NYC DCP Facilities Database (FacDB, NYC Open Data ji82-xba5): scrap-metal processors
   licensed by NYC DCWP (datasource dca_operatingbusinesses) that are not already in the
   DEC list (matched on normalised street address). DSNY drop-off sites, garages etc. are
   not included.
3. Newtown Creek Wastewater Resource Recovery Facility: NYC DEP data as published in the
   NYC MOCEJ EJNYC "Wastewater Recovery Facilities" layer.
"""
import collections
import re

from shapely.geometry import Point

from common import arcgis_query, socrata, study_area, write_fc

WRRF = ("https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/"
        "Waste_Water_Recovery_Facilities/FeatureServer/0")

DEC_TYPES = [
    (r"^Transfer facility", "Waste transfer station"),
    (r"^CDDHRF", "Construction & demolition debris handling and recovery facility"),
    (r"^C&D processing", "Construction & demolition debris processing"),
    (r"^RHRF", "Recyclables handling and recovery facility"),
    (r"^Scrap metal", "Scrap metal processor"),
    (r"^VDF|Vehicle Dismantling", "Vehicle dismantling facility"),
]

ABBR = {"STREET": "ST", "AVENUE": "AVE", "BOULEVARD": "BLVD", "PLACE": "PL", "ROAD": "RD"}


def norm_addr(a):
    a = re.sub(r"(\d)-(\d)", r"\1\2", (a or "").upper())  # Queens-style 30-27 -> 3027
    a = re.sub(r"[^A-Z0-9 ]", " ", a)
    words = [ABBR.get(w, w) for w in a.split()]
    if words and "-" not in words[0]:
        words[0] = words[0].split("-")[0]
    return " ".join(words[:3])


def ftype(desc):
    for pat, label in DEC_TYPES:
        if re.search(pat, desc or "", re.I):
            return label
    return desc


def tidy(s):
    s = re.sub(r"\s+", " ", (s or "").replace("; ", ", ")).strip()
    return s.title() if s.isupper() else s


def tidy_addr(s):
    """Title-case street addresses that are partly upper-case in the source (e.g. '4600 METROPOLITAN aVE')."""
    s = re.sub(r"\s+", " ", s or "").strip()
    if re.search(r"[A-Z]{3,}", s) or re.search(r"\b[a-z]+[A-Z]", s):
        s = " ".join(w.capitalize() if w.isalpha() else w for w in s.split(" "))
    return s


def main():
    area = study_area()
    feats = []
    seen = set()

    # 1. NYS DEC solid waste management facilities
    groups = collections.OrderedDict()
    for r in socrata("data.ny.gov", "2fni-raj8", where="county in ('Kings','Queens') and active='Yes'"):
        g = r.get("georeference") or {}
        if not g.get("latitude"):
            continue
        pt = Point(float(g["longitude"]), float(g["latitude"]))
        if not area.contains(pt):
            continue
        key = (r["facility_name"].strip().lower(), norm_addr(r["location_address"]))
        groups.setdefault(key, []).append((pt, r))
    for (_, addr_key), items in groups.items():
        pt, r = items[0]
        types = []
        for _, x in items:
            t = ftype(x.get("activity_desc"))
            if t not in types:
                types.append(t)
        auths = sorted({x.get("authorization_number") for _, x in items if x.get("authorization_number")})
        wastes = sorted({w.strip() for _, x in items for w in (x.get("waste_types") or "").split(";") if w.strip()})
        seen.add(addr_key)
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(pt.x, 6), round(pt.y, 6)]},
                      "properties": {
                          "name": tidy(r["facility_name"]),
                          "facility_type": "; ".join(types),
                          "address": f"{tidy_addr(r['location_address'])}, {tidy(r.get('city'))}, NY {r.get('zip_code') or ''}".strip(),
                          "borough": "Brooklyn" if r.get("county") == "Kings" else r.get("county"),
                          "operator": tidy(r.get("owner_name")),
                          "waste_types": ", ".join(wastes),
                          "dec_authorization": ", ".join(auths),
                          "source": "NYS DEC Solid Waste Management Facilities (data.ny.gov 2fni-raj8)",
                      }})

    # 2. DCWP-licensed scrap metal processors from DCP FacDB not already listed by DEC
    for r in socrata("data.cityofnewyork.us", "ji82-xba5",
                     where="borocode in ('3','4') and datasource='dca_operatingbusinesses' "
                           "and factype='SCRAP METAL PROCESSING'"):
        if not r.get("latitude"):
            continue
        pt = Point(float(r["longitude"]), float(r["latitude"]))
        if not area.contains(pt) or norm_addr(r.get("address")) in seen:
            continue
        seen.add(norm_addr(r.get("address")))
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(pt.x, 6), round(pt.y, 6)]},
                      "properties": {
                          "name": tidy(r["facname"]),
                          "facility_type": "Scrap metal processor (NYC DCWP licence)",
                          "address": f"{tidy_addr(r.get('address'))}, {tidy(r.get('city') or 'Brooklyn')}, NY {r.get('zipcode') or ''}".strip(),
                          "borough": {"3": "Brooklyn", "4": "Queens"}.get(r.get("borocode"), r.get("borough")),
                          "operator": tidy(r.get("opname")),
                          "waste_types": "",
                          "dec_authorization": "",
                          "source": "NYC DCP Facilities Database (NYC Open Data ji82-xba5), source NYC DCWP licences",
                      }})

    # 3. Newtown Creek WRRF
    for f in arcgis_query(WRRF, where="Facility_N like '%Newtown%'"):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
                      "properties": {
                          "name": "Newtown Creek Wastewater Resource Recovery Facility",
                          "facility_type": "Wastewater treatment plant (NYC DEP)",
                          "address": "301 Greenpoint Avenue, Brooklyn, NY 11222 (address as registered in EPA ECHO/FRS)",
                          "borough": "Brooklyn",
                          "operator": "NYC Department of Environmental Protection",
                          "waste_types": f"Design capacity {p.get('Design_Cap')}; in operation since {p.get('In_Operati')}; "
                                         f"serves {p.get('Population')} people; discharges to {p.get('Receiving')}",
                          "dec_authorization": "",
                          "source": "NYC DEP via NYC MOCEJ EJNYC 'Wastewater Recovery Facilities' layer",
                      }})

    write_fc("waste_transfer_stations.geojson", feats)
    for f in feats:
        print(" ", f["properties"]["name"], "|", f["properties"]["facility_type"], "|", f["properties"]["address"])


if __name__ == "__main__":
    main()
