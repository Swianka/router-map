from django.urls import path


from . import views
urlpatterns = [
    path('points.json', views.points, name='points'),
    path('lines.json', views.lines, name='lines'),
    path('inactive_connections', views.inactive_connections, name='inactive_connections'),
    path('delete_inactive', views.delete_inactive, name='delete_inactive'),
    path('last_update_time', views.last_update_time, name='last_update_time'),
    path('device/<int:device_pk>/', views.device_info, name='device_info'),
    path('connection/<int:device1>/<int:device2>/', views.connection_info, name='connection_info'),
]
