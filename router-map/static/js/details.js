import $ from 'jquery';

const TYPE = {
    DEVICE: 'device',
    CONNECTION: 'connection'
};

function showDetailsCard(id, type) {
    $.ajax({
        beforeSend: function () {
            $('#card-left-header').empty();
            $('#card-left-body').html('<div class="spinner-border" role="status">');
        },
        url: '/data/' + type + '/' + id + '/',
        type: "get",
        dataType: "html",
        cache: false,
        success: (response) => showInfo(response, id, type)
    });
    $('#card-left').fadeIn();
}

function showInfo(response, id, type) {
    $('#card-left').html(response);
    if(type == TYPE.CONNECTION){
        $('#delete_btn').click(function () {
            deleteInactiveLinks(id)
        });
    }
}

function deleteInactiveLinks(link_id) {
    $('#delete-modal-btn').click(function () {
            $.ajax({
                url: '/data/connection/' + link_id + '/delete',
                type: "post",
                dataType: "html",
                cache: false,
            });
        }
    )
    $('#delete-modal').modal('show');
}


function hideDetailsCard() {
    $('#card-left').fadeOut();
}

export {TYPE, showDetailsCard, hideDetailsCard}
