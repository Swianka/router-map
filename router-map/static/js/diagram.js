import * as diagram from './diagram-creation'
import $ from 'jquery';
import './base-setup'

import '../css/index.css';
import '../css/diagram.css';

import {displayInactiveList} from "./inactive-list";
import {refreshUpdateTime} from "./time-update";

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
        data: diagram.positionsJSON,
        dataType: "json"
    });
});

$("#loader").remove();
$("#page-content").show();

