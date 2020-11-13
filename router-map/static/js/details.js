import $ from 'jquery';

import {handleConnectionFail, CONNECTION_TIMEOUT} from './connection-fail'

const TYPE = {
    DEVICE: 'device',
    CONNECTION: 'connection'
};

function showDetailsCard(id, type, refreshFunction) {
    $.ajax({
        beforeSend: function () {
            $('#card-left-header').empty();
            $('#card-left-body').html('<div class="spinner-border" role="status">');
        },
        url: '/data/' + type + '/' + id + '/',
        type: "get",
        dataType: "html",
        cache: false,
        timeout: 1000 //1 second timeout
    })
        .done((response) => showInfo(response, id, type, refreshFunction))
        .fail(handleConnectionFail);
    $('#card-left').fadeIn();
}

function showInfo(response, id, type, refreshFunction) {
    $('#card-left').html(response);
    if (type == TYPE.CONNECTION) {
        $('#delete_btn').off('click')
        $('#delete_btn').click(function () {
            deleteInactiveLinks(id, refreshFunction)
        });
    }
}

function deleteInactiveLinks(link_id, refreshFunction) {
    $('#delete-modal-btn').off('click')
    $('#delete-modal-btn').click(function () {
            $.ajax({
                url: '/data/connection/' + link_id + '/delete',
                type: "post",
                dataType: "html",
                cache: false,
                timeout: CONNECTION_TIMEOUT
            })
                .done(() => {
                    refreshFunction();
                    hideDetailsCard();
                })
                .fail(handleConnectionFail);
        }
    )
    $('#delete-modal').modal('show');
}


function hideDetailsCard() {
    $('#card-left').fadeOut();
}

export {TYPE, showDetailsCard, hideDetailsCard}
