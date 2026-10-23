"""Build data/cancer_mapping.geojson: observed and expected cancer counts, 2011-2015,
for the census block groups (2010 vintage) that make up the study area
(Brooklyn Community Districts 1, 2 and 4).

Source: NYS DOH / NYS Cancer Registry, "Cancer Mapping Data: 2011-2015"
(health.data.ny.gov dataset y4pv-ib8r, a zip "blob" published 2018-08-17). This is
the data behind DOH's Environmental Facilities and Cancer Map. The healthdata.gov
catalog entry ybxz-mnf5 ("updated 2025-04-08") is only a harvested link back to
y4pv-ib8r, not a newer release.

The zip holds an .xlsx data table (one row per DOH region = 2010 block group, or a
"DOH" merger of block groups) and a geoid10 -> DOH region crosswalk. It has no
geometry, so polygons come from TIGER/Line 2010 block groups for Kings County,
dissolved per DOH region and clipped to the boundary of the three districts.

Significance (`<key>_sig`) is DOH's own `highlight_<site>` flag: whether the block
group lies inside a "highlighted area" found by DOH's spatial scan statistic
(1 = higher, -1 = lower, 0 = not in a highlighted area). DOH publishes no flag for
total cancers or "other" cancers, and its scan method cannot be reproduced exactly
from the published table, so those are null.
"""
import io
import zipfile

import shapefile  # pyshp

from common import DISTRICTS, districts, feature, fetch, shape, simplify, to_metric, unary_union, write_fc, xlsx_dicts

ZIP_URL = ("https://health.data.ny.gov/api/views/y4pv-ib8r/files/"
           "313b3230-e2b0-4ee9-9063-dc30c6c04264?download=true"
           "&filename=NYSDOH_CancerMapping_Data_2011_2015.zip")
DATA_XLSX = "NYSDOH_CancerMapping_Data_2011_2015.xlsx"
XWALK_XLSX = "NYSDOH_CancerMapping_Crosswalk_2011_2015.xlsx"
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2010/BG/2010/tl_2010_36047_bg10.zip"
COUNTY = "36047"            # Kings
MIN_SHARE = 0.5             # keep regions with more than half their land area in the districts

# key -> (DOH column suffix, DOH label from the data dictionary, ICD-O-3 codes)
SITES = {
    "all": ("Total", "All cancers combined (the 23 sites plus all other reportable cancers)", "all"),
    "bladder": ("Bladder", "Urinary bladder, including in situ", "C67, behavior 2 and 3"),
    "bone": ("Bone", "Bones and joints", "C40-C41"),
    "brain": ("Brain", "Brain and other nervous system", "C70-C72"),
    "breast": ("Breast", "Female breast", "C50"),
    "colorectal": ("Colorectal", "Colon and rectum", "C18-C20, C26.0"),
    "esophagus": ("Esophagus", "Esophagus", "C15"),
    "kidney": ("Kidney", "Kidney and renal pelvis", "C64, C65"),
    "larynx": ("Larynx", "Larynx", "C32"),
    "leukemia": ("Leukemias", "Leukemia", "morphologies 9733, 9742, 9800-9949, 9963, 9964"),
    "liver": ("Liver", "Liver and intrahepatic bile duct", "C22"),
    "lung": ("Lung", "Lung and bronchus", "C34"),
    "mesothelioma": ("Mesothelioma", "Mesothelioma", "morphologies 9050-9055"),
    "nasal": ("Nasal", "Nasal cavity and nasopharynx (nasopharynx, nose, nasal cavity and middle ear)",
              "C11, C30, C31"),
    "nhl": ("NHL", "Non-Hodgkin lymphoma", "selected morphologies 9590-9729, 9823, 9827"),
    "oral": ("Oral", "Oral cavity and pharynx, excluding nasopharynx", "C00-C10, C12-C14"),
    "other": ("Other", "Other cancers not specifically listed", "C00-C80 excluding the sites listed"),
    "ovary": ("Ovary", "Ovary", "C56"),
    "pancreas": ("Pancreas", "Pancreas", "C25"),
    "prostate": ("Prostate", "Prostate", "C61"),
    "soft_tissue": ("Soft_Tissue", "Soft tissue", "C38.0, C47, C49"),
    "stomach": ("Stomach", "Stomach", "C16"),
    "testis": ("Testis", "Testis", "C62"),
    "thyroid": ("Thyroid", "Thyroid", "C73"),
    "uterus": ("Uterus", "Corpus uterus, including uterus NOS", "C54, C55"),
}
SIG = {1: "higher", -1: "lower", 0: "not significant"}

