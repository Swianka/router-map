import $ from 'jquery';

function displayInactiveList() {
    let list = $('#inactive_list');
    list.empty();
    $.ajax({
        url: '/map/inactive_connections',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            response.forEach(function (connection) {
                list.append($('<li class="list-group-item">').append(connection.description));
            });
        }
    });
    $('#card-right').fadeIn();
}

$('#close_right_card_btn').click(function () {
    $('#card-right').fadeOut();
});

export {displayInactiveList}
