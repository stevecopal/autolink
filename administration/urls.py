from django.urls import path

from . import views

app_name = "administration"

urlpatterns = [
    path("dashboard/", views.admin_dashboard_view, name="dashboard"),
    path("monitoring/", views.admin_monitoring_view, name="monitoring"),
    path("geography/", views.admin_geography_view, name="geography"),
    path("users/", views.admin_users_view, name="users"),
    path("users/<uuid:user_id>/", views.admin_user_detail_view, name="user_detail"),
    path("garages/", views.admin_garages_view, name="garages"),
    path(
        "garages/<uuid:garage_id>/verify/",
        views.admin_garage_verify_view,
        name="garage_verify",
    ),
    path("cities/", views.admin_cities_view, name="cities"),
    path("cities/create/", views.admin_city_create_view, name="city_create"),
    path("cities/<uuid:city_id>/edit/", views.admin_city_edit_view, name="city_edit"),
    path(
        "cities/<uuid:city_id>/delete/",
        views.admin_city_delete_view,
        name="city_delete",
    ),
    path("neighborhoods/", views.admin_neighborhoods_view, name="neighborhoods"),
    path(
        "neighborhoods/create/",
        views.admin_neighborhood_create_view,
        name="neighborhood_create",
    ),
    path(
        "neighborhoods/<uuid:neighborhood_id>/edit/",
        views.admin_neighborhood_edit_view,
        name="neighborhood_edit",
    ),
    path(
        "neighborhoods/<uuid:neighborhood_id>/delete/",
        views.admin_neighborhood_delete_view,
        name="neighborhood_delete",
    ),
    path("payments/", views.admin_payments_view, name="payments"),
    path(
        "payments/<uuid:payment_id>/",
        views.admin_payment_detail_view,
        name="payment_detail",
    ),
    path(
        "receipts/<uuid:receipt_id>/",
        views.admin_receipt_detail_view,
        name="receipt_detail",
    ),
    path("support/", views.admin_support_view, name="support"),
    path(
        "support/<uuid:ticket_id>/",
        views.admin_ticket_detail_view,
        name="ticket_detail",
    ),
    path(
        "users/<uuid:user_id>/send-urgent-message/",
        views.admin_send_urgent_message_view,
        name="send_urgent_message",
    ),
]
