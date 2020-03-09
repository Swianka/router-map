import $ from 'jquery';

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
        url: '/map/' + type + '/' + id + '/',
        type: "get",
        dataType: "html",
        cache: false,
        success: (response) => showInfo(response, id, type, refreshFunction)
    });
    $('#card-left').fadeIn();
}

function showInfo(response, id, type, refreshFunction) {
    $('#card-left').html(response);
    $('#info-edit-btn').click(() => showUpdateForm(id, type, refreshFunction));
    if (type === TYPE.CONNECTION) {
        $('#info-delete-btn').click(() => deleteConnection(id, type, refreshFunction));
    }
}

function showUpdateForm(id, type, refreshFunction) {
    $.ajax({
        url: '/map/' + type + '/' + id + '/update/',
        type: "get",
        dataType: "html",
        cache: false,
        success: function (response) {
            $('#card-left-body').html(response);
            $('#info-save-btn').click(() => saveForm(id, type, refreshFunction));
            $('#info-cancel-btn').click(() => showDetailsCard(id, type, refreshFunction));
        }
    });
}

function saveForm(id, type, refreshFunction) {
    $.ajax({
        url: '/map/' + type + '/' + id + '/update/',
        type: "post",
        data: $("#update-form").serialize(),
        success: (response) => showInfo(response, id, type, refreshFunction)
    });
}

function deleteConnection(id, type, refreshFunction) {
    console.log(id);
    $.ajax({
        url: '/map/' + type + '/' + id + '/delete/',
        type: "post",
        success: () => {
            hideDetailsCard();
            refreshFunction()
        }
    });
}

function hideDetailsCard() {
    $('#card-left').fadeOut();
}

export {TYPE, showDetailsCard, hideDetailsCard}
