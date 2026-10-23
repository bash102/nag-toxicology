"""Build data/acs.geojson: ACS 2020-2024 5-year estimates for census tracts covering the study area
(common.DISTRICTS).

Sources
- Tract polygons: NYC DCP "2020 Census Tracts" (clipped to shoreline), ArcGIS
  FeatureServer NYC_Census_Tracts_for_2020_US_Census.
- ACS 2020-2024 5-year table-based Summary File (www2.census.gov), tables
  B03002 (Hispanic or Latino origin by race; B03002_001 = total population)
  and B19013 (median household income, 2024 inflation-adjusted dollars).
- Land area: 2024 Census Gazetteer tract file for New York (ALAND_SQMI).
"""
import csv
import io

from common import DCP, arcgis_query, districts, feature, fetch, shape, simplify, study_area, to_metric, write_fc

YEAR = 2024
SF = f"https://www2.census.gov/programs-surveys/acs/summary_file/{YEAR}/table-based-SF/data/5YRData"
GAZ = f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{YEAR}_Gazetteer/{YEAR}_gaz_tracts_36.txt"
TRACTS = DCP + "/NYC_Census_Tracts_for_2020_US_Census/FeatureServer/0"
MIN_SHARE = 0.25  # keep tracts with >= 25% of their (land) area inside the study area


def read_sf_table(table, geoids):
    txt = fetch(f"{SF}/acsdt5y{YEAR}-{table}.dat")
    out = {}
    rdr = csv.reader(io.StringIO(txt), delimiter="|")
    header = next(rdr)
    for row in rdr:
        g = row[0]
        if g.startswith("1400000US") and g[9:] in geoids:
            out[g[9:]] = dict(zip(header, row))
    return out


def num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    # Summary file uses large negative sentinel values for N/A / suppressed estimates
    return None if x < 0 else x


def main():
    area = districts()
    area_m = to_metric(area)
    tracts = arcgis_query(TRACTS, where="BoroCode='3'", geometry=study_area())
    keep = {}
    for f in tracts:
        g = shape(f["geometry"]).buffer(0)
        gm = to_metric(g)
        share = gm.intersection(area_m).area / gm.area if gm.area else 0
        if share >= MIN_SHARE:
            keep[f["properties"]["GEOID"]] = (g, f["properties"], share)
    geoids = set(keep)

    gaz = {}
    for row in csv.DictReader(io.StringIO(fetch(GAZ)), delimiter="\t"):
        row = {k.strip(): v.strip() for k, v in row.items()}
        if row["GEOID"] in geoids:
            gaz[row["GEOID"]] = float(row["ALAND_SQMI"])

    b03002 = read_sf_table("b03002", geoids)
    b19013 = read_sf_table("b19013", geoids)

    feats = []
    for gid in sorted(keep):
        g, p, share = keep[gid]
        r = b03002.get(gid)
        if r is None:
            print("no ACS row for", gid)
            continue
        tot = num(r["B03002_E001"])
        nh_white = num(r["B03002_E003"])
        nh_black = num(r["B03002_E004"])
        nh_asian = num(r["B03002_E006"])
        hisp = num(r["B03002_E012"])
        mhi = num(b19013.get(gid, {}).get("B19013_E001"))
        aland = gaz.get(gid)

        def pct(x):
            return round(100.0 * x / tot, 1) if tot else None

        props = {
            "geoid": gid,
            "tract_label": p.get("CTLabel"),
            "nta_name": p.get("NTAName"),
            "total_population": int(tot) if tot is not None else None,
            "land_area_sq_mi": round(aland, 4) if aland else None,
            "people_per_square_mile": round(tot / aland) if (tot and aland) else 0,
            "median_household_income": int(mhi) if mhi is not None else None,
            "percent_hispanic": pct(hisp),
            "percent_nonhispanic_black": pct(nh_black),
            "percent_nonhispanic_asian": pct(nh_asian),
            "percent_nonhispanic_white": pct(nh_white),
            "share_in_area": round(share, 3),
            "no_population": not tot,
            "acs_vintage": f"{YEAR-4}-{YEAR} ACS 5-year",
        }
        if not tot:
            # parks / industrial / water tracts: keep geometry but flag (and blank the percentages)
            print("zero-population tract flagged:", gid, p.get("NTAName"))
        feats.append(feature(simplify(g, 1.0), props))

    write_fc("acs.geojson", feats, meta={
        "source": f"U.S. Census Bureau, American Community Survey {YEAR-4}-{YEAR} 5-year estimates "
                  "(tables B03002, B19013); NYC DCP 2020 census tract boundaries (clipped to shoreline)",
        "notes": "people_per_square_mile = B03002_001 / Census Gazetteer ALAND_SQMI; "
                 "median_household_income in 2024 inflation-adjusted dollars (250001 = $250,000+); "
                 "tracts with no population have no_population=true and null percentages",
    })


if __name__ == "__main__":
    main()
