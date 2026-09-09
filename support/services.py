from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from notifications.models import Notification
from notifications.services import notify_user

from .models import Conversation, Message, Ticket

User = get_user_model()


def admin_users():
    from django.db.models import Q

    return User.objects.filter(
        Q(is_superuser=True) | Q(role__in=[User.Role.ADMIN, User.Role.SUPERUSER]),
        is_active=True,
    )


def get_or_create_ticket_conversation(ticket):
    conversation, created = Conversation.objects.get_or_create(
        ticket=ticket,
        defaults={"subject": ticket.subject},
    )
    if created:
        conversation.participants.add(ticket.user, *admin_users())
    return conversation


def can_access_conversation(conversation, user):
    return bool(
        user and user.is_authenticated and (
            user.is_admin_or_above or conversation.participants.filter(pk=user.pk).exists()
        )
    )


def send_message(conversation, sender, body, attachment=None):
    if not can_access_conversation(conversation, sender):
        raise PermissionError("Conversation access denied")
    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            body=body,
            attachment=attachment,
        )
        conversation.save(update_fields=["updated_at"])
    recipients = conversation.participants.exclude(pk=sender.pk)
    for recipient in recipients:
        notify_user(
            recipient,
            Notification.Category.SUPPORT,
            _("Nouveau message"),
            _("Vous avez reçu un nouveau message dans « %(subject)s ».")
            % {"subject": conversation.subject},
            link=f"/support/messages/{conversation.pk}/",
            metadata={
                "event": "message.created",
                "conversation_id": str(conversation.pk),
                "message_id": str(message.pk),
            },
        )
    return message


def mark_conversation_read(conversation, user):
    if not can_access_conversation(conversation, user):
        raise PermissionError("Conversation access denied")
    return conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)
