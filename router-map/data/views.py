from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView

from data.models import Device, Link
from data.redis_client import redis_client


@login_required
def last_update_time(request):
    time = redis_client.get_last_update_time()
    if time is None:
        return HttpResponse()
    else:
        return HttpResponse(time)


class DeviceDetailView(LoginRequiredMixin, DetailView):
    model = Device
    template_name = 'device_detail.html'


class ConnectionView(LoginRequiredMixin, TemplateView):
    template_name = 'connection_detail.html'

    def get_context_data(self, **kwargs):
        link_pk_list = [int(x) for x in kwargs['connection_id'].split('_')]
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
            "interface1": last_link.local_interface.name
            if last_link.local_interface.aggregate_interface is None
            else last_link.local_interface.aggregate_interface.name,
            "interface2": last_link.remote_interface.name
            if last_link.remote_interface.aggregate_interface is None
            else last_link.remote_interface.aggregate_interface.name,
        }
        context = super().get_context_data(**kwargs)
        context['connection'] = connection
        return context


@require_POST
@login_required
@permission_required('data.delete_link', raise_exception=True)
def delete_inactive_links(request, connection_id):
    link_pk_list = [int(x) for x in connection_id.split('_')]
    links = Link.objects.filter(pk__in=link_pk_list)
    if not links.exists():
        raise Http404("The requested resource was not found on this server.")
    inactive_links = links.filter(active=False)
    inactive_links.delete()
    return HttpResponse()
