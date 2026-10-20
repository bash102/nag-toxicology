var app = app || {};

// Definitions for the map's data-layers.
// Each layer is a GeoJSON file in data/ that is drawn with Leaflet using the
// styles in app.styles (ported from the CartoCSS in mss/).
app.layers = (function(){

  var styles = app.styles;

  return {
      sublayers: [{
          name: 'acs_pop',
          url: 'data/acs.geojson',
          style: styles.popdensity,
          interactivity: "people_per_square_mile"
      }, {
          name: 'acs_income',
          url: 'data/acs.geojson',
          style: styles.income,
          interactivity: "median_household_income, percent_hispanic, percent_nonhispanic_black, percent_nonhispanic_asian, percent_nonhispanic_white"
      }, {
          name: 'asthma',
          url: 'data/asthma.geojson',
          style: styles.asthma,
          interactivity: "geography_name, asthma_rate_per_1000_people, measure, period"
      }, {
          name: 'flood_risk',
          url: 'data/flood_risk.geojson',
          style: styles.floodrisk,
          interactivity: ""
      }, {
          name: 'polluted_polygons',
          url: 'data/polluted_polygons.geojson',
          style: styles["polluted-areas"],
          interactivity: "site_or_owner_name, address, description, program, link, reference_number"
      }, {
          name: 'industrial_history_lines',
          url: 'data/industrial_history_points.geojson',
          style: styles["industrial-history-lines"],
          toLine: true,
          interactivity: ""
      }, {
          name: 'industrial_history_points',
          url: 'data/industrial_history_points.geojson',
          marker: styles["industrial-history-points"],
          interactivity: "name, address, type_of_industry_present_or_former, description, source_one, source_two"
      }, {
          name: 'polluted_points',
          url: 'data/polluted_points.geojson',
          marker: styles["polluted-points"],
          interactivity: "name, category, description, address, date, program, link, source",
          valueLabels: {
            category: {
              highly_regulated: "Highly Regulated Site",
              e_designation: "E-Designated Lot",
              spill_major: "Spill >= 100 Gallons",
              spill_minor: "Spill < 100 Gallons"
            }
          }
      }, {
          name: 'waste_transfer_stations',
          url: 'data/waste_transfer_stations.geojson',
          marker: styles.wts,
          interactivity: "name, facility_type, address, source"
      }]
  }
})();
