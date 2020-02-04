import 'bootstrap';
import $ from 'jquery';
import Cookies from 'js-cookie'

import 'bootstrap/dist/css/bootstrap.min.css';
import 'ol/ol.css';

import '../css/index.css';

import {showSettingsModal} from './settingsChange'
import * as map from './map'
import {refreshUpdateTime} from './updateTime'
import {displayInactiveList} from "./inactiveList";

var csrftoken = Cookies.get('csrftoken');

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

$('#settings_btn').click(function () {
    showSettingsModal()
});

$('#delete_btn').click(function () {
    $.ajax({
        url: '/map/delete_inactive',
        type: "POST",
        success: function (data) {
            map.refresh();
        }
    });
});

$('#show_btn').click(function () {
    displayInactiveList()
});

window.setInterval(function () {
    map.refresh();
    refreshUpdateTime();
    if ($("#card-right").is(":visible") === true) {
        displayInactiveList();
    }
}, 300000);
