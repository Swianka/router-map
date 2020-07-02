import './base-setup'
import $ from 'jquery';

import '../css/visualisation-tree-view.css';


$(document).ready(function () {
    $(".caret").each(function () {
        $(this).click(function () {
            $(this).closest("li").children(".nested").toggleClass("active")
            $(this).toggleClass("caret-down")
            $(this).toggleClass("caret-right")
        });
    });
});
