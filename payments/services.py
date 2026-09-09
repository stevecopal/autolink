from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment
from .receipts import create_or_update_receipt


class PaymentWebhookError(ValueError):
    pass


def _receipt_number(payment):
    return f"RC-{payment.pk.hex[:12].upper()}"


def _validate_garage_payment(payment, amount, currency):
    if not payment.garage_id:
        return
    try:
        received_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PaymentWebhookError("invalid_amount") from exc
    if (
        received_amount != GARAGE_ACTIVATION_AMOUNT
        or payment.amount != GARAGE_ACTIVATION_AMOUNT
    ):
        raise PaymentWebhookError("amount_mismatch")
    if (
        currency != GARAGE_ACTIVATION_CURRENCY
        or payment.currency != GARAGE_ACTIVATION_CURRENCY
    ):
        raise PaymentWebhookError("currency_mismatch")


def confirm_payment(
    payment,
    *,
    provider_transaction_id="",
    provider_reference="",
    amount=None,
    currency=None,
    metadata=None,
):
    """Confirm one provider payment atomically and activate its garage once."""
    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("garage")
            .get(pk=payment.pk)
        )
        _validate_garage_payment(payment, amount, currency)
        if payment.status == Payment.Status.SUCCESS:
            if provider_transaction_id and payment.provider_transaction_id not in (
                None,
                provider_transaction_id,
            ):
                raise PaymentWebhookError("transaction_mismatch")
            create_or_update_receipt(payment)
            return payment
        if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED):
            raise PaymentWebhookError("payment_already_closed")

        if provider_transaction_id:
            payment.provider_transaction_id = provider_transaction_id
        if provider_reference:
            payment.provider_reference = provider_reference
        payment.status = Payment.Status.SUCCESS
        payment.paid_at = payment.paid_at or timezone.now()
        receipt_metadata = dict(payment.metadata or {})
        receipt_metadata.update(metadata or {})
        receipt_metadata.setdefault("receipt_number", _receipt_number(payment))
        payment.metadata = receipt_metadata
        payment.save(
            update_fields=[
                "provider_transaction_id",
                "provider_reference",
                "status",
                "paid_at",
                "metadata",
                "updated_at",
            ]
        )

        garage = payment.garage
        if garage and garage.approval_status == Garage.ApprovalStatus.APPROVED:
            garage.payment_status = Garage.PaymentStatus.PAID
            if garage.activation_status != Garage.ActivationStatus.SUSPENDED:
                garage.activation_status = Garage.ActivationStatus.ACTIVE
            garage.save(
                update_fields=["payment_status", "activation_status", "updated_at"]
            )
        create_or_update_receipt(payment)
    return payment


def process_webhook(
    *,
    provider,
    transaction_id,
    payment_id=None,
    status,
    amount=None,
    currency=None,
    provider_reference="",
    metadata=None,
):
    """Process a provider callback; it is the only success authority."""
    if status not in (
        Payment.Status.SUCCESS,
        Payment.Status.FAILED,
        Payment.Status.CANCELLED,
    ):
        raise PaymentWebhookError("invalid_status")
    if not transaction_id and not payment_id:
        raise PaymentWebhookError("missing_transaction")

    with transaction.atomic():
        payment = None
        if transaction_id:
            payment = (
                Payment.objects.select_for_update()
                .filter(provider_transaction_id=transaction_id)
                .first()
            )
        if not payment and payment_id:
            payment = Payment.objects.select_for_update().filter(pk=payment_id).first()
        if not payment:
            raise PaymentWebhookError("unknown_transaction")
        if transaction_id and payment_id and str(payment.pk) != str(payment_id):
            raise PaymentWebhookError("transaction_payment_mismatch")
        if provider and payment.provider != provider:
            raise PaymentWebhookError("provider_mismatch")
        _validate_garage_payment(payment, amount, currency)
        if status == Payment.Status.SUCCESS:
            return confirm_payment(
                payment,
                provider_transaction_id=transaction_id,
                provider_reference=provider_reference,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        if payment.status == Payment.Status.SUCCESS:
            return payment
        if transaction_id:
            payment.provider_transaction_id = transaction_id
        payment.status = status
        payment.status_message = "Provider callback"
        payment.save(
            update_fields=[
                "provider_transaction_id",
                "status",
                "status_message",
                "updated_at",
            ]
        )
        if payment.garage_id:
            garage = Garage.objects.select_for_update().get(pk=payment.garage_id)
            garage.payment_status = (
                Garage.PaymentStatus.FAILED
                if status == Payment.Status.FAILED
                else Garage.PaymentStatus.UNPAID
            )
            garage.save(update_fields=["payment_status", "updated_at"])
        return payment
