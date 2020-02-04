import {Fill, Icon, Stroke, Style, Text} from 'ol/style';
import LineString from 'ol/geom/LineString';

import * as settings from "./settings";
import arc from "./arc";

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
    if (speed >= settings.getFeaturedSpeedMin() && speed <= settings.getFeaturedSpeedMax())
        return settings.getFeaturedWidth();
    else
        return settings.getWidthDefault();
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

    if (settings.getShowLabels() === 'true') {
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
