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

  return {
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
