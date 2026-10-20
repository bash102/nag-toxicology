"""Build data/polluted_polygons.geojson: remediation / brownfield / Superfund site footprints
in CD1 (+200 m buffer).

Sources
1. NYS DEC "Remediation Boundaries" (Remediation_Sites_Group_new FeatureServer layer 2,
   NYSDEC ArcGIS Online, the polygons behind DECinfo Locator) -- State Superfund,
   Brownfield Cleanup, Voluntary Cleanup, Petroleum Remediation and RCRA sites.
   Attributes enriched from data.ny.gov "Environmental Remediation Sites" (c6ci-rzpg):
   current site class, contaminants, owner, institutional/engineering controls.
2. U.S. EPA "National NPL Superfund Site Boundaries (Public)" -- Newtown Creek and
   Meeker Avenue Plume.
3. NYC Office of Environmental Remediation (OER) "OER Cleanup Sites" (NYC Open Data
   3279-pp7v): sites enrolled in the NYC Voluntary Cleanup Program (VCP) in Brooklyn CD1.
   OER publishes points + BBLs only, so the footprint is the union of the site's tax lots
   from NYC DCP MapPLUTO.
"""
import collections
import re

from common import DCP, arcgis_query, feature, shape, simplify, socrata, study_area, unary_union, write_fc

DEC_POLYS = ("https://services6.arcgis.com/DZHaqZm9cxOD4CWM/arcgis/rest/services/"
             "Remediation_Sites_Group_new/FeatureServer/2")
EPA_NPL = ("https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/"
           "FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0")
MAPPLUTO = DCP + "/MAPPLUTO/FeatureServer/0"

SITE_CLASS = {
    "01": "Class 1 - causing or presenting an imminent danger",
    "02": "Class 2 - significant threat to public health or the environment; action required",
    "03": "Class 3 - does not present a significant threat",
    "04": "Class 4 - remediation complete, site management required",
    "05": "Class 5 - no further action",
    "A": "Active",
    "C": "Completed",
    "N": "No further action at this time",
    "P": "Potential site; investigation underway",
    "PR": "Potential RCRA site",
}
DEC_PROGRAM = {
    "HW": "NYS State Superfund Program",
    "BCP": "NYS Brownfield Cleanup Program",
    "VCP": "NYS Voluntary Cleanup Program",
    "ERP": "NYS Environmental Restoration Program",
    "RCRA": "RCRA Corrective Action",
}


def dec_details(codes):
    """Aggregate the many-rows-per-site data.ny.gov table into one dict per site."""
    out = collections.defaultdict(lambda: collections.defaultdict(set))
    codes = sorted(codes)
    for i in range(0, len(codes), 100):
        chunk = ",".join(f"'{c}'" for c in codes[i:i + 100])
        for r in socrata("data.ny.gov", "c6ci-rzpg", where=f"program_number in ({chunk})"):
            d = out[r["program_number"]]
            for k in ("siteclass", "contaminants", "owner_name", "control_code", "address1", "program_type"):
                if r.get(k):
                    d[k].add(r[k].strip())
    return out


def clean(s):
    """Tidy source strings (one DEC name contains a U+FFFD replacement character for a dash)."""
    return re.sub(r"\s+", " ", (s or "").replace("\ufffd", "-")).strip()


def joined(s, limit=12):
    s = sorted(x for x in s if x and x.upper() != "UNKNOWN")
    return ", ".join(s[:limit]) + (f" (+{len(s) - limit} more)" if len(s) > limit else "")


