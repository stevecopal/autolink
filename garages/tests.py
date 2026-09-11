import hashlib
import hmac
import io
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import City, Neighborhood
from garages.services import approve_garage
from payments.constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY
from payments.models import Payment

from .models import Garage

User = get_user_model()


class GarageCRUDPermissionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="garage-user", password="pass", role="USER"
        )
        self.other_user = User.objects.create_user(
            username="other-user", password="pass", role="CLIENT"
        )
        self.city = City.objects.create(name="Douala")
        self.neighborhood = Neighborhood.objects.create(city=self.city, name="Akwa")

    def garage_data(self, name="Mon garage"):
        return {
            "name": name,
            "description": "Réparation automobile",
            "phone": "+237600000000",
            "whatsapp": "+237600000001",
            "email": "garage@test.com",
            "address": "Akwa",
            "city": str(self.city.pk),
            "neighborhood": str(self.neighborhood.pk),
            "latitude": "4.0511",
            "longitude": "9.7679",
            "gps_accuracy": "10",
            "photo": self._fake_jpeg(),
        }

    @staticmethod
    def _fake_jpeg():
        """Return a minimal valid JPEG via Pillow."""
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (1, 1), "red").save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile("garage.jpg", buf.read(), content_type="image/jpeg")

    def test_create_generates_slug_promotes_user_and_starts_inactive(self):
        self.client.login(username="garage-user", password="pass")
        response = self.client.post(
            reverse("garages:garage_create"), self.garage_data()
        )

        self.assertRedirects(response, reverse("garages:garage_dashboard"))
        garage = Garage.objects.get(owner=self.user)
        self.user.refresh_from_db()
        self.assertEqual(garage.slug, "mon-garage")
        self.assertEqual(self.user.role, User.Role.CLIENT)
        self.assertEqual(garage.approval_status, Garage.ApprovalStatus.PENDING)
        self.assertEqual(garage.payment_status, Garage.PaymentStatus.UNPAID)
        self.assertEqual(garage.activation_status, Garage.ActivationStatus.INACTIVE)

    def test_owner_can_edit_but_other_user_cannot(self):
        garage = Garage.objects.create(
            owner=self.user, name="Garage", phone="600", address="A"
        )
        self.client.login(username="other-user", password="pass")
        response = self.client.post(
            reverse("garages:garage_edit", args=[garage.pk]),
            self.garage_data("Intrusion"),
        )
        self.assertEqual(response.status_code, 404)
        garage.refresh_from_db()
        self.assertEqual(garage.name, "Garage")

    def test_owner_can_delete_but_other_user_cannot(self):
        garage = Garage.objects.create(
            owner=self.user, name="Garage", phone="600", address="A"
        )
        self.client.login(username="other-user", password="pass")
        response = self.client.post(reverse("garages:garage_delete", args=[garage.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Garage.objects.filter(pk=garage.pk).exists())

    def test_public_filter_requires_approval_payment_and_activation(self):
        garage = Garage.objects.create(
            owner=self.user, name="ZZZ_PUBLIC_GARAGE", phone="600", address="A"
        )
        garage.approval_status = Garage.ApprovalStatus.APPROVED
        garage.payment_status = Garage.PaymentStatus.PAID
        garage.activation_status = Garage.ActivationStatus.ACTIVE
        garage.save()

        response = self.client.get(reverse("garages:garage_list"))
        self.assertContains(response, "ZZZ_PUBLIC_GARAGE")

        garage.payment_status = Garage.PaymentStatus.UNPAID
        garage.save(update_fields=["payment_status"])
        response = self.client.get(reverse("garages:garage_list"))
        self.assertNotContains(response, "ZZZ_PUBLIC_GARAGE")

    def test_approval_keeps_garage_unpaid_and_inactive(self):
        garage = Garage.objects.create(
            owner=self.user, name="Workflow", phone="600", address="A"
        )
        approve_garage(garage)
        garage.refresh_from_db()
        self.assertEqual(garage.approval_status, Garage.ApprovalStatus.APPROVED)
        self.assertEqual(garage.payment_status, Garage.PaymentStatus.UNPAID)
        self.assertEqual(garage.activation_status, Garage.ActivationStatus.INACTIVE)

    def test_webhook_success_activates_only_approved_garage(self):
        garage = Garage.objects.create(
            owner=self.user, name="Paid", phone="600", address="A"
        )
        garage.approval_status = Garage.ApprovalStatus.APPROVED
        garage.save(update_fields=["approval_status"])
        payment = Payment.objects.create(
            garage=garage,
            user=self.user,
            amount=GARAGE_ACTIVATION_AMOUNT,
            currency=GARAGE_ACTIVATION_CURRENCY,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.PENDING,
            provider_reference="campay_ref_activate",
        )
        response = self.client.post(
            reverse("payments:payment_webhook"),
            data=json.dumps(
                {
                    "external_reference": "campay_ref_activate",
                    "status": "SUCCESS",
                    "amount": str(GARAGE_ACTIVATION_AMOUNT),
                    "currency": GARAGE_ACTIVATION_CURRENCY,
                    "phone_number": "23760000000",
                }
            ).encode("utf-8"),
            content_type="application/json",
            HTTP_X_CAMPAY_SIGNATURE=hmac.new(
                (settings.CAMPAY_WEBHOOK_SECRET or "").encode(),
                json.dumps(
                    {
                        "external_reference": "campay_ref_activate",
                        "status": "SUCCESS",
                        "amount": str(GARAGE_ACTIVATION_AMOUNT),
                        "currency": GARAGE_ACTIVATION_CURRENCY,
                        "phone_number": "23760000000",
                    }
                ).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest(),
        )
        self.assertEqual(response.status_code, 200)
        garage.refresh_from_db()
        self.assertEqual(garage.payment_status, Garage.PaymentStatus.PAID)
        self.assertEqual(garage.activation_status, Garage.ActivationStatus.ACTIVE)


# Create your tests here.
