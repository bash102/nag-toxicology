# Data sources for the North Brooklyn ToxiCity Map layers

The original 2015 layers lived on the `nag-brooklyn` CARTO account, which no longer
exists. These files rebuild them from public sources. All files are GeoJSON
FeatureCollections in WGS84 (EPSG:4326). Coordinates are rounded to 6 decimals, and
polygons are simplified with a 1–1.5 m tolerance.

**Study area:** Brooklyn Community Districts 1 through 4 (BoroCD 301 to 304:
Greenpoint and Williamsburg; Downtown Brooklyn, DUMBO, Fort Greene, Brooklyn Heights,
Boerum Hill, Clinton Hill and the Navy Yard; Bedford-Stuyvesant; Bushwick), set by
`DISTRICTS` in `scripts/common.py`. The boundary comes from NYC DCP *Community
Districts* (clipped to shoreline), served as `NYC_Community_Districts` FeatureServer at
`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Community_Districts/FeatureServer/0`.
Unless a layer says otherwise, it covers the four districts plus a 200 m buffer. The
buffer is computed in UTM 18N. Because Newtown Creek forms the northeastern edge of the
area, the buffer also takes in a few Queens sites on the far bank, such as Sims Metal,
Phelps Dodge and Quanta Resources.

**Retrieved:** 2026-10-20 to 2026-10-23 (see each layer).

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
- Keeps every 2020 tract with at least 25% of its area inside the four districts: 167
  tracts. All but three lie wholly inside; one (in Ocean Hill) is 48% inside, and two (in
  Carroll Gardens–Cobble Hill–Gowanus–Red Hook) only 29–31%.
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
- Six tracts have 0 population: 36047003102 (Fort Greene), 36047040700 (The Evergreens
  Cemetery), 36047044902 (East Williamsburg), 36047054300 (Brooklyn Navy Yard), and
  36047057902 and 36047058902 (Greenpoint). They are kept, with `no_population: true`,
  density 0, and null percentages and income.
- Extra properties: `tract_label`, `nta_name`, `land_area_sq_mi`, `share_in_area` (share
  of the tract's area inside the districts), `acs_vintage`.

## asthma.geojson — `scripts/build_asthma.py`

| | |
|---|---|
| Rates | NYC Department of Health and Mental Hygiene, **Environment & Health Data Portal** open data, `https://github.com/nychealth/EHDP-data` (branch `production`, commit `cf418fd` of 2026-10-20; retrieved 2026-10-23). Indicator files `indicators/data/<IndicatorID>.json`, with `indicators/metadata/metadata.json`, `TimePeriods.json` and `geography/GeoLookup.csv`. The underlying data is SPARCS emergency-department (ED) visits with a principal diagnosis of asthma. |
| Geometry | NYC DCP *2010 Neighborhood Tabulation Areas*: `https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/NYC_Neighborhood_Tabulation_Areas_2010/FeatureServer/0` |

Processing:
- NTA rates are the **average annual rate per 10,000 residents of the age group, 2017–2019**
  (TimePeriodID 282, the latest NTA period), GeoType `NTA2010`:
  - `ed_adults_rate`: indicator 2384 (adults 18+), measure 1208 "Average annual rate" (crude).
  - `ed_adults_age_adjusted_rate`: indicator 2384, measure 1209 "Average annual age-adjusted rate".
  - `ed_5_17_rate`: indicator 2383, measure 1206.
  - `ed_0_4_rate`: indicator 2378, measure 1193. It is **null everywhere** because the portal
    publishes the age 4-and-under NTA rate for 2014–2016 only. That value is kept as
    `ed_0_4_rate_2014_2016`.
- EHDP NTA2010 GeoIDs are the county FIPS code × 100 + the NTA number (BK09 → 4709). The
  script checks every code against the names in `GeoLookup.csv`.
- `community_district` = the community district holding most of the NTA's clipped area.
  `cd_ed_adults_rate` (indicator 2380, measure 1198) and `cd_ed_5_17_rate` (indicator 2379,
  measure 1196) are that district's crude "Estimated annual rate" per 10,000 for the latest year,
  `cd_period` = "2023". The crude rate is used because it matches the NTA crude rates. 2023
  values: CD 1 43.8 / 74.3, CD 2 53.2 / 178.9, CD 3 123.8 / 219.2, CD 4 81.5 / 125.6 (adults /
  age 5–17).
- Other properties: `geography_name` (NTA name), `nta_code`, `rate_units`, `period`
  ("2017–2019"), `notes` (portal flags such as "estimate based on small numbers"; none occur in
  the study area), `source`.
- NTA polygons are clipped to the boundary of Community Districts 1–4 (no buffer), and
  slivers smaller than 2 ha are dropped. That leaves 17 areas. Small overlaps that remain:
  Prospect Heights (4.9 ha), Ocean Hill (9.7 ha) and Park Slope–Gowanus (3.9 ha), each 1–5% of
  the NTA. Crown Heights North is 22% inside (104 ha). `park-cemetery-etc-Brooklyn` (BK99,
  156 ha: the Brooklyn Navy Yard and part of the cemeteries on the Bushwick edge) has no rates in the portal, so all its
  values are null.
- Study-area min–max per 10,000: `ed_adults_rate` 12.8–208.3, `ed_adults_age_adjusted_rate`
  14.8–206.9, `ed_5_17_rate` 22.1–320.9, `ed_0_4_rate_2014_2016` 39.4–511.2.

Caveats:
- The rates are SPARCS-based ED visits coded with ICD-10 (2017–2019). They are **not
  comparable** with the old 2013–2017 NYS EPHT layer (a different rate definition that
  straddles the October 2015 ICD-9 → ICD-10 change) or with pre-2015 data. EHDP says adult
  asthma is classified differently under ICD-9 and ICD-10. Childhood rates are comparable
  across the change.
- Rates use the population of each age group, so the adult, 5–17 and 0–4 rates should not be
  compared with one another.
- The CD values are single years (2023) for whole districts. Years after 2019 include the
  COVID-19 drop in ED use. Use them as context only, not as a trend from the NTA values.

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
in places; inside the study area it covers about 8.8 km², against 4.8 km² for the
current layer.

Processing:
- Each layer is intersected with the study area (+ 200 m), dissolved into one
  MultiPolygon per storm, and simplified at 1.5 m. Specks smaller than 25 m² are dropped.
- The 500-year feature comes first in the file so the 100-year feature draws on top.
- The floodplain polygons include open water within the buffer.
- Properties: `storm`, `period`, `description`, `area_acres`, `source`.

## polluted_points.geojson — `scripts/build_polluted_points.py`

Common properties: `category`, `name`, `address`, `description`, `program`, `date`,
`link` (a URL or ""), `source`.

### `highly_regulated`: U.S. EPA ECHO (Enforcement and Compliance History Online)

- Source: the ECHO facility search REST service (`https://echodata.epa.gov/echo/echo_rest_services.get_facilities`,
  then `get_qid`), active facilities only (`p_act=Y`). Coordinates are ECHO/FRS
  `FacLat`/`FacLong`. Points are kept if they fall inside CDs 1–4 + 200 m.
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
- Result of the 2026-10-23 run: 44 facilities, 4 of them in the buffer (all in Queens,
  including sites across Newtown Creek).
- ECHO's point for "Atlas Park" (Cooper Avenue, Glendale) is on the Bushwick/Ridgewood line,
  well away from the Glendale mall. It is kept as ECHO publishes it.

### `e_designation`: NYC DCP (E) Designations

- Source: NYC DCP *(E) Designations* (`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/nyedesignations/FeatureServer/0`),
  joined by BBL to NYC DCP **MapPLUTO 26v2**
  (`https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/MAPPLUTO/FeatureServer/0`).
- Selection: lots with `CD` in 301 to 304 (`DISTRICTS`) that have an (E) designation.
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
- Result of the 2026-10-23 run: 1,460 lots, 9 of them with a centroid just outside the
  district boundary.

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
- Kept if the point falls inside the boundary of CDs 1–4 (no buffer).
- Records are grouped by `spill_number`, since a spill can have one row per material.
- `spill_major` = total reported quantity of at least 100 **gallons**. Everything else is
  `spill_minor`: smaller spills, unreported quantities (often 0), and quantities in other
  units such as pounds.
- `date` = spill date. `link` = "" (DEC has no stable per-spill URL).
- Extra properties: `spill_number`, `quantity_gallons`, `geocode_label`.
- Result of the 2026-10-23 run (every address was already in the geocoding cache):
  - 5,704 Kings County spills since 2011-01-01.
  - 3,592 geocoded to an address-level match. The other 2,112 had no usable street
    address (intersections, highway or waterbody descriptions, blank) and are left out.
  - 1,224 of the geocoded spills fall in the four districts: 77 major and 1,147 minor.
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
     2024-12). Polygons intersecting CDs 1–4 + 200 m are kept, and polygons sharing
     a site code are merged.
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
     - National Grid / Brooklyn Union MGP sites, including the DUMBO / Vinegar Hill sites
       224048 *Brooklyn Gas Light A*, C224049 *Brooklyn Gas Light B*, 224063 / C224063
       *Front St. Station* and 224065 / C224065 *Plymouth Station*
     - Newtown Creek (241117)
     - Through the 200 m buffer: 224133 *Gowanus Canal Site* (south of CD 2) and 241180
       *Wolff-Alport Chemical Company* (Ridgewood, Queens, next to Bushwick)
   - These are DEC's mapped site or parcel boundaries, **not** measured plume footprints.
