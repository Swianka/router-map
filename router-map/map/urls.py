from django.urls import path


from . import views
urlpatterns = [
    path("", views.index, name='index'),
    path('points.json', views.points, name='points'),
    path('lines.json', views.lines, name='lines'),
    path('graph.json', views.graph, name='graph'),
    path('inactive_connections', views.inactive_connections, name='inactive_connections'),
    path('delete_inactive', views.delete_inactive, name='delete_inactive'),
    path('last_update_time', views.last_update_time, name='last_update_time'),
    path('device/<int:device_pk>/', views.device_info, name='device_info'),
    path('connection/<connection_id>/', views.connection_info, name='connection_info'),
]
