from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from garages.models import Garage
from orders.models import Order
from payments.models import Payment
from support.models import Ticket

from .models import Notification
from .services import (
    notify_garage_event,
    notify_order_event,
    notify_payment_event,
    notify_ticket_event,
)

User = get_user_model()


class NotificationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.owner = User.objects.create_user(
            username="owner", password="pass", role="CLIENT"
        )
        self.other = User.objects.create_user(username="other", password="pass")
        self.garage = Garage.objects.create(
            owner=self.owner, name="Garage test", phone="600", address="Akwa"
        )
        self.order = Order.objects.create(
            user=self.user, garage=self.garage, total=1000
        )

    def test_order_garage_payment_and_support_events_create_notifications(self):
        notify_order_event(self.order, "confirmed", actor=self.owner)
        notify_garage_event(self.garage, "approved")
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=1000,
            provider=Payment.Provider.CASH,
            status=Payment.Status.INITIATED,
        )
        notify_payment_event(payment)
        ticket = Ticket.objects.create(
            user=self.user,
            order=self.order,
            garage=self.garage,
            subject="Problème",
            description="Détail",
        )
        notify_ticket_event(ticket, "created", sender=self.user)
        notify_ticket_event(ticket, "reply", sender=self.owner)

        self.assertTrue(
            Notification.objects.filter(
                user=self.user, category=Notification.Category.ORDER
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner, title="Garage approuvé"
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, category=Notification.Category.PAYMENT
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, title="Réponse à votre problème"
            ).exists()
        )

    def test_payment_success_signal_notifies_once_per_transition(self):
        payment = Payment.objects.create(
            order=self.order,
            user=self.user,
            amount=1000,
            provider=Payment.Provider.CASH,
        )
        payment.status = Payment.Status.SUCCESS
        payment.save()
        payment.save()
        self.assertEqual(
            Notification.objects.filter(
                user=self.user, category=Notification.Category.PAYMENT
            ).count(),
            1,
        )

    def test_read_count_and_permission(self):
        notification = Notification.objects.create(
            user=self.user,
            category=Notification.Category.SYSTEM,
            title="Message",
            message="Bonjour",
        )
        self.client.login(username="buyer", password="pass")
        response = self.client.get(reverse("notifications:notification_count"))
        self.assertEqual(response.json()["unread_count"], 1)

        response = self.client.post(
            reverse("notifications:notification_mark_read", args=[notification.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["unread_count"], 0)

        notification.is_read = False
        notification.save(update_fields=["is_read"])
        self.client.login(username="other", password="pass")
        response = self.client.post(
            reverse("notifications:notification_mark_read", args=[notification.pk])
        )
        self.assertEqual(response.status_code, 404)


# Create your tests here.