2. **U.S. EPA "National NPL Superfund Site Boundaries (Public)"**
   - Source: `https://services.arcgis.com/cJ9YHowT8TU7DUyn/arcgis/rest/services/FAC_Superfund_Site_Boundaries_EPA_Public/FeatureServer/0`.
   - Sites: Newtown Creek (NYN000206282) and Meeker Avenue Plume (NYN000203407), both
     EPA's published "Total Site Polygon" boundaries. Two more sites reach the 200 m buffer:
     Gowanus Canal (NYN000206222), whose site boundary comes within 200 m of CD 2, and
     Wolff-Alport Chemical Company (NYC200400810, "Approximate Site Boundary"), on the
     Ridgewood side of the Bushwick line.
3. **NYC Office of Environmental Remediation (OER) cleanup sites**
   - Source: NYC Open Data **"OER Cleanup Sites"** `3279-pp7v` (updated 2026-10-19).
   - Selection: Brooklyn sites with `community_district` 1 to 4 whose `oer_program`
     includes **"VCP (Enrolled)"** (the NYC Voluntary Cleanup / brownfield program).
   - OER publishes only points and BBLs. Each footprint is the union of the project's tax
     lots from MapPLUTO 26v2.
   - Projects whose BBLs are not in MapPLUTO (29 of them, mostly retired or condo lots)
     are skipped.
   - E-designation-only OER projects are not drawn here; they appear as `e_designation`
     points.

Result of the 2026-10-23 run: **501 polygons**: 217 NYS DEC sites (148 Brownfield Cleanup, 49
State Superfund, 13 Voluntary Cleanup, 6 Petroleum Remediation, 1 RCRA), 280 NYC OER VCP
sites and 4 EPA NPL sites.

## waste_transfer_stations.geojson — `scripts/build_waste_transfer_stations.py`

Properties: `name`, `facility_type`, `address`, `source`. Extras: `borough`, `operator`,
`waste_types`, `dec_authorization`.

1. **NYS DEC "Solid Waste Management Facilities"** (active facilities)
   - Source: data.ny.gov `2fni-raj8` (updated 2026-04-21).
   - Facilities in Kings or Queens with DEC coordinates inside CDs 1–4 + 200 m.
   - Rows are per authorization. Rows with the same name and address are merged, and
     their activity types are listed in `facility_type`. Types include transfer station,
     C&D debris processing and handling/recovery, recyclables handling/recovery, scrap
     metal processor, and vehicle dismantler.
2. **NYC DCP Facilities Database (FacDB)**
   - Source: NYC Open Data `ji82-xba5`.
   - Adds scrap-metal processors licensed by NYC DCWP (`datasource = dca_operatingbusinesses`)
     that are not already in the DEC list, matched on normalised street address.
   - DSNY drop-off sites and garages are not included.
3. **NYC DEP Wastewater Resource Recovery Facilities (WRRFs)**
   - Source: NYC DEP data as published in the MOCEJ EJNYC "Wastewater Recovery
     Facilities" layer (`https://services6.arcgis.com/yG5s3afENB5iO9fj/arcgis/rest/services/Waste_Water_Recovery_Facilities/FeatureServer/0`).
   - Selection: every plant whose point is inside the study area. These are the Newtown
     Creek WRRF in Greenpoint and the Red Hook WRRF in the Brooklyn Navy Yard.
   - Coordinates and capacity come from that layer. The street addresses are the ones
     registered in EPA ECHO/FRS: 301 Greenpoint Avenue for Newtown Creek, and "Marshall
     Street and Little Street" for Red Hook.

Result of the 2026-10-23 run: **39 facilities**: 23 from DEC, 14 DCWP-licensed scrap-metal
processors from FacDB, and the 2 WRRFs.

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

## air_pm25.geojson, air_no2.geojson — `scripts/build_air_quality.py`

| | |
|---|---|
| Source | NYC Department of Health and Mental Hygiene (DOHMH), **New York City Community Air Survey (NYCCAS)**. NYC Open Data file asset **"NYCCAS Air Pollution Rasters"** `q68s-8qxv` (`https://data.cityofnewyork.us/api/views/q68s-8qxv.json`). The download is `AnnAvg_1_16_300m.zip` (blob `6a525137-8d0e-4af3-a58b-fc7d9df060d0`, 8.4 MB), described by the attached `Data-Dictionary_NYCCAS_March_2026.xlsx`. Year 16 was added on 2026-03-04. |
| Vintage | **NYCCAS year 16 = December 2023 – December 2024**, labelled "2024 annual average". This is the latest year in the zip. Grids: `aa16_pm300m` (PM2.5, µg/m³) and `aa16_no2300m` (NO2, ppb). |
| Raster | ESRI ArcInfo grid, float32, 156 rows × 157 columns at **984 ft (300 m)** resolution, NAD83 / New York Long Island State Plane (US feet). Cells with no value include most of the East River. |

How NYCCAS surfaces are made (from the DOHMH data dictionary): NYCCAS measures
street-level air quality at monitoring sites across the city. The raw monitor data are
adjusted for weather and season, then a **land-use regression** model relates them to
nearby emission sources and landscape factors. That model predicts seasonal averages at
unmonitored locations, the point predictions are smoothed to the grid with
inverse-distance weighting, and the seasonal values are averaged into annual averages.
See DOHMH's NYCCAS page (`https://www1.nyc.gov/site/doh/data/data-sets/air-quality-nyc-community-air-survey.page`)
for the monitoring design and model details.

Processing:
- The script reads the asset metadata for the current blob, downloads and caches the
  zip, and picks the highest-numbered `aa<N>_pm300m` / `aa<N>_no2300m` grids in it.
- Clip: every cell that touches the study area (+ 200 m; 470 cells), then the polygons
  are cut exactly to the study-area boundary.
- Values in those cells: **PM2.5 5.78–8.48 µg/m³**, **NO2 12.90–20.93 ppb**.
- Classified into 5 bands with fixed, round-number breaks: PM2.5 5.6–8.6 µg/m³ in
  0.6 µg/m³ steps, NO2 12–22 ppb in 2 ppb steps (lower edge inclusive; the top band
  includes its upper edge). The script stops if a future year falls outside them.
- Polygonized, dissolved to one MultiPolygon per band, reprojected to WGS84, and
  simplified at **5 m** (the grid is 300 m, so this only affects the clipped edge). Band 1
  comes first in each file.
- Properties: `pollutant` ("pm25" / "no2"), `band` (1 = lowest), `band_min`,
  `band_max`, `label`, `units`, `period`, `source`. The FeatureCollection also carries a
  `metadata` object with the NYCCAS year, grid name, raster CRS, breaks and study-area
  min/max.

