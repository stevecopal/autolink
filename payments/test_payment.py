# payments/test_payment.py
"""
Tests du workflow de paiement CamPay (PayUnit) avec mise à jour du statut.

Flux couvert :
    GARAGE UNPAID -> INITIALIZE -> choix ORANGE/MTN -> MAKE PAYMENT
        -> PENDING -> WEBHOOK -> SUCCESS (garage PAID / ACTIF)
                              -> FAILED  -> RETRY -> INITIALIZE

Les accès réseau vers CamPay sont simulés par un fournisseur factice.
Les webhooks sont signés avec le secret (verification de signature testée).
"""
import hashlib
import hmac
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Notification
from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment, Receipt
from .providers import (
    CamPayCollectResult,
    CamPayProvider,
    set_cam_pay_provider_for_tests,
)

User = get_user_model()

WEBHOOK_SECRET = "test-secret"


class _FakeCamPayProvider(CamPayProvider):
    """Fournisseur CamPay simulé : aucune requête réseau."""

    def initialize(self, payment):
        return CamPayCollectResult(transaction_id="FAKE-TXN-001")

    def make_payment(self, payment, phone_number, gateway="ORANGE_CM"):
        return "FAKE-TXN-002"

    def collect(self, payment, phone_number):
        return CamPayCollectResult(transaction_id="FAKE-TXN-002")


