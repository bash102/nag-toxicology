var app = app || {};

// Leaflet styles for the map's data-layers, ported from the original CartoCSS.
// Polygon & line styles take a GeoJSON feature and return a Leaflet path style.
// Marker styles also take the current zoom level and return circleMarker options.
// Keep the class breaks & colors in sync with js/legendstyles.js
app.styles = (function(){

  // returns the color of the first class whose minimum the value meets
  function classify(value, classes, fallback) {
    if (value === null || value === undefined || isNaN(value)) return fallback;
    for (var i = classes.length - 1; i >= 0; i--) {
      if (value >= classes[i][0]) return classes[i][1];
    }
    return fallback;
  }

  // picks a value for the current zoom from {minZoom: value} pairs
  function byZoom(zoom, steps) {
    var result;
    Object.keys(steps).map(Number).sort(function(a, b) { return a - b; }).forEach(function(z) {
      if (zoom >= z) result = steps[z];
    });
    return result;
  }

  function popdensity(feature) {
    return {
      fillColor: classify(feature.properties.people_per_square_mile, [
        [0, '#fcfaef'],
        [25001, '#f0ecd7'],
        [40001, '#e8dc91'],
        [55001, '#dfcd66'],
        [75001, '#cfb928']
      ], '#ffffff'),
      fillOpacity: 0.7,
      color: '#696969',
      weight: 0.5,
      opacity: 0.5
    };
  }

  function income(feature) {
    return {
      fillColor: classify(feature.properties.median_household_income, [
        [0, '#dcf5e8'],
        [50001, '#a5d0b4'],
        [90001, '#75ab7e'],
        [130001, '#4f8759'],
        [160001, '#216437']
      ], '#ECF0F6'),
      fillOpacity: 0.8,
      color: '#000000',
      weight: 0.5,
      opacity: 0.1
    };
  }

  function asthma(feature) {
    return {
      fillColor: classify(feature.properties.asthma_rate_per_1000_people, [
        [0, '#bfa4cd'],
        [6, '#9c7aac'],
        [10, '#7a518b'],
        [21, '#5a3072']
      ], '#ffffff'),
      fillOpacity: 0.7,
      color: '#666666',
      weight: 0.5,
      opacity: 0.5
    };
  }

  function floodrisk(feature) {
    return {
      fillColor: feature.properties.storm === '500' ? '#93a5b6' : '#2E5387',
      fillOpacity: 0.5,
      stroke: false
    };
  }

  function pollutedAreas() {
    return {
      fillColor: '#FFCC00',
      fillOpacity: 0.6,
      color: '#FFF',
      weight: 0.4,
      opacity: 1
    };
  }

  function industrialHistoryLines(feature, zoom) {
    return {
      color: '#2E5387',
      weight: zoom >= 16 ? 6 : 4,
      opacity: 0.5,
      dashArray: zoom >= 16 ? '0.3,15' : '0.2,10',
      lineCap: 'round',
      interactive: false
    };
  }

  function industrialHistoryPoints(feature, zoom) {
    return {
      radius: (zoom >= 16 ? 14 : 10) / 2,
      fillColor: '#2E5387',
      fillOpacity: 0.9,
      color: '#FFF',
      weight: 1,
      opacity: 1
    };
  }

  // keys match the "category" property of data/polluted_points.geojson
  var pollutedPointColors = {
    spill_major: '#9801d6',
    e_designation: '#f7b699',
    highly_regulated: '#a50008',
    spill_minor: '#e171fb'
  };

  function pollutedPoints(feature, zoom) {
    var category = feature.properties.category,
        large = category === 'spill_major' || category === 'highly_regulated',
        width = large ?
          byZoom(zoom, {0: 9, 12: 6, 13: 8, 14: 10, 16: 12, 18: 14}) :
          byZoom(zoom, {0: 6, 12: 4, 13: 5, 14: 6, 16: 8, 18: 10});

    return {
      radius: width / 2,
      fillColor: pollutedPointColors[category] || '#999999',
      fillOpacity: 0.9,
      color: '#FFFFFF',
      weight: 0.5,
      opacity: 0.7
    };
  }

  function wts(feature, zoom) {
    return {
      radius: byZoom(zoom, {0: 7, 12: 6, 13: 8, 14: 10, 16: 12, 18: 14}) / 2,
      fillColor: '#FFFFFF',
      fillOpacity: 0,
      color: '#010101',
      weight: byZoom(zoom, {0: 3.5, 12: 1.5, 13: 2.5, 14: 3, 16: 4, 18: 5}),
      opacity: 0.7
    };
  }

  // NYCCAS air pollution surfaces, one feature per band (1 = lowest)
  var pm25Colors = ['#fef0d9', '#fdcc8a', '#fc8d59', '#e34a33', '#b30000'],
      no2Colors = ['#edf8fb', '#b3cde3', '#8c96c6', '#8856a7', '#810f7c'];

  function airBand(colors) {
    return function(feature) {
      return {
        fillColor: colors[feature.properties.band - 1] || '#ffffff',
        fillOpacity: 0.6,
        stroke: false
      };
    };
  }

  // fill for areas with no value, eg: tracts with no residents
  var noDataColor = '#ffffff';

  // turns class breaks into legend labels, eg: [5, 10] -> ["Less than 5%", "5 - 10%", "10% or more"]
  function breakLabels(breaks, unit) {
    var labels = ['Less than ' + breaks[0] + unit];
    for (var i = 1; i < breaks.length; i++) {
      labels.push(breaks[i - 1] + ' - ' + breaks[i] + unit);
    }
    labels.push(breaks[breaks.length - 1] + unit + ' or more');
    return labels;
  }

  // legend items for breakLabels, with an optional row for areas with no value
  function breakItems(breaks, colors, unit, noDataLabel) {
    var items = breakLabels(breaks, unit).map(function(label, i) {
      return { color: colors[i], label: label };
    });
    if (noDataLabel) items.push({ color: noDataColor, label: noDataLabel });
    return items;
  }

  // classifies a value with breaks like those passed to breakLabels
  function breakColor(value, breaks, colors, fallback) {
    if (value === null || value === undefined || isNaN(value)) return fallback || noDataColor;
    for (var i = 0; i < breaks.length; i++) {
      if (value < breaks[i]) return colors[i];
    }
    return colors[breaks.length];
  }

  // census tract choropleths share their outline & opacity
  function choropleth(value, breaks, colors) {
    return {
      fillColor: breakColor(value, breaks, colors),
      fillOpacity: 0.7,
      color: '#666666',
      weight: 0.5,
      opacity: 0.5
    };
  }

  // the measure picked for a data-layer with a measure picker, or its first measure
  function selectedMeasure(id) {
    var measures = layerMeasures[id];
    return measures[app.state[id]] ? app.state[id] : Object.keys(measures)[0];
  }

  // CDC PLACES measures, % of adults; keys match data/health_conditions.geojson
  var healthColors = ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'],
      healthMeasures = {
        casthma: { label: 'Asthma', breaks: [9, 9.5, 10, 11.5] },
        copd: { label: 'COPD', breaks: [2.5, 3.5, 5, 10] },
        cancer: { label: 'Cancer (excluding skin cancer)', breaks: [3.5, 4, 4.5, 5.5] },
        chd: { label: 'Coronary heart disease', breaks: [2, 3, 4, 7] },
        diabetes: { label: 'Diabetes', breaks: [4, 6, 9, 13] },
        bphigh: { label: 'High blood pressure', breaks: [15, 18, 22, 30] },
        mhlth: { label: 'Frequent poor mental health', breaks: [14, 15.5, 17, 20] },
        csmoking: { label: 'Smoking', breaks: [6, 8, 11, 17] }
      };

  function healthConditions(feature) {
    var key = selectedMeasure('health_conditions');
    return choropleth(feature.properties[key], healthMeasures[key].breaks, healthColors);
  }

  // DEP service line inventory, % of lots with lead or galvanized lines needing replacement
  var leadColors = ['#f7f7f7', '#cccccc', '#969696', '#636363', '#252525'],
      leadBreaks = [5, 10, 15, 20];

  function leadServiceLines(feature) {
    return choropleth(feature.properties.pct_lead_or_grr, leadBreaks, leadColors);
  }

  // combined sewer overflow outfalls: color by overflow events per year, size by overflow volume
  var csoColors = ['#c6dbef', '#6baed6', '#3182bd', '#08519c', '#08306b'],
      csoBreaks = [1, 10, 20, 30];

  function csoOutfalls(feature, zoom) {
    var volume = feature.properties.overflow_volume_mg,
        size = volume >= 200 ? 18 : volume >= 50 ? 14 : volume >= 10 ? 11 : 8;

    return {
      radius: (size + (zoom >= 16 ? 4 : 0)) / 2,
      fillColor: breakColor(feature.properties.overflow_events, csoBreaks, csoColors),
      fillOpacity: 0.9,
      color: '#08306b',
      weight: 1,
      opacity: 0.8
    };
  }

  // harbor survey stations: color by fecal coliform geometric mean (NYS standard is 200 per 100 mL)
  var harborColors = ['#1a9850', '#fee08b', '#fc8d59', '#d73027'],
      harborBreaks = [201, 401, 801];

  function harborWaterQuality(feature, zoom) {
    return {
      radius: zoom >= 16 ? 11 : 9,
      fillColor: breakColor(feature.properties.fecal_coliform_geomean, harborBreaks, harborColors, '#999999'),
      fillOpacity: feature.properties.active === false ? 0.5 : 0.95,
      color: '#ffffff',
      weight: 2.5,
      opacity: 1
    };
  }

  // NYS DOH cancer mapping, observed / expected cases; keys match data/cancer_mapping.geojson
  // the outer breaks are DOH's own 50% thresholds for higher (1.5) and lower (1 / 1.5) than expected
  var cancerColors = ['#4575b4', '#91bfdb', '#f7f7f7', '#fc8d59', '#d73027'],
      cancerBreaks = [0.67, 0.9, 1.1, 1.5],
      cancerMeasures = {
        all: { label: 'All cancers combined' },
        lung: { label: 'Lung and bronchus' },
        breast: { label: 'Female breast' },
        prostate: { label: 'Prostate' },
        colorectal: { label: 'Colon and rectum' },
        bladder: { label: 'Urinary bladder' },
        kidney: { label: 'Kidney and renal pelvis' },
        leukemia: { label: 'Leukemia' },
        nhl: { label: 'Non-Hodgkin lymphoma' },
        liver: { label: 'Liver and intrahepatic bile duct' },
        pancreas: { label: 'Pancreas' },
        thyroid: { label: 'Thyroid' }
      };

  function cancerMapping(feature) {
    var key = selectedMeasure('cancer_mapping'),
        sig = feature.properties[key + '_sig'],
        style = choropleth(feature.properties[key + '_ratio'], cancerBreaks, cancerColors);

    style.fillOpacity = 0.75;
    // outline the areas DOH flagged as higher or lower than expected
    if (sig === 'higher' || sig === 'lower') {
      style.color = sig === 'higher' ? '#67001f' : '#053061';
      style.weight = 2;
      style.opacity = 0.9;
    }
    return style;
  }

  // EPA AirToxScreen modeled lifetime cancer risk from air toxics, per million people
  var airToxicsColors = ['#feedde', '#fdbe85', '#fd8d3c', '#e6550d', '#a63603'],
      airToxicsBreaks = [35, 36, 37, 39];

  function airToxicsRisk(feature) {
    return choropleth(feature.properties.cancer_risk_per_million, airToxicsBreaks, airToxicsColors);
  }

  // data-layers with a measure picker in the map layers menu
  var layerMeasures = {
    health_conditions: healthMeasures,
    cancer_mapping: cancerMeasures
  };

  return {
    breakLabels: breakLabels,
    breakItems: breakItems,
    selectedMeasure: selectedMeasure,
    layerMeasures: layerMeasures,
    airToxicsColors: airToxicsColors,
    airToxicsBreaks: airToxicsBreaks,
    airToxicsRisk: airToxicsRisk,
    cancerColors: cancerColors,
    cancerBreaks: cancerBreaks,
    cancerMapping: cancerMapping,
    csoColors: csoColors,
    csoOutfalls: csoOutfalls,
    harborColors: harborColors,
    harborWaterQuality: harborWaterQuality,
    healthColors: healthColors,
    healthConditions: healthConditions,
    leadColors: leadColors,
    leadBreaks: leadBreaks,
    leadServiceLines: leadServiceLines,
    pm25Colors: pm25Colors,
    no2Colors: no2Colors,
    pm25: airBand(pm25Colors),
    no2: airBand(no2Colors),
    popdensity: popdensity,
    income: income,
    asthma: asthma,
    floodrisk: floodrisk,
    "polluted-areas": pollutedAreas,
    "industrial-history-lines": industrialHistoryLines,
    "industrial-history-points": industrialHistoryPoints,
    "polluted-points": pollutedPoints,
    wts: wts
  };
})();
