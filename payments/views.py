import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from autolink import settings
from garages.models import Garage
from payments.providers.base import ProviderUnavailable

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment, Receipt
from .providers import CamPayError, get_provider
from .services import PaymentWebhookError, process_webhook

logger = logging.getLogger("payments")


def _response_json(request, success, message, status_code=200, data=None):
    payload = {"success": success, "message": str(message)}
    if data:
        payload.update(data)
    return JsonResponse(payload, status=status_code)


def _mark_garage_payment_failed(payment):
    """
    Réinitialise le statut de paiement du garage en FAILED quand un collect
    CamPay échoue. Sans cela le garage reste bloqué en PENDING et ne peut
    plus être relancé (can_activate() refuse PENDING).
    """
    if payment is None or not payment.garage_id:
        return
    garage = payment.garage
    if garage.payment_status == Garage.PaymentStatus.PENDING:
        garage.payment_status = Garage.PaymentStatus.FAILED
        garage.save(update_fields=["payment_status", "updated_at"])


# =============================================================================
# ÉTAPE 1 — INITIALISER LE PAIEMENT CHEZ CAMPAY (COLLECT)
# =============================================================================


@login_required
@require_POST
def garage_payment_init_view(request, garage_id):
    """
    Initialisation CamPay (collect).

    Crée un Payment en attendant, appelle CamPay /token/ puis /collect/,
    et met le Payment en PENDING si HTTP 200.
    """
    try:
        garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)

        if garage.approval_status != Garage.ApprovalStatus.APPROVED:
            return _response_json(
                request,
                False,
                _("Le garage doit être approuvé avant le paiement."),
                400,
            )

        if garage.payment_status == Garage.PaymentStatus.PAID:
            return _response_json(
                request,
                True,
                _("Ce garage est déjà payé et actif."),
            )

        if garage.payment_status in (Garage.PaymentStatus.PENDING,):
            return _response_json(
                request,
                False,
                _("Un paiement est déjà en cours pour ce garage."),
                409,
            )

        phone_number = request.POST.get("phone_number", "").strip()
        if not phone_number:
            return _response_json(
                request,
                False,
                _("Veuillez saisir votre numéro de téléphone."),
                400,
            )

        with transaction.atomic():
            garage = Garage.objects.select_for_update().get(pk=garage.pk)

            payment = (
                Payment.objects.filter(
                    garage=garage,
                    provider=Payment.Provider.CAMPAY,
                    status__in=[Payment.Status.INITIATED, Payment.Status.PENDING],
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
                    provider=Payment.Provider.CAMPAY,
                    status=Payment.Status.PENDING,
                )
            else:
                if payment.status not in (Payment.Status.INITIATED, Payment.Status.PENDING):
                    return _response_json(
                        request,
                        False,
                        _("Impossible de relancer le paiement dans l'état actuel."),
                        409,
                    )

            provider = get_provider("CAMPAY")
            try:
                collect_result = provider.collect(payment, phone_number)
            except CamPayError as exc:
                payment.status = Payment.Status.FAILED
                payment.status_message = str(exc)
                payment.save(update_fields=["status", "status_message", "updated_at"])
                return _response_json(
                    request,
                    False,
                    _("Le paiement n'a pas pu être initialisé. Veuillez réessayer."),
                    503,
                )

            # CamPay collect réussi → PENDING local.
            payment.provider_reference = payment.idempotency_key
            payment.status = Payment.Status.PENDING
            payment.phone_number = phone_number
            payment.save(update_fields=["provider_reference", "status", "phone_number", "updated_at"])

            garage.payment_status = Garage.PaymentStatus.PENDING
            garage.save(update_fields=["payment_status", "updated_at"])

            return _response_json(
                request,
                True,
                _("Paiement initialisé. Confirmez sur votre téléphone."),
                data={
                    "payment_id": str(payment.pk),
                    "provider_reference": payment.provider_reference,
                    "status": "pending",
                },
            )

    except CamPayError as exc:
        logger.warning(
            "CAMPAY INIT FAILED | user=%s garage=%s error=%s",
            getattr(request, "user", None),
            garage_id,
            exc,
        )
        return _response_json(
            request,
            False,
            _("Le paiement n'a pas pu être initialisé. Veuillez réessayer."),
            503,
        )

    except Exception as e:
        logger.exception(
            "CAMPAY INIT UNEXPECTED | user=%s garage=%s",
            getattr(request, "user", None),
            garage_id,
        )
        return _response_json(
            request,
            False,
            _("Une erreur inattendue est survenue. Veuillez réessayer."),
            500,
        )


# =============================================================================
# RETRY — NOUVELLE TENTATIVE
# =============================================================================


@login_required
@require_POST
def garage_payment_retry_view(request, garage_id):
    """
    Nouvelle tentative de paiement CamPay.

    Depuis un état d'échec (FAILED) ou non payé (UNPAID), on relance
    une initialisation : RETRY → INITIALIZE (choix du moyen de paiement).
    """
    try:
        garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)

        if garage.approval_status != Garage.ApprovalStatus.APPROVED:
            return _response_json(
                request,
                False,
                _("Le garage doit être approuvé avant le paiement."),
                400,
            )

        # Un garage payé/actif ne doit pas être re-facturé.
        if garage.payment_status == Garage.PaymentStatus.PAID:
            return _response_json(
                request,
                False,
                _("Ce garage est déjà payé et actif."),
                409,
            )

        # Tout autre état (UNPAID, FAILED, PENDING, PROCESSING) est relançable.
        # garage_activation_payment_view clôture les éventuels paiements non
        # confirmés et en crée un nouveau.
        return garage_activation_payment_view(request, garage_id)

    except Exception as e:
        logger.exception(
            "CAMPAY RETRY UNEXPECTED | user=%s garage=%s",
            getattr(request, "user", None),
            garage_id,
        )
        return _response_json(
            request,
            False,
            _("Une erreur inattendue est survenue. Veuillez réessayer."),
            500,
        )