def main():
    area = study_area()
    feats = []

    # 1. NYS DEC remediation boundaries
    dec = [f for f in arcgis_query(DEC_POLYS, geometry=area) if shape(f["geometry"]).intersects(area)]
    details = dec_details({f["properties"]["SITECODE"].strip() for f in dec})
    by_code = collections.defaultdict(list)
    for f in dec:
        by_code[f["properties"]["SITECODE"].strip()].append(f)
    for code, fs in sorted(by_code.items()):
        p = fs[0]["properties"]
        d = details.get(code, {})
        cls = (sorted(d["siteclass"])[0] if d.get("siteclass") else (p["SITECLASS"] or "").strip())
        prog = (p["PROGRAM"] or "").strip()
        if d.get("program_type"):
            prog = DEC_PROGRAM.get(sorted(d["program_type"])[0], prog)
        desc = [f"Site class: {SITE_CLASS.get(cls, cls)}"]
        if d.get("contaminants"):
            desc.append("Contaminants: " + joined(d["contaminants"]))
        if d.get("control_code"):
            desc.append("Controls: " + joined(d["control_code"]))
        g = unary_union([shape(f["geometry"]).buffer(0) for f in fs])
        addr = ", ".join(x.strip() for x in (p.get("ADDRESS1"), p.get("LOCALITY")) if x and x.strip())
        feats.append(feature(simplify(g, 1.0), {
            "site_or_owner_name": clean(p["SITENAME"]),
            "address": addr,
            "program": prog,
            "description": ". ".join(desc),
            "reference_number": code,
            "link": f"https://extapps.dec.ny.gov/cfmx/extapps/derexternal/haz/details.cfm?ProgNo={code}",
            "site_class": cls,
            "owner_name": joined(d.get("owner_name", set()), 3) or None,
            "agency": "NYS DEC",
            "source": "NYS DEC Remediation Boundaries; data.ny.gov c6ci-rzpg",
        }))

    # 2. EPA Superfund (NPL) site boundaries
    for f in arcgis_query(EPA_NPL, geometry=area):
        p = f["properties"]
        g = shape(f["geometry"]).buffer(0)
        if not g.intersects(area):
            continue
        status = {"F": "Final NPL", "P": "Proposed NPL", "D": "Deleted from NPL", "N": "Not on NPL"}
        url = p.get("URL_ALIAS_TXT") or ""
        feats.append(feature(simplify(g, 1.5), {
            "site_or_owner_name": p["SITE_NAME"].title(),
            "address": ", ".join(x.strip().title() for x in (p.get("STREET_ADDR_TXT"), p.get("CITY_NAME")) if x and x.strip()),
            "program": "U.S. EPA Superfund (" + status.get(p.get("NPL_STATUS_CODE"), p.get("NPL_STATUS_CODE") or "") + ")",
            "description": (p.get("SITE_FEATURE_NAME") or "Site boundary")
                           + (" - " + p["SITE_FEATURE_DESCRIPTION"] if p.get("SITE_FEATURE_DESCRIPTION") else "")
                           + ". Footprint is EPA's published site boundary, not a measured plume extent.",
            "reference_number": p["EPA_ID"],
            "link": ("https://" + url) if url and not url.startswith("http") else url,
            "agency": "U.S. EPA",
            "source": "EPA National NPL Superfund Site Boundaries (Public)",
        }))

    # 3. NYC OER Voluntary Cleanup Program sites -> MapPLUTO lot footprints
    oer = socrata("data.cityofnewyork.us", "3279-pp7v",
                  where="borough='Brooklyn' and community_district='1' and oer_program like '%VCP (Enrolled)%'")
    bbls = sorted({b.strip() for r in oer for b in (r.get("bbl") or "").split(",") if b.strip()})
    lots = {}
    for i in range(0, len(bbls), 80):
        chunk = ",".join(bbls[i:i + 80])
        for f in arcgis_query(MAPPLUTO, where=f"BBL in ({chunk})", out_fields="BBL,Address,OwnerName"):
            lots[str(int(float(f["properties"]["BBL"])))] = shape(f["geometry"]).buffer(0)
    missing = 0
    for r in oer:
        geoms = [lots[b.strip()] for b in (r.get("bbl") or "").split(",") if b.strip() in lots]
        if not geoms:
            missing += 1
            continue
        g = unary_union(geoms)
        if not g.intersects(area):
            continue
        link = (r.get("project_specific_document") or {}).get("url", "")
        feats.append(feature(simplify(g, 1.0), {
            "site_or_owner_name": clean(r.get("project_name")),
            "address": f"{r.get('street_number', '')} {r.get('street_name', '')}, Brooklyn".strip(),
            "program": "NYC Voluntary Cleanup Program (NYC OER)",
            "description": f"OER program(s): {r.get('oer_program')}. Status: {r.get('class', '')} / phase: {r.get('phase', '')}. "
                           "Footprint = MapPLUTO tax lot(s) listed for the project.",
            "reference_number": r.get("oer_project_numbers", ""),
            "link": link,
            "agency": "NYC OER",
            "source": "NYC Open Data 3279-pp7v (OER Cleanup Sites) + NYC DCP MapPLUTO",
        }))
    if missing:
        print(f"OER sites with no MapPLUTO lot match (skipped): {missing}")

    write_fc("polluted_polygons.geojson", feats)
    print(collections.Counter(f["properties"]["agency"] for f in feats))


if __name__ == "__main__":
    main()
