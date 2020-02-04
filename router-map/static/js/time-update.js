import $ from 'jquery';

function refreshUpdateTime() {
    $.ajax({
        url: '/map/last_update_time',
        type: "get",
        success: function (data) {
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
    });
}

refreshUpdateTime();

export {refreshUpdateTime}
