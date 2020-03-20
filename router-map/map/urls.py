from django.urls import path


from . import views
urlpatterns = [
    path("<map_pk>/", views.index, name='index'),
    path('points/<map_pk>/', views.points, name='points'),
    path('lines/<map_pk>/', views.lines, name='lines'),
    path('graph/<diagram_pk>/', views.graph, name='graph'),
    path('inactive_connections', views.inactive_connections, name='inactive_connections'),
    path('delete_inactive', views.delete_inactive, name='delete_inactive'),
    path('last_update_time', views.last_update_time, name='last_update_time'),
    path('device/<int:pk>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('connection/<connection_id>/', views.connection_detail, name='connection_detail'),
    path('map_list', views.map_list, name='map_list'),
]
