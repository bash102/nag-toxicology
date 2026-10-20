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