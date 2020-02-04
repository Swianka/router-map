import LineString from 'ol/geom/LineString';

function arc(number, point1, point2) {
    var q = Math.sqrt(Math.pow(point2[0] - point1[0], 2) + Math.pow(point2[1] - point1[1], 2)) / 2;
    var r =  Math.floor(number / 2) * q / 4;
    var center = [(point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2];
    var arc = halfEclipse(q, r, center, 50);
    var angle = (point1[1] === point2[1]) ? Math.PI / 2 : Math.atan2(point2[1] - point1[1], point2[0] - point1[0]);
    if (number % 2 === 1)
        angle = angle + Math.PI;
    arc.rotate(angle, center);
    return arc;
}

function halfEclipse(q, r, center, segments) {
    var pointList = [];
    var dAngle = segments + 1;
    for (var i = 0; i < dAngle; i++) {
        var Angle = Math.PI * i / (dAngle - 1);
        var x = center[0] + q * Math.cos(Angle);
        var y = center[1] + r * Math.sin(Angle);
        var point = [x, y];
        pointList.push(point);
    }
    return new LineString(pointList)
}

export default arc;
