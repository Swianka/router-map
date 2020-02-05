import 'bootstrap';
import $ from 'jquery';
import Cookies from 'js-cookie'

import 'bootstrap/dist/css/bootstrap.min.css';

import {showSettingsModal} from './settings-change'
import {refreshUpdateTime} from './time-update'
import {displayInactiveList} from "./inactive-list";

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

function handleDeleteBtnClick(refresh) {
    return function () {
        $.ajax({
            url: '/map/delete_inactive',
            type: "POST",
            success: function (data) {
                refresh();
            }
        });
    }
}

$('#show_btn').click(function () {
    displayInactiveList()
});

function dataUpdate(refresh) {
    return function () {
        refresh();
        refreshUpdateTime();
        if ($("#card-right").is(":visible") === true) {
            displayInactiveList();
        }
    }
}

export {dataUpdate, handleDeleteBtnClick}
