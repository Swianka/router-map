import toastr from 'toastr';
import 'toastr/build/toastr.css';

const connection_timeout = 1000

toastr.options = {
    "closeButton": true,
    "debug": false,
    "positionClass": "toast-custom",
    "preventDuplicates": true,
    "onclick": null,
    "showDuration": "300",
    "hideDuration": "1000",
    "timeOut": "100000",
    "extendedTimeOut": "10000",
    "showEasing": "swing",
    "hideEasing": "linear",
    "showMethod": "fadeIn",
    "hideMethod": "fadeOut"
}

function handleConnectionFail(jqXHR, textStatus) {
    let msg
    if (jqXHR.status === 0) {
        msg = 'Connection error. Please try again later.';
    } else if (jqXHR.status == 404) {
        msg = 'Requested page not found. [404]';
    } else if (jqXHR.status == 500) {
        msg = 'Internal Server Error [500].';
    } else if (textStatus === 'timeout') {
        msg = 'Time out error.';
    } else {
        msg = 'Unknown Error.\n' + jqXHR.responseText;
    }
    toastr.error(msg);

}

export {handleConnectionFail, connection_timeout}