# =============================================================================
# WEBHOOK CAMPAY
# =============================================================================


@csrf_exempt
@require_POST
def payment_webhook_view(request):
    """
    Webhook CamPay.

    - Vérifie la signature.
    - Extrait external_reference.
    - Met à jour Payment (SUCCESS/FAILED).
    - Idempotent : si SUCCESS déjà enregistré, retourne 200.
    """
    provider = get_provider("CAMPAY")

    if not provider.verify_webhook(request):
        logger.warning("Tentative de webhook non autorisée ou signature invalide.")
        return JsonResponse({"success": False, "message": "Invalid Signature"}, status=403)

    try:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Webhook JSON decode error: %s", e)
            return JsonResponse({"success": False, "message": "Invalid JSON payload"}, status=400)

        parsed = provider.parse_webhook(payload)
        external_reference = parsed.get("external_reference")
        status = parsed.get("status")
        amount = parsed.get("amount")
        currency = parsed.get("currency")
        provider_reference = parsed.get("provider_reference", "")
        provider_transaction_id = parsed.get("transaction_id", "")
        phone_number = parsed.get("phone_number", "")

        if not external_reference:
            logger.error("Webhook CamPay: external_reference manquant.")
            return JsonResponse({"success": False, "message": "Missing external_reference"}, status=400)

        payment = process_webhook(
            provider=Payment.Provider.CAMPAY,
            transaction_id=external_reference,
            payment_id=None,
            status=status,
            amount=amount,
            currency=currency,
            provider_reference=provider_reference,
            provider_transaction_id=provider_transaction_id,
            metadata={"phone_number": phone_number, "provider": "CAMPAY"},
        )

        return JsonResponse({"success": True, "message": "Webhook traité avec succès"}, status=200)

    except PaymentWebhookError as e:
        logger.error("Webhook processing error: %s", e)
        return JsonResponse({"success": False, "message": str(e)}, status=400)

    except Exception as e:
        logger.exception("Webhook critical error: %s", e)
        return JsonResponse({"success": False, "message": "Internal Server Error"}, status=500)


# =============================================================================
# VUES POUR LES CLIENTS (DÉTAILS DES PAIEMENTS)
# =============================================================================