Caveats:
- These are **modeled** estimates of annual-average street-level pollution, not
  measurements. DOHMH notes they are not comparable to short-term local monitoring or
  regulatory (EPA/DEC) monitors.
- The grid is **300 m**, coarser than a city block, so the bands show neighborhood-scale
  gradients only. A band edge is a cell edge, not a real boundary.
- The range across the study area is narrow, so the bands separate fairly small
  differences. Read them as relative levels within the study area, not as health or
  regulatory thresholds. For reference, every PM2.5 cell is below the EPA annual standard
  of 9.0 µg/m³ (set in 2024).
- Cells with no value (mainly East River water) leave about 1.6% of the buffered study
  area uncovered. Nearly all of it is outside the four districts themselves (about
  0.2 ha along the shoreline is inside).
- Breaks were chosen for the 2024 surfaces. Earlier NYCCAS years had higher levels, so
  comparing years would need different or shared breaks.

## health_conditions.geojson — `scripts/build_health_conditions.py`

| | |
|---|---|
| Estimates | CDC **PLACES: Local Data for Better Health, Census Tract Data, 2025 release**, data.cdc.gov dataset `cwsq-ngmh` (`https://data.cdc.gov/resource/cwsq-ngmh.json`; data last updated 2025-12-12). This is the newest PLACES tract release on data.cdc.gov as of retrieval (2026-10-21). |
| Geometry | Reused from `data/acs.geojson` (NYC DCP 2020 census tracts, clipped to shoreline). |

Processing:
- The 2025 release uses **2020 census tracts**, so it joins directly on `locationid` =
  `geoid`. All 161 populated tracts of the study area match; no 2010→2020 crosswalk is
  needed.
- Measures (crude prevalence, % of adults 18+, `datavaluetypeid = CrdPrv`, one decimal):
  `casthma` (current asthma), `copd`, `cancer` (non-skin cancer or melanoma), `chd`
  (coronary heart disease), `diabetes` (diagnosed), `mhlth` (frequent mental distress,
  14+ bad days in the past 30), `bphigh` (high blood pressure), `csmoking` (current
  smoking).
- `year` = object giving each measure's data year. All eight are **2023** (BRFSS 2023).
- `total_population` = PLACES `totalpopulation`, which is the **Census 2020** count. It
  differs from the ACS 2020–2024 `total_population` in `acs.geojson`.
- The six zero-population tracts (see `acs.geojson`) are not in PLACES. They are kept
  with `no_population: true`, null measures, null years and `total_population` 0.
- Extra properties: `no_population`, `places_release`. The FeatureCollection `metadata`
  lists the full measure names.

Caveats:
- PLACES values are **model-based small-area estimates**, not counts or measured local
  rates. CDC derives them with multilevel regression and post-stratification from
  state-level BRFSS survey responses plus Census 2020 and ACS 2019–2023 demographics. A
  tract's value mostly reflects its age, sex, race/ethnicity and poverty mix, so tracts
  with similar demographics get similar values whatever their local environment. CDC
  warns against using them to evaluate local programs or policies. Each value has a 95%
  confidence interval in the source (not carried into this file).
- Crude prevalence (not age-adjusted) is used, so age-related conditions (COPD, CHD,
  diabetes, high blood pressure, cancer) track each tract's age mix closely. The lowest
  values are in tracts of the Williamsburg and Downtown Brooklyn–DUMBO–Boerum Hill NTAs
  (diabetes 2.9–3.5%). The highest are in East Williamsburg, South Williamsburg,
  Bedford-Stuyvesant, Downtown Brooklyn–DUMBO–Boerum Hill and Fort Greene tracts
  (diabetes 17.7–25.4%).
- Current asthma among *adults* is a different measure from the NYS EPHT asthma ED-visit
  rates in `asthma.geojson`.
- Study-area min–max (%): `casthma` 8.3–12.8, `copd` 1.4–15.8, `cancer` 2.6–8.8, `chd`
  1.4–11.6, `diabetes` 2.9–25.4, `mhlth` 10.7–25.4, `bphigh` 11.8–43.0, `csmoking`
  4.4–27.8. Map class breaks are in `js/styles.js`.

## lead_service_lines.geojson — `scripts/build_lead_service_lines.py`

| | |
|---|---|
| Inventory | NYC DEP water service line inventory, NYC Open Data **"Lead Service Line Location Coordinates"** `jqfp-uff7` (`https://data.cityofnewyork.us/resource/jqfp-uff7.json`; rows last updated 2026-01-30; DEP updates it about every 6 months). Record and category counts match DEP's own map layer `NYC_WaterConnection_DEP25V11_202601_PG` (`https://services.arcgis.com/at3rDjch5X7i9Bag/arcgis/rest/services/NYC_WaterConnection_DEP25V11_202601_PG_gdb/FeatureServer/0`), the **January 2026** edition behind the NYC Service Line Map. No other service-line inventory dataset is listed on NYC Open Data (`jpn2-huby` is a map view of the same data). |
| Study-area lots | NYC DCP MapPLUTO (`CD IN (301,302,303,304)`), `https://services5.arcgis.com/GfwWNkhOj9bNBqoJ/arcgis/rest/services/MAPPLUTO/FeatureServer/0` |
| Geometry | Reused from `data/acs.geojson` (2020 census tracts). |
| Definitions | DEP "Water Service Line Map FAQs" (`https://www.nyc.gov/content/leadfree/pages/maps-faq`), the dataset's data dictionary, and DEP's *Lead Service Line Replacement Plan* (2025). |

The inventory has one record per tax lot (BBL) with a tax-lot polygon, the last known
service-line `material` and the `record_ty` (record type) it is based on.

Material categories, as DEP describes them:
- **Lead**: "DEP has records indicating that at least a portion of the water service
  line is lead."
- **Galvanized Service Line Requiring Replacement** (GRR): DEP's FAQ says "Galvanized"
  means DEP "has records indicating that at least a portion of the water service line is
  galvanized steel." DEP's replacement plan counts lead and GRR lines together as "LSLs".
  "Requiring replacement" is the federal Lead and Copper Rule category: a galvanized
  line that is or ever was downstream of a lead service line or lead connector, or is
  downstream of a line of unknown status.
- **Unknown – Lead Status Unknown**: "DEP has no records of a material type for your
  service line or there are conflicting records."
- **Non-Lead**: "DEP has records indicating that your water service line is made of
  another material type, such as copper or ductile iron."
- **Non-Applicable** ("N/A"): "there is no operational water service line located at
  this property."

Record types: *Records* = latest plumbing records filed by a licensed master plumber;
*Field Inspection* = visual inspection at the meter inside the building; *Excavation* =
external visual inspection where the line meets the City main; *Statistical
Analysis/Predictive Model* = modeled likelihood from property age, service size,
building class and billing records; *Not Verified* = no plumbing records on file;
*Other* = no operational service line.

Processing:
- Inventory lots in Brooklyn are queried within the bounding box of the four districts.
  A lot is in the study area if its BBL is a MapPLUTO lot with `CD` 301 to 304 (50,840
  lots), or, for the 206 inventory BBLs not in MapPLUTO (retired or re-numbered lots), if
  its representative point is inside the four districts. 140 MapPLUTO study-area lots
  have no inventory record.
- Each lot goes to the tract containing its representative point. 49 waterfront lots
  whose point falls just outside the shoreline-clipped tracts (0–90 m) go to the
  nearest tract.
- Per tract: `lead`, `galvanized_requiring_replacement`, `unknown`, `non_lead`,
  `not_applicable` (lot counts). `total_lines` = lead + GRR + unknown + non-lead, i.e.
  **excluding** Non-Applicable lots.
- `pct_lead_or_grr` = (lead + GRR) / `total_lines` × 100; `pct_unknown` = unknown /
  `total_lines` × 100 (one decimal; null if `total_lines` is 0).
- `small_sample` = `total_lines` < 25. `inventory_date` = "2026-01".
- Also `tract_label`, `nta_name` from `acs.geojson`.
- Result of the 2026-10-23 run: 50,906 study-area lots in 167 tracts: 7,777 Lead,
  180 GRR, 6,943 Unknown, 33,612 Non-Lead, 2,394 Non-Applicable. 16.4% of the 48,512
  lots with a service line are lead or GRR and 14.3% unknown.
