"""Build data/cso_outfalls.geojson: combined sewer overflow (CSO) outfalls discharging to the
waters that border the study area (common.DISTRICTS; the Brooklyn bank of the East River
from Atlantic Avenue past DUMBO, the Navy Yard and Wallabout Bay to the mouth of Newtown Creek,
and Newtown Creek with English Kills, East Branch, Maspeth Creek, Dutch Kills and Whale Creek),
with NYC DEP's modeled overflow counts and volumes for the latest calendar year. The outfalls
drain to the Newtown Creek, Bowery Bay and Red Hook WRRFs.

Sources
1. Locations: NYC DEP "Citywide Outfalls" (NYC Open Data 8rjn-kpsh), rows with
   outfall_ty = 'CSO'.
2. Overflow counts / volumes: NYC DEP "Fourteen Wastewater Resource Recovery Facilities' SPDES
   Permits, Best Management Practices Annual Report" for CY2025 (submitted April 2026),
   Appendix 14.1 "Table - CSO Discharge Summary for CY 2025 Checklist" (InfoWorks ICM model
   runs driven by NOAA/NSSL radar rainfall). The outfall inventory in the same report
   (Appendix 13) supplies the receiving-water names.
3. NYS DEC "Combined Sewer Overflows (CSOs): Beginning 2013" (data.ny.gov ephi-ffu6; the
   dataset behind the "CSOs Map" i8hd-rmbi): DEC's per-outfall overflow detection method
   ("Model" / "Monitoring"). DEC has no counts for NYC (every NYC row says "Visit facility
   website"), so it is used for that one attribute only.

Selection: DEP CSO outfalls within the districts + 500 m, plus every outfall whose receiving
water (per the BMP inventory) is Newtown Creek or one of its tributaries, wherever it is.
Manhattan-bank East River outfalls (NCM-*) are excluded, although some lie within 500 m.

Requires the `pdftotext` command-line tool (poppler-utils) to read the BMP report.
"""
import hashlib
import os
import re
import subprocess
import urllib.request

from shapely.geometry import Point

from common import CACHE_DIR, districts, feature, socrata, study_area, to_metric, write_fc

BMP_YEAR = 2025
BMP_URL = ("https://www.nyc.gov/assets/dep/downloads/pdf/water/stormwater/"
           f"spdes-bmp-cso-annual-report-{BMP_YEAR}.pdf")
BUFFER_M = 500.0

NEWTOWN_SYSTEM = re.compile(r"NEWTOWN|ENGLISH KILLS|EAST BRANCH|MASPETH|DUTCH KILLS|WHALE CREEK")

# DEP's Citywide Outfalls layer and the BMP report number two Greenpoint outfalls differently.
# Matched on location: NCB-088 "Huron Street (Reg # B-12)" in the layer = NCB-027 "East River &
# Huron Street, Reg #B-12" in the BMP report (DEC's NY0026204-027 point is within 1 m of it);
# NCB-084 "Commercial St" = NCB-023 "Newtown Creek & Franklin Street, Reg #B-16" (DEC's
# NY0026204-023 point is ~25 m away, where Franklin St meets Commercial St).
BMP_ALIAS = {"NCB-088": "NCB-027", "NCB-084": "NCB-023"}

NOTES = {
    "RH-001": ("Main outfall of the Red Hook WRRF (treated effluent). DEP's outfall layer and DEC's "
               "CSO dataset list it as a CSO outfall, but it has no row in the BMP CSO discharge table."),
    "NCB-001": ("Main outfall of the Newtown Creek WRRF (treated effluent). DEP's outfall layer and DEC's "
                "CSO dataset list it as a CSO outfall, but it has no row in the BMP CSO discharge table."),
    "NCB-084": "Overflow figures are those the BMP report gives for NCB-023 (Newtown Creek & Franklin St, Reg. B-16), matched by location.",
    "NCB-088": "Overflow figures are those the BMP report gives for NCB-027 (East River & Huron St, Reg. B-12), matched by location.",
}

