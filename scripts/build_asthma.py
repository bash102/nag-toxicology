"""Build data/asthma.geojson: asthma emergency-department visit rates for the
NYS Environmental Public Health Tracking (EPHT) sub-county areas covering the study area
(common.DISTRICTS).

Source: NYS DOH, "Sub-County Data for Selected Health Outcomes in New York State,
2008-2012, 2013-2017" (health.data.ny.gov dataset vtby-z2yc; SPARCS data), and the
dataset's attached sub-county boundary shapefile EPHT7p5k_2010_NYS.zip. In NYC the
sub-county areas are 2010 Neighborhood Tabulation Areas (NTAs).

Rates are published per 10,000 (annual average); we divide by 10 to get per 1,000.
Polygons are clipped to the boundary of the three districts.
"""
import io
import zipfile

import shapefile  # pyshp

from common import districts, feature, fetch, shape, simplify, socrata, to_metric, write_fc

DATASET = "vtby-z2yc"
SHP_URL = ("https://health.data.ny.gov/api/views/vtby-z2yc/files/"
           "526acd4b-20f3-4ead-903d-d3194ddb2172?download=true&filename=EPHT7p5k_2010_NYS.zip")
PERIOD = "2013-2017"          # most recent period in the dataset
MIN_AREA_M2 = 20000           # drop slivers of neighbouring NTAs (< 2 ha inside the districts)


def main():
    area = districts()
    area_m = to_metric(area)

    z = zipfile.ZipFile(io.BytesIO(fetch(SHP_URL, binary=True)))
    names = {n.rsplit(".", 1)[1].lower(): n for n in z.namelist()}
    r = shapefile.Reader(shp=io.BytesIO(z.read(names["shp"])),
                         shx=io.BytesIO(z.read(names["shx"])),
                         dbf=io.BytesIO(z.read(names["dbf"])))
    fields = [f[0] for f in r.fields[1:]]

    polys = {}
    for sr in r.iterShapeRecords():
        rec = dict(zip(fields, sr.record))
        if not rec["epht7p5kid"].startswith("N047"):  # Brooklyn NTAs
            continue
        g = shape(sr.shape.__geo_interface__).buffer(0)  # NAD83 geographic ~= WGS84 at this scale
        if not g.intersects(area):
            continue
        clip = g.intersection(area)
        if to_metric(clip).area < MIN_AREA_M2:
            continue
        polys[rec["epht7p5kid"]] = (clip, rec)

    ids = ",".join(f"'{i}'" for i in polys)
    rows = socrata("health.data.ny.gov", DATASET, where=f"epht_id in ({ids}) and content='Asthma'")
    rates = {}
    for row in rows:
        rates[(row["epht_id"], row["years"], row["indicator"], row["rate_type"])] = row

    def rate(eid, years, ind, rt):
        row = rates.get((eid, years, ind, rt))
        if not row:
            return None
        try:
            return round(float(row["rate"]) / 10.0, 2)
        except ValueError:
            return None

    feats = []
    for eid, (g, rec) in sorted(polys.items()):
        props = {
            "geography_name": f"{rec['epht_mcds']} (NTA)",
            "epht_id": eid,
            "asthma_rate_per_1000_people": rate(eid, PERIOD, "ED Visits", "crude"),
            "measure": "Asthma emergency department visits per 1,000 residents per year "
                       "(crude rate, annual average)",
            "period": PERIOD.replace("-", "–"),
            "asthma_ed_age_adjusted_per_1000": rate(eid, PERIOD, "ED Visits", "age-adjusted"),
            "asthma_hosp_crude_per_1000": rate(eid, PERIOD, "Hospitalizations", "crude"),
            "asthma_ed_crude_per_1000_2008_2012": rate(eid, "2008-2012", "ED Visits", "crude"),
            "share_of_study_area": round(to_metric(g).area / area_m.area, 3),
            "source": "NYS DOH Environmental Public Health Tracking / SPARCS (health.data.ny.gov vtby-z2yc)",
        }
        feats.append(feature(simplify(g, 1.5), props))
        print(eid, rec["epht_mcds"], props["asthma_rate_per_1000_people"])

    write_fc("asthma.geojson", feats)


if __name__ == "__main__":
    main()
