from django.urls import path

from . import views

app_name = 'diagram'
urlpatterns = [
    path("<diagram_pk>/", views.index, name='index'),
    path("<diagram_pk>/graph.json", views.graph, name='graph'),
    path('<diagram_pk>/inactive_connections', views.InactiveView.as_view(), name='inactive_connections'),
    path('<diagram_pk>/update_positions', views.update_positions, name='update_positions'),
    path('new', views.update, name='create'),
    path('<diagram_pk>/update', views.update, name='update'),
    path('<diagram_pk>/manage_devices', views.manage_devices, name='manage_devices'),
]
