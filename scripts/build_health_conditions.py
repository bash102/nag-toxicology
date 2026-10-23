"""Build data/health_conditions.geojson: CDC PLACES census-tract estimates of
adult chronic-disease prevalence for the 123 census tracts of the study area
(Brooklyn Community Districts 1, 2 and 4).

Source: CDC PLACES "Local Data for Better Health, Census Tract Data, 2025 release"
(data.cdc.gov Socrata dataset cwsq-ngmh). The 2025 release uses 2020 census tracts,
so it joins directly on GEOID to data/acs.geojson; tract geometry is reused from there.

Values are model-based small-area estimates (crude prevalence, % of adults 18+),
not counts. BRFSS 2023 is the data year for all eight measures used here.
"""
import json
import os

from common import DATA_DIR, socrata, write_fc

DATASET = "cwsq-ngmh"
RELEASE = "PLACES 2025 release"
MEASURES = ["CASTHMA", "COPD", "CANCER", "CHD", "DIABETES", "MHLTH", "BPHIGH", "CSMOKING"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    with open(os.path.join(DATA_DIR, "acs.geojson")) as f:
        acs = json.load(f)
    tracts = acs["features"]
    geoids = [t["properties"]["geoid"] for t in tracts]
    assert len(geoids) == 123, len(geoids)

    ids = ",".join(f"'{g}'" for g in geoids)
    ms = ",".join(f"'{m}'" for m in MEASURES)
    rows = socrata("data.cdc.gov", DATASET,
                   where=f"locationid in ({ids}) and measureid in ({ms}) "
                         f"and datavaluetypeid='CrdPrv'")
    data = {}
    names = {}
    for r in rows:
        key = (r["locationid"], r["measureid"])
        assert key not in data, key
        data[key] = r
        names[r["measureid"]] = r.get("measure")

    feats = []
    missing = []
    for t in tracts:
        p = t["properties"]
        g = p["geoid"]
        nopop = bool(p.get("no_population"))
        props = {"geoid": g, "tract_label": p["tract_label"], "nta_name": p["nta_name"]}
        years = {}
        pop = None
        for m in MEASURES:
            r = data.get((g, m))
            val = None
            if r is not None and not nopop:
                val = num(r.get("data_value"))
                if val is not None:
                    val = round(val, 1)
                years[m.lower()] = r.get("year")
                pop = int(r["totalpopulation"]) if r.get("totalpopulation") else pop
            elif r is None:
                years[m.lower()] = None
            props[m.lower()] = val
            if val is None:
                missing.append((g, m))
        props["year"] = years
        props["total_population"] = pop if not nopop else 0
        props["no_population"] = nopop
        props["places_release"] = RELEASE
        feats.append({"type": "Feature", "properties": props, "geometry": t["geometry"]})

    print(f"{len(rows)} PLACES rows; null values: {len(missing)} "
          f"({sorted(set(g for g, _ in missing))})")
    for m in MEASURES:
        vals = sorted(f["properties"][m.lower()] for f in feats
                      if f["properties"][m.lower()] is not None)
        print(f"  {m:9s} n={len(vals)} min={vals[0]} max={vals[-1]}")

    meta = {
        "source": "CDC PLACES: Local Data for Better Health, Census Tract Data, 2025 release "
                  "(data.cdc.gov cwsq-ngmh); geometry from data/acs.geojson (2020 tracts)",
        "notes": "Model-based small-area estimates (BRFSS 2023 + Census 2020 + ACS 2019-2023), "
                 "crude prevalence in % of adults 18+; not counts. total_population = Census 2020 "
                 "count as published by PLACES. Tracts with no population have nulls.",
        "measures": {m.lower(): names.get(m) for m in MEASURES},
    }
    write_fc("health_conditions.geojson", feats, meta)


if __name__ == "__main__":
    main()