- `pct_lead_or_grr` by tract runs from 0 to 30.6% (0 to 100% counting the
  `small_sample` tracts: 36047003102 has a single lot, which is lead or GRR). Map class
  breaks are in `js/styles.js`.

Caveats:
- Counts are **tax lots, not service lines or people**. DEP's data does not account for
  multiple service lines or addresses on one BBL, and condos appear once under their
  billing BBL. Tracts dominated by large lots (NYCHA campuses, parks, industrial areas)
  have few lots, so their percentages rest on small numbers. 13 tracts are
  `small_sample`, with 1 to 24 lots each.
- Lead lines are mostly in older 1–4 family buildings, so a high share of lots does not
  mean a high share of residents.
- Most classifications come from historical plumbing records, not inspection. DEP says
  it cannot confirm the recorded material covers the whole length of a line, and its
  plan notes that many lines recorded as lead have turned out not to be.
- The inventory is a snapshot; lines replaced since January 2026 are not reflected.

## cso_outfalls.geojson — `scripts/build_cso_outfalls.py`

| | |
|---|---|
| Locations | NYC DEP **"Citywide Outfalls"**, NYC Open Data `8rjn-kpsh` (updated 2025-12-18), rows with `outfall_ty = 'CSO'`. The same data is republished by MOCEJ as the EJNYC "Combined Sewer Overflow (CSO) Outfalls" layer. |
| Overflow counts and volumes | NYC DEP, *Fourteen Wastewater Resource Recovery Facilities' SPDES Permits, Best Management Practices Annual Report* for **calendar year 2025** (dated 2026-04-28): `https://www.nyc.gov/assets/dep/downloads/pdf/water/stormwater/spdes-bmp-cso-annual-report-2025.pdf`, Appendix 14.1 "Table – CSO Discharge Summary for CY 2025 Checklist". The outfall inventory in the same report supplies the receiving-water names. |
| Detection method | NYS DEC **"Combined Sewer Overflows (CSOs): Beginning 2013"**, data.ny.gov `ephi-ffu6` (last updated 2020-11-11). This is the table behind DEC's "Combined Sewer Overflows (CSOs) Map" (`i8hd-rmbi`). Both are on data.ny.gov, not NYC Open Data. |

Why these sources: DEC's CSO dataset has outfall points and a "Number of Overflow Events"
column, but every NYC DEP row says "Visit facility website" / "Real-time waterbody advisory".
Its data dates from 2015, and some of its receiving-water names are wrong (for example, it
places NCB-019 and NCQ-029 in the "East River"). NYC Open Data has no CSO dataset with
overflow frequencies. The only per-outfall frequency and volume figures found are the modeled
annual figures in DEP's BMP annual report, so that report is parsed with `pdftotext`.

Selection:
- Every DEP CSO outfall within **CDs 1–4 + 500 m** (not the usual 200 m). On the CD 2
  waterfront this takes in the Red Hook WRRF's East River outfalls from the Navy Yard and
  Wallabout Bay past DUMBO and Brooklyn Heights to Atlantic Avenue (RH-001 to RH-016 and
  RH-040), plus RH-018 at Kane Street (405 m from CD 2). The Wallabout outfalls NCB-013,
  NCB-014 and NCB-082 belong to the Newtown Creek WRRF.
- Plus every outfall whose receiving water is Newtown Creek or a tributary (Dutch Kills,
  Whale Creek, Maspeth Creek, English Kills, East Branch), however far it is from the
  districts. This adds BB-009, BB-026 and BB-040 at the head of Dutch Kills and NCQ-077 at
  the head of Maspeth Creek, 530–870 m away.
- The Gowanus Canal does not border the districts, but the 500 m buffer reaches its head.
  Four Red Hook WRRF outfalls there are included: RH-034 (head of the canal / Gowanus Pumping
  Station, 200 m from CD 2), RH-033 Douglass St (238 m), RH-038 Degraw St (316 m) and RH-037
  Sackett St (398 m). The other Gowanus outfalls (RH-036, RH-041, RH-035, OH-007 and those
  further south) are more than 500 m away and are left out.
- Manhattan-bank East River outfalls (NCM-*) are excluded. Five on the Lower East Side
  (NCM-059 to NCM-063, 427–497 m across the river from DUMBO and the Navy Yard) are within
  500 m.
