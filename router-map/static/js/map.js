import $ from 'jquery';
import Map from 'ol/Map'
import View from 'ol/View';
import {Tile as TileLayer, Vector as VectorLayer} from 'ol/layer'
import {Vector as VectorSource} from 'ol/source';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import OSM from 'ol/source/OSM';
import {fromLonLat} from 'ol/proj';
import Feature from 'ol/Feature';
import GeoJSON from 'ol/format/GeoJSON';

import * as mapStyle from "./mapStyle";
import {showConnectionInfo, showDeviceInfo} from "./details";


const START_ZOOM = 7;
const START_CENTER_LOCATION = [19.5, 52.1];

$("body").append($('<div id="map">'));

const lineVectorSource = new VectorSource({
    loader: function (extent, resolution, projection) {
        $.ajax({
            url: '/map/lines.json',
            type: "get",
            dataType: "json",
            cache: false,
        }).done(loadLines);
    }
});

function getPointLayerVectorSource() {
    return new VectorSource({
        url: '/map/points.json',
        format: new GeoJSON()
    });
}

const lineLayer = new VectorLayer({
    source: lineVectorSource,
    style: mapStyle.getLineStyle,
});

const highlightLineLayer = new VectorLayer({
    source: new VectorSource(),
    style: mapStyle.getHighlightLineStyle
});

const pointLayer = new VectorLayer({
    source: getPointLayerVectorSource(),
    style: mapStyle.getPointStyle
});

function loadLines(response) {
    let features = [];
    response.forEach(function (x) {
        x.forEach(function (link, i) {
            let lineStr = new LineString([fromLonLat(link.device1_coordinates), fromLonLat(link.device2_coordinates)]);

            let feature = new Feature({
                geometry: lineStr,
                connection_id: link.id,
                description: link.number_of_active_links + '/' + link.number_of_links + '\xD7' + link.speed + 'G',
                status: status(link.number_of_active_links, link.number_of_links),
                speed: link.speed,
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


map.on('singleclick', function (evt) {
    let feature = map.forEachFeatureAtPixel(evt.pixel,
        function (feature) {
            return feature;
        }, {
            hitTolerance: 5
        });

    if (feature) {
        if (feature.getGeometry().getType() === 'LineString') {
            showConnectionInfo(feature.get('connection_id'));

        } else if (feature.getGeometry().getType() === 'Point') {
            showDeviceInfo(feature.get('pk'))
        }
    } else {
        $('#card-left').fadeOut();
    }
});


map.on('pointermove', function (evt) {
    if (evt.dragging) {
        return;
    }
    const pixel = map.getEventPixel(evt.originalEvent);
    highlightLineLayer.getSource().clear();
    const feature = map.forEachFeatureAtPixel(pixel,
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

pointLayer.getSource().once('change', function (e) {
    if (pointLayer.getSource().getFeatures().length > 1) {
        map.getView().fit(e.target.getExtent());
    }
});

function refresh() {
    lineLayer.getSource().refresh();
    pointLayer.getSource().refresh();
}

export {refresh}
