import json
from itertools import groupby

from django import forms
from django.core.serializers import serialize
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, DetailView
from django.views.generic.edit import UpdateView

from map.models import Device, Link, Interface
from map.redis_client import redis_client


@ensure_csrf_cookie
def index(request):
    return render(request, 'map.html')


def points(request):
    points_json = serialize('geojson', Device.objects.all().exclude(point=None), geometry_field='point',
                            fields=('pk', 'snmp_connection'))
    return HttpResponse(points_json, 'application/json')


def lines(request):
    return HttpResponse(json.dumps(get_connections()), 'application/json')


def graph(request):
    return HttpResponse(json.dumps(get_graph()), 'application/json')


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


def get_connections():
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
                    add_connection(connection_list, links_with_common_local_interface, local_device, remote_device,
                                   True)
            else:
                add_connection(connection_list, links_with_common_aggregate_interface, local_device, remote_device,
                               True)
        all_connections.append(connection_list)
    return all_connections


def get_graph():
    all_devices = list(Device.objects.values('id', 'name', 'snmp_connection'))

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
    return {
        "devices": all_devices,
        "connections": all_connections
    }


def add_connection(connection_list, link_list, local_device, remote_device, with_location):
    number_of_active_links = sum([link.get('active') for link in link_list])

    if link_list[-1].get('local_interface__aggregate_interface') is not None:
        speed = link_list[-1].get('local_interface__speed')
    elif number_of_active_links == 1 or number_of_active_links == 0:
        speed = link_list[-1].get('local_interface__speed')
    else:
        speed = link_list[-1].get('local_interface__speed') / number_of_active_links

    if with_location:
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


class DeviceUpdateView(UpdateView):
    model = Device
    fields = ['description']
    template_name = 'form.html'


def connection_detail(request, connection_id):
    links = get_links(connection_id)
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
        "description": last_link.description,
    }
    return render(request, 'connection_detail.html', {'connection': connection})


class ConnectionForm(forms.Form):
    description = forms.CharField(widget=forms.Textarea)


def connection_update(request, connection_id):
    links = get_links(connection_id)
    if not links.exists():
        raise Http404("The requested resource was not found on this server.")
    if request.method == 'POST':
        form = ConnectionForm(request.POST)
        if form.is_valid():
            description = form.cleaned_data['description']
            print(description)
            links.update(description=description)

            return HttpResponseRedirect(reverse('connection_detail', args=[str(connection_id)]))
    else:
        last_link = links.last()
        form = ConnectionForm(initial={'description': last_link.description})

    return render(request, 'form.html', {'form': form})


@require_POST
def connection_delete(request, connection_id):
    links = get_links(connection_id)
    links.filter(active=False).delete()
    return HttpResponseRedirect(reverse('connection_detail', args=[str(connection_id)]))


def get_links(connection_id):
    link_pk_list = [int(x) for x in connection_id.split('_')]
    return Link.objects.filter(pk__in=link_pk_list)
