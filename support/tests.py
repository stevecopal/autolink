from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from garages.models import Garage
from notifications.models import Notification
from orders.models import Order

from .models import Conversation, Message, Ticket
from .services import get_or_create_ticket_conversation, send_message

User = get_user_model()


class ConversationTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.client_user = User.objects.create_user(
            username="client", password="pass", role="CLIENT"
        )
        self.other = User.objects.create_user(username="other", password="pass")
        self.admin = User.objects.create_user(
            username="admin", password="pass", role="ADMIN", is_staff=True
        )
        self.garage = Garage.objects.create(
            owner=self.client_user, name="Garage support", phone="600", address="Akwa"
        )
        self.order = Order.objects.create(
            user=self.user, garage=self.garage, total=1000
        )
        self.ticket = Ticket.objects.create(
            user=self.user,
            order=self.order,
            garage=self.garage,
            subject="Commande problématique",
            description="La pièce est incorrecte.",
        )
        self.conversation = get_or_create_ticket_conversation(self.ticket)

    def test_ticket_conversation_keeps_context_and_participants(self):
        self.assertEqual(self.conversation.ticket, self.ticket)
        self.assertTrue(self.conversation.participants.filter(pk=self.user.pk).exists())
        self.assertTrue(
            self.conversation.participants.filter(pk=self.admin.pk).exists()
        )

    def test_other_user_cannot_read_or_send(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(
            reverse("support:conversation_detail", args=[self.conversation.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.conversation.messages.exists())

    def test_client_can_send_and_admin_receives_notification(self):
        self.client.login(username="user", password="pass")
        response = self.client.post(
            reverse("support:conversation_detail", args=[self.conversation.pk]),
            {"body": "Pouvez-vous aider ?"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Message.objects.filter(
                conversation=self.conversation, body="Pouvez-vous aider ?"
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, title="Nouveau message"
            ).exists()
        )

    def test_admin_reply_and_read_state(self):
        message = send_message(self.conversation, self.admin, "Nous vérifions.")
        self.assertFalse(message.is_read)
        self.client.login(username="user", password="pass")
        response = self.client.get(
            reverse("support:conversation_detail", args=[self.conversation.pk])
        )
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_client_cannot_access_another_clients_conversation(self):
        self.client.login(username="client", password="pass")
        response = self.client.get(
            reverse("support:conversation_detail", args=[self.conversation.pk])
        )
        self.assertEqual(response.status_code, 404)


# Create your tests here.
