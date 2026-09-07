from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    path('dashboard/', views.admin_dashboard_view, name='dashboard'),
    path('users/', views.admin_users_view, name='users'),
    path('users/<int:user_id>/', views.admin_user_detail_view, name='user_detail'),
    path('garages/', views.admin_garages_view, name='garages'),
    path('garages/<int:garage_id>/verify/', views.admin_garage_verify_view, name='garage_verify'),
    path('orders/', views.admin_orders_view, name='orders'),
    path('payments/', views.admin_payments_view, name='payments'),
    path('support/', views.admin_support_view, name='support'),
    path('support/<int:ticket_id>/', views.admin_ticket_detail_view, name='ticket_detail'),
    path('reviews/', views.admin_reviews_view, name='reviews'),
]
