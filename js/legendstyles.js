// legend data
var app = app || {};

app.legends = (function(){

  // legend items for bands between consecutive edges, eg: ['12', '14', '16'] -> "12 - 14", "14 - 16"
  // the air quality edges match the band breaks in scripts/build_air_quality.py
  function bands(edges, colors) {
    return colors.map(function(color, i) {
      return { color : color, label : edges[i] + ' - ' + edges[i + 1] };
    });
  }

  return {
    acs_pop : {
      title : "Population Density",
      subtitle: "People per sq mile, 2020-2024",
      type : 'polygon',
      items : [
        {
          color : "#fcfaef",
          label : "0 - 25,000"
        },{
          color : "#f0ecd7",
          label : "25,001 - 40,000"
        },{
          color : "#e8dc91",
          label : "40,001 - 55,000"
        },{
          color : "#dfcd66",
          label : "55,001 - 75,000"
        },{
          color : "#cfb928",
          label : "75,001 or more"
        }
      ]
    },

    acs_income : {
      title : "Median Household Income",
      subtitle : "2020-2024, in 2024 dollars",
      type : 'polygon',
      items : [
          {
          color : "#dcf5e8",
          label : "$50,000 or less"
        },{
          color : "#a5d0b4",
          label : "$50,001 - $90,000"
        },{
          color : "#75ab7e",
          label : "$90,001 - $130,000"
        },{
          color : "#4f8759",
          label : "$130,001 - $160,000"
        },{
          color : "#216437",
          label : "$160,001 or more"
        }
      ]
    },

    // depends on the age group picked in the map layers menu
    asthma : function() {
      var styles = app.styles,
          measure = styles.layerMeasures.asthma[styles.selectedMeasure('asthma')];

      return {
        title : "Asthma Emergency Visits",
        subtitle : measure.label + ", per 10,000 per year, " + measure.period,
        type : 'polygon',
        items : styles.breakItems(measure.breaks, styles.asthmaColors, '', "No data")
      };
    },

    flood_risk : {
      title : "Future Flood Risk",
      type : 'polygon',
      items : [
        {
          color : "#93a5b6",
          label : "Projected 500-year storm, 2050s"
        },
        {
          color : "#2E5387",
          label : "Projected 100-year storm, 2050s"
        }
      ]
    },

    polluted_polygons : {
      title : "",
      type : 'polygon',
      items : [
        {
          color : "#FFCC00",
          label : "Polluted and Remediated Sites"
        }
      ]
    },

    industrial_history_points : {
      title : "Industrial History Walking Tour",
      type : "point",
      items : [
        {
          color : "#000000",
          label : "Industrial History Tour Site"
        }
      ]
    },

    polluted_points : {
      title : "Potentially Polluted Sites",
      type : 'point',
      items : [
        {
          color : "#a50008",
          label : "Highly Regulated Sites"
        },
        {
          color : "#f7b699",
          label : "E-Designated"
        },
        {
          color : "#9801d6",
          label : "Spills >= 100 Gallons"
        },
        {
          color : "#e171fb",
          label : "Spills < 100 Gallons"
        }
      ]
    },

    air_pm25 : {
      title : "Fine Particles (PM2.5)",
      subtitle : "Annual average, µg/m³, 2024",
      type : 'polygon',
      items : bands(['5.6', '6.2', '6.8', '7.4', '8.0', '8.6'], app.styles.pm25Colors)
    },

    air_no2 : {
      title : "Nitrogen Dioxide (NO2)",
      subtitle : "Annual average, ppb, 2024",
      type : 'polygon',
      items : bands(['12', '14', '16', '18', '20', '22'], app.styles.no2Colors)
    },

    // depends on the health condition picked in the map layers menu
    health_conditions : function() {
      var styles = app.styles,
          measure = styles.layerMeasures.health_conditions[styles.selectedMeasure('health_conditions')];

      return {
        title : "Health Conditions",
        subtitle : measure.label + ", % of adults, 2023 estimates",
        type : 'polygon',
        items : styles.breakItems(measure.breaks, styles.healthColors, '%', "No residents")
      };
    },

    // depends on the cancer type picked in the map layers menu
    cancer_mapping : function() {
      var styles = app.styles,
          measure = styles.layerMeasures.cancer_mapping[styles.selectedMeasure('cancer_mapping')],
          words = ['Much lower', 'Lower', 'About as expected', 'Higher', 'Much higher'];

      return {
        title : "Cancer Cases",
        subtitle : measure.label + ", observed / expected, 2011-2015. Thick outlines: areas NYS DOH flagged as higher or lower",
        type : 'polygon',
        items : styles.breakItems(styles.cancerBreaks, styles.cancerColors, '').map(function(item, i) {
          return { color : item.color, label : words[i] + ' (' + item.label.toLowerCase() + ')' };
        })
      };
    },

    air_toxics_risk : {
      title : "Cancer Risk from Air Toxics",
      subtitle : "Estimated lifetime cases per million people, 2020 (EPA model)",
      type : 'polygon',
      items : app.styles.breakItems(app.styles.airToxicsBreaks, app.styles.airToxicsColors, '', "No residents")
    },

    lead_service_lines : {
      title : "Lead Water Service Lines",
      subtitle : "% of lots with lead or galvanized lines needing replacement, 2026",
      type : 'polygon',
      items : app.styles.breakItems(app.styles.leadBreaks, app.styles.leadColors, '%')
    },

    cso_outfalls : {
      title : "Combined Sewer Overflows",
      subtitle : "Overflow events in 2025 (DEP model estimates); larger circles overflowed more volume",
      type : 'point-large',
      items : [
        { color : app.styles.csoColors[0], label : "None" },
        { color : app.styles.csoColors[1], label : "1 - 9" },
        { color : app.styles.csoColors[2], label : "10 - 19" },
        { color : app.styles.csoColors[3], label : "20 - 29" },
        { color : app.styles.csoColors[4], label : "30 or more" }
      ]
    },

    harbor_water_quality : {
      title : "Harbor Water Quality",
      subtitle : "Fecal coliform, geometric mean per 100 mL, 2023-2025 (lighter dots: older years, see popup)",
      type : 'point-large',
      items : [
        { color : app.styles.harborColors[0], label : "200 or less (meets NYS standard)" },
        { color : app.styles.harborColors[1], label : "201 - 400" },
        { color : app.styles.harborColors[2], label : "401 - 800" },
        { color : app.styles.harborColors[3], label : "More than 800" }
      ]
    },

    waste_transfer_stations : {
      title : "",
      type : 'point-donut',
      items : [
        {
          color : "#fff",
          label : "Waste Transfer Stations"
        }
      ]
    }
  }
})();