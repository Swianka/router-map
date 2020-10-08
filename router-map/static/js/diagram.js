import $ from 'jquery';
import './base-setup'

import '../css/index.css';
import '../css/diagram.css';

import * as diagram from './diagram-creation'
import {displayInactiveList} from "./inactive-list";
import {refreshUpdateTime} from "./time-update";
import {handleConnectionFail, connection_timeout} from './connection-fail'

$('#show_btn').click(function () {
    displayInactiveList('diagram', diagram.diagramId)
});

function dataUpdate(refresh) {
    return function () {
        refresh();
        refreshUpdateTime();
        if ($("#card-right").is(":visible") === true) {
            displayInactiveList('diagram', diagram.diagramId);
        }
    }
}

window.setInterval(dataUpdate(diagram.refresh), 100000);

$('#save_position_btn').click(function () {
    $.ajax({
        url: '/diagram/' + diagram.diagramId + '/update_positions',
        type: "post",
        data: Json(diagram.positionsJSON),
        dataType: "json",
        timeout: connection_timeout
    }).
    fail(handleConnectionFail);
});

$("#loader").remove();
$("#page-content").show();

