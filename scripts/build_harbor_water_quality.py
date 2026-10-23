"""Build data/harbor_water_quality.geojson: NYC DEP Harbor Survey Monitoring (HSM) stations in
the waters near Brooklyn Community Districts 1, 2 and 4 (East River off Greenpoint; Newtown
Creek, English Kills, East Branch; the head of the Gowanus Canal), with bacteria and
dissolved-oxygen summaries for the latest complete years.

Source: NYC Open Data "Harbor Water Quality" (5uug-f49n), NYC DEP Marine Sciences Section.

Station positions: the dataset has no station table. Its `lat`/`long` columns hold a position
for each sample (the nominal station position in 2016-2020, a GPS fix in 2021-2022, blank since
late 2022; about a third of the 2021 rows have lat and long swapped). A station's point is the
median of its valid recorded positions since 2016 (swapped pairs are corrected; values outside
the harbor, e.g. "-74"/"41" or 0, are dropped).

Selection: stations sampled since 2021-01-01 whose point is within 1 km of the districts. That
yields E2 (East River) and NC0, NC0A, NC0B, NC1, NC2, NC3 (Newtown Creek and tributaries), plus
GC3, GC4 and GC5 at the head of the Gowanus Canal, 0.5-0.9 km south of CD 2 (GC6 is ~1.3 km
away). NC0A was discontinued in May 2022 and replaced by NC0B ~200 m away. HSM has no current
station in the East River off DUMBO, Brooklyn Heights or Wallabout Bay: the nearest, E1 (off
the Brooklyn Bridge), was last sampled in 2013.

Summaries (per station, over PERIOD_YEARS, or for a discontinued station its last three
calendar years with >= 20 sampling dates):
- fecal coliform / enterococci: geometric mean of all top and bottom results (cells/100 mL).
  Results flagged "<", ">" or "E" (estimated) are used at their reported value.
- DO: each depth's value is the Winkler titration result, else the CTD probe, else the YSI
  probe (DEP's summer YSI-only runs). Mean over all top and bottom values.
- % of DO values below the NYS acute standard for the water's class (6 NYCRR 703.3): Class I
  (East River) 4.0 mg/L "at any time"; Class SD (Newtown Creek and tributaries) and Class SC
  (Gowanus Canal) 3.0 mg/L "at any time". The share below 4.8 mg/L (the SA/SB/SC chronic daily-average standard) is
  given as well, for comparison.
- water_quality_class: period geomean of fecal coliform against the 6 NYCRR 703.4(b) standard
  for Class I, SC and SD waters, "monthly geometric mean, from a minimum of five examinations,
  shall not exceed 200" per 100 mL. As a closer check on the standard's form,
  fecal_months_evaluated / fecal_months_over_200 count the months with >= 5 surface results and
  those whose geometric mean is above 200.
"""
import collections
import math
import statistics

from shapely.geometry import Point

from common import districts, feature, socrata, to_metric, write_fc

DATASET = "5uug-f49n"
PERIOD_YEARS = (2023, 2024, 2025)
ACTIVE_SINCE = "2021-01-01"
MAX_DIST_M = 1000.0

# Waterbody and NYS classification (6 NYCRR Part 890) by station. Waterbody names are assigned
# from the station positions. Newtown Creek is Class SD; DEC proposed reclassifying it to
# Class I on 2026-09-16 (comments due 2026-11-30), which is not yet adopted. The Gowanus Canal
# was reclassified to Class SC effective 2025-10-15 (previously SD above the Gowanus Expressway).
STATIONS = {
    "E2": ("East River (near the mouth of Newtown Creek)", "I"),
    "NC3": ("Newtown Creek", "SD"),
    "NC2": ("Newtown Creek", "SD"),
    "NC1": ("Newtown Creek", "SD"),
    "NC0": ("English Kills (Newtown Creek)", "SD"),
    "NC0A": ("East Branch (Newtown Creek)", "SD"),
    "NC0B": ("East Branch (Newtown Creek)", "SD"),
    "GC3": ("Gowanus Canal", "SC"),
    "GC4": ("Gowanus Canal", "SC"),
    "GC5": ("Gowanus Canal", "SC"),
    "GC6": ("Gowanus Canal", "SC"),  # ~1.3 km from the districts; dropped by MAX_DIST_M
}
DO_STANDARD = {"I": 4.0, "SD": 3.0, "SC": 3.0}  # acute ("at any time") standards
FECAL_STANDARD = 200.0

FIELDS = {
    "fecal": ("top_fecal_coliform_bacteria_cells_100ml", "bottom_fecal_coliform_bacteria_cells_100ml"),
    "entero": ("top_enterococci_bacteria_cells_100ml", "bottom_enterococci_bacteria_cells_100ml"),
}
DO_FIELDS = [  # in order of preference, per depth
    ("winkler_method_top_dissolved_oxygen_mg_l", "winkler_method_bottom_dissolved_oxygen_mg_l"),
    ("ctd_conductivity_temperature_depth_profiler_top_dissolved_oxygen_mg_l",
     "ctd_conductivity_temperature_depth_profiler_bottom_dissolved_oxygen_mg_l"),
    ("top_dissolved_oxygen_ysi_mg_l", "bottom_dissolved_oxygen_ysi_mg_l"),
]