- Queens-bank outfalls on Newtown Creek and Dutch Kills (Bowery Bay WRRF's BB-* and Newtown
  Creek WRRF's NCQ-*) are included.
- Result: **56 outfalls**. 24 drain to the Newtown Creek WRRF, 20 to the Red Hook WRRF and 12
  to the Bowery Bay WRRF. By receiving water: East River 28, Newtown Creek 12, Dutch Kills 6,
  Gowanus Canal 4, Wallabout Channel 2, and 1 each in Whale Creek, English Kills, Maspeth
  Creek and Navy Yard Basin.

Properties:
- `outfall_id`: DEP id.
- `name`: DEP location, title-cased.
- `receiving_water`: from the BMP inventory, falling back to DEP's layer.
- `operator`: "NYC DEP".
- `facility`: the WRRF drainage area.
- `overflow_events`, `overflow_volume_mg`: modeled CSO events and annual CSO volume (million
  gallons) for CY2025, as printed in Appendix 14.1.
- `overflow_period` = "Calendar year 2025".
- `detection`: these figures come from DEP's InfoWorks ICM collection-system model, driven by
  NOAA/NSSL radar rainfall estimates (QPE). They are not metered.
- `link`: the BMP report.
- `source`.
- Extras:
  - `overflow_events_prev_year`, `overflow_volume_mg_prev_year` (CY2024, from the same
    table)
  - `bmp_outfall_id`
  - `dec_cso_id`
  - `dec_detection_method`: DEC's 2015 "Discharge Activation Type", either "Model" or
    "Monitoring"
  - `outfall_size`
  - `distance_to_area_m`: metres from the outfall to the nearest of the four districts
  - `note`

Results:
- CY2025 events range from 0 to 47 per outfall. NCQ-077 has 47, RH-014 (Atlantic Ave) 43,
  NCB-083 41, RH-005 (Gold St) 39, and BB-009 and RH-034 (head of the Gowanus Canal) 38 each.
- Volumes range from 0 to 360 MG. The largest are NCB-014 (Kent Ave, Wallabout Channel,
  360 MG), NCQ-077 (326), NCB-083 (251), NCB-015 (131), RH-005 (84) and RH-034 (79).
- The 54 outfalls with figures total about 1,534 MG. The 19 Red Hook outfalls account for
  about 241 MG of that.

Caveats:
- All counts and volumes are **model estimates**, not measurements. They depend on that
  year's rainfall, and DEP warns that its model updates make figures "not directly
  comparable" between years. For example, BB-004 goes from 1 event in 2024 to 28 in 2025.
- Volumes are printed to the nearest million gallons, so 0 means less than about 0.5 MG,
  not "no overflow".
- **ID crosswalk:** DEP's outfall layer and the BMP report number two Greenpoint outfalls
  differently. They are matched by location:
  - Layer NCB-088 "Huron Street (Reg. B-12)" = BMP NCB-027 "East River & Huron Street,
    Reg #B-12". DEC's NY0026204-027 point is within 1 m of it.
  - Layer NCB-084 "Commercial St" = BMP NCB-023 "Newtown Creek & Franklin Street,
    Reg #B-16". DEC's NY0026204-023 point is about 25 m away.
  - DEC's own NY0026204-088 is a different point on the East Branch (40.7201, −73.9239).
    It is not in DEP's layer or the BMP table and is not mapped.
- NCB-001 and RH-001 are the main treated-effluent outfalls of the Newtown Creek and Red
  Hook WRRFs. DEP's layer and DEC's dataset list them as CSO outfalls, but they have no BMP
  overflow row, so their overflow fields are null.
- BB-049 ("Newtown Creek & 21st Street"; 0 events in 2024 and 2025) has no coordinates in
  DEP's layer or DEC's dataset, so it is not mapped.
- Receiving-water names follow the BMP inventory. NCB-019 and NCB-083 at the
  Metropolitan Ave head of the East Branch are listed there as "Newtown Creek". RH-014,
  RH-016 and RH-018 (Atlantic Ave, Amity St, Kane St) are "East River" in the BMP inventory
  but "Buttermilk Channel" in DEP's layer. RH-040 is "East River & Navy Yard" in the BMP
  inventory but "Navy Yard Basin" in the layer.
- Red Hook ids match DEC's NY0027073 records by number. DEC's points are within 0–58 m of
  DEP's.
- RH-034's name keeps DEP's spelling, "Head Of Gownaus Canal".
- The Newtown Creek CSO storage tunnel and other Long Term Control Plan projects for the
  four largest outfalls (BB-026, NCQ-077, NCB-083, NCB-015) are not yet in service. Counts
  will change as they come online.

## harbor_water_quality.geojson — `scripts/build_harbor_water_quality.py`

| | |
|---|---|
| Source | NYC Open Data **"Harbor Water Quality"**, `5uug-f49n` (NYC DEP Harbor Survey Monitoring program, Marine Sciences Section; updated 2026-10-06). Data runs through **2025-12-16**. |
| Standards | 6 NYCRR **703.3** (dissolved oxygen) and **703.4** (coliforms, enterococci), as currently in force (last amended 2023-10-18). Classifications are from 6 NYCRR Part 890: the East River is **Class I**, and Newtown Creek and its tributaries are **Class SD**. DEC's Newtown Creek Use Attainability Analysis (2026-09-09, `https://dec.ny.gov/sites/default/files/2026-09/newtowncreek_uaa_fca.pdf`) confirms both. DEC proposed reclassifying Newtown Creek from SD to I on 2026-09-16. Comments close 2026-11-30, and the change is not adopted. The Gowanus Canal has been **Class SC** since DEC's Notice of Adoption of 2025-10-15. Before that it was SD above the Gowanus Expressway, where GC3–GC5 are, and I below it. Source for this: the Gowanus Canal CAG resolution of 2026-01-27 (`https://gowanuscag.org/wp-content/uploads/2026/01/CAG-DO-Levels-Resolution-012926.pdf`), which cites the State Register notice. The notice itself was not checked. |

Station positions: the dataset has no station table, and no separate DEP station-location
dataset was found on NYC Open Data, data.ny.gov or ArcGIS Online. Instead, each row's
`lat`/`long` is used:
- 2016–2020: nominal station coordinates.
- 2021–2022: per-visit GPS fixes. About a third of the 2021 rows have lat and long swapped.
- Since late 2022: blank.

Each station's point is the median of its valid recorded positions since 2016. Swapped pairs
are corrected, and values outside the harbor (such as `-74`/`41` or 0) are dropped.
`position_basis` gives the count. No coordinates were typed in.

Selection:
- Stations sampled since 2021-01-01 whose point lies within 1 km of CDs 1–4.
- HSM has **no current station in the East River off DUMBO, Brooklyn Heights or Wallabout
  Bay**. The only stations ever recorded there are historical. E1, off the Brooklyn Bridge
  at (40.7, −74.00655), is 519 m from CD 2 and was last sampled 2013-07-16. The rest are
  one-off X-series points from 1909–1949. None meets the "sampled since 2021" rule. The next
  active East River station, E2, is the one off Greenpoint.
- The 1 km rule does take in the head of the Gowanus Canal, south of CD 2, where the CSO
  layer also maps four outfalls. GC6 is about 1.3 km away and is left out.
- Result: **10 stations**:
  - E2: East River off Greenpoint, near the Newtown Creek mouth, 667 m from CD 1.
  - NC3, NC2, NC1: Newtown Creek main channel.
  - NC0: English Kills.
  - NC0B: East Branch.
  - NC0A: East Branch. Sampled 2019 to May 2022, then replaced by NC0B about 200 m away.
    It is kept with `active: false`, a `note`, and its own period (2019; 2020–2021 had fewer
    than 20 fecal coliform sampling dates).
  - GC3, GC4, GC5: Gowanus Canal, 477 m, 647 m and 872 m from CD 2. All are still sampled
    (latest 2025-12-08), but on only 10–17 dates a year in 2022–2024. So they have
    `active: false` and use the fallback period: the latest three years with at least 20
    fecal coliform sampling dates (GC3 and GC5: 2020, 2021, 2025; GC4, which has no fecal
    coliform result after 2021-06-03: 2018–2020). A `note` gives the last fecal result.
- `waterbody` is assigned from each station's position, not from a DEP label. The dataset
  has none.

Period: **2023–2025**, the three most recent complete calendar years. All active stations
were sampled throughout: about 53 dates a year at NC stations and about 31 at E2. The
Gowanus stations were not (see above). Summer visits are roughly twice weekly; winter
visits are monthly.

Processing (per station, over the period):
- `n_samples` = sampling dates (rows) in the period.
- `fecal_coliform_geomean`, `enterococci_geomean`: geometric mean (cells/100 mL) of all top
  and bottom results. Values with commas are parsed. Results flagged `<`, `>` or `E`
  (estimated) are used at their reported value, so the means are approximate at the
  extremes.
- `do_mean_mg_l`: mean of all top and bottom DO values. For each depth, the value is the
  Winkler titration result, or else the CTD probe, or else the YSI probe; DEP's extra
  summer runs report YSI only. Winkler and CTD agree to within about 0.2–0.3 mg/L on
  average.
- `pct_do_below_standard`: share of DO values below the acute standard for the station's
  class, each depth counted separately:
  - Class I (E2): "shall not be less than 4.0 mg/L at any time".
  - Class SD (NC*): "Acute: shall not be less than 3.0 mg/L at any time".
  - Class SC (GC*): the same acute value, 3.0 mg/L at any time.
  - `do_standard_mg_l` and `do_standard` give the value used.
  - `pct_do_below_4_8` gives the share below 4.8 mg/L for comparison. That is the SA/SB/SC
    chronic daily-average standard, and the one Newtown Creek would face if it is ever
    reclassified to SB/SC.
- `water_quality_class`: compares the period geomean of fecal coliform with 703.4(b). For
  Class I, SC and SD waters this says "the monthly geometric mean, from a minimum of five
  examinations, shall not exceed 200" per 100 mL. The result reads "Meets … (geomean ≤200 per
  100 mL)" or "Exceeds … (>200)". It does **not** call the water "swimmable":
  - Class SD has no primary-contact use and no enterococci standard.
  - Class I is protected for secondary contact, with an enterococci 30-day geomean ≤72.
  - Class SC (Gowanus) is protected for primary contact and has its own enterococci
    standard, which this layer does not evaluate.
  - DEP's Harbor Survey reports use fecal coliform ≤200 as their historical swimmable
    benchmark.
- `fecal_months_evaluated` / `fecal_months_over_200`: a closer check on the monthly form of
  the standard. They count months with at least 5 surface results, and those whose geomean
  is above 200. Only summer months qualify: about 3–6 per station, and 0–1 at the Gowanus
  stations.
- Extras: `water_class`, `n_fecal_results`, `n_enterococci_results`, `n_do_results`,
  `active`.

Results, 2023–2025:

| Station | Fecal coliform geomean (/100 mL) | Enterococci geomean (/100 mL) | DO mean (mg/L) | % DO below standard |
|---|---|---|---|---|
| E2 | 68 | 14 | 6.5 | 2% (<4.0) |
| NC3 | 280 | 42 | 5.9 | 2% (<3.0) |
| NC2 | 352 | 55 | 5.6 | 9% |
| NC1 | 438 | 67 | 5.2 | 17% |
| NC0B | 834 | 113 | 4.8 | 25% |
| NC0 | 519 | 121 | 3.9 | 39% |
| NC0A (2019) | 2,235 | 105 | 5.8 | 6% |
| GC3 (2020, 2021, 2025) | 80 | 37 | 6.6 | 3% (<3.0) |
| GC4 (2018–2020) | 111 | 44 | 7.9 | 3% |
| GC5 (2020, 2021, 2025) | 196 | 58 | 6.4 | 4% |

E2 and the three Gowanus stations meet the fecal standard; GC5 only just does, at 196.
All Newtown Creek stations exceed it. The Gowanus figures cover different years from the
others, so they are not directly comparable.

Caveats:
- Pooling top and bottom results and taking a geomean over three years smooths over
  wet-weather spikes. Single results reach 182,000 cells/100 mL.
- DEP runs in-stream aeration systems in English Kills and the East Branch, which raise DO
  at NC0/NC0A/NC0B.
- A small number of DO values are 0.0 mg/L: 2 of the 2,253 values in the mapped stations'
  summary periods. They are kept as reported.

## cancer_mapping.geojson — `scripts/build_cancer_mapping.py`

| | |
|---|---|
| Counts | NYS Department of Health, New York State Cancer Registry, **"Cancer Mapping Data: 2011-2015"**, health.data.ny.gov dataset `y4pv-ib8r` (`https://health.data.ny.gov/d/y4pv-ib8r`), published 2018-08-17. It is a zip file (`NYSDOH_CancerMapping_Data_2011_2015.zip`, blob `313b3230-e2b0-4ee9-9063-dc30c6c04264`) holding `NYSDOH_CancerMapping_Data_2011_2015.xlsx`, `NYSDOH_CancerMapping_Crosswalk_2011_2015.xlsx`, the Overview PDF and the Data Dictionary PDF. These are the data behind DOH's Environmental Facilities and Cancer Map (Public Health Law §2401-B). DOH says the cancer data are provisional as of December 2017. |
| Other catalog entry | `ybxz-mnf5` ("updated 2025-04-08") is **not** a newer release. It is a healthdata.gov (HHS) catalog record, type `href`, harvested from health.data.ny.gov's data.json on 2025-04-08. It has no data of its own and points back to `y4pv-ib8r` (its metadata lists `Common-Core_Unique-Identifier` = `y4pv-ib8r` and `Last-Update` 2018-08-17). `y4pv-ib8r` is the authoritative source. An older release, 2005–2009, is `cw3n-fkji`. |
| Geometry | The dataset ships no shapes. U.S. Census Bureau TIGER/Line 2010 block groups for Kings County: `https://www2.census.gov/geo/tiger/TIGER2010/BG/2010/tl_2010_36047_bg10.zip` |
| Documentation | Dataset attachments "NYSDOH Cancer Mapping Overview.pdf" and "NYSDOH Cancer Mapping DataDictionary.pdf" (2018); DOH's *About the Data* and *Frequently Asked Questions* pages under `https://www.health.ny.gov/statistics/cancer/environmental_facilities/mapping/about/`. www.health.ny.gov returned 403 from this environment, so the pages were read from the identical `healthweb-back.health.ny.gov` host (About the Data revised April 2026; FAQ revised July 2018). |

Geography: 2010 census block groups. To protect confidentiality, DOH merged neighbouring
block groups until each area had at least 6 male and 6 female cancer cases in total (12
cases where all cases were of one sex, e.g. prisons). Statewide, 15,464 block groups
became 13,513 areas. Merged areas have a custom ID such as `36047DOH0208`, and the
crosswalk lists their 2010 block groups. Merging is DOH's only confidentiality measure:
no counts are suppressed, and zeros are real zeros.

Cancer types: 23 sites, plus "other" and the total. The keys and DOH labels (from the
data dictionary; ICD-O-3 codes are in the file's `metadata.icd_o_3`) are:
- `all`: all cancers combined
- `bladder`: urinary bladder, including in situ
- `bone`: bones and joints
- `brain`: brain and other nervous system
- `breast`: female breast
- `colorectal`: colon and rectum
- `esophagus`, `larynx`, `mesothelioma`, `ovary`, `pancreas`, `prostate`, `stomach`,
  `testis`, `thyroid`
- `kidney`: kidney and renal pelvis
- `leukemia`: leukemia
- `liver`: liver and intrahepatic bile duct
- `lung`: lung and bronchus
- `nasal`: nasal cavity and nasopharynx
- `nhl`: non-Hodgkin lymphoma
- `oral`: oral cavity and pharynx, excluding nasopharynx
- `other`: other cancers not specifically listed
- `soft_tissue`: soft tissue
- `uterus`: corpus uterus, including uterus NOS

Field meanings, from DOH:
- **Observed**: newly diagnosed cases from 2011 to 2015 among residents, by address at
  diagnosis. Every primary tumour is counted.
- **Expected**: the number of cases the area would have "if the likelihood of being
  diagnosed with cancer at a given age and gender were uniform throughout the state". That
  is, statewide age- and sex-specific rates applied to the area's population, so the
  expected counts are age- and sex-adjusted. They make no adjustment for smoking, other
  individual risk factors, income or race/ethnicity.
- **Population**: `total_pop`. The data dictionary says this is the 2010 census
  population, but the About page says block-group populations for 2011–2015 were estimated
  from the 2010 census by iterative proportional fitting to county estimates, then
  averaged. The numbers follow the About page: they sum to 2,595,285 for Kings and
  19,673,173 statewide, against 2010 census counts of 2,504,700 and 19,378,102.
- **Highlight**: `highlight_<site>` is 1 if the block group is inside a "higher than
  expected" highlighted area, −1 if inside a "lower than expected" one, and 0 otherwise.
  DOH found these areas with the spatial scan statistic (Boscoe et al., *Health & Place*
  2003, 9(3):273–277):
  - The scan was limited to locations where observed and expected differ by 50% or more.
  - The ratio "had to be such that it was unlikely to be a chance occurrence". DOH
    publishes no p-value threshold.
  - Areas were capped at 2% of the state population (about 400,000 people).
  - DOH publishes no highlight for the total or for "other", and no area was highlighted
    for pancreas, soft tissue or uterus.
- The data dictionary text still says "between 2005 and 2009" for the observed and
  expected fields. This is a leftover from the earlier release; the file covers 2011–2015.

Processing:
- Kings County block groups are dissolved into DOH areas using the crosswalk.
- Selection keeps the DOH areas with **more than 50% of their land area (TIGER `ALAND10`)
  inside the four districts**. Most areas are almost entirely inside (98% or more) or
  under 2% inside. Of the areas in between, eight (90.7–97.9% inside) are kept, and six
  merged areas (15.4–47.2%) and seven block groups (2.2–4.3%) are dropped. The dropped
  parts leave small gaps along the districts' edges.
- Result: **308 features** (178 single block groups and 130 DOH merged areas). Together
  they cover 98.7% of the four districts, with a 2011–2015 average population of
  556,438.
- Polygons are clipped to the boundary of the four districts. TIGER 2010 block groups
  extend into the East River and Newtown Creek. They are simplified at 1.5 m.
- Properties:
  - `geoid`: the DOH area ID, which is the 12-digit 2010 block-group GEOID or the `DOH`
    code.
  - `merged_geoid10`: member block groups, for merged areas only.
  - `total_population`: DOH `total_pop`.
  - `share_in_area`: share of the area's land area (`ALAND10`) inside the four
    districts (capped at 1).
  - For each key: `<key>_obs`; `<key>_exp` (2 decimals); `<key>_ratio` = observed /
    expected, 2 decimals, null if expected is 0 (none are); and `<key>_sig`.
- `<key>_sig` comes from DOH's highlight flag: "higher" (1), "lower" (−1) or "not
  significant" (0). It is **membership in a multi-block-group highlighted area**, not a
  test of that block group alone. A block group with observed below expected can sit in a
  "higher" area, and vice versa (DOH FAQ).
  - `all_sig` and `other_sig` are null because DOH publishes no flag for them.
  - No significance was computed here. DOH's method is a spatial scan whose p-value
    threshold is not published, and DOH documents no per-block-group test, so it cannot be
    reproduced exactly.
- A top-level `metadata` object gives the labels, ICD-O-3 codes, years, the suppression
  rule and the field definitions.

Interpretation caveats, from DOH:
- **Small numbers and chance.** Many block groups have expected counts well below 1 for
  most sites, so a single case gives a ratio of 5–20 or more. Five-year totals are used
  because single-year counts "can vary considerably". DOH: "Some cancers occur at the same,
  or nearly the same, rate in all locations. Any small variations that are seen are likely
  due to chance."
- **Not a cause.** The map "cannot prove that something in the environment, including
  emissions from environmental facilities, causes cancer". Living in a pink area "does not
  mean that you are more likely to get cancer". Individual risk factors (tobacco, alcohol,
  physical inactivity, workplace exposures, family history) are not taken into account.
- **Latency and mobility.** Cancers usually appear 5 to 40 years after exposure, and
  counts are by residence at diagnosis. People may have lived elsewhere when exposed.
- **Crude rates.** Crude rates are cases ÷ (population × 5). Unlike observed/expected,
  they do not account for age structure.
- Registry data are continuously updated, so these provisional counts may differ from other
  NYSCR publications.

## air_toxics_risk.geojson — `scripts/build_air_toxics_risk.py`

| | |
|---|---|
| Source | U.S. EPA **Air Toxics Screening Assessment (AirToxScreen), 2020 assessment**, the newest year with risk results (`https://www.epa.gov/AirToxScreen`, results page `https://www.epa.gov/AirToxScreen/2020-airtoxscreen-assessment-results`; data files on `https://gaftp.epa.gov/rtrmodeling_public/AirToxScreen/2020/`, files dated 2024-05 to 2025-04). |
| Newer years | None with risk. The AirToxScreen home page (updated 2026-09-15) has a "2021 Data Available" note, but it links to the *2021 Multipollutant Platform* (`https://gaftp.epa.gov/Air/Multipollutant_Platform/2021/`), which has emissions and block-level ambient/exposure **concentrations** only. It has no cancer risk or hazard index. |
| Cancer risk | Block-level cancer risk by source group, all 13 regional files: `Cancer/BySource/Region{1,2,3,4a,4b,5a,5b,6a,6b,7,8,9,10}_CancerRisk_by_block_srcgrp.xlsx` (1.6 GB). Block-level cancer risk by pollutant for EPA Region 2: `Cancer/ByPollutant/Region2_CancerRisk_by_block_poll.xlsx`. |
| Respiratory hazard | `Exposure Concentrations/Region2_2020ATS_Exposure_Concentrations.xlsx` (block-level exposure concentrations, µg/m³, 177 air toxics), plus EPA's RfCs and target-organ flags from `2020AirToxScreenPollutants.xlsx` in the 2020 supplemental data zip (`https://www.epa.gov/system/files/other-files/2024-06/2020-airtoxscreen-supplemental-data-files.zip`). |
| Retrieved | 2026-10-22. |
| Check | EPA county averages, `https://www.epa.gov/system/files/documents/2025-01/national_cancerrisk_by_county_srcgrp.xlsx`, used for a one-time check of the tract method below (the build script does not download it). |
| Methods | *AirToxScreen 2020 Documentation* (TSD), `https://www.epa.gov/system/files/documents/2024-05/airtoxscreen_2020-tsd.pdf`; AirToxScreen Limitations and Frequent Questions pages. |
| Geometry | Reused from `data/acs.geojson` (NYC DCP 2020 census tracts, clipped to shoreline). |

**Tract vintage.** AirToxScreen 2017–2019 (and NATA) reported 2010 census tracts. The 2020
assessment is the first to report **2020 census blocks** instead. The TSD says risks "have
previously been generated at the census tract level, but for the 2020 version of
AirToxScreen, have been generated at the census block level". The block IDs are 2020
blocks: Kings County's 8,015 populated blocks sum to 2,736,074 people, the Census 2020
count. 2020 blocks nest inside 2020 tracts, so no 2010 geometry or crosswalk is needed.
EPA publishes no tract file for 2020, so the blocks are aggregated to tracts here.

Processing:
- **Aggregation.** Tract value = population-weighted mean of its blocks (block value ×
  block population, summed, ÷ tract population). This is the method EPA uses for its own
  county and state averages (TSD §6.4.1). Check: aggregating Kings County's blocks the
  same way gives 34.74 per million, which matches the unrounded sum of EPA's published
  Kings County source columns to 10 decimals. EPA's files list only populated blocks.
- `cancer_risk_per_million`: total lifetime cancer risk per million from **all modeled
  sources**, as EPA defines "Total Cancer Risk". This is the sum of all 39 source types:
  point, on-road, nonroad, nonpoint, fires, biogenics, **secondary formation** and
  **background**. It equals the sum over the 72 carcinogens in the pollutant file (they
  agree to 1e-14). It does **not** include diesel PM (EPA has no cancer URE for diesel).
  EPA's own "Total Cancer Risk" column is rounded to one significant figure (every one
  of the 1,724 study-area blocks reads 30 or 40), so the unrounded sum of the source
  columns is used instead, and the tract mean is given to one decimal. Rounding the sum
  reproduces EPA's published total in every block except 11 of the 5.8 million nationally
  (in Louisiana, Texas and Washington). None of those is in New York. That decimal shows
  relative position only. It is far finer than EPA's stated precision (see caveats).
