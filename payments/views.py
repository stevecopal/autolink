import json

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
from orders.models import Order

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .forms import PaymentForm, RefundRequestForm
from .models import Payment, Refund
from .providers import ProviderError, ProviderUnavailable, get_provider
from .services import PaymentWebhookError, process_webhook


@login_required
def payment_initiate_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status != Order.Status.PENDING:
        messages.error(request, _("This order can no longer be paid."))
        return redirect("orders:order_detail", order_number=order_number)

    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = Payment(
                order=order,
                user=request.user,
                amount=order.total,
                provider=form.cleaned_data["provider"],
                phone_number=form.cleaned_data.get("phone_number", ""),
                status=Payment.Status.INITIATED,
            )
            payment.save()

            messages.success(
                request, _("Payment initiated. You will receive a confirmation.")
            )
            return redirect("payments:payment_detail", payment_id=payment.pk)
    else:
        form = PaymentForm()

    return render(
        request,
        "dashboard/pages/client/payments/initiate.html",
        {"order": order, "form": form},
    )


@login_required
@require_POST
def garage_activation_payment_view(request, garage_id):
    garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)
    if garage.approval_status != Garage.ApprovalStatus.APPROVED:
        messages.error(request, _("Le garage doit être approuvé avant le paiement."))
        return redirect("garages:garage_dashboard")
    if garage.payment_status == Garage.PaymentStatus.PAID:
        messages.info(request, _("Le garage est déjà payé."))
        return redirect("garages:garage_dashboard")
    provider_name = request.POST.get("provider", Payment.Provider.PAYUNIT)
    if provider_name not in (Payment.Provider.PAYUNIT, Payment.Provider.CAMPAY):
        messages.error(request, _("Provider de paiement invalide."))
        return redirect("garages:garage_dashboard")
    with transaction.atomic():
        garage = Garage.objects.select_for_update().get(pk=garage.pk)
        payment = (
            Payment.objects.filter(
                garage=garage,
                provider=provider_name,
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
                provider=provider_name,
                status=Payment.Status.PENDING,
            )
    try:
        initialization = get_provider(provider_name).initialize(payment)
        if initialization and initialization.transaction_id:
            payment.provider_transaction_id = initialization.transaction_id
            payment.save(update_fields=["provider_transaction_id", "updated_at"])
    except ProviderUnavailable as exc:
        payment.status_message = str(exc)
        payment.save(update_fields=["status_message", "updated_at"])
    except ProviderError:
        payment.status = Payment.Status.FAILED
        payment.status_message = "Provider initialization failed"
        payment.save(update_fields=["status", "status_message", "updated_at"])
        messages.error(request, _("Le provider de paiement est indisponible."))
        return redirect("garages:garage_dashboard")
    garage.payment_status = Garage.PaymentStatus.PENDING
    garage.save(update_fields=["payment_status", "updated_at"])
    messages.success(
        request,
        _("Paiement de %(amount)s %(currency)s initié.")
        % {"amount": GARAGE_ACTIVATION_AMOUNT, "currency": GARAGE_ACTIVATION_CURRENCY},
    )
    return redirect("payments:payment_detail", payment_id=payment.pk)


@csrf_exempt
@require_POST
def payment_webhook_view(request):
    expected_secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")
    if expected_secret and request.headers.get("X-Webhook-Secret") != expected_secret:
        return JsonResponse({"success": False, "error": "unauthorized"}, status=401)
    try:
        payload = json.loads(request.body or "{}")
        provider = payload.get("provider", "")
        if provider and not get_provider(provider).verify_webhook(request):
            return JsonResponse(
                {"success": False, "error": "invalid_signature"}, status=401
            )
        payment = process_webhook(
            provider=provider,
            transaction_id=payload.get("provider_transaction_id")
            or payload.get("transaction_id"),
            payment_id=payload.get("payment_id"),
            status=payload.get("status"),
            amount=payload.get("amount"),
            currency=payload.get("currency"),
            provider_reference=payload.get("provider_reference", ""),
            metadata=payload.get("metadata"),
        )
    except PaymentWebhookError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    except (ValueError, TypeError, json.JSONDecodeError, ProviderError):
        return JsonResponse({"success": False, "error": "invalid_payment"}, status=400)
    return JsonResponse(
        {"success": True, "payment_id": str(payment.pk), "status": payment.status}
    )


@login_required
def payment_detail_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related("order"), pk=payment_id, user=request.user
    )
    template = (
        "dashboard/pages/client/payments/garage_activation_detail.html"
        if payment.garage_id
        else "dashboard/pages/client/payments/detail.html"
    )
    return render(request, template, {"payment": payment})


@login_required
def payment_list_view(request):
    payments = (
        Payment.objects.filter(user=request.user)
        .select_related("order")
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
def refund_request_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if order.status not in ["PAID", "PROCESSING", "READY"]:
        messages.error(request, _("Cannot request a refund for this order."))
        return redirect("orders:order_detail", order_number=order_number)

    if request.method == "POST":
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            payment = order.payments.filter(status=Payment.Status.SUCCESS).first()
            if not payment:
                messages.error(request, _("No payment found for this order."))
                return redirect("orders:order_detail", order_number=order_number)

            refund = Refund(
                payment=payment,
                order=order,
                user=request.user,
                amount=payment.amount,
                reason=form.cleaned_data["reason"],
            )
            refund.save()
            messages.success(request, _("Your refund request has been recorded."))
            return redirect("payments:refund_detail", refund_id=refund.pk)
    else:
        form = RefundRequestForm()

    return render(
        request,
        "dashboard/pages/client/payments/refund_request.html",
        {"order": order, "form": form},
    )


@login_required
def refund_detail_view(request, refund_id):
    refund = get_object_or_404(
        Refund.objects.select_related("order", "payment"),
        pk=refund_id,
        user=request.user,
    )
    return render(
        request,
        "dashboard/pages/client/payments/refund_detail.html",
        {"refund": refund},
    )
