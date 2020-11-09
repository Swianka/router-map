from itertools import groupby

from crispy_forms.bootstrap import AppendedText
from crispy_forms.layout import Layout, Fieldset, HTML
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from visualisation.models import Visualisation


@login_required
def visualisation_tree_view(request):
    return render(request, 'visualisation_tree_view.html',
                  {'visualisations': Visualisation.objects.filter(parent__isnull=True)})


def get_visualisation_layout():
    return Layout(
        Fieldset(
            'General',
            'name',
        ),
        HTML("<hr>"),
        Fieldset(
            'View',
            'display_link_descriptions',
            'links_default_width',
            'highlighted_links_width',
            AppendedText('highlighted_links_range_min', 'Gbit/s', active=True),
            AppendedText('highlighted_links_range_max', 'Gbit/s', active=True),
        ),
        Fieldset(
            'Tree view of visualisations',
            'parent'
        )
    )


def get_inactive_connections(all_links):
    list_inactive_connections = []
    all_links_values = all_links.values('local_interface__device', 'remote_interface__device', 'active',
                                        'local_interface__device__name', 'remote_interface__device__name') \
        .order_by('local_interface__device', 'remote_interface__device')

    grouped_by_devices = groupby(all_links_values, lambda x: (
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