- `cancer_risk_pctile_national`, `cancer_risk_pctile_state`: EPA does not publish
  percentiles. They are computed here from the full national block files, aggregated to
  tracts in the same way. A value is the share of populated tracts with a lower tract value
  (ties count half), × 100, rounded. "National" = the 83,845 populated tracts in the 50
  states + DC (Puerto Rico and the Virgin Islands left out). "State" = the 5,358 populated
  New York tracts. These are tract-count percentiles, not population percentiles.
- `respiratory_hi`: total chronic **respiratory hazard index**. EPA computes it ("For
  noncancer effects in the 2020 assessment, we estimated the effect of air toxics on the
  respiratory target system only"), but it has **not published 2020 HI values** as files or
  in the 2020 mapping tool service (`Cancer_Risk_2020` FeatureServer has cancer fields
  only). It is therefore **computed here** with EPA's documented formula (TSD §6.3):
  HI = Σ HQ, HQ = exposure concentration ÷ RfC. The sum runs over the 42 air toxics that
  EPA's pollutant table flags `resp` and gives an RfC: acrolein, formaldehyde,
  acetaldehyde, diesel PM, naphthalene, chlorine, nickel, chromium VI and others. Each
  block's HI is computed, then the tract takes the population-weighted mean. The inputs and
  units are checked: exposure concentration × EPA's URE reproduces EPA's published
  pollutant cancer risks in every CD 1 tract (CDs 2–4 not checked), for
  formaldehyde, acetaldehyde, chromium VI, nickel, naphthalene, 1,4-dichlorobenzene,
  acrylonitrile and epichlorohydrin (ratio 1.000000). For comparison, EPA's published 2019 AirToxScreen respiratory HI for
  Brooklyn's 2010 tracts is mostly 0.5, with some 0.4 (rounded to one significant figure;
  EPA ArcGIS service `NATA2019_RespHI_with_Pollutants_SourceGroups`). That is in line with
  the 0.42–0.54 computed here. Two decimals.
