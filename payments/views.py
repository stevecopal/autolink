import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment, Receipt
from .providers import ProviderError, ProviderUnavailable, get_provider
from .services import PaymentWebhookError, process_webhook

logger = logging.getLogger("payments")


@login_required
@require_POST
def garage_activation_payment_view(request, garage_id):
    """Initiate a PayUnit payment for garage activation (1000 XAF)."""
    garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)

    if garage.approval_status != Garage.ApprovalStatus.APPROVED:
        messages.error(request, _("Le garage doit etre approuve avant le paiement."))
        return redirect("garages:garage_dashboard")

    if garage.payment_status == Garage.PaymentStatus.PAID:
        messages.info(request, _("Le garage est deja paye."))
        return redirect("garages:garage_dashboard")

    with transaction.atomic():
        garage = Garage.objects.select_for_update().get(pk=garage.pk)
        # Reuse an existing pending payment or create a new one
        payment = (
            Payment.objects.filter(
                garage=garage,
                provider=Payment.Provider.PAYUNIT,
                status__in=[
                    Payment.Status.INITIATED,
                    Payment.Status.PENDING,
                    Payment.Status.PROCESSING,
                ],
            )
            .order_by("-created_at")
            .first()
        )
        if not payment:
            payment = Payment.objects.create(
                garage=garage,
                user=request.user,
                amount=GARAGE_ACTIVATION_AMOUNT,
                currency=GARAGE_ACTIVATION_CURRENCY,
                provider=Payment.Provider.PAYUNIT,
                status=Payment.Status.PENDING,
            )

    try:
        provider = get_provider("PAYUNIT")
        init_result = provider.initialize(payment)

        if init_result and init_result.transaction_id:
            payment.provider_transaction_id = init_result.transaction_id
            payment.status = Payment.Status.PROCESSING
            payment.save(update_fields=["provider_transaction_id", "status", "updated_at"])

            # Redirect user to PayUnit hosted checkout page
            if init_result.checkout_url:
                return redirect(init_result.checkout_url)

    except ProviderUnavailable as exc:
        payment.status_message = str(exc)
        payment.save(update_fields=["status_message", "updated_at"])
        messages.error(
            request,
            _("PayUnit indisponible: %(error)s") % {"error": str(exc)},
        )
        return redirect("garages:garage_dashboard")
    except ProviderError as exc:
        payment.status = Payment.Status.FAILED
        payment.status_message = str(exc)
        payment.save(update_fields=["status", "status_message", "updated_at"])
        messages.error(request, _("Erreur de paiement: %(error)s") % {"error": str(exc)})
        return redirect("garages:garage_dashboard")

    garage.payment_status = Garage.PaymentStatus.PENDING
    garage.save(update_fields=["payment_status", "updated_at"])

    messages.success(
        request,
        _("Paiement de %(amount)s %(currency)s initie via PayUnit.")
        % {"amount": GARAGE_ACTIVATION_AMOUNT, "currency": GARAGE_ACTIVATION_CURRENCY},
    )
    return redirect("payments:payment_detail", payment_id=payment.pk)


# ── PayUnit Webhook ──────────────────────────────────────────────


@csrf_exempt
@require_POST
def payment_webhook_view(request):
    """
    Receive PayUnit webhook callbacks.

    PayUnit POSTs to this endpoint when a payment status changes.
    Body example:
    {
      "status": "SUCCESS",
      "data": {
        "transaction_status": "SUCCESS",
        "transaction_id": "PU 1672929285456",
        "transaction_amount": 1000,
        "transaction_currency": "XAF",
        "transaction_gateway": "orange_money",
        "message": "payment has been collected"
      }
    }
    """
    try:
        payload = json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

    # Verify webhook authenticity
    provider = get_provider("PAYUNIT")
    if not provider.verify_webhook(request):
        logger.warning("Webhook signature verification failed")
        return JsonResponse({"success": False, "error": "unauthorized"}, status=401)

    # Parse the normalized payload
    parsed = provider.parse_webhook(payload)
    transaction_id = parsed.get("transaction_id", "")
    status = parsed.get("status", "")
    amount = parsed.get("amount")
    currency = parsed.get("currency")

    if not transaction_id:
        return JsonResponse(
            {"success": False, "error": "missing_transaction_id"}, status=400
        )

    if status not in ("SUCCESS", "FAILED", "CANCELLED"):
        return JsonResponse(
            {"success": False, "error": f"invalid_status: {status}"}, status=400
        )

    try:
        payment = process_webhook(
            provider="PAYUNIT",
            transaction_id=transaction_id,
            status=status,
            amount=amount,
            currency=currency,
            provider_reference=parsed.get("provider_reference", ""),
            metadata={"raw_webhook": payload},
        )
    except PaymentWebhookError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    except (ValueError, TypeError) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)

    return JsonResponse(
        {"success": True, "payment_id": str(payment.pk), "status": payment.status}
    )


# ── Client payment views ────────────────────────────────────────


@login_required
def payment_detail_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("garage"), pk=payment_id, user=request.user
    )
    receipt = getattr(payment, "receipt", None)
    template = (
        "dashboard/pages/client/payments/garage_activation_detail.html"
        if payment.garage_id
        else "dashboard/pages/client/payments/detail.html"
    )
    return render(request, template, {"payment": payment, "receipt": receipt})


@login_required
def payment_list_view(request):
    payments = (
        Payment.objects.filter(user=request.user)
        .select_related("garage")
        .order_by("-created_at")
    )
    paginator = Paginator(payments, 15)
    page = request.GET.get("page")
    payments_page = paginator.get_page(page)
    return render(
        request,
        "dashboard/pages/client/payments/list.html",
        {"payments": payments_page},
    )


@login_required
def receipt_download_view(request, receipt_id):
    """Download a payment receipt as a printable view."""
    receipt = get_object_or_404(
        Receipt.objects.select_related("payment", "garage", "owner"),
        pk=receipt_id,
        owner=request.user,
    )
    return render(
        request,
        "dashboard/pages/client/payments/receipt_print.html",
        {"receipt": receipt},
    )
