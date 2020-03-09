import * as d3 from "d3";

import * as settings from './settings'
import {hideDetailsCard, showDetailsCard, TYPE} from "./details";

let width = window.innerWidth;
let height = window.innerHeight - 56;

const svg = d3.select("body").insert("svg", ".main-row")
    .attr("width", window.innerWidth)
    .attr("height", window.innerHeight - 56);

svg.call(d3.zoom()
    .scaleExtent([1 / 2, 8])
    .on("zoom", zoomed));

const defs = svg.append("defs");

defs.append('pattern')
    .attr("id", "router")
    .attr("width", 1)
    .attr("height", 1)
    .append("svg:image")
    .attr("xlink:href", "/static/images/router.png")
    .attr("width", 42)
    .attr("height", 42)
    .attr("y", 0)
    .attr("x", 0);

defs.append('pattern')
    .attr("id", "router_red")
    .attr("width", 1)
    .attr("height", 1)
    .append("svg:image")
    .attr("xlink:href", "/static/images/router_red.png")
    .attr("width", 42)
    .attr("height", 42)
    .attr("x", 0)
    .attr("y", 0);

const container = svg.append("g");

function zoomed() {
    container.attr("transform", d3.event.transform);
}

refresh();

function refresh() {
    d3.json("map/graph.json", function (error, graph) {
        if (error) throw error;


        graph.connections.forEach(function (link) {
            const connections_grouped_by_devices = graph.connections.filter(function (otherLink) {
                return (otherLink.source === link.source && otherLink.target === link.target)
                    || (otherLink.source === link.target && otherLink.target === link.source);
            });

            connections_grouped_by_devices.forEach(function (s, i) {
                s.sameIndex = (i + 1);
                s.sameTotal = connections_grouped_by_devices.length;
                s.sameTotalHalf = (s.sameTotal / 2);
                s.sameUneven = ((s.sameTotal % 2) !== 0);
                s.sameMiddleLink = ((s.sameUneven === true) && (Math.ceil(s.sameTotalHalf) === s.sameIndex));
                s.sameLowerHalf = (s.sameIndex <= s.sameTotalHalf);
                s.sameArcDirection = s.sameLowerHalf ? 0 : 1;
                s.sameIndexCorrected = s.sameLowerHalf ? s.sameIndex : (s.sameIndex - Math.ceil(s.sameTotalHalf));
            });
        });

        graph.connections.sort((a, b) => b.sameTotal - a.sameTotal);
        const maxSame = graph.connections[0].sameTotal;

        graph.connections.forEach(function (link) {
            link.maxSameHalf = Math.floor(maxSame / 2);
        });

        const fixedNodes = JSON.parse(localStorage.getItem("fixedNodes"));
        if (fixedNodes) {
            graph.devices.forEach(function (node) {
                let location = fixedNodes[node.id];
                if (location) {
                    node.fx = location.x;
                    node.fy = location.y;
                }
            });
        }

        let simulation = createSimulation(graph.devices, graph.connections);

        for (let i = 0; i < 100; ++i) simulation.tick();

        let links = container.selectAll(".link");

        links = links.data(graph.connections, d => d.id);

        links.exit().remove();

        let newLinks = links.enter().insert("g", ".node")
            .attr("class", "link")
            .style("cursor", "pointer")
            .on("click", function (d) {
                showDetailsCard(d.id, TYPE.CONNECTION, refresh);
                d3.event.stopPropagation();
            });

        newLinks.append("path")
            .attr("fill-opacity", 0);

        newLinks.append('text');

        let allLinks = links.merge(newLinks);

        allLinks.select("path")
            .attr("d", linkArc)
            .attr("stroke-width", function (d) {
                return lineWidth(d.speed);
            })
            .attr("stroke", function (d) {
                return lineColor(d.number_of_active_links, d.number_of_links);
            });

        allLinks.select('text')
            .attr('x', function () {
                return pathMiddle(d3.select(this.parentNode).select("path").node()).x;
            })
            .attr('y', function () {
                return pathMiddle(d3.select(this.parentNode).select("path").node()).y;
            })
            .text(function (d) {
                if (settings.getShowLabels() === 'true') {
                    return d.number_of_active_links + '/' + d.number_of_links + '\xD7' + d.speed + 'G';
                } else {
                    return ""
                }
            });

        let nodes = container
            .selectAll(".node")
            .data(graph.devices, d => d.id);

        nodes.exit().remove();

        let newNodes = nodes.enter()
            .append("g")
            .attr("class", "node")
            .style("cursor", "pointer")
            .on("click", function (d) {
                showDetailsCard(d.id, TYPE.DEVICE, refresh);
                d3.event.stopPropagation();
            });

        newNodes.append("circle")
            .attr("r", 21);

        newNodes.append("text")
            .attr("dx", 0)
            .attr("dy", -25);

        let allNodes = nodes.merge(newNodes)
            .call(drag(simulation))
            .attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            });

        allNodes.select("circle")
            .attr("fill", function (d) {
                return icon(d.snmp_connection)
            });

        allNodes.select("text")
            .text(function (d) {
                if (settings.getShowLabels() === 'true') {
                    return d.name;
                } else {
                    return ""
                }
            });

    });
}

