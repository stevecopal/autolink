from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "paiement/<str:order_number>/",
        views.payment_initiate_view,
        name="payment_initiate",
    ),
    path(
        "paiement/<uuid:payment_id>/", views.payment_detail_view, name="payment_detail"
    ),
    path("paiements/", views.payment_list_view, name="payment_list"),
    path(
        "garages/<uuid:garage_id>/activation/",
        views.garage_activation_payment_view,
        name="garage_activation_payment",
    ),
    path("webhook/", views.payment_webhook_view, name="payment_webhook"),
    path(
        "remboursement/<str:order_number>/",
        views.refund_request_view,
        name="refund_request",
    ),
    path(
        "remboursement/<uuid:refund_id>/",
        views.refund_detail_view,
        name="refund_detail",
    ),
]
