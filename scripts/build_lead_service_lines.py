"""Build data/lead_service_lines.geojson: NYC DEP water service line inventory
(material of the private service line, one record per tax lot), aggregated to the
54 census tracts of Brooklyn CD1.

Source: NYC Open Data "Lead Service Line Location Coordinates" (jqfp-uff7), published
by NYC DEP. It is the same inventory as DEP's ArcGIS layer
NYC_WaterConnection_DEP25V11_202601_PG (January 2026 edition; identical record and
category counts). One row per BBL with a tax-lot polygon, `material` and `record_ty`.

CD1 membership: BBL listed in MapPLUTO with CD = 301; inventory BBLs not in MapPLUTO
(e.g. retired lots) are kept if their lot's representative point lies in CD1.
Tract assignment: lot representative point in tract polygon (data/acs.geojson);
points just outside the shoreline-clipped tracts (waterfront lots) go to the nearest tract.
"""
import json
import os
from collections import Counter

from shapely.geometry import box
from shapely.strtree import STRtree

from common import DATA_DIR, DCP, arcgis_query, cd1, shape, socrata, to_metric, write_fc

DATASET = "jqfp-uff7"
MAPPLUTO = DCP + "/MAPPLUTO/FeatureServer/0"
INVENTORY_DATE = "2026-01"   # DEP edition DEP25V11_202601; Open Data rows updated 2026-01-30
MAX_SNAP_M = 60              # max snap distance for lots not confirmed by MapPLUTO CD=301

CATS = {
    "Lead": "lead",
    "Galvanized Service Line Requiring Replacement": "galvanized_requiring_replacement",
    "Unknown - Lead Status Unknown": "unknown",
    "Non-Lead": "non_lead",
    "Non-Applicable": "not_applicable",
}


def main():
    with open(os.path.join(DATA_DIR, "acs.geojson")) as f:
        tracts = json.load(f)["features"]
    tgeoms = [shape(t["geometry"]) for t in tracts]
    tgeoms_m = [to_metric(g) for g in tgeoms]
    tree = STRtree(tgeoms_m)

    area = cd1()
    area_m = to_metric(area)

    # MapPLUTO lots in CD1
    pluto = arcgis_query(MAPPLUTO, where="CD=301", out_fields="BBL",
                         extra={"returnGeometry": "false"})
    cd1_bbls = {str(int(float(f["properties"]["BBL"]))) for f in pluto}
    print(f"MapPLUTO CD=301 lots: {len(cd1_bbls)}")

    minx, miny, maxx, maxy = area.buffer(0.003).bounds
    wkt = box(minx, miny, maxx, maxy).wkt
    rows = socrata("data.cityofnewyork.us", DATASET,
                   where=f"starts_with(tbbl,'3') AND intersects(the_geom,'{wkt}')",
                   select="tbbl,material,record_ty,city_owned,the_geom")
    print(f"inventory lots in CD1 bounding box: {len(rows)}")

    counts = {t["properties"]["geoid"]: Counter() for t in tracts}
    rec_types = Counter()
    cat_totals = Counter()
    unmatched = []
    not_in_pluto = []
    snapped = []
    seen = set()
    for r in rows:
        bbl = r["tbbl"]
        if bbl in seen:
            continue
        seen.add(bbl)
        if not r.get("the_geom"):
            continue
        pt_m = to_metric(shape(r["the_geom"]).representative_point())
        if bbl not in cd1_bbls:
            if not area_m.contains(pt_m):
                continue
            not_in_pluto.append(bbl)
        idx = [i for i in tree.query(pt_m) if tgeoms_m[i].contains(pt_m)]
        if not idx:
            # waterfront lots whose point falls outside the shoreline-clipped tracts
            i = int(tree.nearest(pt_m))
            if bbl not in cd1_bbls and tgeoms_m[i].distance(pt_m) > MAX_SNAP_M:
                unmatched.append(bbl)
                continue
            snapped.append((bbl, round(tgeoms_m[i].distance(pt_m))))
            idx = [i]
        geoid = tracts[idx[0]]["properties"]["geoid"]
        cat = CATS.get(r.get("material"))
        if cat is None:
            raise ValueError(f"unexpected material {r.get('material')!r} ({bbl})")
        counts[geoid][cat] += 1
        cat_totals[cat] += 1
        rec_types[(cat, r.get("record_ty"))] += 1

    print(f"CD1 lots assigned: {sum(cat_totals.values())}; unmatched: {unmatched}; "
          f"kept by point-in-CD1 (not in MapPLUTO CD=301): {len(not_in_pluto)}")
    print(f"snapped to nearest tract (bbl, m): {snapped}")
    missing_pluto = cd1_bbls - seen
    print(f"MapPLUTO CD=301 lots absent from the inventory: {len(missing_pluto)}")
    print("CD1 totals:", dict(cat_totals))
    for k, v in sorted(rec_types.items()):
        print("  ", k, v)

    feats = []
    for t in tracts:
        p = t["properties"]
        c = counts[p["geoid"]]
        total = c["lead"] + c["galvanized_requiring_replacement"] + c["unknown"] + c["non_lead"]
        props = {
            "geoid": p["geoid"],
            "tract_label": p["tract_label"],
            "nta_name": p["nta_name"],
            "total_lines": total,
            "lead": c["lead"],
            "galvanized_requiring_replacement": c["galvanized_requiring_replacement"],
            "unknown": c["unknown"],
            "non_lead": c["non_lead"],
            "not_applicable": c["not_applicable"],
            "pct_lead_or_grr": round(100 * (c["lead"] + c["galvanized_requiring_replacement"])
                                     / total, 1) if total else None,
            "pct_unknown": round(100 * c["unknown"] / total, 1) if total else None,
            "small_sample": total < 25,
            "inventory_date": INVENTORY_DATE,
        }
        feats.append({"type": "Feature", "properties": props, "geometry": t["geometry"]})

    meta = {
        "source": "NYC DEP water service line inventory, NYC Open Data jqfp-uff7 "
                  "('Lead Service Line Location Coordinates'; DEP edition DEP25V11_202601), "
                  "aggregated to 2020 census tracts (geometry from data/acs.geojson)",
        "notes": "Counts are tax lots (BBLs) by DEP's last known service-line material; one "
                 "record per BBL, so multiple service lines on one lot count once. total_lines "
                 "excludes 'Non-Applicable' lots (no operational service line), reported "
                 "separately as not_applicable. Percentages use total_lines as denominator. "
                 "small_sample = fewer than 25 lots (percentages unstable).",
        "inventory_date": INVENTORY_DATE,
    }
    write_fc("lead_service_lines.geojson", feats, meta)


if __name__ == "__main__":
    main()
