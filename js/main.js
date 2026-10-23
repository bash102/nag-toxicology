var app = app || {};

// user selections that change how a data-layer is drawn, eg: app.state.health_conditions = 'casthma'
app.state = app.state || {};

app.map = (function(w, d, $, H) {

    // "global" variables accessible within the entire app.map scope:
    var sublayers = [], // For storing the data-layers, in the same order as app.layers.sublayers
        map_object, // the Leaflet map
        legend_data = app.legends,
        layerSource = app.layers,
        hb_source = d.getElementById('legend-template').innerHTML,
        hb_template = H.compile(hb_source);

    // register Handlebars JS helpers for rendering legends
    H.registerHelper('each', function(context, options) {
        var ret = "";
        for(var i=0, j=context.length; i<j; i++) {
          ret = ret + options.fn(context[i]);
        }
        return ret;
    });

    H.registerHelper('if', function(conditional, options) {
        if (conditional) {
          return options.fn(this);
        } else {
          return options.inverse(this);
        }
    });

    // create the Leaflet Map
    function initMap() {
        // the study area (Brooklyn Community Districts 1, 2 and 4) and a wider box that limits panning
        var studyArea = L.latLngBounds([40.679, -74.004], [40.740, -73.896]),
            mapBounds = studyArea.pad(0.5);

        // map paramaters to pass to Leaflet
        var params = {
            zoomControl: false,
            zoomSnap: 0.5,
            maxZoom: 19,
            minZoom: 12,
            scrollWheelZoom: false,
            maxBounds: mapBounds,
            attributionControl: true
        };

        map_object = L.map('map', params).fitBounds(studyArea);

        // the custom Mapbox basemap is no longer hosted, so use Esri's light gray canvas basemap
        // with the custom basemap's data layers (truck routes, zip codes) drawn on top of it
        var esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/',
            attr = 'Tiles &copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, ' +
                   '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

        L.tileLayer(esri + 'World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
            attribution: attr,
            maxNativeZoom: 16,
            maxZoom: 19
        }).addTo(map_object);

        // street labels go above the data-layers
        map_object.createPane('labels');
        map_object.getPane('labels').style.zIndex = 650;
        map_object.getPane('labels').style.pointerEvents = 'none';

        L.tileLayer(esri + 'World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
            maxNativeZoom: 16,
            maxZoom: 19,
            pane: 'labels'
        }).addTo(map_object);

        initBasemapOverlays();

        // parameters for the geocoder
        var geocoderOptions = {
            url: 'https://geosearch.planninglabs.nyc/v2',
            attribution: 'Geocoding by <a href="https://geosearch.planninglabs.nyc/">NYC GeoSearch</a>',
            bounds: mapBounds,
            placeholder : 'Search for an address',
            position: 'topright'
        };

        // add the geocoder, NYC GeoSearch is a Pelias API that doesn't need an API key
        L.control.geocoder(null, geocoderOptions).addTo(map_object);

    } // end init map

    // draws the custom basemap's data layers, which sit underneath the data-layers
    function initBasemapOverlays() {
        map_object.createPane('basemapOverlays');
        map_object.getPane('basemapOverlays').style.zIndex = 350;
        map_object.getPane('basemapOverlays').style.pointerEvents = 'none';

        var overlays = [{
            url: 'data/basemap/area_mask.geojson',
            style: { fillColor: '#a0a090', fillOpacity: 0.3, stroke: false }
        }, {
            url: 'data/basemap/zip_boundaries.geojson',
            style: { color: '#4b4b51', weight: 1, opacity: 0.4, dashArray: '6,6' }
        }, {
            url: 'data/basemap/truck_routes_local.geojson',
            style: { color: '#dfa7c9', weight: 1.8, opacity: 0.5 }
        }, {
            url: 'data/basemap/truck_routes_through.geojson',
            style: { color: '#ab819c', weight: 2.5, opacity: 0.6 }
        }];

        // load the overlays in sequence so they stack in the order above
        overlays.reduce(function(prev, overlay) {
            return prev.then(function() {
                return $.getJSON(overlay.url).then(function(data) {
                    L.geoJSON(data, {
                        pane: 'basemapOverlays',
                        interactive: false,
                        style: overlay.style
                    }).addTo(map_object);
                });
            });
        }, $.Deferred().resolve().promise()).fail(function(err) {
            console.log('error loading basemap overlays: ', err);
        });

        $.getJSON('data/basemap/zip_labels.geojson').done(function(data) {
            L.geoJSON(data, {
                pointToLayer: function(feature, latlng) {
                    return L.marker(latlng, {
                        pane: 'basemapOverlays',
                        interactive: false,
                        icon: L.divIcon({
                            className: 'zip-label',
                            html: feature.properties.zipcode,
                            iconSize: [80, 24],
                            iconAnchor: [40, 12]
                        })
                    });
                }
            }).addTo(map_object);
        });
    }

    // turns a property name such as "link_for_more_information" into "Link for more information"
    function humanize(field) {
        var text = field.replace(/_/g, ' ');
        return text.charAt(0).toUpperCase() + text.slice(1);
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, function(c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function formatValue(field, value, source) {
        var valueLabels = source.valueLabels,
            percentFields = source.percentFields || [];

        if (valueLabels && valueLabels[field] && valueLabels[field][value]) {
            return escapeHtml(valueLabels[field][value]);
        }
        if (typeof value === 'number') {
            if (field.indexOf('percent') === 0 || percentFields.indexOf(field) !== -1) return value.toFixed(1) + '%';
            if (field.indexOf('income') !== -1) return '$' + Math.round(value).toLocaleString();
            return value.toLocaleString();
        }
        var text = escapeHtml(value);
        if (/^https?:\/\//.test(value)) {
            return '<a target="_blank" rel="noopener" href="' + text + '">' + text + '</a>';
        }
        return text;
    }

    // builds the info-window content from the layer's interactivity fields
    function popupContent(fields, properties, source) {
        var fieldLabels = source.fieldLabels || {},
            html = fields.filter(function(field) {
            var value = properties[field];
            return value !== null && value !== undefined && value !== '';
        }).map(function(field) {
            return '<h4>' + escapeHtml(fieldLabels[field] || humanize(field)) + '</h4><p>' + formatValue(field, properties[field], source) + '</p>';
        }).join('');

        return '<div class="map-popup-content">' + (html || '<p>No data for this area.</p>') + '</div>';
    }

    // joins the walking tour stops into a line, in the order of their "stop" property
    function tourLine(data) {
        var coords = data.features.slice().sort(function(a, b) {
            return a.properties.stop - b.properties.stop;
        }).map(function(feature) {
            return feature.geometry.coordinates;
        });

        return {
            type: 'Feature',
            properties: {},
            geometry: { type: 'LineString', coordinates: coords }
        };
    }

    // creates a data-layer that downloads its GeoJSON the first time it is shown
    function createSubLayer(source) {
        var group = L.featureGroup(),
            geojson = null,
            request = null,
            visible = false;

        // hidden layers are restyled when shown
        function restyle() {
            if (!geojson || !map_object.hasLayer(group)) return;
            var zoom = map_object.getZoom();
            geojson.eachLayer(function(layer) {
                var style = source.marker ?
                    source.marker(layer.feature, zoom) :
                    source.style(layer.feature, zoom);
                layer.setStyle(style);
                if (style.radius) layer.setRadius(style.radius);
            });
        }

        // built when opened, so a layer's fields can follow its measure picker
        function popup(layer) {
            var fields = typeof source.interactivity === 'function' ? source.interactivity() : source.interactivity;
            return popupContent(fields.replace(/ /g, '').split(','), layer.feature.properties, source);
        }

        function load() {
            if (request) return request;

            request = $.getJSON(source.url).done(function(data) {
                if (source.toLine) data = tourLine(data);

                geojson = L.geoJSON(data, {
                    style: function(feature) {
                        return (source.style || source.marker)(feature, map_object.getZoom());
                    },
                    pointToLayer: function(feature, latlng) {
                        return L.circleMarker(latlng, source.marker(feature, map_object.getZoom()));
                    },
                    onEachFeature: function(feature, layer) {
                        if (source.interactivity) {
                            layer.bindPopup(popup, { maxWidth: 240, maxHeight: 220 });
                        }
                    }
                });
                group.addLayer(geojson);
            }).fail(function(xhr, status, error) {
                console.log('error loading data-layer ' + source.name + ': ', error || status);
                showLayerError(source.name);
            });

            return request;
        }

        map_object.on('zoomend', restyle);

        return {
            name: source.name,
            restyle: restyle,
            show: function() {
                visible = true;
                load().done(function() {
                    if (visible) {
                        group.addTo(map_object);
                        restyle();
                        // keep polygons beneath points
                        if (source.marker) group.bringToFront(); else group.bringToBack();
                    }
                });
            },
            hide: function() {
                visible = false;
                group.remove();
            }
        };
    }

    // tells the user a data-layer couldn't be loaded
    function showLayerError(id) {
        var $legend = $('#legend-' + id);
        if ($legend.length && !$legend.find('.layer-error').length) {
            $legend.append('<p class="layer-error">This layer\'s data could not be loaded.</p>');
        }
    }

    // set up the map's data-layers
    function initDataLayers() {
        layerSource.sublayers.forEach(function(source) {
            sublayers.push(createSubLayer(source));
        });
    }

    // gets a data-layer's numeric index or text id from the app.layers.sublayers
    function getSubLayerIndex(val) {
        var idx = null;
        if (typeof val === 'number') {
            layerSource.sublayers.forEach(function(d,i){
                if (val === i) {
                    idx = d.name;
                }
            });
        } else {
            layerSource.sublayers.forEach(function(d,i){
                if (d.name === val) {
                    idx = i;
                }
            });
        }
        return idx;
    }

    // hide or show the data layer
    function hideShow(id) {
        var id_hash = '#' + id + '.data-layer', // the button id
            $button = $(id_hash); // the button itself

        if ($button.prop('disabled')) return;

        if (id === "industry") {
            var a = getSubLayerIndex('industrial_history_lines'),
                b = getSubLayerIndex('industrial_history_points');

            // if the layer is already selected turn it off
            if ($button.hasClass('active')) {
                sublayers[a].hide();
                sublayers[b].hide();
                removeLegend('industrial_history_points');
                $button.removeClass('active');

            } else if (!$button.hasClass('active')) {
                // otherwise turn it on
                sublayers[a].show();
                sublayers[b].show();
                renderLegend('industrial_history_points');
                $button.addClass('active');
            }

        } else if (id === "polluted") {
            var a = getSubLayerIndex('polluted_points'),
                b = getSubLayerIndex('polluted_polygons');

            // if the layer is already selected turn it off
            if ($button.hasClass('active')) {
                sublayers[a].hide();
                sublayers[b].hide();
                removeLegend('polluted_points');
                removeLegend('polluted_polygons');
                $button.removeClass('active');

            } else if (!$button.hasClass('active')) {
                // otherwise turn it on
                sublayers[a].show();
                sublayers[b].show();
                renderLegend('polluted_points');
                renderLegend('polluted_polygons');
                $button.addClass('active');
            }

        } else {

            var index = getSubLayerIndex(id); // numeric index of the data-layer in the sublayers array

            // if the layer is already selected turn it off
            if ($button.hasClass('active')) {
                sublayers[index].hide();
                removeLegend(id);
                $button.removeClass('active');
            
            } else {
                // otherwise turn it on
                sublayers[index].show();
                renderLegend(id);
                $button.addClass('active');

                // remove other choropleth legends & layers if they are displayed,
                // multiple choropleth layers displayed simultaneously look muddy and aren't a useful UX
                if (layerSource.sublayers[index].choropleth) {
                    layerSource.sublayers.forEach(function(source, i) {
                        if (i !== index && source.choropleth) {
                            removeLegend(source.name);
                            sublayers[i].hide();
                            $('#' + source.name + '.data-layer').removeClass('active');
                            $('.layer-options[data-layer="' + source.name + '"]').hide();
                        }
                    });
                }
            }

            $('.layer-options[data-layer="' + id + '"]').toggle($button.hasClass('active'));
        }
    }
    
    // renders the data-layer's legend using Handlebars JS
    function renderLegend(id) {
        var data = legend_data[id];
        if (typeof data === 'function') data = data();
        data.id = id;

        $('#map-legend-container').append(hb_template(data));
    }

    // removes the data-layer's legend
    function removeLegend(id) {
        $('#legend-' + id).remove();
    }

    /***
        Map Interaction Event Listeners
    ***/

    // load the appropriate data-layer on its corresponding button click
    $('.data-layer').click(function() {
        var layer = $(this).attr('id');
        hideShow(layer);
        if ($(this).hasClass('active')) $(d).trigger('layer:shown', layer);
    });

    // switch the measure shown by layers with a measure picker, eg: health conditions
    $('.layer-options select').on('change', function() {
        var id = $(this).closest('.layer-options').attr('data-layer'),
            index = getSubLayerIndex(id);

        app.state[id] = $(this).val();
        sublayers[index].restyle();
        // an open popup would still show the previous measure's fields
        map_object.closePopup();

        if ($('#legend-' + id).length) {
            removeLegend(id);
            renderLegend(id);
        }
    });

    // clear all the layers
    $('.nextsteps .clear').on('click', function(e) {
        e.preventDefault();
        sublayers.forEach(function(sublayer,i) {
            sublayer.hide();
            var id = getSubLayerIndex(i);
            removeLegend(id);
        });

        // de-activate the buttons
        $('.data-layer').removeClass('selected pressed active');
        $('.layer-options').hide();

        // close any open info-windows
        map_object.closePopup();
    });

    // set up custom zoom buttons
    var initZoomButtons = function(){
        $('#zoom-in').on('click', function(){
          map_object.zoomIn();
        });

        $('#zoom-out').on('click', function(){
          map_object.zoomOut();
        });

        // gray out the zoom button if user is at max-zoom or min-zoom
        function updateZoomButtons() {
            var curZoom = map_object.getZoom();
            $('#zoom-in').toggleClass('not-active', curZoom >= map_object.getMaxZoom());
            $('#zoom-out').toggleClass('not-active', curZoom <= map_object.getMinZoom());
        }

        map_object.on('zoomend', updateZoomButtons);
        updateZoomButtons();
    };

    // fills each data-layer's measure picker, eg: health conditions, with the measures in app.styles.layerMeasures
    function initLayerOptions() {
        $('.layer-options').each(function() {
            var id = $(this).attr('data-layer'),
                measures = app.styles.layerMeasures[id],
                $select = $(this).find('select');

            Object.keys(measures).forEach(function(key) {
                $select.append($('<option>').val(key).text(measures[key].label));
            });

            app.state[id] = $select.val();
        });
    }

    /* get it all going! */
    var init = function() {
        initLayerOptions();
        initMap();
        initDataLayers();
        initZoomButtons();
    };

    // stuff that's publicly accessible outside the app.map module,
    // eg: in the console do app.map.sublayers;
    return {
        init: init,
        sublayers : sublayers,
        hideShow : hideShow,
        renderLegend : renderLegend,
        getSubLayerIndex : getSubLayerIndex
    };

})(window, document, jQuery, Handlebars);
