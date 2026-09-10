import json

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
    quand CamPay est indisponible (token/collect échoue).
    """

    def get_token(self) -> str:
        raise CamPayError("CamPay unavailable for test")

    def collect(self, payment, phone_number: str) -> CamPayCollectResult:
        raise CamPayError("CamPay unavailable for test")


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

    def _webhook_payload(self, payment, status="SUCCESSFUL", **overrides):
        payload = {
            "external_reference": payment.provider_reference,
            "status": status,
            "amount": str(GARAGE_ACTIVATION_AMOUNT),
            "currency": GARAGE_ACTIVATION_CURRENCY,
            "from": "23760000000",
        }
        payload.update(overrides)
        return payload

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
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
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
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
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
        response1 = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
        response2 = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(Payment.objects.filter(garage=self.garage).count(), 1)

    def test_webhook_rejects_missing_external_reference(self):
        payload = {"status": "SUCCESSFUL"}
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
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

        payload = self._webhook_payload(payment, status="SUCCESSFUL", amount="999")
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE="",
        )
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertNotEqual(payment.status, Payment.Status.SUCCESS)

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

        original = CamPayProvider._get_cam_pay_provider_for_tests()
        try:
            set_cam_pay_provider_for_tests(original)
            response = self.client.post(
                reverse("payments:garage_payment_init", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 503)
        finally:
            set_cam_pay_provider_for_tests(original)

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

        original = CamPayProvider._get_cam_pay_provider_for_tests()
        try:
            set_cam_pay_provider_for_tests(original)
            response = self.client.post(
                reverse("payments:garage_payment_retry", args=[self.garage.pk]),
                data=self._make_payment_payload(),
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            self.assertEqual(response.status_code, 503)
        finally:
            set_cam_pay_provider_for_tests(original)

    def test_retry_blocked_from_pending(self):
        self._approved_garage()
        payment = Payment.objects.create(
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

        self.client.login(username="payer", password="pass")
        response = self.client.post(
            reverse("payments:garage_payment_retry", args=[self.garage.pk]),
            data=self._make_payment_payload(),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 409)


# Create your tests here.
