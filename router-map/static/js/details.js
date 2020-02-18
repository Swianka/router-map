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
        success: (response) => showInfo(response, id, type)
    });
    $('#card-left').fadeIn();
}

function showInfo(response, id, type) {
    $('#card-left').html(response);
    $('#info-edit-btn').click(() => showUpdateForm(id, type));
    if (type === TYPE.CONNECTION) {
        $('#info-delete-btn').click(() => deleteConnection(id, type));
    }
}

function showUpdateForm(id, type) {
    $.ajax({
        url: '/map/' + type + '/' + id + '/update/',
        type: "get",
        dataType: "html",
        cache: false,
        success: function (response) {
            $('#card-left-body').html(response);
            $('#info-save-btn').click(() => saveForm(id, type));
            $('#info-cancel-btn').click(() => showDetailsCard(id, type));
        }
    });
}

function saveForm(id, type) {
    $.ajax({
        url: '/map/' + type + '/' + id + '/update/',
        type: "post",
        data: $("#update-form").serialize(),
        success: (response) => showInfo(response, id, type)
    });
}

function deleteConnection(id, type) {
    console.log(id);
    $.ajax({
        url: '/map/' + type + '/' + id + '/delete/',
        type: "post",
        success: () => hideDetailsCard()
    });
}

function hideDetailsCard() {
    $('#card-left').fadeOut();
}

export {TYPE, showDetailsCard, hideDetailsCard}
