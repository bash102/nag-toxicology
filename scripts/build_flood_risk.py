"""Build data/flood_risk.geojson: 2050s future coastal-surge floodplains clipped to CD1 + 200 m.

Source: NYC Mayor's Office of Climate & Environmental Justice (MOCEJ) EJNYC Mapper layers
"Coastal Storm Surge Flooding: 2050s 1% Annual Chance Storm" (100-year) and
"Coastal Storm Surge Flooding: 2050s 0.2% Annual Chance Storm" (500-year), hosted feature
services in NYC's ArcGIS Online org (tagged 'dcp').

NYC Open Data still publishes the 2013 OLTPS/NPCC "Future Floodplain 2050s" (27ya-gqtm,
100-year only) but the matching 2050s 500-year layer is no longer on the portal, so the
current MOCEJ pair is used for both storms for consistency.
"""
from common import arcgis_query, feature, shape, simplify, study_area, to_metric, to_wgs84, unary_union, write_fc

BASE = "https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services"
LAYERS = {
    "100": (BASE + "/dcp_staging_hosted_feature/FeatureServer/0",
            "Coastal Storm Surge Flooding: 2050s 1% Annual Chance Storm (100-year floodplain)"),
    "500": (BASE + "/FP_500yr_2050s_staged/FeatureServer/0",
            "Coastal Storm Surge Flooding: 2050s 0.2% Annual Chance Storm (500-year floodplain)"),
}


def main():
    area = study_area()
    feats = []
    for storm, (url, title) in LAYERS.items():
        gs = [shape(f["geometry"]).buffer(0) for f in arcgis_query(url, geometry=area) if f.get("geometry")]
        g = unary_union(gs).intersection(area)
        # drop tiny specks (< 25 m2) left over from rasterised floodplain edges
        gm = to_metric(g)
        parts = [p for p in getattr(gm, "geoms", [gm]) if p.area >= 25]
        g = simplify(to_wgs84(unary_union(parts)), 1.5)
        feats.append(feature(g, {
            "storm": storm,
            "period": "2050s",
            "description": title,
            "area_acres": round(to_metric(g).area / 4046.856, 1),
            "source": "NYC MOCEJ EJNYC Mapper / NYC DCP, " + url.rsplit("/FeatureServer", 1)[0].rsplit("/", 1)[1],
        }))
    # draw the 500-year (larger) polygon first so the 100-year sits on top
    feats.sort(key=lambda f: f["properties"]["storm"], reverse=True)
    write_fc("flood_risk.geojson", feats)


if __name__ == "__main__":
    main()