@override_settings(CAMPAY_WEBHOOK_SECRET=WEBHOOK_SECRET)
class PaymentWorkflowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="garagiste",
            password="pass",
            role=User.Role.USER,
        )
        self.garage = Garage.objects.create(
            owner=self.user,
            name="Garage Test",
            phone="600000000",
            address="Yaoundé",
        )
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.save(update_fields=["approval_status"])

        set_cam_pay_provider_for_tests(_FakeCamPayProvider())
        self.addCleanup(set_cam_pay_provider_for_tests, CamPayProvider())

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _login(self):
        self.client.login(username="garagiste", password="pass")

    def _webhook_request(self, payment, status, sig_secret=WEBHOOK_SECRET, **overrides):
        payload = {
            "external_reference": payment.idempotency_key,
            "reference": "CAMP-REF-1",
            "transaction_id": "CAMP-TXN-1",
            "status": status,
            "amount": str(GARAGE_ACTIVATION_AMOUNT),
            "currency": GARAGE_ACTIVATION_CURRENCY,
            "phone_number": "237600000000",
            "provider": "CAMPAY",
        }
        payload.update(overrides)
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            sig_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse("payments:payment_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE=signature,
        )

    def _create_payment(self, status=Payment.Status.PENDING, **kwargs):
        defaults = dict(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
        )
        defaults.update(kwargs)
        payment = Payment.objects.create(status=status, **defaults)
        return payment

    def _garage_state(self, paid=True, active=True):
        self.garage.refresh_from_db()
        self.assertEqual(
            self.garage.payment_status,
            Garage.PaymentStatus.PAID if paid else Garage.PaymentStatus.UNPAID,
        )
        self.assertEqual(
            self.garage.activation_status,
            Garage.ActivationStatus.ACTIVE if active else Garage.ActivationStatus.INACTIVE,
        )

    # ------------------------------------------------------------------
    # Flux complet : UNPAID -> INITIALIZE -> MAKE PAYMENT -> WEBHOOK SUCCESS
    # ------------------------------------------------------------------

    def test_full_flow_initialize_make_payment_webhook_success(self):
        self._login()
        response = self.client.post(
            reverse("payments:garage_activation_payment", args=[self.garage.pk]),
            data={"phone_number": "+237600000000"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        payment = Payment.objects.get(garage=self.garage)
        self.assertEqual(payment.status, Payment.Status.PROCESSING)
        self.assertEqual(
            payment.provider_transaction_id, "",
            "L'id transaction CamPay n'est posée qu'au MAKE PAYMENT.",
        )
        self.assertEqual(payment.provider_reference, payment.idempotency_key)

        gateways = {g["shortcode"]: g["status"] for g in data["providers"]}
        self.assertEqual(gateways, {"ORANGE_CM": "ACTIVE", "MTN_CM": "ACTIVE"})

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.PENDING)

        # MAKE PAYMENT (choix ORANGE)
        response = self.client.post(
            reverse(
                "payments:make_payment",
                args=[payment.pk, "ORANGE_CM"],
            ),
            data={"phone_number": "+237600000000", "gateway": "ORANGE_CM"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.provider_transaction_id, "FAKE-TXN-002")
        self.assertEqual(payment.status, Payment.Status.PROCESSING)

        # WEBHOOK SUCCESS -> mise à jour du statut
        response = self._webhook_request(payment, "SUCCESS")
        self.assertEqual(response.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertIsNotNone(payment.paid_at)

        self._garage_state(paid=True, active=True)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.CLIENT)
        self.assertTrue(
            Receipt.objects.filter(payment=payment).exists(),
            "Un reçu doit être créé après succès.",
        )

    def test_webhook_success_from_initiated_and_pending(self):
        for initial in (Payment.Status.INITIATED, Payment.Status.PENDING, Payment.Status.PROCESSING):
            payment = self._create_payment(status=initial)
            response = self._webhook_request(payment, "SUCCESS")
            self.assertEqual(response.status_code, 200, initial)
            payment.refresh_from_db()
            self.assertEqual(payment.status, Payment.Status.SUCCESS, initial)

    # ------------------------------------------------------------------
    # Statuts FAILED / CANCELLED
    # ------------------------------------------------------------------

    def test_webhook_failed_sets_garage_failed(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(payment, "FAILED")
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.FAILED)
        self.assertEqual(self.garage.activation_status, Garage.ActivationStatus.INACTIVE)

    def test_webhook_cancelled_sets_garage_unpaid(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(payment, "CANCELLED")
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.CANCELLED)
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.UNPAID)

    # ------------------------------------------------------------------
    # Idempotence et états terminaux
    # ------------------------------------------------------------------

    def test_webhook_success_is_idempotent(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        for _ in range(2):
            response = self._webhook_request(payment, "SUCCESS")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Receipt.objects.filter(payment=payment).count(),
            1,
            "Un seul reçu doit exister après succès (idempotence).",
        )
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)

    def test_webhook_failed_after_success_keeps_success(self):
        self._create_payment(status=Payment.Status.SUCCESS)
        self.garage.payment_status = Garage.PaymentStatus.PAID
        self.garage.activation_status = Garage.ActivationStatus.ACTIVE
        self.garage.save(update_fields=["payment_status", "activation_status"])
        payment = Payment.objects.get(garage=self.garage)
        response = self._webhook_request(payment, "FAILED")
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self._garage_state(paid=True, active=True)

    def test_webhook_success_after_failed_rejected(self):
        payment = self._create_payment(status=Payment.Status.FAILED)
        self.garage.payment_status = Garage.PaymentStatus.FAILED
        self.garage.save(update_fields=["payment_status"])
        response = self._webhook_request(payment, "SUCCESS")
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.FAILED)

    # ------------------------------------------------------------------
    # Validation du webhook
    # ------------------------------------------------------------------

    def test_webhook_invalid_status_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(payment, "BOGUS")
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_webhook_unknown_payment_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(
            payment,
            "SUCCESS",
            external_reference="unknown-external-ref",
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_missing_external_reference_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        payload = {
            "external_reference": "",
            "status": "SUCCESS",
            "amount": str(GARAGE_ACTIVATION_AMOUNT),
            "currency": GARAGE_ACTIVATION_CURRENCY,
        }
        body = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE=signature,
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_amount_mismatch_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(
            payment, "SUCCESS", amount="999"
        )
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_webhook_bad_signature_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        response = self._webhook_request(
            payment, "SUCCESS", sig_secret="wrong-secret"
        )
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_webhook_missing_signature_rejected(self):
        payment = self._create_payment(status=Payment.Status.PENDING)
        body = json.dumps(
            {
                "external_reference": payment.idempotency_key,
                "status": "SUCCESS",
                "amount": str(GARAGE_ACTIVATION_AMOUNT),
                "currency": GARAGE_ACTIVATION_CURRENCY,
            }
        ).encode("utf-8")
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=body,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # INITIALIZE / MAKE PAYMENT contraintes
    # ------------------------------------------------------------------

    def test_init_requires_approved_garage(self):
        self.garage.approval_status = Garage.ApprovalStatus.PENDING
        self.garage.save(update_fields=["approval_status"])
        self._login()
        response = self.client.post(
            reverse("payments:garage_activation_payment", args=[self.garage.pk]),
            data={"phone_number": "+237600000000"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Payment.objects.filter(garage=self.garage).exists())

    def test_make_payment_requires_processing_status(self):
        payment = self._create_payment(status=Payment.Status.SUCCESS)
        self._login()
        response = self.client.post(
            reverse("payments:make_payment", args=[payment.pk, "ORANGE_CM"]),
            data={"phone_number": "+237600000000", "gateway": "ORANGE_CM"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)

    def test_make_payment_requires_valid_phone(self):
        payment = self._create_payment(status=Payment.Status.PROCESSING)
        self._login()
        response = self.client.post(
            reverse("payments:make_payment", args=[payment.pk, "ORANGE_CM"]),
            data={"phone_number": "12345", "gateway": "ORANGE_CM"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # RETRY : FAILED -> INITIALIZE
    # ------------------------------------------------------------------

    def test_retry_from_failed_runs_initialize(self):
        payment = self._create_payment(status=Payment.Status.FAILED)
        self.garage.payment_status = Garage.PaymentStatus.FAILED
        self.garage.save(update_fields=["payment_status"])
        self._login()

        response = self.client.post(
            reverse("payments:garage_payment_retry", args=[self.garage.pk]),
            data={"phone_number": "+237600000000"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        new_payment = Payment.objects.filter(garage=self.garage).order_by("-created_at").first()
        self.assertIsNotNone(new_payment)
        self.assertNotEqual(new_payment.pk, payment.pk)
        self.assertEqual(new_payment.status, Payment.Status.PROCESSING)

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.PENDING)

    def test_retry_blocked_from_paid(self):
        self._create_payment(status=Payment.Status.SUCCESS)
        self.garage.payment_status = Garage.PaymentStatus.PAID
        self.garage.activation_status = Garage.ActivationStatus.ACTIVE
        self.garage.save(
            update_fields=["payment_status", "activation_status"]
        )
        self._login()
        response = self.client.post(
            reverse("payments:garage_payment_retry", args=[self.garage.pk]),
            data={"phone_number": "+237600000000"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 409)