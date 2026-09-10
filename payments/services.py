from decimal import Decimal, InvalidOperation
import logging

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment
from .receipts import create_or_update_receipt
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger("payments")


class PaymentWebhookError(ValueError):
    """Erreur levée si le webhook est invalide."""

    pass


def _receipt_number(payment):
    """Génère un numéro de reçu unique."""
    return f"RC-{payment.pk.hex[:12].upper()}"


def _validate_garage_payment(payment, amount, currency):
    """
    Valide que le montant et la devise du paiement correspondent à ceux attendus.
    """
    if not payment.garage_id:
        return  # Pas de validation si pas de garage associé

    try:
        # Convertir amount en Decimal (si c'est une chaîne ou un entier)
        received_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        logger.error(f"Montant invalide dans le webhook: {exc}")
        raise PaymentWebhookError("invalid_amount")

    # Vérifier que le montant correspond à celui attendu (1000 FCFA)
    if (
        received_amount != GARAGE_ACTIVATION_AMOUNT
        or payment.amount != GARAGE_ACTIVATION_AMOUNT
    ):
        logger.error(
            f"Montant incorrect: attendu {GARAGE_ACTIVATION_AMOUNT} {GARAGE_ACTIVATION_CURRENCY}, "
            f"reçu {received_amount} {currency}"
        )
        raise PaymentWebhookError("amount_mismatch")

    # Vérifier que la devise correspond
    if (
        currency != GARAGE_ACTIVATION_CURRENCY
        or payment.currency != GARAGE_ACTIVATION_CURRENCY
    ):
        logger.error(
            f"Devise incorrecte: attendue {GARAGE_ACTIVATION_CURRENCY}, "
            f"reçue {currency}"
        )
        raise PaymentWebhookError("currency_mismatch")


def _upgrade_user_to_client(user):
    """
    Met à jour le rôle de l'utilisateur de USER à CLIENT après un paiement réussi.
    """
    try:
        if user.role == User.Role.USER:
            user.role = User.Role.CLIENT
            user.save(update_fields=["role", "updated_at"])
            logger.info(f"Rôle de l'utilisateur {user.email} mis à jour vers CLIENT.")
    except Exception as e:
        logger.error(f"Impossible de mettre à jour le rôle USER → CLIENT: {e}")
        raise PaymentWebhookError("role_update_failed")


def _create_payment_notification(user, garage, payment):
    """
    Crée une notification in-app pour un paiement réussi.
    """
    try:
        from notifications.models import Notification

        Notification.objects.create(
            user=user,
            category=Notification.Category.PAYMENT,
            title=_("Paiement réussi"),
            message=_(
                "Votre paiement de %(amount)s %(currency)s pour le garage %(garage)s a été validé. "
                "Votre garage est maintenant actif et visible dans les recherches."
            )
            % {
                "amount": payment.amount,
                "currency": payment.currency,
                "garage": garage.name,
            },
            link=f"/garages/{garage.slug}/",
            metadata={
                "payment_id": str(payment.pk),
                "garage_id": str(garage.pk),
            },
        )
    except Exception as e:
        logger.error(f"Impossible de créer la notification de paiement: {e}")


