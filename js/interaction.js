var app = app || {};

app.interaction = (function(d, w, $) {
    // This module creates UI to map interactions on DOM elements

    // matches the small screen layout in css/style.css
    var smallScreen = w.matchMedia('(max-width: 768px)');

    function addToolTips() {
        // touch screens show tooltips on tap, which gets in the way of the buttons
        if (w.matchMedia('(hover: none)').matches) return;

        // add jquery UI tooltips
        // we could probably do this without jQuery UI...
        $('.dlayer').tooltip({
            tooltipClass: "dlayer-tooltip"
        });
    }

    // create a static image of the map's current state option 1:
    // using the HTML 2 Canvas JS library: http://html2canvas.hertzen.com/
    // currently not working, as such I've removed the html2canvas.js file from being loaded in index.html
    function screenshot() {        
        if (screen.width > 0 && screen.height > 0) {
            try {
                html2canvas(document.body, {
                    allowTaint: false,
                    logging: true,
                    taintTest: false,
                    useCORS: true,
                    onrendered: function(canvas) {
                        // canvas is the final rendered <canvas> element
                        var cap = canvas.toDataURL();
                        window.open(cap);
                    }
                });
            } catch (err) {
                console.log(err.message);
            }
        }
    }

    // create a static image of the map's current state option 2:
    // ideally we would use CartoDB's Static Maps API to create a "screenshot" of the current map state
    // however there's currently a bug with it that needs to be resolved before it can be implemented: 
    // https://github.com/CartoDB/cartodb.js/issues/657
    function cdbStaticMap() {
        var basemap = {
            type: "http",
            options: {
                urlTemplate : 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
                subdomains: ['a', 'b', 'c']
            }
        };

        var layerSource = app.layers;

        cartodb.Image(layerSource, {
            basemap : basemap,
            override_bbox : true
        })
        .size(1200, 900)
        .center([40.718640, -73.950605])
        .zoom(14)
        .getUrl(function(err, url) {
            if (err) console.log('error: ', err);
            console.log('image url: ', url);
        });        
    }    

    // adds the event listeners to the non-map interactions UI
    function addListeners() {
        // listener to create a screenshot, currently disabled.
        $('#print_b').click(function() {
            // screenshot();
        });

        // listener to hide / show data layer UI & other content
        $('li.nav').click(function() {
            var c = $(this).attr('id'),
                menu_tabs = $('.tabs');

            $('li.nav').removeClass('active');
            
            if (!$(this).hasClass('active')) {
                $(this).addClass('active');
            } 

            $.each(menu_tabs, function(i, el) {
                var $el = $(el);

                $el.removeClass('active');

                if ($el.attr('class') === "menu tabs " + c) {
                    $(this).addClass('active');
                } 
            });
        });

        // small screens: open & close the menu drawer and the legend
        $('#menu-toggle').on('click', function() {
            toggleOpen('menu-open', $(this));
        });

        $('#legend-toggle').on('click', function() {
            toggleOpen('legend-open', $(this));
        });

        // close the drawer when the user goes back to the map
        $('#map').on('click', function() {
            toggleOpen('menu-open', $('#menu-toggle'), false);
        });

        // show the legend when a data-layer is turned on
        $(d).on('layer:shown', function() {
            if (smallScreen.matches) toggleOpen('legend-open', $('#legend-toggle'), true);
        });
    }

    // toggles a body class that opens a small screen panel, keeping its button's aria-expanded in sync
    function toggleOpen(className, $button, open) {
        $('body').toggleClass(className, open);
        $button.attr('aria-expanded', $('body').hasClass(className));
    }

    // get it all going...
    var init = function() {
        addToolTips();
        addListeners();
    };

    return {
        init: init
    };

})(document, window, jQuery);