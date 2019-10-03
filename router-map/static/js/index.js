import 'bootstrap';
import $ from 'jquery';
import Map from 'ol/Map'
import View from 'ol/View';
import {Vector as VectorSource} from 'ol/source';
import {Tile as TileLayer, Vector as VectorLayer} from 'ol/layer'
import {Fill, Icon, Stroke, Style, Text} from 'ol/style';
import GeoJSON from 'ol/format/GeoJSON';
import OSM from 'ol/source/OSM';
import {fromLonLat} from 'ol/proj';

import 'bootstrap/dist/css/bootstrap.min.css';
import 'ol/ol.css';
import '../css/index.css';

const START_ZOOM = 7;
const START_CENTER_LOCATION = [19.5, 52.1];

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

var show_labels = localStorage.getItem("show_labels");
if (show_labels === 'true') {
    $("#checkbox-show-label").prop('checked', true);
}

$('#checkbox-show-label').change(function () {
    if ($('#checkbox-show-label').is(":checked")) {
        show_labels = 'true';
        localStorage.setItem("show_labels", 'true');
        lineLayer.changed();
    } else {
        show_labels = 'false';
        localStorage.setItem("show_labels", 'false');
        lineLayer.changed();
    }
});

$.ajax({
    url: '/map/last_update_time',
    type: "get",
    success: function (data) {
        if (!data) {
            $('#data').text('Brak informacji o ostatniej aktualizacji danych');
        } else {
            var date = new Date(data * 1000);
            var year = date.getFullYear();
            var month = date.getMonth();
            var day = date.getDate();
            var hours = date.getHours();
            var minutes = "0" + date.getMinutes();
            var convDataTime = day + '-' + month + '-' + year + ' ' + hours + ':' + minutes.substr(-2);
            $('#data').text('Czas ostatniej aktualizacji danych: ' + convDataTime);
        }
    }
});


$('#delete_btn').click(function () {
    $.ajax({
        url: '/map/delete_inactive',
        type: "POST",
        success: function (data) {
            lineLayer.setSource(
                new VectorSource({
                    url: '/map/lines.json',
                    format: new GeoJSON()
                }));
        }
    });
});

const baseLineStyle = new Style({
    stroke: new Stroke({
        color: '#666b6d',
        width: 3
    }),
    text: new Text({
        font: 'bold 15px Calibri,sans-serif',
        fill: new Fill({color: '#000000'}),
        stroke: new Stroke({
            color: '#ffffff', width: 4
        }),
    })
});

const highlightLineStyle = new Style({
    stroke: new Stroke({color: '#324dff', width: 3}),
    text: new Text({
        font: 'bold 15px Calibri,sans-serif',
        fill: new Fill({color: '#324dff'}),
        stroke: new Stroke({
            color: '#ffffff', width: 4
        }),
    })
});

const pointStyle = new Style({
    image: new Icon(({
        crossOrigin: 'anonymous',
        src: "/static/images/router.png",
        scale: 0.6
    }))
});

const inactivePointStyle = new Style({
    image: new Icon(({
        crossOrigin: 'anonymous',
        src: '/static/images/router_red.png',
        scale: 0.6
    }))
});

const lineLayer = new VectorLayer({
    source: new VectorSource({
        url: '/map/lines.json',
        format: new GeoJSON()
    }),
    style: function (feature) {
        const status = feature.get("status");
        if (show_labels === 'true') {
            baseLineStyle.getText().setText(feature.get("description"));
        } else {
            baseLineStyle.getText().setText("")
        }
        if (status === 'active') {
            baseLineStyle.getStroke().setColor('#666b6d');
        } else if (status === 'inactive') {
            baseLineStyle.getStroke().setColor('#ff1300');
        } else {
            baseLineStyle.getStroke().setColor('#a42220');
        }
        return baseLineStyle;
    },
});