- `top_cancer_pollutants`: the 3 pollutants with the highest tract cancer risk, with risk
  per million (one decimal), e.g. "Formaldehyde 19.4, Carbon tetrachloride 3.0, Benzene 2.7".
  Items are separated by ", " (comma and space). Commas inside chemical names such as
  "1,3-Butadiene" have no space after them. Source labels contain no commas.
- `top_cancer_sources`: the 3 largest of 8 broad source groups (EPA's column prefixes):
  Point sources (PT), On-road mobile (OR), Nonroad mobile (NR, which includes commercial
  marine vessels, locomotives, airports and railyards), Nonpoint (NP), Fires, Biogenics,
  Secondary formation, Background.
- `top_cancer_source_types`: the 3 largest of EPA's 37 detailed source types, leaving out
  secondary formation and background. Those two are almost the same across the study
  area, so the broad top-3 is identical in every tract. Labels shorten the mapping tool's names.
- `cancer_risk_by_source_group`: all 8 broad groups (two decimals).
- `top_respiratory_pollutants`: the 3 largest hazard quotients.
- Also `tract_label`, `nta_name` (from `acs.geojson`), `population_2020` (sum of EPA's
  block populations, Census 2020), `n_blocks`, `no_population`, `assessment_year` (2020),
  `tract_vintage` (2020). The FeatureCollection `metadata` holds the context medians.
- Three tracts have no populated blocks in EPA's files and are null with
  `no_population: true`: 36047003102 (Fort Greene) and 36047057902 and 36047058902
  (Greenpoint). Three tracts that the ACS gives 0 population do have populated Census 2020
  blocks in EPA's files, so they get values: 36047044902 (East Williamsburg, 44 people in
  6 blocks), 36047040700 (The Evergreens Cemetery, 6 people, 1 block) and 36047054300
  (Brooklyn Navy Yard, 5 people, 1 block). These three are also the three lowest values.