def main():
    area = districts()

    z = zipfile.ZipFile(io.BytesIO(fetch(ZIP_URL, binary=True)))
    data = {str(r["Dohregion"]): r for r in xlsx_dicts(z.read(DATA_XLSX))
            if str(r["Dohregion"]).startswith(COUNTY)}
    members = {}
    for r in xlsx_dicts(z.read(XWALK_XLSX)):
        g = str(r["geoid10"])
        if g.startswith(COUNTY):
            members.setdefault(str(r["dohregion"]), []).append(g)

    t = zipfile.ZipFile(io.BytesIO(fetch(TIGER_URL, binary=True)))
    names = {n.rsplit(".", 1)[1].lower(): n for n in t.namelist()}
    sr = shapefile.Reader(shp=io.BytesIO(t.read(names["shp"])),
                          shx=io.BytesIO(t.read(names["shx"])),
                          dbf=io.BytesIO(t.read(names["dbf"])))
    fields = [f[0] for f in sr.fields[1:]]
    bgs = {}
    for s in sr.iterShapeRecords():
        rec = dict(zip(fields, s.record))
        # NAD83 geographic ~= WGS84 at this scale
        bgs[rec["GEOID10"]] = (shape(s.shape.__geo_interface__).buffer(0), rec["ALAND10"])

    feats = []
    near = []
    for region, geoids in sorted(members.items()):
        geom = unary_union([bgs[g][0] for g in geoids])
        if not geom.intersects(area):
            continue
        aland = sum(bgs[g][1] for g in geoids)
        inside = geom.intersection(area)
        share = to_metric(inside).area / aland if aland else 0.0
        if share > 0.02:
            near.append((region, round(share, 3)))
        if share <= MIN_SHARE:
            continue
        row = data[region]
        props = {
            "geoid": region,
            "total_population": row["total_pop"],
        }
        if "DOH" in region:
            props["merged_geoid10"] = sorted(geoids)
        for key, (col, _label, _codes) in SITES.items():
            obs = row[f"observed_{col}"]
            exp = row[f"expected_{col}"]
            hl = row.get(f"highlight_{col}")
            props[f"{key}_obs"] = obs
            props[f"{key}_exp"] = round(exp, 2)
            props[f"{key}_ratio"] = round(obs / exp, 2) if exp else None
            props[f"{key}_sig"] = SIG[hl] if hl is not None else None
        props["share_in_area"] = round(min(share, 1.0), 3)
        feats.append(feature(simplify(inside, 1.5), props))

    print("regions touching the districts (share of land area inside):")
    for region, share in sorted(near, key=lambda x: x[1]):
        if share < 0.98:
            print(f"  {region} {share}{'  kept' if share > MIN_SHARE else ''}")

    meta = {
        "title": "Cancer incidence by census block group, 2011-2015 (NYS DOH Cancer Mapping)",
        "source": "NYS Department of Health, New York State Cancer Registry, 'Cancer Mapping Data: "
                  "2011-2015', health.data.ny.gov dataset y4pv-ib8r (published 2018-08-17; cancer data "
                  "provisional as of December 2017)",
        "years": "2011-2015",
        "geography": "2010 census block groups; some merged by DOH (geoid contains 'DOH', members "
                     "in merged_geoid10). Geometry: TIGER/Line 2010 block groups, clipped to "
                     "Brooklyn Community Districts 1, 2 and 4.",
        "selection": f"DOH regions with more than {int(MIN_SHARE * 100)}% of their land area (ALAND10) "
                     "inside Brooklyn Community Districts 1, 2 and 4 "
                     f"(BoroCD {', '.join(map(str, DISTRICTS))})",
        "suppression": "No values are suppressed. To protect confidentiality DOH merged neighbouring "
                       "block groups until each area had at least 6 male and 6 female cancer cases in "
                       "total (12 cases if all one sex, e.g. prisons).",
        "fields": {
            "total_population": "DOH total_pop: average population 2011-2015 estimated from the 2010 "
                                "census by iterative proportional fitting to county estimates",
            "obs": "observed newly diagnosed cases, 2011-2015 (all primaries counted)",
            "exp": "expected cases if New York State age- and sex-specific rates applied to the area's "
                   "population (rounded to 2 decimals)",
            "ratio": "observed / expected (2 decimals); null if expected is 0",
            "sig": "DOH highlight flag: 'higher' / 'lower' = block group lies in a DOH highlighted "
                   "area (spatial scan statistic, >=50% excess or deficit, unlikely to be chance) "
                   "for that cancer; 'not significant' = not in a highlighted area. It describes "
                   "the whole multi-block-group area, not this block group alone. Null where DOH "
                   "publishes no flag (all, other).",
        },
        "cancers": {k: v[1] for k, v in SITES.items()},
        "icd_o_3": {k: v[2] for k, v in SITES.items()},
    }
    write_fc("cancer_mapping.geojson", feats, meta)


if __name__ == "__main__":
    main()
