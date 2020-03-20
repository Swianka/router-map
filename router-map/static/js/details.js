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
        url: '/map/' + type + '/' + id + '/',
        type: "get",
        dataType: "html",
        cache: false,
        success: (response) => showInfo(response)
    });
    $('#card-left').fadeIn();
}

function showInfo(response) {
    $('#card-left').html(response);
}

function hideDetailsCard() {
    $('#card-left').fadeOut();
}

export {TYPE, showDetailsCard, hideDetailsCard}
