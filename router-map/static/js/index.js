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
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import Feature from 'ol/Feature';

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
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

var show_labels = localStorage.getItem("show_labels");

$('#settings_btn').click(function () {
    $("#descriptionCheck").prop('checked', show_labels === "true");
    $('#settingsModal').modal('toggle');
});

$('#save_settings_btn').click(function () {
    if ($('#descriptionCheck').is(":checked")) {
        show_labels = 'true';
        localStorage.setItem("show_labels", 'true');
        lineLayer.changed();
    } else {
        show_labels = 'false';
        localStorage.setItem("show_labels", 'false');
        lineLayer.changed();
    }
});

function updateTime() {
    $.ajax({
        url: '/map/last_update_time',
        type: "get",
        success: function (data) {
            if (!data) {
                $('#data').text('No information about last data update');
            } else {
                var date = new Date(data * 1000);
                var convDataTime = date.toLocaleString('en-GB', {
                    day: 'numeric',
                    month: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                });
                $('#data').text('Time of last data update: ' + convDataTime);
            }
        }
    });
}
updateTime();

$('#delete_btn').click(function () {
    $.ajax({
        url: '/map/delete_inactive',
        type: "POST",
        success: function (data) {
            lineLayer.setSource(get_line_layer_vector_source());
        }
    });
});

$('#show_btn').click(function () {
    display_inactive_list()
});

function display_inactive_list() {
    var list = $('#inactive_list');
    list.empty();
    $.ajax({
        url: '/map/inactive_connections',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            response.forEach(function (connection) {
                list.append($('<li class="list-group-item">').append(connection.description));
            });
        }
    });
    $('#card-right').fadeIn();
}

$('#close_right_card_btn').click(function () {
    $('#card-right').fadeOut();
});

window.setInterval(function () {
    lineLayer.getSource().refresh();
    pointLayer.getSource().refresh();
    updateTime();
    if ($("#card-right").is(":visible") === true) {
        display_inactive_list();
    }
}, 300000);


function get_point_layer_vector_source() {
    return new VectorSource({
        url: '/map/points.json',
        format: new GeoJSON()
    });
}

var lineVectorSource = new VectorSource({
    loader: function (extent, resolution, projection) {
        $.ajax({
            url: '/map/lines.json',
            type: "get",
            dataType: "json",
            cache: false,
        }).done(loadLines);
    }
});

function loadLines(response) {
    var features = [];
    response.forEach(function (x) {
        x.forEach(function (link, i) {
            var lineStr = new LineString([fromLonLat(link.device1_coordinates), fromLonLat(link.device2_coordinates)]);

            var feature = new Feature({
                geometry: lineStr,
                connection_id: link.id,
                description: link.number_of_active_links + '/' + link.number_of_links + '\xD7' + link.speed + 'G',
                status: status(link.number_of_active_links, link.number_of_links),
                number: i + 1
            });
            features.push(feature);
        });
    });
    lineVectorSource.addFeatures(features);
}

function status(number_of_active_links, number_of_links) {
    if (number_of_active_links === number_of_links)
        return 'active';
    else if (number_of_active_links === 0)
        return 'inactive';
    else
        return 'part-active';
}


function createGeometry(feature) {
    const point1 = feature.getGeometry().getFirstCoordinate();
    const point2 = feature.getGeometry().getLastCoordinate();
    const number = feature.get("number");
    if (number === 1)
        return new LineString([point1, point2]);
    else
        return arc(number, point1, point2)
}

function arc(number, point1, point2) {
    var q = Math.sqrt(Math.pow(point2[0] - point1[0], 2) + Math.pow(point2[1] - point1[1], 2)) / 2;
    var r = Math.min(Math.floor(number / 2) * 20 * map.getView().getResolution(), Math.floor(number / 2) * q / 3);
    var center = [(point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2];
    var arc = halfEclipse(q, r, center, 50);
    var angle = (point1[1] === point2[1]) ? Math.PI / 2 : Math.atan2(point2[1] - point1[1], point2[0] - point1[0]);
    if (number % 2 === 1)
        angle = angle + Math.PI;
    arc.rotate(angle, center);
    return arc;
}

function halfEclipse(q, r, center, segments) {
    var pointList = [];
    var dAngle = segments + 1;
    for (var i = 0; i < dAngle; i++) {
        var Angle = Math.PI * i / (dAngle - 1);
        var x = center[0] + q * Math.cos(Angle);
        var y = center[1] + r * Math.sin(Angle);
        var point = [x, y];
        pointList.push(point);
    }
    return new LineString(pointList)
}

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
    source: lineVectorSource,
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
            baseLineStyle.getStroke().setColor('#ba0e00');
        } else {
            baseLineStyle.getStroke().setColor('#ff9f00');
        }
        baseLineStyle.setGeometry(createGeometry(feature));
        return baseLineStyle;
    },
});

const highlightLineLayer = new VectorLayer({
    source: new VectorSource(),
    style: function (feature) {
        highlightLineStyle.getText().setText(feature.get("description"));
        highlightLineStyle.setGeometry(createGeometry(feature));
        return highlightLineStyle;
    }
});

const pointLayer = new VectorLayer({
    source: get_point_layer_vector_source(),
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
        zoom: START_ZOOM,
        zoomFactor: 1.5
    })
});

pointLayer.getSource().once('change', function (e) {
    if (pointLayer.getSource().getFeatures().length > 1) {
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
            show_connection_info(feature.get('connection_id'));

        } else if (feature.getGeometry().getType() === 'Point') {
            show_device_info(feature.get('pk'))
        }
    } else {
        $('#card-left').fadeOut();
    }
});

function show_device_info(device) {
    var card_body = $('#card-left-body');
    var card_header = $('#card-left-header');
    card_body.empty();
    card_header.empty();
    card_body.append($('<div class="spinner-border" role="status">'));
    $.ajax({
        url: '/map/device/' + device + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            card_body.empty();
            card_body.append($('<table class="table table-striped">').append($('<tbody>').append(
                [$('<tr>')
                    .append($('<td>').append($('<b>').append("Name")))
                    .append($('<td>').append(response.name)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("IP address")))
                        .append($('<td>').append(response.ip_address)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("SNMP connection")))
                        .append($('<td>').append(response.snmp_connection))
                ])));
            card_header.append($('<b>').append(response.name))
        }

    });
    $('#card-left').fadeIn();
}

function show_connection_info(connection_id) {
    var card_body = $('#card-left-body');
    var card_header = $('#card-left-header');
    card_body.empty();
    card_header.empty();
    card_body.append($('<div class="spinner-border" role="status">'));
    $.ajax({
        url: '/map/connection/' + connection_id + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            card_body.empty();
            card_body.append($('<table class="table table-striped">').append($('<tbody>').append(
                [$('<tr>')
                    .append($('<td>').append($('<b>').append("Number of links")))
                    .append($('<td>').append(response.number_of_links)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Number of active links")))
                        .append($('<td>').append(response.number_of_active_links)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Speed of each link")))
                        .append($('<td>').append(response.speed + 'G')),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append('Interface of router ' + response.device1)))
                        .append($('<td>').append(response.interface1)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append('Interface of router ' + response.device2)))
                        .append($('<td>').append(response.interface2)),
                ])));
            card_header.append($('<b>').append(response.device1 + "  -  <br>" + response.device2))
        }
    });
    $('#card-left').fadeIn();
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

