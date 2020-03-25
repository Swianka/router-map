import $ from 'jquery';
import './base-setup'

import 'ol/ol.css';

import '../css/index.css';
import '../css/map.css';

import * as map from './map-creation'
import {displayInactiveList} from "./inactive-list";
import {refreshUpdateTime} from "./time-update";


$('#show_btn').click(function () {
    displayInactiveList('map', map.mapId)
});

function dataUpdate(refresh) {
    return function () {
        refresh();
        refreshUpdateTime();
        if ($("#card-right").is(":visible") === true) {
            displayInactiveList('map', map.mapId);
        }
    }
}

window.setInterval(dataUpdate(map.refresh), 100000);
