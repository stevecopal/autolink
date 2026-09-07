from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='notification_list'),
    path('<int:pk>/lu/', views.notification_mark_read_view, name='notification_mark_read'),
    path('tout-lu/', views.notification_mark_all_read_view, name='notification_mark_all_read'),
    path('api/count/', views.notification_count_api, name='notification_count'),
]