svg.on("click", hideDetailsCard);

d3.select(window).on("resize", resize);

function resize() {
    width = window.innerWidth;
    height = window.innerHeight;
    svg.attr("width", width).attr("height", height - 56);
}

function linkArc(d) {
    let dx = (d.target.x - d.source.x),
        dy = (d.target.y - d.source.y),
        dr = Math.sqrt(dx * dx + dy * dy),
        unevenCorrection = (d.sameUneven ? 0 : 0.5);
    let curvature = 1.3,
        arc = (1.0 / curvature) * ((dr * d.maxSameHalf) / (d.sameIndexCorrected - unevenCorrection));
    if (d.sameMiddleLink) {
        arc = 0;
    }

    return "M" + (d.source.x) + "," + (d.source.y) + "A" + arc + "," + arc + " 0 0," + d.sameArcDirection + " " + (d.target.x) + "," + (d.target.y);
}

function createSimulation(nodes, links) {
    let simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink().id(function (d) {
            return d.id;
        }).distance(150))
        .force("charge", d3.forceManyBody().strength(-1500))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("bounds", boxingForce)
        .stop();

    function boxingForce() {
        for (let node of nodes) {
            node.x = Math.max(21, Math.min(width - 42, node.x));
            node.y = Math.max(21, Math.min(height - 42, node.y));
        }
    }

    simulation.force("link")
        .links(links);

    return simulation;
}

function drag(simulation) {
    function dragged(d) {
        svg.selectAll("path")
            .filter(function (e) {
                return (e.source.fx === d.fx && e.source.fy === d.fy) || (e.target.fx === d.fx && e.target.fy === d.fy);
            })
            .attr("d", linkArc)
            .each(function () {
                let label = d3.select(this.parentNode)
                    .select("text");
                let point = pathMiddle(this);
                label.attr('x', point.x)
                    .attr('y', point.y);
            });

        d3.select(this)
            .attr("transform", function (d) {
                d.x = d3.event.x;
                d.y = d3.event.y;
                return "translate(" + d.x + "," + d.y + ")";
            });
    }


    function dragEnded() {
        var dict = {};
        simulation.nodes().forEach(function (node) {
            dict[node.id] = {"x": node.x, "y": node.y}
        });
        localStorage.setItem(
            "fixedNodes",
            JSON.stringify(dict)
        );
    }

    return d3.drag()
        .on("drag", dragged)
        .on("end", dragEnded);
}

function pathMiddle(path) {
    return path.getPointAtLength(.5 * path.getTotalLength())
}


function lineWidth(speed) {
    if (speed >= settings.getFeaturedSpeedMin() && speed <= settings.getFeaturedSpeedMax())
        return settings.getFeaturedWidth();
    else
        return settings.getWidthDefault();
}


function icon(snmpConnection) {
    if (snmpConnection)
        return "url(#router)";
    else
        return "url(#router_red)";
}

function lineColor(number_of_active_links, number_of_links) {
    if (number_of_active_links === number_of_links) {
        return '#666b6d';
    } else if (number_of_active_links === 0) {
        return '#ba0e00';
    } else {
        return '#ff9f00';
    }
}

export {refresh}
