from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('monitoring/', views.admin_monitoring_view, name='monitoring'),
    path('geography/', views.admin_geography_view, name='geography'),

    path('users/', views.admin_users_view, name='users'),
    path('users/<uuid:user_id>/', views.admin_user_detail_view, name='user_detail'),

    path('garages/', views.admin_garages_view, name='garages'),
    path('garages/<uuid:garage_id>/verify/', views.admin_garage_verify_view, name='garage_verify'),

    path('cities/', views.admin_cities_view, name='cities'),
    path('cities/create/', views.admin_city_create_view, name='city_create'),
    path('cities/<uuid:city_id>/edit/', views.admin_city_edit_view, name='city_edit'),
    path('cities/<uuid:city_id>/delete/', views.admin_city_delete_view, name='city_delete'),

    path('neighborhoods/', views.admin_neighborhoods_view, name='neighborhoods'),
    path('neighborhoods/create/', views.admin_neighborhood_create_view, name='neighborhood_create'),
    path('neighborhoods/<uuid:neighborhood_id>/edit/', views.admin_neighborhood_edit_view, name='neighborhood_edit'),
    path('neighborhoods/<uuid:neighborhood_id>/delete/', views.admin_neighborhood_delete_view, name='neighborhood_delete'),

    path('orders/', views.admin_orders_view, name='orders'),
    path('payments/', views.admin_payments_view, name='payments'),

    path('support/', views.admin_support_view, name='support'),
    path('support/<uuid:ticket_id>/', views.admin_ticket_detail_view, name='ticket_detail'),

    path('announcements/', views.admin_announcements_view, name='announcements'),
    path('announcements/create/', views.admin_announcement_create_view, name='announcement_create'),
    path('announcements/<uuid:announcement_id>/edit/', views.admin_announcement_edit_view, name='announcement_edit'),
    path('announcements/<uuid:announcement_id>/delete/', views.admin_announcement_delete_view, name='announcement_delete'),
    path('announcements/<uuid:announcement_id>/', views.admin_announcement_detail_view, name='announcement_detail'),

    path('notifications-admin/', views.admin_notifications_admin_view, name='notifications_admin'),

    path('reviews/', views.admin_reviews_view, name='reviews'),
]