const highlightLineLayer = new VectorLayer({
    source: new VectorSource(),
    style: function (feature) {
        if (show_labels === 'true') {
            highlightLineStyle.getText().setText(feature.get("description"));
        } else {
            baseLineStyle.getText().setText("")
        }
        return highlightLineStyle;
    },
});

const pointLayer = new VectorLayer({
    source: new VectorSource({
        url: '/map/points.json',
        format: new GeoJSON()
    }),
    style:
        function (feature) {
            var _style;
            if (feature.get("snmp_connection")) {
                _style = pointStyle;
            } else {
                _style = inactivePointStyle;
            }
            return _style;
        }
});

const map = new Map({
    target: 'map',
    layers: [
        new TileLayer({
            source: new OSM({
                "url": "https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png"
            })
        }),
        lineLayer,
        highlightLineLayer,
        pointLayer
    ],
    view: new View({
        center: fromLonLat(START_CENTER_LOCATION),
        zoom: START_ZOOM
    })
});

pointLayer.getSource().once('change', function (e) {
    if(pointLayer.getSource().getFeatures().length > 1){
        map.getView().fit(e.target.getExtent());
    }
});

map.on('singleclick', function (evt) {
    var feature = map.forEachFeatureAtPixel(evt.pixel,
        function (feature) {
            return feature;
        }, {
            hitTolerance: 5
        });

    if (feature) {
        if (feature.getGeometry().getType() === 'LineString') {
            show_connection_info(feature.get('device1-pk'), feature.get('device2-pk'));

        } else if (feature.getGeometry().getType() === 'Point') {
            show_device_info(feature.get('pk'))
        }
    } else {
        $('.card').fadeOut();

    }
});

function show_device_info(device) {
    var card = $('#card');
    card.empty();
    $.ajax({
        url: '/map/device/' + device + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            card.append($('<table class="table table-striped">').append(
                [$('<tr>')
                    .append($('<td>').append($('<b>').append("Nazwa")))
                    .append($('<td>').append(response.name)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Adres IP")))
                        .append($('<td>').append(response.ip_address)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Połączenie SNMP")))
                        .append($('<td>').append(response.snmp_connection))
                ]));
        }

    });
    $('.card').fadeIn();
}

function show_connection_info(device1, device2) {
    var card = $('#card ');
    card.empty();
    $.ajax({
        url: '/map/connection/' + device1 + '/' + device2 + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            for (const i in response) {
                card.append($('<table class="table table-striped">').append(
                    [$('<tr>')
                        .append($('<td>').append($('<b>').append("Liczba linków")))
                        .append($('<td>').append(response[i].number_of_links)),
                        $('<tr>')
                            .append($('<td>').append($('<b>').append("Liczba aktywnych linków")))
                            .append($('<td>').append(response[i].number_of_active_links)),
                        $('<tr>')
                            .append($('<td>').append($('<b>').append("Prędkość")))
                            .append($('<td>').append(response[i].speed + 'G')),
                        $('<tr>')
                            .append($('<td>').append($('<b>').append('Interfejs routera ' + response[i].device1)))
                            .append($('<td>').append(response[i].interface1)),
                        $('<tr>')
                            .append($('<td>').append($('<b>').append('Interfejs routera ' + response[i].device2)))
                            .append($('<td>').append(response[i].interface2)),
                    ]));
            }
        }
    });
    $('.card').fadeIn();
}

map.on('pointermove', function (evt) {
    if (evt.dragging) {
        return;
    }
    var pixel = map.getEventPixel(evt.originalEvent);
    highlightLineLayer.getSource().clear();
    var feature = map.forEachFeatureAtPixel(pixel,
        function (feature) {
            return feature;
        }, {
            hitTolerance: 5
        });

    if (feature) {
        document.getElementById("map").style.cursor = "pointer";
        if (feature.getGeometry().getType() === 'LineString') {
            highlightLineLayer.getSource().addFeature(feature);
        }
    } else {
        document.getElementById("map").style.cursor = '';
    }
});

