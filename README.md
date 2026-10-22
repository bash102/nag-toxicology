# NAG Brooklyn's Greenpoint - Williamsburg Toxicity Map
An interactive map for [Neighbors Allied For Good Growth](http://nag-brooklyn.org/) showing pollution and demographic data in the neighborhoods of Greenpoint and Williamsburg in Brooklyn, New York.

Created Summer / Fall, 2015 for [Pratt](https://www.pratt.edu/)'s [Spatial Analysis and Visualization Initiative](https://www.pratt.edu/pratt-research-and-centers/spatial-analysis-visualization-initiative/).

## 2026 Update
This is a fork of [clhenrick/greenpoint_williamsburg_toxicity_map](https://github.com/clhenrick/greenpoint_williamsburg_toxicity_map). By 2026 the original map had stopped working because every hosted service it relied on had shut down:

- **Data layers:** the `nag-brooklyn` CARTO account that held the data no longer exists.
- **Basemap:** the custom Mapbox basemap's access token is revoked.
- **Address search:** Mapzen Search shut down in 2018.

The fork fixes this as follows:

- **Map library:** the map now uses [Leaflet](https://leafletjs.com/) 1.9 directly, in place of cartodb.js and mapbox.js.
- **Basemap:** [Esri's Light Gray Canvas](https://www.arcgis.com/home/item.html?id=8b3d38c0819547faa83f7b7aca80bd76) tiles are the base. The original basemap's truck routes, zip code boundaries and Community District 1 mask are drawn on top, from the shapefiles in `basemap/data/`.
- **Address search:** it uses [NYC GeoSearch](https://geosearch.planninglabs.nyc/), a free Pelias geocoder from NYC Planning that needs no API key.
- **Data layers:** they are rebuilt from current public data, such as ACS 2020-2024, NYS DOH asthma rates, NYC 2050s floodplains, EPA ECHO, NYC (E) designations, NYS DEC spills and remediation sites, NYC OER cleanup sites and DEC solid waste facilities. The layers are stored as GeoJSON in `data/`. See [`data/SOURCES.md`](data/SOURCES.md) for every source and processing step. These are new datasets, so values and site lists differ from the 2015 map.
- **New layers (2026):** air pollution (NYC Community Air Survey PM2.5 and NO2), combined sewer overflow outfalls, harbor water quality, lead water service lines, and adult health conditions from CDC PLACES with a picker for the condition shown.
- **Walking tour:** the **Industrial History Walking Tour** layer is disabled. Its stops were NAG's own content, stored only in the deleted CARTO account. To restore it, add `data/industrial_history_points.geojson` (points with a numeric `stop` property giving the tour order, plus `name`, `address`, `type_of_industry_present_or_former`, `description`, `source_one` and `source_two`), then remove `disabled` from the `#industry` button in `index.html`.

## Running Locally
The map loads its data with XHR, so serve the folder over HTTP rather than opening `index.html` directly:

```
python3 -m http.server 8000
```

Then visit http://localhost:8000.

## Publishing
`.github/workflows/pages.yml` publishes the map to GitHub Pages whenever `main` changes, at https://bash102.github.io/nag-toxicology/. To turn it on the first time, open the repository's **Settings > Pages** and set **Source** to **GitHub Actions**, then re-run the workflow from the **Actions** tab (or push to `main`).

## Dependencies
Loaded from CDNs in `index.html`:

- Leaflet
- jQuery
- jQuery UI
- Font Awesome

Bundled in the repo:

- Handlebars.js (`js/bower_components/`)
- the Pelias Leaflet geocoder (`js/pelias-leaflet-geocoder.js`)
- Normalize.css

## Rebuilding the Data
The scripts in `scripts/` download the public sources and write `data/`. They need Python 3 with `pyshp`, `shapely`, `pyproj`, `rasterio` and `numpy`, plus the `pdftotext` command (poppler-utils) for the sewer overflow report.

```
python3 scripts/build_all.py               # data layers
python3 scripts/build_basemap_overlays.py  # truck routes, zip codes, CD1 mask
```

## Updating the Data Layers' Styles
Layer styles are in `js/styles.js`, which is a port of the original CartoCSS. Legends are in `js/legendstyles.js`. If you change a layer's class breaks or colors, update both files.

## Original Data Processing in CartoDB
See the `sql/` directory for the 2015 code that formatted the original data tables in CartoDB / Postgres.

## Creating The Basemap Tiles
The original custom basemap required [Mapbox Studio Classic](https://www.mapbox.com/mapbox-studio-classic/), which has been discontinued. The `basemap/` directory contains:

- `tm2/`: the files specifying the styling of the basemap's tiles.
- `data/`: zipped ESRI Shapefiles used by the basemap. These are also the source for `data/basemap/`.
- `toxicity-basemap.tm2z`: the project's styles and metadata in a compressed format.

## Contributors:
- [Chris Henrick](https://github.com/clhenrick/)
- [Bowon Chung](https://github.com/bowon)