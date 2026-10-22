// legend data
var app = app || {};

app.legends = (function(){
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

    asthma : {
      title : "Asthma Rate",
      subtitle : "ER visits per 1,000 people per year, 2013-2017",
      type : 'polygon',
      items : [
        {
          color : "#bfa4cd",
          label : "Less than 6"
        },{
          color : "#9c7aac",
          label : "6 - 9.9"
        },{
          color : "#7a518b",
          label : "10 - 20.9"
        },{
          color : "#5a3072",
          label : "21 or more"
        }
      ]
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
      items : [{ color : app.styles.pm25Colors[0], label : "6.5 - 6.9" },{ color : app.styles.pm25Colors[1], label : "6.9 - 7.3" },{ color : app.styles.pm25Colors[2], label : "7.3 - 7.7" },{ color : app.styles.pm25Colors[3], label : "7.7 - 8.1" },{ color : app.styles.pm25Colors[4], label : "8.1 - 8.5" }]
    },

    air_no2 : {
      title : "Nitrogen Dioxide (NO2)",
      subtitle : "Annual average, ppb, 2024",
      type : 'polygon',
      items : [{ color : app.styles.no2Colors[0], label : "14.5 - 15.5" },{ color : app.styles.no2Colors[1], label : "15.5 - 16.5" },{ color : app.styles.no2Colors[2], label : "16.5 - 17.5" },{ color : app.styles.no2Colors[3], label : "17.5 - 18.5" },{ color : app.styles.no2Colors[4], label : "18.5 - 20.0" }]
    },

    // depends on the health condition picked in the map layers menu
    health_conditions : function() {
      var styles = app.styles,
          measure = styles.healthMeasures[styles.selectedMeasure('health_conditions', styles.healthMeasures)];

      return {
        title : "Health Conditions",
        subtitle : measure.label + ", % of adults, 2023 estimates",
        type : 'polygon',
        items : styles.breakLabels(measure.breaks, '%').map(function(label, i) {
          return { color : styles.healthColors[i], label : label };
        }).concat({ color : "#ffffff", label : "No residents" })
      };
    },

    lead_service_lines : {
      title : "Lead Water Service Lines",
      subtitle : "% of lots with lead or galvanized lines needing replacement, 2026",
      type : 'polygon',
      items : app.styles.breakLabels(app.styles.leadBreaks, '%').map(function(label, i) {
        return { color : app.styles.leadColors[i], label : label };
      })
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
      subtitle : "Fecal coliform, geometric mean per 100 mL, 2023-2025",
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