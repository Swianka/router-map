from django.core.serializers import serialize
from django.shortcuts import render
from django.http import HttpResponse
from itertools import groupby

from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from map.models import Device, Connection, Interface
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


def connection_info(request, device1, device2):
    return HttpResponse(json.dumps(get_connection_info(device1, device2)), 'application/json')


def device_info(request, device_pk):
    dev = Device.objects.get(pk=device_pk)
    info = {
        "ip_address": dev.ip_address,
        "name": dev.name,
        "snmp_connection": 'aktywne' if dev.snmp_connection else 'nieaktywne'
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
    Connection.objects.filter(active=False).delete()
    return HttpResponse()


def get_connections():
    features = []
    all_links = Connection.objects.values('local_interface__device', 'remote_interface__device', 'active',
                                          'local_interface',
                                          'local_interface__name', 'local_interface__speed',
                                          'local_interface__aggregate_interface',
                                          'local_interface__aggregate_interface__name', 'remote_interface__name',
                                          'remote_interface__aggregate_interface',
                                          'remote_interface__aggregate_interface',
                                          'remote_interface__aggregate_interface__name') \
        .order_by('local_interface__device', 'remote_interface__device')

    grouped_by_devices = groupby(all_links, lambda x: (
        x.get('local_interface__device'), x.get('remote_interface__device')))

    for key, group in grouped_by_devices:
        local_device = Device.objects.get(pk=key[0])
        remote_device = Device.objects.get(pk=key[1])
        description = ""
        links_number = 0
        active_links_number = 0
        group_by_aggregate = groupby(list(group), lambda x: x.get('local_interface__aggregate_interface'))
        for key2, group2 in group_by_aggregate:
            if key2 is None:
                group_by_local_interface = groupby(list(group2), lambda x: x.get('local_interface'))
                for key3, group3 in group_by_local_interface:
                    links_number, active_links_number, description = add_to_description(group3, links_number,
                                                                                        active_links_number,
                                                                                        description)
            else:
                links_number, active_links_number, description = add_to_description(group2, links_number,
                                                                                    active_links_number,
                                                                                    description)

        features.append({
            "type": "Feature",
            "properties": {
                "description": description[:-1],
                "status": link_status(links_number, active_links_number),
                "device1-pk": key[0],
                "device2-pk": key[1],
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


def get_connection_info(device1, device2):
    connection_list = []
    links = Connection.objects.filter(local_interface__device=device1, remote_interface__device=device2).values(
        'active', 'local_interface', 'local_interface__name', 'local_interface__speed',
        'local_interface__aggregate_interface', 'local_interface__aggregate_interface__name',
        'remote_interface__name', 'remote_interface__aggregate_interface',
        'remote_interface__aggregate_interface', 'remote_interface__aggregate_interface__name',
        'local_interface__device__name', 'remote_interface__device__name')

    rows = groupby(links, lambda z: z.get('local_interface__aggregate_interface'))

    for key, group in rows:
        if key is None:
            group_by_local_interface = groupby(list(group), lambda z: z.get('local_interface'))
            for key2, group2 in group_by_local_interface:
                number_of_active_links = 0
                number_of_links = 0
                for link in list(group2):
                    number_of_links += 1
                    if link.get('active'):
                        number_of_active_links += 1

                connection_list.append({
                    "number_of_links": number_of_links,
                    "number_of_active_links": number_of_active_links,
                    "speed": speed(link, number_of_active_links),
                    "device1": link.get('local_interface__device__name'),
                    "interface1": link.get('local_interface__name'),
                    "device2": link.get('remote_interface__device__name'),
                    "interface2": link.get('remote_interface__name') if link.get(
                        'remote_interface__aggregate_interface') is None else link.get(
                        'remote_interface__aggregate_interface__name')
                })

        else:
            number_of_active_links = 0
            number_of_links = 0
            for link in list(group):
                number_of_links += 1
                if link.get('active'):
                    number_of_active_links += 1

            connection_list.append({
                "number_of_links": number_of_links,
                "number_of_active_links": number_of_active_links,
                "speed": link.get('local_interface__speed'),
                "device1": link.get('local_interface__device__name'),
                "interface1": link.get('local_interface__aggregate_interface__name'),
                "device2": link.get('remote_interface__device__name'),
                "interface2": link.get('remote_interface__aggregate_interface__name')
            })
    return connection_list


def link_status(number_of_links, number_of_active_links):
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


def add_to_description(group, links, active_links, description):
    number_of_active_links = 0
    number_of_links = 0
    for link in list(group):
        number_of_links += 1
        if link.get('active'):
            number_of_active_links += 1
    links += number_of_links
    active_links += number_of_active_links
    description += str(number_of_active_links) + '/' + str(number_of_links) + '\xD7' + '{0:g}'.format(
        speed(link, number_of_active_links)) + 'G\n'
    return links, active_links, description
