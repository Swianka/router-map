let showLabels = localStorage.getItem("show_labels");
let widthDefault = parseInt(localStorage.getItem("width_default"));
if (isNaN(widthDefault)) widthDefault = 3;
let featuredSpeedMin = parseFloat(localStorage.getItem("featured_speed_min"));
if (isNaN(featuredSpeedMin)) featuredSpeedMin = 0;
let featuredSpeedMax = parseFloat(localStorage.getItem("featured_speed_max"));
if (isNaN(featuredSpeedMax)) featuredSpeedMax = 0;
let featuredWidth = parseInt(localStorage.getItem("featured_width"));
if (isNaN(featuredWidth)) featuredWidth = 3;

function getShowLabels() {
    return showLabels
}

function getWidthDefault() {
    return widthDefault
}

function getFeaturedSpeedMin() {
    return featuredSpeedMin
}

function getFeaturedSpeedMax() {
    return featuredSpeedMax
}

function getFeaturedWidth() {
    return featuredWidth
}

function setShowLabels(val) {
    showLabels = val;
    localStorage.setItem("show_labels", val);
}

function setWidthDefault(val) {
    widthDefault = val;
    localStorage.setItem("width_default", val);
}

function setFeaturedSpeedMin(val) {
    featuredSpeedMin = val;
    localStorage.setItem("featured_speed_min", val);
}

function setFeaturedSpeedMax(val) {
    featuredSpeedMax = val;
    localStorage.setItem("featured_speed_max", val);
}

function setFeaturedWidth(val) {
    featuredWidth = val;
    localStorage.setItem("featured_width", val);
}

export {
    getShowLabels, getWidthDefault, getFeaturedSpeedMin, getFeaturedSpeedMax, getFeaturedWidth,
    setShowLabels, setWidthDefault, setFeaturedSpeedMin, setFeaturedSpeedMax, setFeaturedWidth,
}
