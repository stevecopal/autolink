"""Centralised business-event notifications."""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import Notification

User = get_user_model()


def notify_user(user, category, title, message, *, link="", metadata=None):
    if not user or not getattr(user, "is_authenticated", True):
        return None
    return Notification.objects.create(
        user=user,
        category=category,
        title=title,
        message=message,
        link=link,
        metadata=metadata or {},
    )


def notify_users(users, category, title, message, *, link="", metadata=None):
    notifications = []
    seen = set()
    for user in users:
        if user.pk in seen:
            continue
        seen.add(user.pk)
        notification = notify_user(
            user, category, title, message, link=link, metadata=metadata
        )
        if notification:
            notifications.append(notification)
    return notifications


def _order_link(order):
    return f"/commandes/{order.order_number}/"


def notify_new_order(order):
    metadata = {"event": "order.created", "order_id": str(order.pk)}
    notifications = notify_users(
        [order.user],
        Notification.Category.ORDER,
        _("Commande confirmée"),
        _("Votre commande %(number)s a été créée.") % {"number": order.order_number},
        link=_order_link(order),
        metadata=metadata,
    )
    if order.garage and order.garage.owner_id != order.user_id:
        notifications += notify_users(
            [order.garage.owner],
            Notification.Category.ORDER,
            _("Nouvelle commande reçue"),
            _("La commande %(number)s vient d'être créée.")
            % {"number": order.order_number},
            link=_order_link(order),
            metadata=metadata,
        )
    return notifications


def notify_order_event(order, event, actor=None):
    """Notify the party affected by a state transition, once per event call."""
    owner = order.garage.owner if order.garage else None
    buyer = order.user
    recipients = []
    if event in {"confirmed", "delivered"}:
        recipients = [buyer]
    elif event in {"picked_up", "completed"}:
        recipients = [owner]
    elif event == "cancelled":
        recipients = [owner if actor and owner and actor.pk == buyer.pk else buyer]
    if actor:
        recipients = [user for user in recipients if user and user.pk != actor.pk]
    labels = {
        "confirmed": (
            _("Commande confirmée"),
            _("Votre commande %(number)s a été confirmée."),
        ),
        "delivered": (
            _("Commande livrée"),
            _("Votre commande %(number)s a été livrée."),
        ),
        "picked_up": (
            _("Commande récupérée"),
            _("La commande %(number)s a été récupérée."),
        ),
        "completed": (
            _("Commande terminée"),
            _("La commande %(number)s est terminée."),
        ),
        "cancelled": (
            _("Commande annulée"),
            _("La commande %(number)s a été annulée."),
        ),
    }
    if event not in labels:
        return []
    title, message = labels[event]
    return notify_users(
        recipients,
        Notification.Category.ORDER,
        title,
        message % {"number": order.order_number},
        link=_order_link(order),
        metadata={"event": f"order.{event}", "order_id": str(order.pk)},
    )


def notify_garage_event(garage, event, reason=""):
    labels = {
        "submitted": (
            _("Garage soumis"),
            _("Votre garage a été soumis pour validation."),
        ),
        "approved": (_("Garage approuvé"), _("Votre garage a été approuvé.")),
        "rejected": (_("Garage rejeté"), _("Votre garage a été rejeté.")),
        "activated": (_("Garage activé"), _("Votre garage est maintenant actif.")),
    }
    if event not in labels:
        return None
    title, message = labels[event]
    if reason:
        message = f"{message} {reason}"
    return notify_user(
        garage.owner,
        Notification.Category.SYSTEM,
        title,
        message,
        link=f"/garages/{garage.slug}/",
        metadata={"event": f"garage.{event}", "garage_id": str(garage.pk)},
    )


def notify_payment_event(payment, event="confirmed"):
    reference = payment.order.order_number if payment.order else payment.garage.name
    link = _order_link(payment.order) if payment.order else f"/garages/{payment.garage.slug}/"
    labels = {
        "confirmed": (
            _("Paiement confirmé"),
            _("Le paiement de la commande %(number)s a été confirmé."),
        ),
        "failed": (
            _("Paiement échoué"),
            _("Le paiement de la commande %(number)s a échoué."),
        ),
    }
    if event not in labels:
        return None
    title, message = labels[event]
    return notify_user(
        payment.user,
        Notification.Category.PAYMENT,
        title,
        message % {"number": reference},
        link=link,
        metadata={"event": f"payment.{event}", "payment_id": str(payment.pk)},
    )


def _admins():
    return User.objects.filter(is_active=True).filter(
        role__in=[User.Role.ADMIN, User.Role.SUPERUSER]
    )


def notify_ticket_event(ticket, event, sender=None):
    if event == "created":
        recipients = _admins()
        title = _("Problème créé")
        message = _("Le problème %(number)s a été créé.") % {
            "number": ticket.ticket_number
        }
    elif event == "reply":
        if sender and sender.pk == ticket.user_id:
            recipients = _admins()
        else:
            recipients = [ticket.user]
        title = _("Réponse à votre problème")
        message = _(
            "Une nouvelle réponse est disponible pour le problème %(number)s."
        ) % {"number": ticket.ticket_number}
    else:
        return []
    return notify_users(
        recipients,
        Notification.Category.SUPPORT,
        title,
        message,
        link=f"/support/tickets/{ticket.ticket_number}/",
        metadata={"event": f"support.{event}", "ticket_id": str(ticket.pk)},
    )


def publish_announcement(announcement):
    if announcement.status != announcement.Status.PUBLISHED:
        return []
    return notify_users(
        User.objects.filter(is_active=True),
        Notification.Category.SYSTEM,
        announcement.title,
        announcement.message,
        link=announcement.link,
        metadata={
            "event": "announcement.published",
            "announcement_id": str(announcement.pk),
        },
    )