- The national tract table is cached as `airtoxscreen2020_tract_totals.json` in
  `$NAG_CACHE`. A cold run downloads about 2.5 GB of workbooks. With python-calamine
  installed (`pip install python-calamine`) it reads them in about 9 minutes; openpyxl is
  used as a fallback but is about 7× slower.

Result of the 2026-10-23 run (167 tracts, 164 with values):
- `cancer_risk_per_million` **32.9–40.5**. The values are tightly clustered: 139 of the
  164 tracts are between 35.0 and 36.9.
  - Highest: Greenpoint, which holds the 10 highest tracts.
  - Lowest: the three nearly empty tracts above. Among residential tracts, Bushwick and
    Bedford-Stuyvesant are lowest.
- `respiratory_hi` **0.42–0.54**. Every tract is well below 1. Highest in Greenpoint,
  lowest in the same nearly empty tracts, Bushwick and Bedford-Stuyvesant.
- National percentile 71–94, state percentile 68–99.
- Top pollutants in all 164 tracts: formaldehyde (18.7–21.5 per million), then carbon
  tetrachloride (3.0, the same everywhere; it is a long-lived global pollutant that is
  almost entirely background) and benzene (2.5–3.5), in either order depending on the
  tract.
- Top source groups in all 164 tracts: secondary formation (15.4–15.8), nonpoint
  (5.8–8.6), nonroad mobile (4.3–6.8). On-road mobile is 2.5–4.4, background 3.0 and point
  sources 0.6–1.4. Top detailed types: solvents and coatings, commercial cooking, then
  either on-road light-duty gas off-network or nonroad commercial equipment.
- Top respiratory HQs in all tracts: formaldehyde, acetaldehyde, acrolein. Diesel PM is
  fourth in every tract (HQ 0.05–0.08).
- Context (tract-level, same method): US median **29.2**, New York State median 28.3,
  **NYC median 35.2** (2,292 tracts). Population-weighted means: US 30.1 (EPA: "the
  national average risk from air toxics exposure in 2020 was 30-in-1 million"), Kings
  County 34.7 (EPA publishes it rounded as 30).
- Map class breaks are in `js/styles.js`. They separate small differences: the whole
  study-area range of cancer risk is less than one of EPA's rounding steps, so present the
  classes as relative levels within the study area, not as meaningful health differences.

Caveats (EPA's wording in quotes):
- **Screening tool.** "EPA developed AirToxScreen as a screening tool for State, Local and
  Tribal air agencies. AirToxScreen's results help these agencies identify which
  pollutants, emission sources and places they may wish to study further." "Often, more
  localized studies are needed to better characterize local-level risk." Results "should
  not be used … as a definitive means to pinpoint specific risk values within a census
  tract or census block" or "to characterize or compare risks at local levels (such as
  between neighborhoods)" (TSD §1.6). Comparing study-area tracts with each other is exactly
  this kind of local comparison, so treat the map as a pattern, not a ranking.
- **Lifetime, continuous, modeled.** Risks are "lifetime risks, meaning the risk of
  developing cancer due to inhalation exposure to each air toxic compound over a normal
  lifetime of 70 years". AirToxScreen "assume[s] a person breathes the air toxics emitted
  in the analysis every day for 70 years" at 2020 emission levels. Concentrations are
  "based on computer model simulations, not direct measurements". "A lifetime cancer risk
  of 1-in-1 million means that, for every 1 million people who are continuously exposed to
  a certain level of a pollutant over 70 years, one person may develop cancer. These risks
  are on top of any other cancer risks from other sources."
- **Not individual risk.** Results "are meant to represent an average across an area (i.e.,
  a census block) and are not meant to represent risks to an individual person or specific
  place". "AirToxScreen isn't designed to predict actual risks at a specific place."
- **Diesel PM excluded from cancer risk.** "The assessment does not quantify cancer risk
  from diesel PM, although EPA has concluded that the general population is exposed to
  levels close to or overlapping with levels that have been linked to increased cancer
  risk in epidemiology studies." Diesel PM is in the respiratory HI only. This matters near
  the BQE, truck routes and the waterfront.
- **Precision.** EPA says: "we round all calculated risks from 25-in-1 million through
  34 in-1-million to 30-in-1 million" because more digits would be "false precision". By
  EPA's convention every study-area tract is "30" or "40" in a million. The decimals here
  come from aggregating EPA's unrounded components and show relative position only.
- **Hazard index.** "A hazard index (HI) of 1 or lower means air toxics are unlikely to
  cause adverse noncancer health effects over a lifetime of exposure." An HI above 1
  "cannot be interpreted as a statistical probability of adverse effects occurring". The
  2020 HI here is a reconstruction from EPA's published inputs, not an EPA-published value.
- **Scope.** Inhalation only; outdoor-released air toxics only (no indoor sources); US
  sources only; no criteria pollutants (PM2.5, NO2, ozone; see `air_pm25` / `air_no2`);
  only the air toxics with dose-response values. Background concentrations are regional
  averages. Episodic releases may be missed. The 2020 inventory reflects pandemic-year
  activity. EPA's "Risk Changes" caveat layer (`Cancer_Risk_2020_Caveats`) flags no blocks
  in New York City.
- Most of the total comes from pollutants that are uniform at this scale (secondary
  formaldehyde/acetaldehyde, background, carbon tetrachloride). Differences between
  study-area tracts come mostly from nonpoint, nonroad and on-road sources.

## basemap overlays

`data/basemap/*.geojson`, from `scripts/build_basemap_overlays.py`. They are drawn over the
basemap tiles.

| File | Source and processing |
|---|---|
| `truck_routes_through.geojson`, `truck_routes_local.geojson` | NYC DOT **New York City Truck Routes**, NYC Open Data `jjja-shxy` (updated 2026-03-02). Split on `routetype` (`Through` / `Local`), clipped to the study area + 300 m, merged per street and simplified at 2 m. The buffer takes in some Queens and Manhattan approaches across Newtown Creek and the East River. Property: `street` (title case). Through: 58 streets; local: 112. |
| `zip_boundaries.geojson` | U.S. Census Bureau **2020 ZIP Code Tabulation Areas**, TIGERweb `PUMA_TAD_TAZ_UGA_ZCTA/MapServer/1`. A ZCTA is used when at least 10% of its land area (`AREALAND`) lies inside the districts. Draws the ZCTA boundaries inside the districts, leaving out a 25 m band along the outline (the mask draws the outline). Simplified at 2 m; no properties. |
| `zip_labels.geojson` | One point per selected ZCTA: `representative_point()` of the largest part of the ZCTA inside the districts. Property: `zipcode`. ZCTAs: 11201, 11205, 11206, 11207, 11211, 11216, 11217, 11221, 11222, 11233, 11237, 11238, 11249. |
| `area_mask.geojson` | The districts' bounding box plus 0.1° on each side, minus the dissolved districts (simplified at 1.5 m). Drawn grey outside the study area. |

Why Census ZCTAs and not DOHMH MODZCTA (`pri4-ifjk`): MODZCTA merges 11249 into 11211
(label "11211, 11249") and 11243 into 11217. Williamsburg's waterfront ZIP code would
lose its own boundary. Note that ZCTAs approximate USPS ZIP code delivery areas. They
are not the same thing. Point-only ZIP codes (e.g. 11241–11243, 11251) have no ZCTA.
