from django.urls import path

from . import views

app_name = 'map'
urlpatterns = [
    path('<map_pk>/', views.index, name='index'),
    path('<map_pk>/points.json', views.points, name='points'),
    path('<map_pk>/lines.json', views.lines, name='lines'),
    path('<map_pk>/inactive_connections', views.InactiveView.as_view(), name='inactive_connections'),
    path("<map_pk>/view_settings", views.view_settings, name='view_settings'),
    path('new', views.update, name='create'),
    path('<map_pk>/update', views.update, name='update'),
]
