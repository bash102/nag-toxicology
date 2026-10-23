"""Build data/asthma.geojson: asthma emergency-department visit rates for the 2010
Neighborhood Tabulation Areas (NTAs) covering the study area (common.DISTRICTS), with the
community district's latest yearly rate for context.

Source: NYC DOHMH Environment & Health Data Portal (EHDP) open data,
https://github.com/nychealth/EHDP-data (branch production), SPARCS ED visits:
- NTA rates, 2017-2019 average annual rate per 10,000: indicators 2384 (adults),
  2383 (age 5-17), 2378 (age 4 and under; only 2014-2016 is published).
- Community-district yearly rates: indicators 2380 (adults), 2379 (age 5-17).
EHDP NTA2010 GeoIDs are county FIPS * 100 + the NTA number (BK09 -> 4709); CD GeoIDs are BoroCD.

Geometry: NYC DCP 2010 NTAs, clipped to the boundary of the districts.
"""
import csv
import io
import json

from common import (CD_SERVICE, DCP, DISTRICTS_SQL, arcgis_query, districts, feature, fetch, fetch_json, shape, simplify,
                    to_metric, write_fc)

EHDP = "https://raw.githubusercontent.com/nychealth/EHDP-data/production/"
NTA_SERVICE = DCP + "/NYC_Neighborhood_Tabulation_Areas_2010/FeatureServer/0"
PERIOD = 282                  # "2017-2019", the latest NTA period
MIN_AREA_M2 = 20000           # drop slivers of neighbouring NTAs (< 2 ha inside the districts)
SMALL_SHARE = 0.25            # report NTAs with less than this share of their area inside
# property: (indicator, MeasurementType); NTA rates are crude average annual rates
NTA_MEASURES = {
    "ed_adults_rate": (2384, "Average annual rate"),
    "ed_adults_age_adjusted_rate": (2384, "Average annual age-adjusted rate"),
    "ed_5_17_rate": (2383, "Average annual rate"),
    "ed_0_4_rate": (2378, "Average annual rate"),
}
CD_MEASURES = {               # crude yearly rates, comparable with the NTA crude rates
    "cd_ed_adults_rate": (2380, "Estimated annual rate"),
    "cd_ed_5_17_rate": (2379, "Estimated annual rate"),
}


def main():
    meta = {m["IndicatorID"]: m for m in fetch_json(EHDP + "indicators/metadata/metadata.json")}
    periods = {p["TimePeriodID"]: p for p in
               json.loads(fetch(EHDP + "indicators/metadata/TimePeriods.json", binary=True)
                          .decode("utf-8-sig"))}
    assert periods[PERIOD]["TimePeriod"] == "2017-2019", periods[PERIOD]
    lookup = {(r["GeoType"], int(r["GeoID"])): r["Name"]
              for r in csv.DictReader(io.StringIO(fetch(EHDP + "geography/GeoLookup.csv")))}

    def rows(ind, mtype, geotype):
        """{(GeoID, TimePeriodID): row} for one indicator measure, and the measure."""
        (m,) = [m for m in meta[ind]["Measures"] if m["MeasurementType"] == mtype]
        assert m["DisplayType"] == "per 10,000", m
        d = fetch_json(EHDP + f"indicators/data/{ind}.json")
        out = {(r["GeoID"], r["TimePeriodID"]): r for r in (dict(zip(d, v)) for v in zip(*d.values()))
               if r["MeasureID"] == m["MeasureID"] and r["GeoType"] == geotype}
        return out, m

    area = districts()
    cds = {f["properties"]["BoroCD"]: to_metric(shape(f["geometry"]).buffer(0))
           for f in arcgis_query(CD_SERVICE, where=f"BoroCD IN ({DISTRICTS_SQL})")}
    ntas = {}
    for f in arcgis_query(NTA_SERVICE, where="BoroName='Brooklyn'", geometry=area):
        p = f["properties"]
        g = shape(f["geometry"]).buffer(0)
        clip = g.intersection(area)
        clip_m = to_metric(clip)
        if clip_m.area < MIN_AREA_M2:
            continue
        geoid = int(p["CountyFIPS"]) * 100 + int(p["NTACode"][2:])
        assert lookup[("NTA2010", geoid)] == p["NTAName"], (geoid, p["NTAName"])
        share = clip_m.area / to_metric(g).area
        if share < SMALL_SHARE:
            print(f"small overlap: {p['NTACode']} {p['NTAName']}: {clip_m.area / 1e4:.1f} ha, "
                  f"{share:.0%} of the NTA")
        cd = max(cds, key=lambda c: cds[c].intersection(clip_m).area)
        ntas[geoid] = (clip, p, cd)

    nta_rows = {k: rows(ind, mt, "NTA2010") for k, (ind, mt) in NTA_MEASURES.items()}
    cd_vals = {}
    for k, (ind, mt) in CD_MEASURES.items():
        r, m = rows(ind, mt, "CD")
        latest = max({t for _, t in r}, key=lambda t: periods[t]["end_period"])
        cd_vals[k] = ({cd: r.get((cd, latest)) for cd in cds}, periods[latest]["TimePeriod"])
        print(k, m["MeasureName"], periods[latest]["TimePeriod"],
              {cd: v and v["Value"] for cd, v in cd_vals[k][0].items()})
    assert len({p for _, p in cd_vals.values()}) == 1, cd_vals

    def value(row, notes, label):
        """The row's value, or None if missing or suppressed; flags go into notes."""
        if row is None or row["Value"] is None:
            return None
        if row["Note"]:
            notes.append(f"{label}: {row['Note']}")
        return row["Value"]

    feats = []
    for geoid, (g, p, cd) in sorted(ntas.items(), key=lambda kv: kv[1][1]["NTACode"]):
        notes = []
        props = {"geography_name": p["NTAName"], "nta_code": p["NTACode"]}
        for k, (r, m) in nta_rows.items():
            props[k] = value(r.get((geoid, PERIOD)), notes, k)
        # the age 0-4 rate is published for 2014-2016 only; keep it under its own name
        r, m = nta_rows["ed_0_4_rate"]
        if PERIOD not in m["AvailableTimePeriodIDs"]:
            old = max(m["AvailableTimePeriodIDs"], key=lambda t: periods[t]["end_period"])
            props["ed_0_4_rate_" + periods[old]["TimePeriod"].replace("-", "_")] = \
                value(r.get((geoid, old)), notes, "ed_0_4_rate " + periods[old]["TimePeriod"])
        props.update({
            "rate_units": "ED visits per 10,000 residents of the age group per year",
            "period": periods[PERIOD]["TimePeriod"].replace("-", "–"),
            "community_district": f"Brooklyn CD {cd % 100}",
        })
        if not any(r.get((geoid, t)) for r, m in nta_rows.values()
                   for t in m["AvailableTimePeriodIDs"]):
            notes.append("The portal publishes no rates for this NTA")
        for k, (vals, per) in cd_vals.items():
            props[k] = value(vals[cd], notes, k)
            props["cd_period"] = per
        props["notes"] = "; ".join(notes) or None
        props["source"] = ("NYC DOHMH Environment & Health Data Portal (SPARCS); "
                           "NYC DCP 2010 NTA boundaries")
        feats.append(feature(simplify(g, 1.5), props))
        print(p["NTACode"], p["NTAName"], props["community_district"],
              *(props[k] for k in nta_rows), props["notes"] or "")

    write_fc("asthma.geojson", feats)


if __name__ == "__main__":
    main()
