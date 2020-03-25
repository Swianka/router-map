import 'bootstrap';
import $ from 'jquery';
import Cookies from 'js-cookie'

import 'bootstrap/dist/css/bootstrap.min.css';

var csrftoken = Cookies.get('csrftoken');

function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});
