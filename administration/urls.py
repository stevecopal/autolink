from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('monitoring/', views.admin_monitoring_view, name='monitoring'),
    path('geography/', views.admin_geography_view, name='geography'),

    path('users/', views.admin_users_view, name='users'),
    path('users/<int:user_id>/', views.admin_user_detail_view, name='user_detail'),

    path('garages/', views.admin_garages_view, name='garages'),
    path('garages/<int:garage_id>/verify/', views.admin_garage_verify_view, name='garage_verify'),

    path('cities/', views.admin_cities_view, name='cities'),
    path('cities/<int:city_id>/edit/', views.admin_city_edit_view, name='city_edit'),
    path('cities/<int:city_id>/delete/', views.admin_city_delete_view, name='city_delete'),

    path('neighborhoods/', views.admin_neighborhoods_view, name='neighborhoods'),
    path('neighborhoods/<int:neighborhood_id>/edit/', views.admin_neighborhood_edit_view, name='neighborhood_edit'),
    path('neighborhoods/<int:neighborhood_id>/delete/', views.admin_neighborhood_delete_view, name='neighborhood_delete'),

    path('orders/', views.admin_orders_view, name='orders'),
    path('payments/', views.admin_payments_view, name='payments'),

    path('support/', views.admin_support_view, name='support'),
    path('support/<int:ticket_id>/', views.admin_ticket_detail_view, name='ticket_detail'),

    path('announcements/', views.admin_announcements_view, name='announcements'),
    path('announcements/<int:announcement_id>/edit/', views.admin_announcement_edit_view, name='announcement_edit'),
    path('announcements/<int:announcement_id>/delete/', views.admin_announcement_delete_view, name='announcement_delete'),

    path('notifications-admin/', views.admin_notifications_admin_view, name='notifications_admin'),

    path('reviews/', views.admin_reviews_view, name='reviews'),
]
