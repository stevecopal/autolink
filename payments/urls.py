from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path(
        "paiement/<uuid:payment_id>/", views.payment_detail_view, name="payment_detail"
    ),
    path("paiements/", views.payment_list_view, name="payment_list"),
    path(
        "garages/<uuid:garage_id>/activation/",
        views.garage_activation_payment_view,
        name="garage_activation",
    ),
    path("webhook/", views.payment_webhook_view, name="payment_webhook"),
    path(
        "recu/<uuid:receipt_id>/",
        views.receipt_download_view,
        name="receipt_download",
    ),
]
