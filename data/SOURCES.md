# Data sources for the Greenpoint–Williamsburg ToxiCity Map layers

The original 2015 layers lived on the `nag-brooklyn` CARTO account, which no longer
exists. These files rebuild them from public sources. All files are GeoJSON
FeatureCollections in WGS84 (EPSG:4326). Coordinates are rounded to 6 decimals, and
polygons are simplified with a 1–1.5 m tolerance.

**Study area:** Brooklyn Community District 1 (BoroCD 301, Greenpoint and Williamsburg).
The boundary comes from NYC DCP *Community Districts* (clipped to shoreline), served as
`NYC_Community_Districts` FeatureServer at
`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Community_Districts/FeatureServer/0`.
Unless a layer says otherwise, it covers CD1 plus a 200 m buffer. The buffer is computed
in UTM 18N. Because Newtown Creek forms the eastern edge of CD1, the buffer also takes in
a few Queens sites on the far bank, such as Sims Metal, Phelps Dodge and Quanta
Resources.

**Retrieved:** 2026-10-20 (all sources).

**Rebuild:** run `python3 scripts/build_all.py`, or one step at a time with
`python3 scripts/build_<layer>.py`. Shared helpers are in `scripts/common.py`. Downloads
are cached in `~/.cache/nag-toxicology` (override with `$NAG_CACHE`).

---

## acs.geojson — `scripts/build_acs.py`

| | |
|---|---|
| Attributes | U.S. Census Bureau, **American Community Survey 2020–2024 5-year estimates** (the latest 5-year release; the files are dated 2026-01-29). Taken from the table-based Summary File at `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/`, using `acsdt5y2024-b03002.dat` (Hispanic or Latino Origin by Race) and `acsdt5y2024-b19013.dat` (Median Household Income, 2024 inflation-adjusted dollars). api.census.gov was not used because it now requires a key. |
| Land area | 2024 Census Gazetteer tract file for New York: `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_gaz_tracts_36.txt` (`ALAND_SQMI`) |
| Geometry | NYC DCP *2020 Census Tracts* (clipped to shoreline): `https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Census_Tracts_for_2020_US_Census/FeatureServer/0` |

Processing:
- Keeps every 2020 tract with at least 25% of its area inside CD1. CD1 is made up
  exactly of whole tracts, so this gives 54 tracts.
- `total_population` = B03002_001.
- `people_per_square_mile` = B03002_001 / ALAND_SQMI, rounded.
- `percent_hispanic` = B03002_012 / total.
- `percent_nonhispanic_white` = B03002_003 / total.
- `percent_nonhispanic_black` = B03002_004 / total.
- `percent_nonhispanic_asian` = B03002_006 / total.
- All percentages are on a 0–100 scale with one decimal.
- `median_household_income` = B19013_001. It is null when the Census suppresses the
  estimate (negative sentinel values in the Summary File). A value of 250001 means
  "$250,000+".
- Three tracts have 0 population: 36047044902, 36047057902 and 36047058902 (parks and
  industrial waterfront). They are kept, with `no_population: true`, density 0, and null
  percentages and income.
- Extra properties: `tract_label`, `nta_name`, `land_area_sq_mi`, `share_in_cd1`,
  `acs_vintage`.

## asthma.geojson — `scripts/build_asthma.py`

| | |
|---|---|
| Rates | NYS Department of Health, **"Sub-County Data for Selected Health Outcomes in New York State, 2008-2012, 2013-2017"**, health.data.ny.gov dataset `vtby-z2yc` (`https://health.data.ny.gov/resource/vtby-z2yc.json`), from the NYS Environmental Public Health Tracking (EPHT) program. The underlying data is SPARCS hospital and emergency-department discharges. The dataset was last updated 2026-06-16. |
| Geometry | The dataset's attached sub-county boundary shapefile `EPHT7p5k_2010_NYS.zip` (`https://health.data.ny.gov/api/views/vtby-z2yc/files/526acd4b-20f3-4ead-903d-d3194ddb2172?download=true&filename=EPHT7p5k_2010_NYS.zip`). In NYC these areas are 2010 Neighborhood Tabulation Areas (NTAs). |

