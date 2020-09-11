import 'bootstrap';
import $ from 'jquery';
import Cookies from 'js-cookie'

import './base-setup'

$(document).ready(function () {
    $('#add-more').click(function () {
        var form_idx = $('#id_form-TOTAL_FORMS').val();
        $('tbody').append('<tr>' + $('.empty-form').html().replace(/__prefix__/g, form_idx) + '</tr>');
        $('#id_form-TOTAL_FORMS').val(parseInt(form_idx) + 1);
    });
});
