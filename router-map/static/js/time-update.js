import $ from 'jquery';
import {handleConnectionFail, connection_timeout} from './connection-fail'

function refreshUpdateTime() {
    $.ajax({
        url: '/data/last_update_time',
        type: "get",
        cache: false,
        timeout: connection_timeout
    })
        .done(setUpdateTime)
        .fail(handleConnectionFail);
}

function setUpdateTime(data) {
    if (!data) {
        $('#data').text('No information about last data update');
    } else {
        let date = new Date(data * 1000);
        let convDataTime = date.toLocaleString('en-GB', {
            day: 'numeric',
            month: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
        $('#data').text('Time of last data update: ' + convDataTime);
    }
}

refreshUpdateTime();

export {refreshUpdateTime}
