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
    return HttpResponse(json.dumps(get_connections2()), 'application/json')


def inactive_connections(request):
    return HttpResponse(json.dumps(get_inactive_connections()), 'application/json')


def connection_info(request, connection_id):
    return HttpResponse(json.dumps(get_connection_info(connection_id)), 'application/json')


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


def get_connections2():
    all_connections = []
    all_links = Link.objects.values('pk', 'local_interface__device', 'remote_interface__device', 'active',
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
        connection_list = []
        local_device = Device.objects.get(pk=device_pair[0])
        remote_device = Device.objects.get(pk=device_pair[1])

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
                    connection_list = add_connection(connection_list, links_with_common_local_interface,
                                                     local_device, remote_device)
            else:
                connection_list = add_connection(connection_list, links_with_common_aggregate_interface, local_device,
                                                 remote_device)
        all_connections.append(connection_list)
    return all_connections


def add_connection(connection_list, link_list, local_device, remote_device):
    number_of_active_links = sum([link.get('active') for link in link_list])

    if link_list[-1].get('local_interface__aggregate_interface') is not None:
        speed = link_list[-1].get('local_interface__speed')
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = link_list[-1].get('local_interface__speed')
    else:
        speed = link_list[-1].get('local_interface__speed') / number_of_active_links

    connection_list.append({
        "id": '_'.join([str(link.get('pk')) for link in link_list]),
        "number_of_links": len(link_list),
        "number_of_active_links": number_of_active_links,
        "speed": speed,
        "device1_coordinates":
            [
                float(local_device.point[0]),
                float(local_device.point[1])
            ],
        "device2_coordinates":
            [
                float(remote_device.point[0]),
                float(remote_device.point[1])
            ]
    })
    return connection_list


def get_inactive_connections():
    list_inactive_connections = []
    all_links = Link.objects.values('local_interface__device', 'remote_interface__device', 'active',
                                    'local_interface__device__name', 'remote_interface__device__name') \
        .order_by('local_interface__device', 'remote_interface__device')

    grouped_by_devices = groupby(all_links, lambda x: (
        x.get('local_interface__device'), x.get('remote_interface__device')))

    for device_pair, group in grouped_by_devices:
        link_list_between_device_pair = list(group)
        active_links_number = sum([link.get('active') for link in link_list_between_device_pair])
        if active_links_number < len(link_list_between_device_pair):
            list_inactive_connections.append({
                "device1_pk": device_pair[0],
                "device2_pk": device_pair[1],
                "description": f"{link_list_between_device_pair[-1].get('local_interface__device__name')} - "
                               f"{link_list_between_device_pair[-1].get('remote_interface__device__name')}"
            })
    return list_inactive_connections


def get_connection_info(connection_id):
    link_pk_list = [int(x) for x in connection_id.split('_')]
    try:
        link_list = [Link.objects.get(pk=link_pk) for link_pk in link_pk_list]
    except (Link.DoesNotExist, Link.MultipleObjectsReturned):
        return

    number_of_active_links = sum([link.active for link in link_list])
    last_link = link_list[-1]

    if last_link.local_interface.aggregate_interface is not None:
        speed = last_link.local_interface.speed
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = last_link.local_interface.speed
    else:
        speed = last_link.local_interface.speed / number_of_active_links

    connection_details = {
        "device1": last_link.local_interface.device.name,
        "device2": last_link.remote_interface.device.name,
        "number_of_links": len(link_pk_list),
        "number_of_active_links": number_of_active_links,
        "speed": speed,
        "interface1": last_link.local_interface.name,
        "interface2": last_link.remote_interface.name
        if last_link.remote_interface.aggregate_interface is None
        else last_link.remote_interface.aggregate_interface.name
    }
    return connection_details
