import $ from 'jquery';
import * as settings from './settings'

function showSettingsModal() {
    const featuredSpeedMinInput = $('#featured-speed-min-input');
    const featuredSpeedMaxInput = $('#featured-speed-max-input');
    $("#descriptionCheck").prop('checked', settings.getShowLabels() === "true");
    $("#width-default-range").val(settings.getWidthDefault());
    $("#width-default-value").text(settings.getWidthDefault());
    featuredSpeedMinInput.val(settings.getFeaturedSpeedMin());
    featuredSpeedMinInput[0].setCustomValidity('');
    featuredSpeedMaxInput.val(settings.getFeaturedSpeedMax());
    featuredSpeedMaxInput[0].setCustomValidity('');
    $("#featured-width-range").val(settings.getFeaturedWidth());
    $("#featured-width-value").text(settings.getFeaturedWidth());
    $('#settingsModal').modal('toggle');
}


$('#width-default-range').change(function () {
    $("#width-default-value").text($('#width-default-range').val());
});

$('#featured-width-range').change(function () {
    $("#featured-width-value").text($('#featured-width-range').val());
});

$('#featured-speed-min-input').change(function () {
    checkValidity();
});

$('#featured-speed-max-input').change(function () {
    checkValidity();
});

function handleSaveSettingsBtnClick(refresh) {
    return function () {
        if (checkValidity()) {
            if ($('#descriptionCheck').is(":checked")) {
                settings.setShowLabels('true');
            } else {
                settings.setShowLabels('false');
            }
            settings.setWidthDefault(parseInt($('#width-default-range').val()));
            settings.setFeaturedSpeedMin(parseFloat($('#featured-speed-min-input').val()));
            settings.setFeaturedSpeedMax(parseFloat($('#featured-speed-max-input').val()));
            settings.setFeaturedWidth(parseInt($('#featured-width-range').val()));
            refresh();
            $('#settingsModal').modal('hide');
        }
    }
}

function checkValue(value) {
    const min = Number(value);
    if (isNaN(min)) {
        return 'Must be a number.';
    } else if (min < 0) {
        return 'Must be greater than 0.';
    } else {
        return '';
    }
}

function checkValidity() {
    const min = $('#featured-speed-min-input');
    const max = $('#featured-speed-max-input');
    let minFeedback = checkValue(min.val());
    let maxFeedback = checkValue(max.val());
    if (minFeedback === '' && maxFeedback === '' && Number(min.val()) > Number(max.val())) {
        maxFeedback = 'Must be higher.';
    }

    if (minFeedback === '') {
        min[0].setCustomValidity('');
    } else {
        min[0].setCustomValidity('min_feedback');
        $('#featured-speed-min-feedback').text(minFeedback);
    }

    if (maxFeedback === '') {
        max[0].setCustomValidity('');
    } else {
        max[0].setCustomValidity('max_feedback');
        $('#featured-speed-max-feedback').text(maxFeedback);
    }

    return minFeedback === '' && maxFeedback === '';
}


export {
    showSettingsModal, handleSaveSettingsBtnClick
}
