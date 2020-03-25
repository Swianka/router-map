import $ from 'jquery';

function displayInactiveList(visualisation_type, id) {
    let list = $('#inactive_list');
    list.empty();
    $.ajax({
        url: '/' + visualisation_type + '/' + id + '/inactive_connections',
        type: "get",
        dataType: "html",
        cache: false,
        success: function (response) {
            $('#card-right').html(response);
            $('#close_right_card_btn').click(function () {
                $('#card-right').fadeOut();
            });
        }
    });
    $('#card-right').fadeIn();
}


export {displayInactiveList}
