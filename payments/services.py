# payments/services.py
from decimal import Decimal, InvalidOperation
import logging
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from garages.models import Garage
from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment
from .receipts import create_or_update_receipt

logger = logging.getLogger("payments")


class PaymentWebhookError(ValueError):
    pass


def _receipt_number(payment):
    return f"RC-{payment.pk.hex[:12].upper()}"


def _validate_garage_payment(payment, amount, currency):
    if not payment.garage_id:
        return
    try:
        received_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise PaymentWebhookError("Montant invalide")
    if (
        received_amount != GARAGE_ACTIVATION_AMOUNT
        or payment.amount != GARAGE_ACTIVATION_AMOUNT
    ):
        raise PaymentWebhookError("Montant incorrect")
    if (
        currency != GARAGE_ACTIVATION_CURRENCY
        or payment.currency != GARAGE_ACTIVATION_CURRENCY
    ):
        raise PaymentWebhookError("Devise incorrecte")


def _upgrade_user_to_client(user):
    try:
        if user.role == User.Role.USER:
            user.role = User.Role.CLIENT
            user.save(update_fields=["role", "updated_at"])
            logger.info(f"Rôle de {user.email} mis à jour vers CLIENT.")
    except Exception as e:
        logger.error(f"Erreur mise à jour rôle: {e}")
        raise PaymentWebhookError("Échec mise à jour rôle")


def _create_payment_notification(user, garage, payment):
    try:
        from accounts.models import Notification

        Notification.create_payment_success(user, garage, payment)
    except Exception as e:
        logger.error(f"Erreur création notification: {e}")


def confirm_payment(
    payment,
    *,
    provider_transaction_id="",
    provider_reference="",
    amount=None,
    currency=None,
    metadata=None,
):
    try:
        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("garage", "user")
                .get(pk=payment.pk)
            )
            _validate_garage_payment(payment, amount, currency)

            if payment.status == Payment.Status.SUCCESS:
                if (
                    provider_transaction_id
                    and payment.provider_transaction_id != provider_transaction_id
                ):
                    raise PaymentWebhookError("Conflit de transaction")
                return payment

            if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED):
                raise PaymentWebhookError("Paiement déjà terminé")

            if provider_transaction_id:
                payment.provider_transaction_id = provider_transaction_id
            if provider_reference:
                payment.provider_reference = provider_reference
            payment.status = Payment.Status.SUCCESS
            payment.paid_at = timezone.now()
            payment.metadata = {
                **payment.metadata,
                **(metadata or {}),
                "receipt_number": _receipt_number(payment),
            }
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
                _upgrade_user_to_client(payment.user)
                _create_payment_notification(payment.user, garage, payment)

            create_or_update_receipt(payment)
        return payment
    except Exception as e:
        logger.error(f"Erreur confirmation paiement: {e}")
        raise PaymentWebhookError(f"Échec confirmation: {e}")


def process_webhook(
    *,
    provider,
    transaction_id,
    payment_id=None,
    status,
    amount=None,
    currency=None,
    provider_reference="",
    provider_transaction_id="",
    metadata=None,
):
    try:
        if status not in (
            Payment.Status.SUCCESS,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ):
            raise PaymentWebhookError(f"Statut invalide: {status}")

        with transaction.atomic():
            payment = None
            if transaction_id:
                # CamPay envoie external_reference = idempotency_key,
                # stocké dans provider_reference (ou idempotency_key).
                payment = (
                    Payment.objects.select_for_update()
                    .filter(provider_reference=transaction_id)
                    .first()
                )
            if not payment and transaction_id:
                payment = (
                    Payment.objects.select_for_update()
                    .filter(provider_transaction_id=transaction_id)
                    .first()
                )
            if not payment and transaction_id:
                payment = (
                    Payment.objects.select_for_update()
                    .filter(idempotency_key=transaction_id)
                    .first()
                )
            if not payment and payment_id:
                payment = (
                    Payment.objects.select_for_update().filter(pk=payment_id).first()
                )
            if not payment:
                raise PaymentWebhookError("Paiement introuvable")

            if provider and payment.provider != provider:
                raise PaymentWebhookError("Fournisseur incorrect")

            _validate_garage_payment(payment, amount, currency)

            if status == Payment.Status.SUCCESS:
                return confirm_payment(
                    payment,
                    provider_transaction_id=provider_transaction_id,
                    provider_reference=provider_reference,
                    amount=amount,
                    currency=currency,
                    metadata=metadata,
                )

            if payment.status == Payment.Status.SUCCESS:
                return payment

            if provider_transaction_id:
                payment.provider_transaction_id = provider_transaction_id
            payment.status = status
            payment.status_message = "Callback fournisseur"
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
                if status == Payment.Status.FAILED:
                    garage.payment_status = Garage.PaymentStatus.FAILED
                else:
                    garage.payment_status = Garage.PaymentStatus.UNPAID
                garage.save(update_fields=["payment_status", "updated_at"])
            return payment
    except Exception as e:
        logger.error(f"Erreur traitement webhook: {e}")
        raise PaymentWebhookError(f"Échec webhook: {e}")
