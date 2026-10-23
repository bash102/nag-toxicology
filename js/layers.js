var app = app || {};

// Definitions for the map's data-layers.
// Each layer is a GeoJSON file in data/ that is drawn with Leaflet using the
// styles in app.styles (ported from the original CartoCSS).
app.layers = (function(){

  var styles = app.styles;

  // popup labels for every cancer type, so only the popup's fields need to follow the cancer type picker
  var cancerMeasures = styles.layerMeasures.cancer_mapping,
      cancerFieldLabels = { total_population: 'Population' },
      cancerValueLabels = {};

  Object.keys(cancerMeasures).forEach(function(key) {
    cancerFieldLabels[key + '_obs'] = cancerMeasures[key].label + ': cases diagnosed';
    cancerFieldLabels[key + '_exp'] = 'Cases expected for this population';
    cancerFieldLabels[key + '_ratio'] = 'Observed / expected';
    cancerFieldLabels[key + '_sig'] = 'NYS DOH assessment';
    cancerValueLabels[key + '_sig'] = {
      higher: 'Part of an area with more cases than expected',
      lower: 'Part of an area with fewer cases than expected',
      'not significant': 'Not part of a flagged area'
    };
  });

  return {
      sublayers: [{
          name: 'acs_pop',
          choropleth: true,
          url: 'data/acs.geojson',
          style: styles.popdensity,
          interactivity: "people_per_square_mile"
      }, {
          name: 'acs_income',
          choropleth: true,
          url: 'data/acs.geojson',
          style: styles.income,
          interactivity: "median_household_income, percent_hispanic, percent_nonhispanic_black, percent_nonhispanic_asian, percent_nonhispanic_white"
      }, {
          name: 'asthma',
          choropleth: true,
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
      }, {
          name: 'air_pm25',
          choropleth: true,
          url: 'data/air_pm25.geojson',
          style: styles.pm25,
          interactivity: "label, period",
          fieldLabels: { label: "Annual average PM2.5" }
      }, {
          name: 'air_no2',
          choropleth: true,
          url: 'data/air_no2.geojson',
          style: styles.no2,
          interactivity: "label, period",
          fieldLabels: { label: "Annual average NO2" }
      }, {
          name: 'air_toxics_risk',
          choropleth: true,
          url: 'data/air_toxics_risk.geojson',
          style: styles.airToxicsRisk,
          interactivity: "nta_name, cancer_risk_per_million, cancer_risk_pctile_national, cancer_risk_pctile_state, top_cancer_pollutants, top_cancer_sources, top_cancer_source_types, respiratory_hi, top_respiratory_pollutants",
          fieldLabels: {
            nta_name: "Neighborhood",
            cancer_risk_per_million: "Lifetime cancer risk, cases per million people",
            cancer_risk_pctile_national: "National percentile (100 = highest risk)",
            cancer_risk_pctile_state: "New York State percentile",
            top_cancer_pollutants: "Main pollutants (risk per million)",
            top_cancer_sources: "Main sources (risk per million)",
            top_cancer_source_types: "Main source types (risk per million)",
            respiratory_hi: "Respiratory hazard index (1 or more = concern)",
            top_respiratory_pollutants: "Main respiratory irritants"
          }
      }, {
          name: 'lead_service_lines',
          choropleth: true,
          url: 'data/lead_service_lines.geojson',
          style: styles.leadServiceLines,
          interactivity: "pct_lead_or_grr, pct_unknown, total_lines, lead, galvanized_requiring_replacement, unknown, non_lead, inventory_date",
          percentFields: ["pct_lead_or_grr", "pct_unknown"],
          fieldLabels: {
            pct_lead_or_grr: "Lead or galvanized lines needing replacement",
            pct_unknown: "Material unknown",
            total_lines: "Service lines in area",
            lead: "Lead lines",
            galvanized_requiring_replacement: "Galvanized lines needing replacement",
            unknown: "Unknown material lines",
            non_lead: "Non-lead lines",
            inventory_date: "Inventory date"
          }
      }, {
          name: 'health_conditions',
          choropleth: true,
          url: 'data/health_conditions.geojson',
          style: styles.healthConditions,
          interactivity: "nta_name, casthma, copd, cancer, chd, diabetes, bphigh, mhlth, csmoking",
          percentFields: ["casthma", "copd", "cancer", "chd", "diabetes", "bphigh", "mhlth", "csmoking"],
          fieldLabels: {
            nta_name: "Neighborhood",
            casthma: "Adults with asthma",
            copd: "Adults with COPD",
            cancer: "Adults ever diagnosed with cancer (excluding skin cancer)",
            chd: "Adults with coronary heart disease",
            diabetes: "Adults with diabetes",
            bphigh: "Adults with high blood pressure",
            mhlth: "Adults with frequent poor mental health",
            csmoking: "Adults who smoke"
          }
      }, {
          name: 'cancer_mapping',
          choropleth: true,
          url: 'data/cancer_mapping.geojson',
          style: styles.cancerMapping,
          // fields for the cancer type picked in the map layers menu
          interactivity: function() {
            var key = styles.selectedMeasure('cancer_mapping');
            return [key + '_obs', key + '_exp', key + '_ratio', key + '_sig', 'total_population'].join(',');
          },
          fieldLabels: cancerFieldLabels,
          valueLabels: cancerValueLabels
      }, {
          name: 'cso_outfalls',
          url: 'data/cso_outfalls.geojson',
          marker: styles.csoOutfalls,
          interactivity: "outfall_id, name, receiving_water, facility, overflow_events, overflow_volume_mg, overflow_period, detection, link, source",
          fieldLabels: {
            outfall_id: "Outfall",
            overflow_events: "Overflow events",
            overflow_volume_mg: "Overflow volume (million gallons)"
          }
      }, {
          name: 'harbor_water_quality',
          url: 'data/harbor_water_quality.geojson',
          marker: styles.harborWaterQuality,
          interactivity: "station, waterbody, water_quality_class, fecal_coliform_geomean, enterococci_geomean, do_mean_mg_l, pct_do_below_standard, n_samples, period, latest_sample_date, source",
          percentFields: ["pct_do_below_standard"],
          fieldLabels: {
            water_quality_class: "Water quality",
            fecal_coliform_geomean: "Fecal coliform (geometric mean, per 100 mL)",
            enterococci_geomean: "Enterococci (geometric mean, per 100 mL)",
            do_mean_mg_l: "Dissolved oxygen (mean, mg/L)",
            pct_do_below_standard: "Samples with low dissolved oxygen",
            n_samples: "Samples"
          }
      }]
  }
})();