This is very likely the same SPARCS/EPHT source behind the original 2015 layer, which was
"cases per 1,000 people, 2008–2012". No finer public geography exists. NYS publishes
asthma counts by ZIP only for pediatric and young-adult admission indicators, and the NYC
EH Data Portal works at UHF or community-district level, which gives a single value for
all of CD1.

Processing:
- `asthma_rate_per_1000_people` = the **crude asthma emergency-department visit rate,
  2013–2017** (the most recent period), as an annual average per 10,000 residents
  divided by 10.
- `measure` = "Asthma emergency department visits per 1,000 residents per year (crude
  rate, annual average)".
- `period` = "2013–2017".
- Extra properties:
  - `asthma_ed_age_adjusted_per_1000`
  - `asthma_hosp_crude_per_1000` (hospitalizations)
  - `asthma_ed_crude_per_1000_2008_2012` (the same measure for the original map's period)
  - `epht_id`
  - `share_of_area_in_cd1`
- NTA polygons are clipped to the CD1 boundary. Slivers smaller than 2 ha are dropped.
  The result is 7 areas: Greenpoint, North Side–South Side, Williamsburg and East
  Williamsburg, plus small parts of Bushwick North, Bushwick South and Bedford that fall
  inside CD1.
- Note: the original layer probably showed 5-year *cumulative* cases per 1,000
  (`asthma5y / totpop * 1000`, according to `sql/format_asthma.sql`). The new values are
  annual rates, so they are about 1/5 of the old scale.

## flood_risk.geojson — `scripts/build_flood_risk.py`

| | |
|---|---|
| Source | NYC Mayor's Office of Climate & Environmental Justice (MOCEJ) / NYC DCP layers from the **EJNYC Mapper**. They are hosted in NYC's ArcGIS Online organization (owner `mocej.nyc.data`, tagged `dcp`; the services were last edited 2026-05). |
| `storm = "100"` | "Coastal Storm Surge Flooding: 2050s 1% Annual Chance Storm", item `39fec5dbaeb7438592db0a91734ca361`, `https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/dcp_staging_hosted_feature/FeatureServer/0` |
| `storm = "500"` | "Coastal Storm Surge Flooding: 2050s 0.2% Annual Chance Storm", item `4d5d262cdf6c4321b38309eb00b651cd`, `https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/FP_500yr_2050s_staged/FeatureServer/0` |

Why this source: NYC Open Data still has the 2013 OLTPS/NPCC *Future Floodplain 2050s*
(`27ya-gqtm`, map view "Sea Level Rise Maps (2050s 100-year Floodplain)" `hbw8-2bah`),
but that is the 100-year floodplain only. The matching 2050s 500-year dataset is no
longer listed on the portal. The MOCEJ pair is current and internally consistent: the
100-year area lies inside the 500-year area. The 2013 Open Data 100-year layer is larger
in places; inside the study area it covers about 6.2 km², against 3.6 km² for the
current layer.

Processing:
- Each layer is intersected with CD1 + 200 m, dissolved into one MultiPolygon per storm,
  and simplified at 1.5 m. Specks smaller than 25 m² are dropped.
- The 500-year feature comes first in the file so the 100-year feature draws on top.
- The floodplain polygons include open water within the buffer.
- Properties: `storm`, `period`, `description`, `area_acres`, `source`.

## polluted_points.geojson — `scripts/build_polluted_points.py`

Common properties: `category`, `name`, `address`, `description`, `program`, `date`,
`link` (a URL or ""), `source`.

### `highly_regulated`: U.S. EPA ECHO (Enforcement and Compliance History Online)

- Source: the ECHO facility search REST service (`https://echodata.epa.gov/echo/echo_rest_services.get_facilities`,
  then `get_qid`), active facilities only (`p_act=Y`). Coordinates are ECHO/FRS
  `FacLat`/`FacLong`. Points are kept if they fall inside CD1 + 200 m.
- A facility is included if it meets any of these conditions:
  - Clean Air Act "Major Emissions" (Title V)
  - Clean Water Act major NPDES discharger
  - current TRI reporter
  - RCRA TSDF
  - RCRA Large Quantity Generator with an industrial NAICS code: 221 (except 22131),
    31–33, 42, 49319, or 562 (except 56291).
- Excluded: LQG records that are only construction, real estate, schools, transit,
  bridge or road work, remediation, or Con Edison manhole/vault jobs. These are mostly
  one-time generators.
- `link` = ECHO Detailed Facility Report (`https://echo.epa.gov/detailed-facility-report?fid=<FRS registry id>`).

### `e_designation`: NYC DCP (E) Designations

- Source: NYC DCP *(E) Designations* (`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/nyedesignations/FeatureServer/0`),
  joined by BBL to NYC DCP **MapPLUTO 26v2**
  (`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/MAPPLUTO/FeatureServer/0`).
- Selection: lots with `CD = 301` that have an (E) designation.
- E-designations whose only requirements are noise-related are excluded. These are
  "Window Wall Attenuation & Alternate Ventilation", "Double Glazed Windows" and "N2
  Ambient Noise Zone Levels".
- `program` is "Hazardous Materials" if any requirement mentions hazardous-materials
  testing, underground gasoline tanks, or a hazardous-materials restrictive declaration.
  It is "Air Quality" if any requirement is an air-quality, fuel, HVAC or stack
  restriction. It can be both.
- Point = the MapPLUTO lot centroid (`Latitude`/`Longitude`).
- One point per lot, combining all E-numbers on that lot.
- Extra properties: `bbl`, `ceqr_number`.

### `spill_major` / `spill_minor`: NYS DEC Spill Incidents

- Source: data.ny.gov `u44d-k5fk` (`https://data.ny.gov/resource/u44d-k5fk.json`), which
  is updated daily.
- **Filter:** Kings County, spill date on or after **2011-01-01** (about the most recent
  15 years).
- The source has no coordinates. Each spill's `street_1` (plus ZIP) is geocoded with
  NYC GeoSearch (`https://geosearch.planninglabs.nyc/v2/search?text=...`). Requests are
  sequential with a 0.15 s pause, and results are cached in
  `~/.cache/nag-toxicology/geosearch_cache.json`.
- A geocode is accepted only if it is in Brooklyn and its house number matches the input.
  Intersections, descriptive locations and missing addresses are dropped as unusable.
- Kept if the point falls inside the CD1 boundary (no buffer).
- Records are grouped by `spill_number`, since a spill can have one row per material.
- `spill_major` = total reported quantity of at least 100 **gallons**. Everything else is
  `spill_minor`: smaller spills, unreported quantities (often 0), and quantities in other
  units such as pounds.
- `date` = spill date. `link` = "" (DEC has no stable per-spill URL).
- Extra properties: `spill_number`, `quantity_gallons`, `geocode_label`.
- Result of the 2026-10-20 run:
  - 5,704 Kings County spills since 2011-01-01.
  - 3,592 geocoded to an address-level match. The other 2,112 had no usable street
    address (intersections, highway or waterbody descriptions, blank) and are left out.
  - 501 of the geocoded spills fall in CD1: 20 major and 481 minor. Dates run from
    2011-01-12 to 2026-10-08.
  - Because about 37% of Brooklyn spill records cannot be located, the spill layer
    under-counts. It is especially thin for spills on waterways and highways, such as
    Newtown Creek and the BQE.

## polluted_polygons.geojson — `scripts/build_polluted_polygons.py`

Common properties: `site_or_owner_name`, `address`, `program`, `description`,
`reference_number`, `link`. Extras: `agency`, `source`, and for DEC sites `site_class`
and `owner_name`.

1. **NYS DEC "Remediation Boundaries"**
   - Source: `https://services6.arcgis.com/DZHaqZm9cxOD4CWM/arcgis/rest/services/Remediation_Sites_Group_new/FeatureServer/2`
     (NYSDEC ArcGIS Online; the polygons behind DECinfo Locator; data last edited
     2024-12). Polygons intersecting CD1 + 200 m are kept, and polygons sharing a site
     code are merged.
   - Programs covered: State Superfund, Brownfield Cleanup, Voluntary Cleanup, Petroleum
     Remediation and RCRA.
   - Enrichment: joined on site code to data.ny.gov **"Environmental Remediation Sites"**
     `c6ci-rzpg` (updated 2026-10-20). This supplies the current site class, the
     contaminant list, owner, and institutional/engineering controls.
   - `link` = DEC site detail page.
   - Includes:
     - S224150 *ExxonMobil Greenpoint Petroleum Remediation*
     - S224083 *Former Paragon Oil Terminal (Peerless)*
     - 224121 *Meeker Avenue Plume Trackdown*
     - 224136 *Former NuHart Plastic Manufacturing* and C224287 *Former NuHart East*
     - National Grid / Brooklyn Union MGP sites
     - Newtown Creek (241117)
   - These are DEC's mapped site or parcel boundaries, **not** measured plume footprints.
2. **U.S. EPA "National NPL Superfund Site Boundaries (Public)"**
   - Source: `https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0`.
   - Sites: Newtown Creek (NYN000206282) and Meeker Avenue Plume (NYN000203407). Both are
     EPA's published "Total Site Polygon" boundaries.
3. **NYC Office of Environmental Remediation (OER) cleanup sites**
   - Source: NYC Open Data **"OER Cleanup Sites"** `3279-pp7v` (updated 2026-10-19).
   - Selection: Brooklyn CD1 sites whose `oer_program` includes **"VCP (Enrolled)"** (the
     NYC Voluntary Cleanup / brownfield program).
   - OER publishes only points and BBLs. Each footprint is the union of the project's tax
     lots from MapPLUTO 26v2.
   - Projects whose BBLs are not in MapPLUTO (19 of them, mostly retired or condo lots)
     are skipped.
   - E-designation-only OER projects are not drawn here; they appear as `e_designation`
     points.

## waste_transfer_stations.geojson — `scripts/build_waste_transfer_stations.py`

Properties: `name`, `facility_type`, `address`, `source`. Extras: `borough`, `operator`,
`waste_types`, `dec_authorization`.

1. **NYS DEC "Solid Waste Management Facilities"** (active facilities)
   - Source: data.ny.gov `2fni-raj8` (updated 2026-04-21).
   - Facilities in Kings or Queens with DEC coordinates inside CD1 + 200 m.
   - Rows are per authorization. Rows with the same name and address are merged, and
     their activity types are listed in `facility_type`. Types include transfer station,
     C&D debris processing and handling/recovery, recyclables handling/recovery, scrap
     metal processor, and vehicle dismantler.
2. **NYC DCP Facilities Database (FacDB)**
   - Source: NYC Open Data `ji82-xba5`.
   - Adds scrap-metal processors licensed by NYC DCWP (`datasource = dca_operatingbusinesses`)
     that are not already in the DEC list, matched on normalised street address.
   - DSNY drop-off sites and garages are not included.
3. **Newtown Creek Wastewater Resource Recovery Facility**
   - Source: NYC DEP data as published in the MOCEJ EJNYC "Wastewater Recovery
     Facilities" layer (`https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/Waste_Water_Recovery_Facilities/FeatureServer/0`).
   - Coordinates and capacity come from that layer. The street address is the one
     registered in EPA ECHO/FRS.

## industrial_history_points.geojson — not produced

The Industrial History Walking Tour stops were NAG's own curated content, held in the
deleted CARTO tables `industrialhistory_points` and `industrialhistory_lines`. I searched
nag-brooklyn.org via the Wayback Machine:
- the 2015-04-25 announcement post
- the 2015-05-06 follow-up post
- the 2016 ToxiCity Map post

These posts give only the two starting points (Chelsea Fiber Mill, 1175 Manhattan Ave;
Grand Ferry Park). They do not list the stops. No capture of the
`nag-brooklyn.cartodb.com` / `nag-brooklyn.carto.com` SQL API exists in the Wayback CDX
index. A general web search found no published stop list either. Rather than invent
stops, this layer is left out.
