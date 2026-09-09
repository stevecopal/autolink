import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from garages.models import Garage

from .constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from .models import Payment, Receipt
from .providers import ProviderUnavailable, get_provider

User = get_user_model()


class GarageActivationPaymentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="payer", password="pass", role="CLIENT"
        )
        self.garage = Garage.objects.create(
            owner=self.user, name="Garage payé", phone="600", address="A"
        )

    def _approved_payment(self):
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.save(update_fields=["approval_status"])
        return Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.PAYUNIT,
            status=Payment.Status.PENDING,
        )

    def _webhook(self, payment, **overrides):
        payload = {
            "provider": "PAYUNIT",
            "provider_transaction_id": "tx-robust",
            "payment_id": str(payment.pk),
            "status": "SUCCESS",
            "amount": str(GARAGE_ACTIVATION_AMOUNT),
            "currency": GARAGE_ACTIVATION_CURRENCY,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET=getattr(settings, "PAYMENT_WEBHOOK_SECRET", ""),
        )

    def test_webhook_rejects_wrong_amount_and_unknown_transaction(self):
        payment = self._approved_payment()
        response = self._webhook(payment, amount="999")
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(
                {
                    "provider": "PAYUNIT",
                    "provider_transaction_id": "unknown",
                    "status": "SUCCESS",
                    "amount": str(GARAGE_ACTIVATION_AMOUNT),
                    "currency": GARAGE_ACTIVATION_CURRENCY,
                }
            ),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET=getattr(settings, "PAYMENT_WEBHOOK_SECRET", ""),
        )
        self.assertEqual(response.status_code, 400)

    def test_repeated_webhook_is_idempotent(self):
        payment = self._approved_payment()
        self.assertEqual(self._webhook(payment).status_code, 200)
        self.assertEqual(self._webhook(payment).status_code, 200)
        self.assertEqual(Payment.objects.filter(garage=self.garage).count(), 1)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertIn("receipt_number", payment.metadata)
        self.assertTrue(Receipt.objects.filter(payment=payment).exists())

    def test_failed_webhook_does_not_activate(self):
        payment = self._approved_payment()
        response = self._webhook(payment, status="FAILED")
        self.assertEqual(response.status_code, 200)
        self.garage.refresh_from_db()
        self.assertEqual(
            self.garage.activation_status, Garage.ActivationStatus.INACTIVE
        )
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.FAILED)

    def test_provider_unavailable_never_simulates_success(self):
        with self.assertRaises(ProviderUnavailable):
            get_provider("PAYUNIT").initialize(None)

    def test_payment_requires_approval(self):
        self.client.login(username="payer", password="pass")
        response = self.client.post(
            reverse("payments:garage_activation_payment", args=[self.garage.pk])
        )
        self.assertRedirects(response, reverse("garages:garage_dashboard"))
        self.assertFalse(Payment.objects.filter(garage=self.garage).exists())

    def test_webhook_does_not_activate_unapproved_garage(self):
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.PAYUNIT,
            status=Payment.Status.PENDING,
        )
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(
                {
                    "provider": "PAYUNIT",
                    "provider_transaction_id": "tx-unapproved",
                    "payment_id": str(payment.pk),
                    "status": "SUCCESS",
                    "amount": str(GARAGE_ACTIVATION_AMOUNT),
                    "currency": GARAGE_ACTIVATION_CURRENCY,
                }
            ),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET=getattr(settings, "PAYMENT_WEBHOOK_SECRET", ""),
        )
        self.assertEqual(response.status_code, 200)
        self.garage.refresh_from_db()
        self.assertEqual(
            self.garage.activation_status, Garage.ActivationStatus.INACTIVE
        )
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.UNPAID)


# Create your tests here.
