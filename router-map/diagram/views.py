import csv
import json
from io import StringIO
from itertools import groupby

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.utils import DataError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from data.models import Device, Link
from diagram.forms import DiagramForm, DiagramFormSet, DiagramFormSetHelper
from diagram.models import Diagram, DeviceDiagramRelationship
from visualisation.views import get_inactive_connections


@ensure_csrf_cookie
@login_required
def index(request, diagram_pk):
    d = get_object_or_404(Diagram, pk=diagram_pk)
    return render(request, 'diagram.html', {'diagram': d})


@login_required
def graph(request, diagram_pk):
    get_object_or_404(Diagram, pk=diagram_pk)
    g = {
        "devices": diagram_points(diagram_pk),
        "connections": diagram_lines(diagram_pk),
        "settings": settings(diagram_pk)
    }
    return JsonResponse(g, safe=False)


class InactiveView(LoginRequiredMixin, TemplateView):
    template_name = 'inactive_connection_list.html'

    def get_context_data(self, **kwargs):
        diagram_pk = kwargs['diagram_pk']
        get_object_or_404(Diagram, pk=diagram_pk)
        context = super().get_context_data(**kwargs)
        context['inactive_list'] = get_inactive_connections(get_all_links(diagram_pk))
        return context


@require_POST
@login_required
@permission_required('diagram.change_diagram', raise_exception=True)
def update_positions(request, diagram_pk):
    get_object_or_404(Diagram, pk=diagram_pk)
    positions = json.loads(request.body)
    for position in positions:
        DeviceDiagramRelationship.objects.filter(diagram=diagram_pk, device=position['id']).update(
            device_position_x=position['x'], device_position_y=position['y'])

    return HttpResponse()


@login_required
@permission_required('diagram.change_diagram', raise_exception=True)
def update(request, diagram_pk=None):
    if diagram_pk is None:
        edited_diagram = None
    else:
        edited_diagram = get_object_or_404(Diagram, pk=diagram_pk)

    template_name = 'form.html'

    if request.method == 'POST':
        form = DiagramForm(instance=edited_diagram, data=request.POST, files=request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    edited_diagram = form.save()
                    file = request.FILES.get('devices')
                    if file:
                        add_devices(edited_diagram, file)
                if diagram_pk is None:
                    return HttpResponseRedirect(
                        reverse('diagram:manage_devices', kwargs={'diagram_pk': edited_diagram.pk}))
                else:
                    return HttpResponseRedirect(reverse('diagram:index', kwargs={'diagram_pk': edited_diagram.pk}))
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
    reader = csv.DictReader(csv_file,
                            fieldnames=['name', 'ip_address', 'connection_type', 'snmp_community', 'device_position_x',
                                        'device_position_y'], restval='', delimiter=',')
    try:
        for row in reader:
            device, created = Device.objects.get_or_create(ip_address=row['ip_address'],
                                                           snmp_community=row['snmp_community'])
            device.connection_type = row['connection_type']
            device.save()
            edited_diagram.devices.add(device, through_defaults={'device_position_x': float(row['device_position_x']),
                                                                 'device_position_y': float(row['device_position_y'])})
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
            "connection_is_active": device_diagram.device.connection_is_active,
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
                for link in links_with_common_aggregate_interface:
                    all_connections.append(get_connection_details([link], local_device, remote_device))
            else:
                all_connections.append(get_connection_details(links_with_common_aggregate_interface, local_device,
                                                              remote_device))
    return all_connections


def get_connection_details(link_list, local_device, remote_device):
    number_of_active_links = sum([link.get('active') for link in link_list])
    speed = link_list[-1].get('local_interface__speed')

    return {
        "source": local_device.id,
        "target": remote_device.id,
        "id": '_'.join([str(link.get('pk')) for link in link_list]),
        "number_of_links": len(link_list),
        "number_of_active_links": number_of_active_links,
        "speed": speed,
    }


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


@login_required
@permission_required('diagram.change_diagram', raise_exception=True)
def manage_devices(request, diagram_pk):
    diagram = Diagram.objects.get(pk=diagram_pk)
    helper = DiagramFormSetHelper()
    if request.method == 'POST':
        formset = DiagramFormSet(request.POST,
                                 queryset=DeviceDiagramRelationship.objects.filter(diagram=diagram))

        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.diagram = diagram
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            return HttpResponseRedirect(reverse('diagram:index', kwargs={'diagram_pk': diagram_pk}))
    else:
        formset = DiagramFormSet(queryset=DeviceDiagramRelationship.objects.filter(diagram=diagram))
    cancel_url = reverse('diagram:index', kwargs={'diagram_pk': diagram_pk})
    return render(request, 'formset.html', {'form': formset, 'helper': helper, 'cancel_url': cancel_url})
