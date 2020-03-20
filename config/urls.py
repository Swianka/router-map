from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import include, path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import defaults as default_views
from map.models import Diagram

@ensure_csrf_cookie
def index(request):
    if settings.HOME_PAGE == 'diagram':
        return render(request, 'diagram.html')
    else:
        return render(request, 'map.html')


@ensure_csrf_cookie
def diagram(request, diagram_pk):
    try:
        d = Diagram.objects.get(pk=diagram_pk)
    except Diagram.DoesNotExist:
        raise Http404("The requested resource was not found on this server.")
    return render(request, 'diagram.html', {'diagram': d})


urlpatterns = [
    path("", index, name='index'),
    path("diagram/<diagram_pk>/", diagram, name='diagram'),
    path('map/', include('map.urls')),
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
