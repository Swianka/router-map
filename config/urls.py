from django.conf import settings
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path
from django.views import defaults as default_views
from django.views.decorators.csrf import ensure_csrf_cookie
from map.models import Map
from diagram.models import Diagram


@ensure_csrf_cookie
def index(request):
    return visualisation_list(request)


def visualisation_list(request):
    list_of_visualisations = []
    for obj in Map.objects.all():
        list_of_visualisations.append({
            "pk": obj.pk,
            "name": obj.name,
            "type": "map"
        })

    for obj in Diagram.objects.all():
        list_of_visualisations.append({
            "pk": obj.pk,
            "name": obj.name,
            "type": "diagram"
        })
    return render(request, 'visualisation_list.html', {'visualisation_list': list_of_visualisations})


urlpatterns = [
    path("", index, name='index'),
    path('map/', include('map.urls')),
    path('diagram/', include('diagram.urls')),
    path('data/', include('data.urls')),
    path('account/', include('account.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
