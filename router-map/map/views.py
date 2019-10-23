from django.core.serializers import serialize
from django.shortcuts import render
from django.http import HttpResponse
from itertools import groupby

from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from map.models import Device, Link, Interface
import json

from map.redis_client import redis_client


@ensure_csrf_cookie
def index(request):
    return render(request, 'map/index.html')


def points(request):
    points_json = serialize('geojson', Device.objects.all().exclude(point=None), geometry_field='point',
                            fields=('pk', 'snmp_connection'))
    return HttpResponse(points_json, 'application/json')


def lines(request):
    return HttpResponse(json.dumps(get_connections()), 'application/json')


def inactive_connections(request):
    return HttpResponse(json.dumps(get_inactive_connections()), 'application/json')


def connection_info(request, device1, device2):
    return HttpResponse(json.dumps(get_connection_info(device1, device2)), 'application/json')


def device_info(request, device_pk):
    dev = Device.objects.get(pk=device_pk)
    info = {
        "ip_address": dev.ip_address,
        "name": dev.name,
        "snmp_connection": 'active' if dev.snmp_connection else 'inactive'
    }
    return HttpResponse(json.dumps(info), 'application/json')


def last_update_time(request):
    time = redis_client.get_last_update_time()
    if time is None:
        return HttpResponse()
    else:
        return HttpResponse(time)


@require_POST
def delete_inactive(request):
    Interface.objects.filter(active=False).delete()
    Link.objects.filter(active=False).delete()
    return HttpResponse()


def get_connections():
    features = []
    all_links = Link.objects.values('local_interface__device', 'remote_interface__device', 'active',
                                    'local_interface',
                                    'local_interface__name', 'local_interface__speed',
                                    'local_interface__aggregate_interface',
                                    'local_interface__aggregate_interface__name', 'remote_interface__name',
                                    'remote_interface__aggregate_interface',
                                    'remote_interface__aggregate_interface',
                                    'remote_interface__aggregate_interface__name') \
        .order_by('local_interface__device', 'remote_interface__device', 'local_interface__aggregate_interface',
                  'local_interface')

    for device_pair, link_list_between_device_pair in groupby(all_links, lambda x: (x.get('local_interface__device'),
                                                                                    x.get('remote_interface__device'))):
        local_device = Device.objects.get(pk=device_pair[0])
        remote_device = Device.objects.get(pk=device_pair[1])
        description = ""
        links_number = 0
        active_links_number = 0
        link_list_between_device_pair = list(link_list_between_device_pair)
        group_by_aggregate = groupby(link_list_between_device_pair,
                                     lambda x: x.get('local_interface__aggregate_interface'))
        for aggregate_interface, links_with_common_aggregate_interface in group_by_aggregate:
            links_with_common_aggregate_interface = list(links_with_common_aggregate_interface)
            if aggregate_interface is None:
                group_by_local_interface = groupby(links_with_common_aggregate_interface,
                                                   lambda x: x.get('local_interface'))
                for _, links_with_common_local_interface in group_by_local_interface:
                    links_with_common_local_interface = list(links_with_common_local_interface)
                    links_number, active_links_number, description = add_to_description(
                        links_with_common_local_interface,
                        links_number,
                        active_links_number,
                        description)
            else:
                links_number, active_links_number, description = add_to_description(
                    links_with_common_aggregate_interface,
                    links_number,
                    active_links_number,
                    description)

        features.append({
            "type": "Feature",
            "properties": {
                "description": description[:-1],
                "status": aggregated_links_status(links_number, active_links_number),
                "device1-pk": device_pair[0],
                "device2-pk": device_pair[1],
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [
                        float(local_device.point[0]),
                        float(local_device.point[1])
                    ],
                    [
                        float(remote_device.point[0]),
                        float(remote_device.point[1])
                    ]
                ]
            }
        })
    collection = {
        "type": "FeatureCollection",
        "features": features
    }
    return collection