@login_required
def payment_detail_view(request, payment_id):
    """
    Affiche les détails d'un paiement pour un client.
    """
    payment = get_object_or_404(
        Payment.objects.select_related("garage", "user"),
        pk=payment_id,
        user=request.user,
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
    """
    Liste des paiements d'un client.
    """
    payments = (
        Payment.objects.filter(user=request.user)
        .select_related("garage", "user")
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
    """
    Télécharger un reçu de paiement sous forme de vue imprimable.
    """
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






@login_required
@require_POST
def garage_activation_payment_view(request, garage_id):
    """
    Vue pour initier un paiement Campay pour l'activation d'un garage.
    """
    try:
        garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)

        # Un garage payé/actif ne doit pas être re-facturé.
        if garage.payment_status == Garage.PaymentStatus.PAID:
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Ce garage est déjà payé et actif."),
                },
                status=200,
            )

        # Le garage doit être approuvé pour être activé (payé).
        if garage.approval_status != Garage.ApprovalStatus.APPROVED:
            return JsonResponse(
                {
                    "success": False,
                    "message": _(
                        "Ce garage doit être approuvé avant le paiement."
                    ),
                },
                status=400,
            )

        with transaction.atomic():
            garage = Garage.objects.select_for_update().get(pk=garage.pk)

            # Si un paiement précédent n'a jamais été confirmé (initié/en attente),
            # on le clôture en FAILED avant d'en créer un nouveau. Cela évite de
            # bloquer le garage en PENDING après un collect échoué.
            Payment.objects.filter(
                garage=garage,
                provider=Payment.Provider.CAMPAY,
                status__in=[
                    Payment.Status.INITIATED,
                    Payment.Status.PENDING,
                    Payment.Status.PROCESSING,
                ],
            ).update(
                status=Payment.Status.FAILED,
                status_message=_("Remplacé par une nouvelle tentative de paiement."),
            )

            payment = Payment.objects.create(
                garage=garage,
                user=request.user,
                amount=GARAGE_ACTIVATION_AMOUNT,
                currency=GARAGE_ACTIVATION_CURRENCY,
                provider=Payment.Provider.CAMPAY,
                status=Payment.Status.PENDING,
            )

            # CamPay renvoie external_reference = idempotency_key dans le webhook.
            payment.provider_reference = payment.idempotency_key

            # Initialiser le paiement via Campay (valide montant + identifiants API)
            provider = get_provider("CAMPAY")
            init_result = provider.initialize(payment)

            if init_result:
                payment.status = Payment.Status.PROCESSING
                payment.save(
                    update_fields=[
                        "provider_reference",
                        "status",
                        "updated_at",
                    ]
                )

                garage.payment_status = Garage.PaymentStatus.PENDING
                garage.save(update_fields=["payment_status", "updated_at"])

                return JsonResponse(
                    {
                        "success": True,
                        "payment_id": str(payment.pk),
                        "active_gateways": [
                            "ORANGE_CM",
                            "MTN_CM",
                        ],  # Gateways disponibles
                        "providers": [
                            {
                                "shortcode": "ORANGE_CM",
                                "name": "Orange Money",
                                "status": "ACTIVE",
                            },
                            {
                                "shortcode": "MTN_CM",
                                "name": "MTN Mobile Money",
                                "status": "ACTIVE",
                            },
                        ],
                        "message": _("Sélectionnez un moyen de paiement."),
                    }
                )
            else:
                raise ProviderUnavailable("Initialisation Campay échouée.")

    except ProviderUnavailable as e:
        logger.error(f"Erreur initialisation paiement: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500 if "Erreur réseau" in str(e) else 400,
        )
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": _("Une erreur est survenue. Veuillez réessayer."),
            },
            status=500,
        )


@login_required
@require_POST
def make_payment_view(request, payment_id, gateway):
    """
    Vue pour effectuer un paiement Campay via USSD.
    """
    try:
        payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
        if payment.status != Payment.Status.PROCESSING:
            return JsonResponse(
                {
                    "success": False,
                    "message": _("Paiement non valide pour le paiement USSD."),
                },
                status=400,
            )

        phone_number = request.POST.get("phone_number", "").strip()
        if not phone_number:
            return JsonResponse(
                {
                    "success": False,
                    "message": _("Numéro de téléphone requis."),
                },
                status=400,
            )

        # Vérifier le format du numéro (+237 suivi de 9 chiffres)
        if not phone_number.startswith("+237") or len(phone_number) != 13:
            return JsonResponse(
                {
                    "success": False,
                    "message": _(
                        "Numéro de téléphone invalide. Format: +237XXXXXXXXX."
                    ),
                },
                status=400,
            )

        provider = get_provider("CAMPAY")
        provider_transaction_id = provider.make_payment(
            payment,
            phone_number=phone_number,
            gateway=gateway,
        )

        if provider_transaction_id:
            payment.provider_transaction_id = provider_transaction_id
            payment.save(update_fields=["provider_transaction_id", "updated_at"])
            return JsonResponse(
                {
                    "success": True,
                    "message": _(
                        "Paiement en cours. Vous allez recevoir un SMS pour confirmation."
                    ),
                    "status": "pending",
                    "retry_allowed": True,
                }
            )
        else:
            _mark_garage_payment_failed(payment)
            return JsonResponse(
                {
                    "success": False,
                    "message": _("Échec du paiement USSD."),
                    "retry_allowed": True,
                },
                status=500,
            )

    except ProviderUnavailable as e:
        logger.error(f"Erreur paiement USSD: {e}")
        _mark_garage_payment_failed(payment)
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
                "retry_allowed": True,
            },
            status=500 if "Erreur réseau" in str(e) else 400,
        )
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        _mark_garage_payment_failed(payment)
        return JsonResponse(
            {
                "success": False,
                "message": _("Une erreur est survenue. Veuillez réessayer."),
                "retry_allowed": True,
            },
            status=500,
        )


