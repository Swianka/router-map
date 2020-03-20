import json
from itertools import groupby

from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import DetailView

from map.models import Device, Link, Interface, Map, Diagram, DeviceDiagramRelationship, DeviceMapRelationship
from map.redis_client import redis_client


@ensure_csrf_cookie
def index(request, map_pk):
    try:
        m = Map.objects.get(pk=map_pk)
    except Map.DoesNotExist:
        raise Http404("The requested resource was not found on this server.")
    return render(request, 'map.html', {'map': m})


def points(request, map_pk):
    if not Map.objects.filter(pk=map_pk).exists():
        raise Http404("The requested resource was not found on this server.")

    return HttpResponse(json.dumps(map_points(map_pk)), 'application/json')


def lines(request, map_pk):
    if not Map.objects.filter(pk=map_pk).exists():
        raise Http404("The requested resource was not found on this server.")
    return HttpResponse(json.dumps(map_lines(map_pk)), 'application/json')


def graph(request, diagram_pk):
    if not Diagram.objects.filter(pk=diagram_pk).exists():
        raise Http404("The requested resource was not found on this server.")

    g = {
        "devices": diagram_points(diagram_pk),
        "connections": diagram_lines(diagram_pk)
    }
    return HttpResponse(json.dumps(g), 'application/json')


def inactive_connections(request):
    return HttpResponse(json.dumps(get_inactive_connections()), 'application/json')


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


def map_points(map_pk):
    all_devices = []

    for device_map in DeviceMapRelationship.objects.filter(map=map_pk):
        all_devices.append({
            "id": device_map.device.id,
            "name": device_map.device.name,
            "coordinates":
                [
                    float(device_map.point[0]),
                    float(device_map.point[1])
                ],
            "snmp_connection": device_map.device.snmp_connection,
        })
    return all_devices


def map_lines(map_pk):
    all_connections = []
    all_links = get_links(Map.objects.get(pk=map_pk).devices.all())

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
                    add_connection(connection_list, links_with_common_local_interface, local_device, remote_device,
                                   True, map_pk)
            else:
                add_connection(connection_list, links_with_common_aggregate_interface, local_device, remote_device,
                               True, map_pk)
        all_connections.append(connection_list)
    return all_connections


def diagram_points(diagram_pk):
    all_devices = []

    for device_diagram in DeviceDiagramRelationship.objects.filter(diagram=diagram_pk):
        all_devices.append({
            "id": device_diagram.device.id,
            "name": device_diagram.device.name,
            "coordinates":
                [
                    device_diagram.device_position_x,
                    device_diagram.device_position_y
                ],
            "snmp_connection": device_diagram.device.snmp_connection,
        })

    return all_devices


def diagram_lines(diagram_pk):
    all_connections = []
    all_links = get_links(Diagram.objects.get(pk=diagram_pk).devices.all())

    for device_pair, link_list_between_device_pair in groupby(all_links, lambda x: (x.get('local_interface__device'),
                                                                                    x.get('remote_interface__device'))):
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
                    add_connection(all_connections, links_with_common_local_interface,
                                   local_device, remote_device, False)
            else:
                add_connection(all_connections, links_with_common_aggregate_interface, local_device,
                               remote_device, False)
    return all_connections


def add_connection(connection_list, link_list, local_device, remote_device, with_location, map_pk=None):
    number_of_active_links = sum([link.get('active') for link in link_list])

    if link_list[-1].get('local_interface__aggregate_interface') is not None:
        speed = link_list[-1].get('local_interface__speed')
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = link_list[-1].get('local_interface__speed')
    else:
        speed = link_list[-1].get('local_interface__speed') / number_of_active_links

    if with_location:
        d1 = DeviceMapRelationship.objects.get(device=local_device.id, map=map_pk)
        d2 = DeviceMapRelationship.objects.get(device=remote_device.id, map=map_pk)
        connection_list.append({
            "id": '_'.join([str(link.get('pk')) for link in link_list]),
            "number_of_links": len(link_list),
            "number_of_active_links": number_of_active_links,
            "speed": speed,
            "device1_coordinates":
                [
                    float(d1.point[0]),
                    float(d1.point[1])
                ],
            "device2_coordinates":
                [
                    float(d2.point[0]),
                    float(d2.point[1])
                ]
        })
    else:
        connection_list.append({
            "source": local_device.id,
            "target": remote_device.id,
            "id": '_'.join([str(link.get('pk')) for link in link_list]),
            "number_of_links": len(link_list),
            "number_of_active_links": number_of_active_links,
            "speed": speed,
        })


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


class DeviceDetailView(DetailView):
    model = Device
    template_name = 'device_detail.html'


def connection_detail(request, connection_id):
    link_pk_list = [int(x) for x in connection_id.split('_')]
    links = Link.objects.filter(pk__in=link_pk_list)
    if not links.exists():
        raise Http404("The requested resource was not found on this server.")
    number_of_active_links = links.filter(active=True).count()
    last_link = links.last()

    if last_link.local_interface.aggregate_interface is not None:
        speed = last_link.local_interface.speed
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = last_link.local_interface.speed
    else:
        speed = last_link.local_interface.speed / number_of_active_links
    connection = {
        "device1": last_link.local_interface.device.name,
        "device2": last_link.remote_interface.device.name,
        "number_of_links": len(links),
        "number_of_active_links": number_of_active_links,
        "speed": speed,
        "interface1": last_link.local_interface.name,
        "interface2": last_link.remote_interface.name
        if last_link.remote_interface.aggregate_interface is None
        else last_link.remote_interface.aggregate_interface.name,
    }
    return render(request, 'connection_detail.html', {'connection': connection})


def get_links(devices):
    links = Link.objects.filter(local_interface__device__in=devices,
                                remote_interface__device__in=devices)
    all_links = links.values('pk', 'local_interface__device', 'remote_interface__device', 'active', 'local_interface',
                             'local_interface__name', 'local_interface__speed', 'local_interface__aggregate_interface',
                             'local_interface__aggregate_interface__name', 'remote_interface__name',
                             'remote_interface__aggregate_interface', 'remote_interface__aggregate_interface',
                             'remote_interface__aggregate_interface__name') \
        .order_by('local_interface__device', 'remote_interface__device', 'local_interface__aggregate_interface',
                  'local_interface')
    return all_links


def map_list(request):
    list_of_maps = []
    for obj in Map.objects.all():
        list_of_maps.append({
            "pk": obj.pk,
            "name": obj.name,
            "type": "map"
        })

    for obj in Diagram.objects.all():
        list_of_maps.append({
            "pk": obj.pk,
            "name": obj.name,
            "type": "diagram"
        })
    return render(request, 'map_list.html', {'map_list': list_of_maps})
