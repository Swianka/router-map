import csv
from io import StringIO
from itertools import groupby

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.utils import DataError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from data.models import Device, Link
from map.forms import MapForm
from map.models import Map, DeviceMapRelationship
from utils.visualisation import get_inactive_connections


@ensure_csrf_cookie
@login_required
def index(request, map_pk):
    m = get_object_or_404(Map, pk=map_pk)
    return render(request, 'map.html', {'map': m})


@login_required
def inactive_connections(request, map_pk):
    get_object_or_404(Map, pk=map_pk)
    return render(request, 'inactive_connection_list.html',
                  {'inactive_list': get_inactive_connections(get_all_links(map_pk))})


@login_required
def points(request, map_pk):
    get_object_or_404(Map, pk=map_pk)
    return JsonResponse(map_points(map_pk), safe=False)


@login_required
def lines(request, map_pk):
    get_object_or_404(Map, pk=map_pk)
    return JsonResponse(map_lines(map_pk), safe=False)


@login_required
def view_settings(request, map_pk):
    m = get_object_or_404(Map, pk=map_pk)
    settings = {
        "display_link_descriptions": m.display_link_descriptions,
        "links_default_width": m.links_default_width,
        "highlighted_links_width": m.highlighted_links_width,
        "highlighted_links_range_min": m.highlighted_links_range_min,
        "highlighted_links_range_max": m.highlighted_links_range_max
    }
    return JsonResponse(settings, safe=False)


@login_required
@permission_required('map.change_map', raise_exception=True)
def update(request, map_pk=None):
    if map_pk is None:
        edited_map = None
    else:
        edited_map = get_object_or_404(Map, pk=map_pk)

    template_name = 'base_form.html'

    if request.method == 'POST':
        form = MapForm(instance=edited_map, data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    edited_map = form.save()
                    file = request.FILES.get('devices')
                    if file:
                        add_devices(edited_map, file)

                return HttpResponseRedirect(reverse('map:index', kwargs={'map_pk': edited_map.pk}))
            except (LookupError, DataError, ValueError, IndexError):
                form.add_error('devices', 'Bad format of the file')
    else:
        form = MapForm(instance=edited_map)

    return render(request, template_name, {
        'object': edited_map,
        'form': form,
    })


def add_devices(edited_map, file):
    csv_file = StringIO(file.read().decode())
    reader = csv.reader(csv_file, delimiter=',')
    try:
        for row in reader:
            ip_address = row[1]
            community = row[2]
            device_position_x = float(row[3])
            device_position_y = float(row[4])
            device, created = Device.objects.get_or_create(ip_address=ip_address, snmp_community=community)
            edited_map.devices.add(device, through_defaults={'point': Point(device_position_x, device_position_y)})
    except (LookupError, DataError, ValueError, IndexError) as e:
        raise e


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
    devices = Map.objects.get(pk=map_pk).devices.all()
    links = Link.objects.filter(local_interface__device__in=devices,
                                remote_interface__device__in=devices)
    all_links = links.values('pk', 'local_interface__device', 'remote_interface__device', 'active', 'local_interface',
                             'local_interface__name', 'local_interface__speed', 'local_interface__aggregate_interface',
                             'local_interface__aggregate_interface__name', 'remote_interface__name',
                             'remote_interface__aggregate_interface', 'remote_interface__aggregate_interface',
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
                    add_connection(connection_list, links_with_common_local_interface, local_device, remote_device,
                                   map_pk)
            else:
                add_connection(connection_list, links_with_common_aggregate_interface, local_device, remote_device,
                               map_pk)
        all_connections.append(connection_list)
    return all_connections


def add_connection(connection_list, link_list, local_device, remote_device, map_pk):
    number_of_active_links = sum([link.get('active') for link in link_list])

    if link_list[-1].get('local_interface__aggregate_interface') is not None:
        speed = link_list[-1].get('local_interface__speed')
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = link_list[-1].get('local_interface__speed')
    else:
        speed = link_list[-1].get('local_interface__speed') / number_of_active_links

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


def get_all_links(map_pk):
    devices = Map.objects.get(pk=map_pk).devices.all()
    return Link.objects.filter(local_interface__device__in=devices, remote_interface__device__in=devices)