def num(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def position(rows):
    pts = []
    for r in rows:
        if r["sample_date"] < "2016-01-01":
            continue
        a, b = num(r.get("lat")), num(r.get("long"))
        if a is None or b is None:
            continue
        if a < 0 < b:
            a, b = b, a
        if 40.45 < a < 40.95 and -74.3 < b < -73.65:
            pts.append((a, b))
    if not pts:
        return None, 0
    return Point(statistics.median(p[1] for p in pts), statistics.median(p[0] for p in pts)), len(pts)


def geomean(vals):
    vals = [v for v in vals if v is not None and v > 0]
    if not vals:
        return None
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def summarize(rows):
    fecal, entero, do = [], [], []
    for r in rows:
        for f in FIELDS["fecal"]:
            fecal.append(num(r.get(f)))
        for f in FIELDS["entero"]:
            entero.append(num(r.get(f)))
        for depth in (0, 1):
            for pair in DO_FIELDS:
                v = num(r.get(pair[depth]))
                if v is not None:
                    do.append(v)
                    break
    fecal = [v for v in fecal if v is not None]
    entero = [v for v in entero if v is not None]
    return fecal, entero, do


def monthly_fecal(rows):
    """Months with >= 5 surface (top) fecal coliform results, and how many of them have a
    geometric mean above 200 -- the form of the 703.4(b) standard."""
    by_month = collections.defaultdict(list)
    for r in rows:
        v = num(r.get(FIELDS["fecal"][0]))
        if v is not None:
            by_month[r["sample_date"][:7]].append(v)
    months = [geomean(v) for v in by_month.values() if len(v) >= 5]
    return len(months), sum(g > FECAL_STANDARD for g in months if g is not None)


def main():
    where = f"sampling_location in ({','.join(repr(s) for s in STATIONS)}) and sample_date >= '2016-01-01'"
    rows = socrata("data.cityofnewyork.us", DATASET, where=where)
    by_station = collections.defaultdict(list)
    for r in rows:
        if r.get("sampling_location"):
            by_station[r["sampling_location"]].append(r)
    last_year = max(int(r["sample_date"][:4]) for r in rows if r["sample_date"][5:7] == "12")
    assert last_year >= PERIOD_YEARS[-1], last_year

    districts_m = to_metric(districts())
    feats = []
    for st, (waterbody, wclass) in STATIONS.items():
        srows = by_station.get(st, [])
        if not srows or max(r["sample_date"] for r in srows) < ACTIVE_SINCE:
            continue
        pt, npos = position(srows)
        dist = districts_m.distance(to_metric(pt))
        if dist > MAX_DIST_M:
            continue
        dates_by_year = collections.Counter(int(r["sample_date"][:4]) for r in srows)
        years = [y for y in PERIOD_YEARS if dates_by_year[y] >= 20]
        active = len(years) == len(PERIOD_YEARS)
        if not active:
            years = sorted(y for y, n in dates_by_year.items() if n >= 20 and y <= last_year)[-3:]
        prows = [r for r in srows if int(r["sample_date"][:4]) in years]
        fecal, entero, do = summarize(prows)
        fgm, egm = geomean(fecal), geomean(entero)
        n_months, n_months_over = monthly_fecal(prows)
        std = DO_STANDARD[wclass]
        if fgm is None:
            wq = None
        elif fgm <= FECAL_STANDARD:
            wq = "Meets NYS fecal coliform standard (geomean ≤200 per 100 mL)"
        else:
            wq = "Exceeds NYS fecal coliform standard (geomean >200 per 100 mL)"
        props = {
            "station": st,
            "waterbody": waterbody,
            "latest_sample_date": max(r["sample_date"] for r in srows)[:10],
            "period": (f"{years[0]}–{years[-1]}" if years == list(range(years[0], years[-1] + 1))
                       else ", ".join(str(y) for y in years)),
            "n_samples": len(prows),
            "fecal_coliform_geomean": round(fgm) if fgm is not None else None,
            "enterococci_geomean": round(egm) if egm is not None else None,
            "do_mean_mg_l": round(statistics.mean(do), 2) if do else None,
            "pct_do_below_standard": round(100 * sum(v < std for v in do) / len(do), 1) if do else None,
            "water_quality_class": wq,
            "source": f"NYC DEP Harbor Survey Monitoring, NYC Open Data {DATASET}",
            "water_class": wclass,
            "do_standard_mg_l": std,
            "do_standard": (f"NYS Class {wclass}: DO not less than {std} mg/L at any time (6 NYCRR 703.3)"),
            "pct_do_below_4_8": round(100 * sum(v < 4.8 for v in do) / len(do), 1) if do else None,
            "fecal_months_evaluated": n_months,
            "fecal_months_over_200": n_months_over,
            "n_fecal_results": len(fecal),
            "n_enterococci_results": len(entero),
            "n_do_results": len(do),
            "active": active,
            "position_basis": f"median of {npos} recorded sample positions since 2016",
        }
        if not active:
            if st == "NC0A":
                props["note"] = "Discontinued after 2022-05; replaced by NC0B"
            else:
                thin = [y for y in PERIOD_YEARS if dates_by_year[y] < 20]
                note = (f"Sampled on fewer than 20 dates in {', '.join(map(str, thin))}, so the summaries "
                        f"use {props['period']}, the latest years with at least 20 sampling dates")
                last_fecal = max((r["sample_date"][:10] for r in srows
                                  if any(num(r.get(f)) is not None for f in FIELDS["fecal"])), default=None)
                if last_fecal and last_fecal[:4] < str(years[-1]):
                    note += f". Last fecal coliform result: {last_fecal}"
                props["note"] = note
        feats.append(feature(pt, props))
        print(st, props["period"], props["n_samples"], fgm and round(fgm), egm and round(egm),
              props["do_mean_mg_l"], props["pct_do_below_standard"], props["pct_do_below_4_8"],
              f"{n_months_over}/{n_months} months >200", round(dist))
    write_fc("harbor_water_quality.geojson", feats)


if __name__ == "__main__":
    main()
