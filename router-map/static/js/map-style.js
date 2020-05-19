import $ from 'jquery';
import {Fill, Icon, Stroke, Style, Text} from 'ol/style';
import LineString from 'ol/geom/LineString';

import arc from "./arc";


const mapId = $('#title').data("mapId");

let display_link_descriptions = true;
let links_default_width = 3;
let highlighted_links_width;
let highlighted_links_range_min;
let highlighted_links_range_max;

$.ajax({
    url: '/map/' + mapId + '/view_settings',
    type: "get",
    dataType: "json",
    cache: false,
    success: function (response) {
        display_link_descriptions = response.display_link_descriptions;
        links_default_width = response.links_default_width;
        highlighted_links_width = response.highlighted_links_width;
        highlighted_links_range_min = response.highlighted_links_range_min;
        highlighted_links_range_max = response.highlighted_links_range_max;
    }
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

function width(speed) {
    if (highlighted_links_width && speed >= highlighted_links_range_min && speed <= highlighted_links_range_max) {
        return highlighted_links_width;
    } else
        return links_default_width;
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

function getLineStyle(feature) {
    const status = feature.get("status");

    if (display_link_descriptions) {
        baseLineStyle.getText().setText(feature.get("description"));
    } else {
        baseLineStyle.getText().setText("")
    }

    baseLineStyle.getStroke().setWidth(width(feature.get("speed")));

    if (status === 'active') {
        baseLineStyle.getStroke().setColor('#666b6d');
    } else if (status === 'inactive') {
        baseLineStyle.getStroke().setColor('#ba0e00');
    } else {
        baseLineStyle.getStroke().setColor('#ff9f00');
    }
    baseLineStyle.setGeometry(createGeometry(feature));
    return baseLineStyle;
}

function getHighlightLineStyle(feature) {
    highlightLineStyle.getText().setText(feature.get("description"));
    highlightLineStyle.setGeometry(createGeometry(feature));
    highlightLineStyle.getStroke().setWidth(width(feature.get("speed")) + 1);
    return highlightLineStyle;
}

function getPointStyle(feature) {
    if (feature.get("snmp_connection")) {
        return pointStyle;
    } else {
        return inactivePointStyle;
    }
}

export {getLineStyle, getHighlightLineStyle, getPointStyle}