# DEP treatment-plant code -> (DEC SPDES permit number in ephi-ffu6, WRRF name)
PLANTS = {"NC": ("NY0026204", "Newtown Creek WRRF"), "BB": ("NY0026158", "Bowery Bay WRRF"),
          "RH": ("NY0027073", "Red Hook WRRF")}

WWTP_NAMES = ["26th Ward", "Bowery Bay", "Coney Island", "Hunts Point", "Jamaica", "Newtown Creek",
              "North River", "Owls Head", "Port Richmond", "Red Hook", "Rockaway", "Tallman Island",
              "Wards Island", "Oakwood Beach"]



def bmp_text():
    """Download the BMP report (cached) and return its text, via `pdftotext -layout`.
    nyc.gov refuses the default script User-Agent, so a browser-style one is sent."""
    key = hashlib.sha1(BMP_URL.encode()).hexdigest()
    txt = os.path.join(CACHE_DIR, key + ".txt")
    if not os.path.exists(txt):
        src = os.path.join(CACHE_DIR, key + ".pdf")
        if not os.path.exists(src):
            req = urllib.request.Request(BMP_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=600) as r, open(src + ".part", "wb") as f:
                f.write(r.read())
            os.replace(src + ".part", src)
        subprocess.run(["pdftotext", "-layout", src, txt], check=True)
    with open(txt, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()


def num(tok):
    if tok in ("?", ""):
        return None
    return float(tok.replace(",", ""))


def parse_bmp(lines):
    """Return ({outfall_id: (wwtp, ev24, vol24, ev25, vol25)}, {outfall_id: location})."""
    start = next(i for i, l in enumerate(lines)
                 if re.match(r"^\s*Appendix 14\.1:\s+TABLE", l, re.I))
    header = " ".join(lines[start:start + 6])
    assert f"CY{BMP_YEAR} - QPE" in header and f"CY{BMP_YEAR - 1} - QPE" in header, header
    row = re.compile(r"^\s*(" + "|".join(WWTP_NAMES) + r")\s+([A-Z]{2})\s+([A-Z0-9]+-\s?[0-9]+[A-Z]?)\s+(.*)$")
    table = {}
    for l in lines[start:start + 3000]:
        if re.match(r"^\s*Appendix 15", l):
            break
        m = row.match(l)
        if not m:
            continue
        oid = m.group(3).replace(" ", "")
        if oid in table:  # a second copy of an older table follows; keep the first (CY2025) one
            continue
        toks = m.group(4).split()
        if len(toks) < 4 or not all(re.fullmatch(r"\?|[\d,.]+", t) for t in toks):
            continue
        e24, v24, e25, v25 = (num(t) for t in toks[-4:])
        table[oid] = (m.group(1), e24, v24, e25, v25)
    # outfall inventory (Appendix 13): "<no> <ID> <WATERBODY> & <LOCATION> <contributors> <status>"
    inv = {}
    inv_row = re.compile(r"^\s*\d+\s+([A-Z]{2,3}\s?-\s?\d+[A-Z]?)\s{2,}(.+?)\s{2,}")
    for l in lines[:start]:
        m = inv_row.match(l)
        if m:
            inv.setdefault(m.group(1).replace(" ", ""), m.group(2).strip())
    return table, inv


def tidy(s):
    """Title-case DEP's upper-case location strings, keeping regulator ids and ordinals."""
    s = re.sub(r"\s+", " ", s or "").strip()
    s = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", s))  # Red Hook names read "( REG # R-21A )"
    s = re.sub(r"[A-Za-z][A-Za-z.']*", lambda m: m.group(0).capitalize(), s)
    s = re.sub(r"\b(\d+)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s)
    s = re.sub(r"\bReg\b\s*#?\s*", "Reg. ", s)
    s = re.sub(r"Reg\. ([A-Za-z])-", lambda m: "Reg. " + m.group(1).upper() + "-", s)
    s = re.sub(r"\b(W|S|N|E)/O\b", lambda m: m.group(1).lower() + "/o", s)
    s = re.sub(r"\bWpcp\b|\bW\.p\.c\.p\.", "WPCP", s)
    return s.replace("Mcguiness", "McGuinness").replace("Mcguinness", "McGuinness")


def main():
    lines = bmp_text()
    table, inv = parse_bmp(lines)
    print(f"BMP CY{BMP_YEAR} table: {len(table)} outfalls; inventory: {len(inv)}")

    dec = {}
    for r in socrata("data.ny.gov", "ephi-ffu6", where="county in ('Kings','Queens')"):
        if r.get("facility_owner_name") == "NYC DEP":
            dec[r["cso_identification_number"]] = r

    area = study_area(BUFFER_M)
    districts_m = to_metric(districts())
    feats = []
    for x in socrata("data.cityofnewyork.us", "8rjn-kpsh", where="outfall_ty='CSO'"):
        if not x.get("latitude"):
            continue
        oid = x["unitid"]
        pt = Point(float(x["longitude"]), float(x["latitude"]))
        bid = BMP_ALIAS.get(oid, oid)
        inv_loc = inv.get(bid, "")
        water = inv_loc.split("&")[0].strip() if "&" in inv_loc else ""
        if not water:
            water = x.get("receiving_") or ""
        in_system = bool(NEWTOWN_SYSTEM.search(water.upper()) or
                         NEWTOWN_SYSTEM.search((x.get("receiving_") or "").upper()))
        if not (area.contains(pt) or in_system):
            continue
        if oid.startswith("NCM-"):
            continue
        wwtp, e24, v24, e25, v25 = table.get(bid, (None,) * 5)
        prefix, facility = PLANTS.get(x.get("treatment_"), (None, x.get("treatment_")))
        num_part = re.sub(r"\D", "", bid)
        d = dec.get(f"{prefix}-{int(num_part):03d}") if prefix and num_part else None
        has = e25 is not None
        props = {
            "outfall_id": oid,
            "name": tidy(x.get("location")) or tidy(inv_loc.split("&")[-1]),
            "receiving_water": tidy(water.replace(", LOWER", "")).replace("And Tidal Tribs", "and tidal tributaries"),
            "operator": "NYC DEP" if x.get("ownership") == "DEP" else x.get("ownership"),
            "facility": facility,
            "overflow_events": int(e25) if has else None,
            "overflow_volume_mg": v25 if has else None,
            "overflow_period": f"Calendar year {BMP_YEAR}" if has else None,
            "detection": (f"Modeled (DEP InfoWorks ICM, CY{BMP_YEAR} NOAA/NSSL radar rainfall)" if has else None),
            "link": BMP_URL,
            "source": ("Location: NYC DEP Citywide Outfalls (NYC Open Data 8rjn-kpsh). Overflows: NYC DEP "
                       f"SPDES BMP Annual Report CY{BMP_YEAR}, Appendix 14.1" if has else
                       "Location: NYC DEP Citywide Outfalls (NYC Open Data 8rjn-kpsh). Not listed in the "
                       f"CY{BMP_YEAR} BMP CSO discharge table"),
            "overflow_events_prev_year": int(e24) if e24 is not None else None,
            "overflow_volume_mg_prev_year": v24,
            "bmp_outfall_id": bid if bid != oid else None,
            "dec_cso_id": d["cso_identification_number"] if d else None,
            "dec_detection_method": d.get("discharge_activation_type") if d else None,
            "outfall_size": x.get("of_size"),
            "distance_to_area_m": round(districts_m.distance(to_metric(pt))),
            "note": NOTES.get(oid),
        }
        feats.append((oid, feature(pt, props)))
    feats.sort(key=lambda t: (t[0].split("-")[0], int(re.sub(r"\D", "", t[0]) or 0)))
    feats = [f for _, f in feats]
    have = [f["properties"]["overflow_events"] for f in feats if f["properties"]["overflow_events"] is not None]
    print(f"{len(feats)} outfalls, {len(have)} with CY{BMP_YEAR} counts"
          + (f" (events {min(have)}-{max(have)})" if have else ""))
    write_fc("cso_outfalls.geojson", feats)


if __name__ == "__main__":
    main()
