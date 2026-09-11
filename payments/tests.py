import hashlib
import hmac
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment, Receipt
from .providers import CamPayCollectResult, CamPayError, CamPayProvider, set_cam_pay_provider_for_tests

User = get_user_model()


class _FailingCamPayProvider(CamPayProvider):
    """
    Provider utilitaire pour les tests qui doivent vérifier le comportement
    quand CamPay est indisponible (token/collect/initialize échoue).
    """

    def get_token(self) -> str:
        raise CamPayError("CamPay unavailable for test")

    def initialize(self, payment):
        raise CamPayError("CamPay unavailable for test")

    def collect(self, payment, phone_number: str) -> CamPayCollectResult:
        raise CamPayError("CamPay unavailable for test")


class _RecordingCamPayProvider(CamPayProvider):
    """Provider qui enregistre le payload /collect/ sans appeler le réseau."""

    def __init__(self):
        super().__init__()
        self.last_payload = None

    def get_token(self, force=False):
        return "test-token"

    def _post(self, path, payload, timeout=30):
        self.last_payload = payload
        # Status dans le whitelist de _check_body_error ("SUCCESSFUL").
        return {
            "reference": "camp-ref",
            "transaction_id": "camp-txn",
            "status": "SUCCESSFUL",
        }


class CamPayGarageActivationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payer", password="pass", role="CLIENT"
        )
        self.garage = Garage.objects.create(
            owner=self.user, name="Garage payé", phone="600", address="A"
        )

    def _approved_garage(self):
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.save(update_fields=["approval_status"])
        return self.garage

    def _make_payment_payload(self, phone_number="23760000000"):
        return {
            "phone_number": phone_number,
        }

    def _webhook_payload(self, payment, status="SUCCESS", **overrides):
        payload = {
            "external_reference": payment.provider_reference or payment.idempotency_key,
            "status": status,
            "amount": str(GARAGE_ACTIVATION_AMOUNT),
            "currency": GARAGE_ACTIVATION_CURRENCY,
            "phone_number": "23760000000",
        }
        payload.update(overrides)
        return payload

    def _post_webhook(self, payload):
        body = json.dumps(payload).encode("utf-8")
        secret = settings.CAMPAY_WEBHOOK_SECRET or ""
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.client.post(
            reverse("payments:payment_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE=signature,
        )

    # ------------------------------------------------------------------
    # Webhook
    # ------------------------------------------------------------------

    def test_webhook_success_activates_garage(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
            provider_reference="campay_ref_test",
        )

        payload = self._webhook_payload(payment)
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.PAID)
        self.assertEqual(self.garage.activation_status, Garage.ActivationStatus.ACTIVE)

    def test_webhook_failed_does_not_activate(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
            provider_reference="campay_ref_failed",
        )

        payload = self._webhook_payload(payment, status="FAILED")
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.FAILED)
        self.assertNotEqual(self.garage.activation_status, Garage.ActivationStatus.ACTIVE)

    def test_webhook_idempotent_success(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.SUCCESS,
            provider_reference="campay_ref_already_success",
        )

        payload = self._webhook_payload(payment)
        response1 = self._post_webhook(payload)
        response2 = self._post_webhook(payload)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(Payment.objects.filter(garage=self.garage).count(), 1)

    def test_webhook_rejects_missing_external_reference(self):
        payload = {"status": "SUCCESS"}
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 400)

    def test_payment_webhook_amount_mismatch_rejected(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
            provider_reference="campay_ref_wrong_amount",
        )

        payload = self._webhook_payload(payment, status="SUCCESS", amount="999")
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.Status.SUCCESS)

    # ------------------------------------------------------------------
    # Collect / make_payment payload
    # ------------------------------------------------------------------

    def test_collect_from_is_normalized_without_plus(self):
        """Le numéro "+237…" doit être envoyé à Campay sans le signe '+'."""
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
        )

        provider = _RecordingCamPayProvider()
        txid = provider.make_payment(payment, "+237690000000")
        self.assertEqual(provider.last_payload["from"], "237690000000")
        self.assertEqual(txid, "camp-txn")

    def test_collect_from_accepts_plain_country_code(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
        )

        provider = _RecordingCamPayProvider()
        provider.make_payment(payment, "237690000000")
        self.assertEqual(provider.last_payload["from"], "237690000000")

    # ------------------------------------------------------------------
    # Init / retry
    # ------------------------------------------------------------------

    def test_init_requires_approval(self):
        self.client.login(username="payer", password="pass")
        response = self.client.post(
            reverse("payments:garage_payment_init", args=[self.garage.pk]),
            data=self._make_payment_payload(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.filter(garage=self.garage).exists())

    def test_init_creates_pending_payment(self):
        self._approved_garage()
        self.client.login(username="payer", password="pass")

        set_cam_pay_provider_for_tests(_FailingCamPayProvider())
        try:
            response = self.client.post(
                reverse("payments:garage_payment_init", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 503)
        finally:
            set_cam_pay_provider_for_tests(CamPayProvider())

    def test_retry_from_failed(self):
        self._approved_garage()
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.FAILED,
            provider_reference="campay_ref_failed_retry",
        )
        self.garage.payment_status = Garage.PaymentStatus.FAILED
        self.garage.save(update_fields=["payment_status"])

        self.client.login(username="payer", password="pass")

        set_cam_pay_provider_for_tests(_FailingCamPayProvider())
        try:
            response = self.client.post(
                reverse("payments:garage_payment_retry", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 500)
        finally:
            set_cam_pay_provider_for_tests(CamPayProvider())

    def test_retry_from_pending_unblocks_garage(self):
        """
        Un garage resté bloqué en PENDING (collect jamais confirmé) doit pouvoir
        être relancé : le paiement non confirmé est marqué FAILED et un nouvel
        appel d'initialisation a lieu au lieu de renvoyer un blocage 409.
        """
        self._approved_garage()
        stale = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
            provider_reference="campay_ref_pending_retry",
        )
        self.garage.payment_status = Garage.PaymentStatus.PENDING
        self.garage.save(update_fields=["payment_status"])

        provider = _RecordingCamPayProvider()
        set_cam_pay_provider_for_tests(provider)
        try:
            self.client.login(username="payer", password="pass")
            response = self.client.post(
                reverse("payments:garage_payment_retry", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
        finally:
            set_cam_pay_provider_for_tests(CamPayProvider())

        # L'ancien paiement non confirmé est bien clôturé en FAILED.
        stale.refresh_from_db()
        self.assertEqual(stale.status, Payment.Status.FAILED)

        # Un nouveau paiement prêt pour le collect a été créé.
        fresh = (
            Payment.objects.filter(garage=self.garage)
            .exclude(pk=stale.pk)
            .order_by("-created_at")
            .first()
        )
        self.assertIsNotNone(fresh)
        self.assertEqual(fresh.status, Payment.Status.PROCESSING)
        self.assertEqual(fresh.provider_reference, fresh.idempotency_key)

    def test_activation_unblocks_pending_garage(self):
        """
        Le point d'entrée /activation/ ne doit plus renvoyer 400 quand le garage
        est resté bloqué en PENDING : il doit clôturer l'ancien paiement et en
        créer un nouveau (règne le scénario exact du bug rapporté).
        """
        self._approved_garage()
        stale = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
        )
        self.garage.payment_status = Garage.PaymentStatus.PENDING
        self.garage.save(update_fields=["payment_status"])

        provider = _RecordingCamPayProvider()
        set_cam_pay_provider_for_tests(provider)
        try:
            self.client.login(username="payer", password="pass")
            response = self.client.post(
                reverse("payments:garage_activation_payment", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("payment_id", data)
        finally:
            set_cam_pay_provider_for_tests(CamPayProvider())

        stale.refresh_from_db()
        self.assertEqual(stale.status, Payment.Status.FAILED)
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.PENDING)
