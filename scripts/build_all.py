"""Rebuild every data layer in ../data. Usage: python3 scripts/build_all.py

Requires: python3, shapely, pyproj, pyshp, plus rasterio and numpy for air quality (all on PyPI). The CSO step also needs the
`pdftotext` command (poppler-utils). Network access to the public
sources listed in data/SOURCES.md. Downloads are cached in $NAG_CACHE
(default ~/.cache/nag-toxicology); delete it to force fresh downloads. The spill
geocoding step (polluted_points) makes several thousand sequential NYC GeoSearch
requests on a cold cache and takes 30-90 minutes.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STEPS = [
    "build_acs",
    "build_asthma",
    "build_flood_risk",
    "build_polluted_polygons",
    "build_waste_transfer_stations",
    "build_air_quality",
    "build_health_conditions",
    "build_lead_service_lines",
    "build_cso_outfalls",
    "build_harbor_water_quality",
    "build_polluted_points",
    "build_cancer_mapping",
]

if __name__ == "__main__":
    only = sys.argv[1:]
    for name in STEPS:
        if only and name not in only:
            continue
        print(f"== {name}")
        importlib.import_module(name).main()