def get_inactive_connections():
    list_inactive_connections = []
    all_links = Link.objects.values('local_interface__device', 'remote_interface__device', 'active',
                                    'local_interface__device__name', 'remote_interface__device__name') \
        .order_by('local_interface__device', 'remote_interface__device')

    grouped_by_devices = groupby(all_links, lambda x: (
        x.get('local_interface__device'), x.get('remote_interface__device')))

    for device_pair, group in grouped_by_devices:
        link_list_between_device_pair = list(group)
        active_links_number = get_number_of_active_links(link_list_between_device_pair)
        if active_links_number < len(link_list_between_device_pair):
            list_inactive_connections.append({
                "device1-pk": device_pair[0],
                "device2-pk": device_pair[1],
                "description": f"{link_list_between_device_pair[-1].get('local_interface__device__name')} - "
                               f"{link_list_between_device_pair[-1].get('remote_interface__device__name')}"
            })
    return list_inactive_connections


def get_connection_info(device1_pk, device2_pk):
    try:
        device1 = Device.objects.get(pk=device1_pk)
        device2 = Device.objects.get(pk=device2_pk)
    except (Device.DoesNotExist, Device.MultipleObjectsReturned):
        return

    connection_detail_list = []
    link_list_between_device_pair = Link.objects.filter(local_interface__device=device1_pk,
                                                        remote_interface__device=device2_pk).values(
        'active', 'local_interface', 'local_interface__name', 'local_interface__speed',
        'local_interface__aggregate_interface', 'local_interface__aggregate_interface__name',
        'remote_interface__name', 'remote_interface__aggregate_interface',
        'remote_interface__aggregate_interface', 'remote_interface__aggregate_interface__name')\
        .order_by('local_interface__aggregate_interface', 'local_interface')

    grouped_by_aggregate_interface = groupby(link_list_between_device_pair,
                                             lambda z: z.get('local_interface__aggregate_interface'))
    for aggregate_interface, grouped_by_aggregate_interface in grouped_by_aggregate_interface:
        links_with_common_aggregate_interface = list(grouped_by_aggregate_interface)
        if aggregate_interface is None:
            group_by_local_interface = groupby(links_with_common_aggregate_interface,
                                               lambda z: z.get('local_interface'))
            for _, links_with_common_local_interface in group_by_local_interface:
                links_with_common_local_interface = list(links_with_common_local_interface)
                number_of_active_links = get_number_of_active_links(links_with_common_local_interface)
                number_of_links = len(links_with_common_local_interface)
                last_link = links_with_common_local_interface[-1]
                connection_detail_list.append({
                    "number_of_links": number_of_links,
                    "number_of_active_links": number_of_active_links,
                    "speed": speed(last_link, number_of_active_links),
                    "interface1": last_link.get('local_interface__name'),
                    "interface2": last_link.get('remote_interface__name') if last_link.get(
                        'remote_interface__aggregate_interface') is None else last_link.get(
                        'remote_interface__aggregate_interface__name')
                })

        else:
            number_of_active_links = get_number_of_active_links(links_with_common_aggregate_interface)
            number_of_links = len(links_with_common_aggregate_interface)
            last_link = links_with_common_aggregate_interface[-1]
            connection_detail_list.append({
                "number_of_links": number_of_links,
                "number_of_active_links": number_of_active_links,
                "speed": last_link.get('local_interface__speed'),
                "interface1": last_link.get('local_interface__aggregate_interface__name'),
                "interface2": last_link.get('remote_interface__aggregate_interface__name')
            })

    connection_details = {
        "device1": device1.name,
        "device2": device2.name,
        "links": connection_detail_list
    }
    return connection_details


def aggregated_links_status(number_of_links, number_of_active_links):
    if number_of_active_links == 0:
        return 'inactive'
    elif number_of_links == number_of_active_links:
        return 'active'
    else:
        return 'part-active'


def speed(link, number_of_active_links):
    if link.get('local_interface__aggregate_interface') is not None:
        return link.get('local_interface__speed')
    elif number_of_active_links == 1 or number_of_active_links == 0:
        return link.get('local_interface__speed')
    else:
        return link.get('local_interface__speed') / number_of_active_links


def add_to_description(link_list, links, active_links, description):
    number_of_active_links = get_number_of_active_links(link_list)
    number_of_links = len(link_list)
    last_link = link_list[-1]
    links += number_of_links
    active_links += number_of_active_links
    description += f"{number_of_active_links}/{number_of_links}\xD7{speed(last_link, number_of_active_links):g}G\n"
    return links, active_links, description


def get_number_of_active_links(link_list):
    number_of_active_links = 0
    for link in link_list:
        if link.get('active'):
            number_of_active_links += 1
    return number_of_active_links
