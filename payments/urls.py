from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "paiement/<uuid:payment_id>/",
        views.payment_detail_view,
        name="payment_detail",
    ),
    path("paiements/", views.payment_list_view, name="payment_list"),
    path(
        "garages/<uuid:garage_id>/init/",
        views.garage_payment_init_view,
        name="garage_payment_init",
    ),
    path(
        "garages/<uuid:garage_id>/activation/",
        views.garage_activation_payment_view,
        name="garage_activation_payment",
    ),
    path(
        "garages/<uuid:garage_id>/retry/",
        views.garage_payment_retry_view,
        name="garage_payment_retry",
    ),
    path(
        "webhook/campay/",
        views.payment_webhook_view,
        name="payment_webhook",
    ),
    path(
        "recu/<uuid:receipt_id>/",
        views.receipt_download_view,
        name="receipt_download",
    ),
    path(
        "payments/<uuid:payment_id>/make/<str:gateway>/",
        views.make_payment_view,
        name="make_payment",
    ),
]
