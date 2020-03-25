import csv
import json
from io import StringIO
from itertools import groupby

from crispy_forms.helper import FormHelper
from django import forms
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.utils import DataError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from data.models import Device, Link
from diagram.models import Diagram, DeviceDiagramRelationship
from utils.visualisation import get_inactive_connections, visualisation_layout


@ensure_csrf_cookie
def index(request, diagram_pk):
    d = get_object_or_404(Diagram, pk=diagram_pk)
    return render(request, 'diagram.html', {'diagram': d})


def graph(request, diagram_pk):
    get_object_or_404(Diagram, pk=diagram_pk)
    g = {
        "devices": diagram_points(diagram_pk),
        "connections": diagram_lines(diagram_pk),
        "settings": settings(diagram_pk)
    }
    return HttpResponse(json.dumps(g), 'application/json')


def inactive_connections(request, diagram_pk):
    get_object_or_404(Diagram, pk=diagram_pk)
    return HttpResponse(json.dumps(get_inactive_connections(get_all_links(diagram_pk))), 'application/json')


@require_POST
def update_positions(request, diagram_pk):
    get_object_or_404(Diagram, pk=diagram_pk)
    positions = json.loads(request.body)
    for position in positions:
        DeviceDiagramRelationship.objects.filter(diagram=diagram_pk, device=position['id']).update(
            device_position_x=position['x'], device_position_y=position['y'])

    return HttpResponse()


class DiagramForm(forms.ModelForm):
    devices = forms.FileField(label='Add new devices', required=False, help_text="File with new device list",
                              validators=[FileExtensionValidator(['csv'])])

    class Meta:
        model = Diagram
        fields = ['name', 'display_link_descriptions', 'links_default_width', 'highlighted_links_width',
                  'highlighted_links_range_min', 'highlighted_links_range_max']

    def __init__(self, *args, **kwargs):
        super(DiagramForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = visualisation_layout


def update(request, diagram_pk=None):
    if diagram_pk is None:
        edited_diagram = None
    else:
        edited_diagram = get_object_or_404(Diagram, pk=diagram_pk)

    template_name = 'base_form.html'

    if request.method == 'POST':
        form = DiagramForm(instance=edited_diagram, data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    edited_diagram = form.save()
                    file = request.FILES.get('devices')
                    if file:
                        add_devices(edited_diagram, file)
                return HttpResponseRedirect(reverse('diagram:index', kwargs={'diagram_pk': diagram_pk}))
            except (LookupError, DataError, ValueError, IndexError):
                form.add_error('devices', 'Bad format of the file')
    else:
        form = DiagramForm(instance=edited_diagram)

    return render(request, template_name, {
        'object': edited_diagram,
        'form': form,
    })


def add_devices(edited_diagram, file):
    csv_file = StringIO(file.read().decode())
    reader = csv.reader(csv_file, delimiter=',')
    try:
        for row in reader:
            ip_address = row[1]
            community = row[2]
            device_position_x = float(row[3])
            device_position_y = float(row[4])
            device, created = Device.objects.get_or_create(ip_address=ip_address, snmp_community=community)
            edited_diagram.devices.add(device, through_defaults={'device_position_x': device_position_x,
                                                                 'device_position_y': device_position_y})
    except (LookupError, DataError, ValueError, IndexError) as e:
        raise e


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
    all_links = get_all_links(diagram_pk).values('pk', 'local_interface__device', 'remote_interface__device', 'active',
                                                 'local_interface', 'local_interface__name', 'local_interface__speed',
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
                                   local_device, remote_device)
            else:
                add_connection(all_connections, links_with_common_aggregate_interface, local_device,
                               remote_device)
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
        "source": local_device.id,
        "target": remote_device.id,
        "id": '_'.join([str(link.get('pk')) for link in link_list]),
        "number_of_links": len(link_list),
        "number_of_active_links": number_of_active_links,
        "speed": speed,
    })


def get_all_links(diagram_pk):
    devices = Diagram.objects.get(pk=diagram_pk).devices.all()
    return Link.objects.filter(local_interface__device__in=devices, remote_interface__device__in=devices)


def settings(diagram_pk):
    d = Diagram.objects.get(pk=diagram_pk)
    return {
        "display_link_descriptions": d.display_link_descriptions,
        "links_default_width": d.links_default_width,
        "highlighted_links_width": d.highlighted_links_width,
        "highlighted_links_range_min": d.highlighted_links_range_min,
        "highlighted_links_range_max": d.highlighted_links_range_max
    }
