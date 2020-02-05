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
            let table = `<table class="table table-striped">
                            <tbody>
                                <tr>
                                    <td><b>Name</b></td>
                                    <td>${response.name}</td>
                                </tr>
                                <tr>
                                    <td><b>IP address</b></td>
                                    <td>${response.ip_address}</td>
                                </tr>
                                <tr>
                                    <td><b>SNMP connection</b></td>
                                    <td>${response.snmp_connection}</td>
                                </tr>
                            </tbody>
                         </table>`;
            cardBody.append(table);
            cardHeader.append(`<b>${response.name}</b>`);
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
            let table = `<table class="table table-striped">
                            <tbody>
                                <tr>
                                    <td><b>Number of links</b></td>
                                    <td>${response.number_of_links}</td>
                                </tr>
                                <tr>
                                    <td><b>Number of active links</b></td>
                                    <td>${response.number_of_active_links}</td>
                                </tr>
                                <tr>
                                    <td><b>Speed of each link</b></td>
                                    <td>${response.speed}G</td>
                                </tr>
                                <tr>
                                    <td><b>Interface of router ${response.device1}</b></td>
                                    <td>${response.interface1}</td>
                                </tr>
                                <tr>
                                    <td><b>Interface of router ${response.device2}</b></td>
                                    <td>${response.interface2}</td>
                                </tr>
                            </tbody>
                         </table>`;
            cardBody.append(table);
            cardHeader.append(`<b>${response.device1} -  <br>${response.device2}</b>`);
        }
    });
    $('#card-left').fadeIn();
}

function hideInfo() {
    $('#card-left').fadeOut();
}

export {showDeviceInfo, showConnectionInfo, hideInfo}
