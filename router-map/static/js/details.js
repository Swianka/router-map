import $ from 'jquery';

function showDeviceInfo(device) {
    const cardBody = $('#card-left-body');
    const cardHeader = $('#card-left-header');
    cardBody.empty();
    cardHeader.empty();
    cardBody.append($('<div class="spinner-border" role="status">'));
    $.ajax({
        url: '/map/device/' + device + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            cardBody.empty();
            cardBody.append($('<table class="table table-striped">').append($('<tbody>').append(
                [$('<tr>')
                    .append($('<td>').append($('<b>').append("Name")))
                    .append($('<td>').append(response.name)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("IP address")))
                        .append($('<td>').append(response.ip_address)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("SNMP connection")))
                        .append($('<td>').append(response.snmp_connection))
                ])));
            cardHeader.append($('<b>').append(response.name))
        }

    });
    $('#card-left').fadeIn();
}

function showConnectionInfo(connection_id) {
    const cardBody = $('#card-left-body');
    const cardHeader = $('#card-left-header');
    cardBody.empty();
    cardHeader.empty();
    cardBody.append($('<div class="spinner-border" role="status">'));
    $.ajax({
        url: '/map/connection/' + connection_id + '/',
        type: "get",
        dataType: "json",
        cache: false,
        success: function (response) {
            cardBody.empty();
            cardBody.append($('<table class="table table-striped">').append($('<tbody>').append(
                [$('<tr>')
                    .append($('<td>').append($('<b>').append("Number of links")))
                    .append($('<td>').append(response.number_of_links)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Number of active links")))
                        .append($('<td>').append(response.number_of_active_links)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append("Speed of each link")))
                        .append($('<td>').append(response.speed + 'G')),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append('Interface of router ' + response.device1)))
                        .append($('<td>').append(response.interface1)),
                    $('<tr>')
                        .append($('<td>').append($('<b>').append('Interface of router ' + response.device2)))
                        .append($('<td>').append(response.interface2)),
                ])));
            cardHeader.append($('<b>').append(response.device1 + "  -  <br>" + response.device2))
        }
    });
    $('#card-left').fadeIn();
}

export {showDeviceInfo, showConnectionInfo}
