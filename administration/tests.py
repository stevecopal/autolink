from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import City, Neighborhood
from garages.models import Garage
from payments.models import Payment, Receipt

User = get_user_model()


class AdminCRUDPermissionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="pass", role="ADMIN", is_staff=True
        )
        self.city, _ = City.objects.get_or_create(
            slug="test-city-douala", defaults={"name": "Douala Test", "is_active": True}
        )
        self.neighborhood, _ = Neighborhood.objects.get_or_create(
            city=self.city,
            slug="test-bonamoussadi",
            defaults={"name": "Bonamoussadi Test", "is_active": True},
        )

    def test_admin_can_load_cities(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get(reverse("administration:cities"))
        self.assertEqual(resp.status_code, 200)

    def test_anon_cannot_load_cities(self):
        resp = self.client.get(reverse("administration:cities"))
        self.assertNotEqual(resp.status_code, 200)

    def test_admin_can_load_neighborhoods(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get(reverse("administration:neighborhoods"))
        self.assertEqual(resp.status_code, 200)

    def test_city_edit_json_returns_form(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get(
            reverse("administration:city_edit", args=[self.city.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIn("form", data)

    def test_city_edit_invalid_post_returns_errors(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.post(
            reverse("administration:city_edit", args=[self.city.id]),
            {"name": "", "slug": "", "is_active": "on"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertIn(resp.status_code, [200, 400])
        data = resp.json()
        self.assertFalse(data.get("success"))
        self.assertIn("errors", data)

    def test_city_delete_non_empty_fails(self):
        from garages.models import Garage

        self.client.login(username="admin", password="pass")
        Garage.objects.create(
            name="Test Garage",
            owner=self.admin,
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status="APPROVED",
        )
        resp = self.client.post(
            reverse("administration:city_delete", args=[self.city.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        data = resp.json()
        self.assertFalse(data.get("success"))
        self.assertIn("message", data)

    def test_city_delete_empty_succeeds(self):
        self.client.login(username="admin", password="pass")
        city2, _ = City.objects.get_or_create(
            slug="test-city-to-delete", defaults={"name": "To Delete"}
        )
        resp = self.client.post(
            reverse("administration:city_delete", args=[city2.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        data = resp.json()
        self.assertTrue(data.get("success"))

    def test_neighborhood_edit_json_returns_form(self):
        self.client.login(username="admin", password="pass")
        resp = self.client.get(
            reverse("administration:neighborhood_edit", args=[self.neighborhood.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"))
        self.assertIn("form", data)

    def test_neighborhood_delete_non_empty_fails(self):
        from garages.models import Garage

        self.client.login(username="admin", password="pass")
        Garage.objects.create(
            name="Test Garage",
            owner=self.admin,
            city=self.city,
            neighborhood=self.neighborhood,
            verification_status="APPROVED",
        )
        resp = self.client.post(
            reverse("administration:neighborhood_delete", args=[self.neighborhood.id]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        data = resp.json()
        self.assertFalse(data.get("success"))
        self.assertIn("message", data)


class AdminPaymentAndSuspensionTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="payment-admin", password="pass", role="ADMIN", is_staff=True
        )
        self.client_user = User.objects.create_user(
            username="payment-client", password="pass", role="CLIENT"
        )
        self.city = City.objects.create(name="Payment City")
        self.garage = Garage.objects.create(
            owner=self.client_user,
            name="Payment Garage",
            phone="600",
            address="A",
            city=self.city,
        )

    def test_admin_can_filter_payments_and_view_receipt(self):
        payment = Payment.objects.create(
            garage=self.garage,
            user=self.client_user,
            amount=1000,
            provider=Payment.Provider.CAMPAY,
            status=Payment.Status.SUCCESS,
            provider_transaction_id="admin-tx-1",
        )
        receipt = Receipt.objects.create(
            payment=payment,
            garage=self.garage,
            owner=self.client_user,
            amount=payment.amount,
            currency=payment.currency,
            provider=payment.provider,
            status=payment.status,
        )
        self.client.login(username="payment-admin", password="pass")
        response = self.client.get(
            reverse("administration:payments")
            + f"?status=SUCCESS&garage={self.garage.pk}&provider=CAMPAY&client=payment-client"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-tx-1")
        response = self.client.get(
            reverse("administration:receipt_detail", args=[receipt.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, receipt.reference)

    def test_admin_can_suspend_client_but_not_admin_or_self(self):
        self.client.login(username="payment-admin", password="pass")
        response = self.client.post(
            reverse("administration:user_detail", args=[self.client_user.pk]),
            {"action": "toggle_active"},
        )
        self.assertEqual(response.status_code, 302)
        self.client_user.refresh_from_db()
        self.assertEqual(self.client_user.account_status, User.AccountStatus.SUSPENDED)

        response = self.client.post(
            reverse("administration:user_detail", args=[self.admin.pk]),
            {"action": "toggle_active"},
        )
        self.assertEqual(response.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.account_status, User.AccountStatus.ACTIVE)


class AdminGarageActivationTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="garage-admin", password="pass", role="ADMIN", is_staff=True
        )
        self.client_user = User.objects.create_user(
            username="garage-client", password="pass", role="CLIENT"
        )
        self.garage = Garage.objects.create(
            owner=self.client_user,
            name="Activation Garage",
            phone="600",
            address="A",
        )

    def _login(self):
        self.client.login(username="garage-admin", password="pass")

    def _post_action(self, action):
        return self.client.post(
            reverse("administration:garage_verify", args=[self.garage.pk]),
            {"action": action},
        )

    def test_admin_can_activate_approved_garage(self):
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.activation_status = Garage.ActivationStatus.INACTIVE
        self.garage.payment_status = Garage.PaymentStatus.UNPAID
        self.garage.save(
            update_fields=["approval_status", "activation_status", "payment_status"]
        )

        self._login()
        response = self._post_action("activate")
        self.assertEqual(response.status_code, 302)

        self.garage.refresh_from_db()
        self.assertEqual(self.garage.activation_status, Garage.ActivationStatus.ACTIVE)
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.PAID)
        self.assertTrue(self.garage.is_active)

    def test_admin_can_deactivate_active_garage(self):
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.activation_status = Garage.ActivationStatus.ACTIVE
        self.garage.payment_status = Garage.PaymentStatus.PAID
        self.garage.is_active = True
        self.garage.save(
            update_fields=[
                "approval_status",
                "activation_status",
                "payment_status",
                "is_active",
            ]
        )

        self._login()
        response = self._post_action("deactivate")
        self.assertEqual(response.status_code, 302)

        self.garage.refresh_from_db()
        self.assertEqual(
            self.garage.activation_status, Garage.ActivationStatus.INACTIVE
        )
        self.assertEqual(self.garage.payment_status, Garage.PaymentStatus.UNPAID)
        self.assertFalse(self.garage.is_active)

    def test_cannot_activate_unapproved_garage(self):
        self._login()
        response = self._post_action("activate")
        self.assertEqual(response.status_code, 302)

        self.garage.refresh_from_db()
        self.assertNotEqual(
            self.garage.activation_status, Garage.ActivationStatus.ACTIVE
        )

    def test_reject_button_hidden_when_approved(self):
        """Une fois approuvé, le bouton 'Rejeter le garage' ne doit plus apparaître."""
        self.garage.approval_status = Garage.ApprovalStatus.APPROVED
        self.garage.save(update_fields=["approval_status"])

        self._login()
        response = self.client.get(
            reverse("administration:garage_verify", args=[self.garage.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activer le garage")
        self.assertNotContains(response, 'name="action" value="reject"')

    def test_reject_button_visible_when_pending(self):
        self.garage.approval_status = Garage.ApprovalStatus.PENDING
        self.garage.save(update_fields=["approval_status"])

        self._login()
        response = self.client.get(
            reverse("administration:garage_verify", args=[self.garage.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="action" value="reject"')


class AdminTicketCreateTest(TestCase):
    """L'admin peut créer un ticket de support adressé à un utilisateur
    ou à une boutique (garage)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="adminticket", password="pass", role="ADMIN", is_staff=True
        )
        self.client_user = User.objects.create_user(
            username="clientticket", password="pass", role="CLIENT"
        )
        self.owner = User.objects.create_user(
            username="ownerticket", password="pass", role="CLIENT"
        )
        self.garage = Garage.objects.create(
            owner=self.owner,
            name="Garage Ticket Test",
            phone="600",
            address="A",
        )

    def _login(self):
        self.client.login(username="adminticket", password="pass")

    def test_admin_sees_create_button_in_list(self):
        self._login()
        resp = self.client.get(reverse("administration:support"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse("administration:ticket_create"))

    def test_admin_can_create_ticket_for_user(self):
        from support.models import Ticket, Conversation

        self._login()
        resp = self.client.post(
            reverse("administration:ticket_create"),
            {
                "recipient_type": "USER",
                "user": self.client_user.pk,
                "category": "PLATFORM",
                "subject": "Message officiel",
                "description": "Bonjour, votre compte a été vérifié.",
            },
        )
        self.assertEqual(resp.status_code, 302)

        ticket = Ticket.objects.get(subject="Message officiel")
        self.assertEqual(ticket.user, self.client_user)
        self.assertIsNone(ticket.garage)
        self.assertEqual(ticket.status, Ticket.Status.OPEN)

        # Conversation liée + premier message de l'admin
        conversation = Conversation.objects.get(ticket=ticket)
        self.assertTrue(
            conversation.messages.filter(sender=self.admin).exists()
        )

        # Notification envoyée au destinataire
        self.assertTrue(
            self.client_user.notifications.filter(
                notif_type="TICKET_REPLY"
            ).exists()
        )

    def test_admin_can_create_ticket_for_garage(self):
        from support.models import Ticket

        self._login()
        resp = self.client.post(
            reverse("administration:ticket_create"),
            {
                "recipient_type": "GARAGE",
                "garage": self.garage.pk,
                "category": "GARAGE",
                "subject": "Docs manquants",
                "description": "Envoyez vos documents.",
            },
        )
        self.assertEqual(resp.status_code, 302)

        ticket = Ticket.objects.get(subject="Docs manquants")
        self.assertEqual(ticket.garage, self.garage)
        self.assertEqual(ticket.user, self.owner)

    def test_user_recipient_required(self):
        self._login()
        resp = self.client.post(
            reverse("administration:ticket_create"),
            {
                "recipient_type": "USER",
                "category": "PLATFORM",
                "subject": "Sans destinataire",
                "description": "Test",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "à qui envoyer le ticket")

    def test_non_admin_forbidden(self):
        self.client.login(username="clientticket", password="pass")
        resp = self.client.get(reverse("administration:ticket_create"))
        self.assertEqual(resp.status_code, 302)  # redirigé vers login
