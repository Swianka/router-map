from django.urls import path

from . import views

app_name = 'data'
urlpatterns = [
    path('last_update_time', views.last_update_time, name='last_update_time'),
    path('device/<int:pk>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('connection/<connection_id>/', views.ConnectionView.as_view(), name='connection_detail'),
]