def confirm_payment(
    payment,
    *,
    provider_transaction_id="",
    provider_reference="",
    amount=None,
    currency=None,
    metadata=None,
):
    """
    Confirme un paiement de manière atomique et active le garage associé.
    """
    try:
        with transaction.atomic():
            # Verrouiller le paiement pour éviter les conflits
            payment = (
                Payment.objects.select_for_update()
                .select_related("garage", "user")
                .get(pk=payment.pk)
            )

            # Valider le paiement
            _validate_garage_payment(payment, amount, currency)

            # Si le paiement est déjà un succès, vérifier l'idempotence
            if payment.status == Payment.Status.SUCCESS:
                if provider_transaction_id and payment.provider_transaction_id not in (
                    None,
                    provider_transaction_id,
                ):
                    raise PaymentWebhookError("transaction_mismatch")
                # Le reçu a déjà été créé
                return payment

            # Si le paiement a déjà échoué ou été annulé, ne pas le traiter
            if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED):
                raise PaymentWebhookError("payment_already_closed")

            # Mettre à jour les champs du paiement
            if provider_transaction_id:
                payment.provider_transaction_id = provider_transaction_id
            if provider_reference:
                payment.provider_reference = provider_reference
            payment.status = Payment.Status.SUCCESS
            payment.paid_at = payment.paid_at or timezone.now()

            # Mettre à jour les métadonnées (pour le reçu)
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

            # Mettre à jour le garage
            garage = payment.garage
            if garage and garage.approval_status == Garage.ApprovalStatus.APPROVED:
                garage.payment_status = Garage.PaymentStatus.PAID
                if garage.activation_status != Garage.ActivationStatus.SUSPENDED:
                    garage.activation_status = Garage.ActivationStatus.ACTIVE
                garage.save(
                    update_fields=["payment_status", "activation_status", "updated_at"]
                )

                # Mettre à jour le rôle de l'utilisateur
                _upgrade_user_to_client(payment.user)

                # Créer une notification
                _create_payment_notification(payment.user, garage, payment)

            # Créer ou mettre à jour le reçu
            create_or_update_receipt(payment)

        return payment

    except Exception as e:
        logger.error(f"Erreur lors de la confirmation du paiement: {e}")
        raise PaymentWebhookError(f"confirmation_failed: {e}")


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
    """
    Traite un callback de fournisseur de paiement.
    C'est la seule autorité pour valider un paiement.
    """
    try:
        # Valider le statut
        if status not in (
            Payment.Status.SUCCESS,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ):
            raise PaymentWebhookError(f"Statut invalide: {status}")

        if not transaction_id and not payment_id:
            raise PaymentWebhookError("transaction_id ou payment_id manquant")

        with transaction.atomic():
            payment = None

            # Rechercher le paiement par transaction_id ou payment_id
            if transaction_id:
                payment = (
                    Payment.objects.select_for_update()
                    .filter(provider_transaction_id=transaction_id)
                    .first()
                )
            if not payment and payment_id:
                payment = (
                    Payment.objects.select_for_update().filter(pk=payment_id).first()
                )

            if not payment:
                raise PaymentWebhookError("Paiement introuvable")

            if transaction_id and payment_id and str(payment.pk) != str(payment_id):
                raise PaymentWebhookError("transaction_payment_mismatch")

            if provider and payment.provider != provider:
                raise PaymentWebhookError("provider_mismatch")

            # Valider le montant et la devise
            _validate_garage_payment(payment, amount, currency)

            # Si le paiement est déjà un succès, retourner le paiement
            if status == Payment.Status.SUCCESS:
                return confirm_payment(
                    payment,
                    provider_transaction_id=transaction_id,
                    provider_reference=provider_reference,
                    amount=amount,
                    currency=currency,
                    metadata=metadata,
                )

            # Si le paiement a déjà été traité (échec ou annulation), ne pas le modifier
            if payment.status == Payment.Status.SUCCESS:
                return payment

            # Mettre à jour le statut du paiement
            if transaction_id:
                payment.provider_transaction_id = transaction_id
            payment.status = status
            payment.status_message = "Callback du fournisseur"
            payment.save(
                update_fields=[
                    "provider_transaction_id",
                    "status",
                    "status_message",
                    "updated_at",
                ]
            )

            # Mettre à jour le statut du garage si le paiement a échoué
            if payment.garage_id:
                garage = Garage.objects.select_for_update().get(pk=payment.garage_id)
                if status == Payment.Status.FAILED:
                    garage.payment_status = Garage.PaymentStatus.FAILED
                else:
                    garage.payment_status = Garage.PaymentStatus.UNPAID
                garage.save(update_fields=["payment_status", "updated_at"])

            return payment

    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook: {e}")
        raise PaymentWebhookError(f"webhook_processing_failed: {e}")
