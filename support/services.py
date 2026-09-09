from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import Conversation, Message, Ticket
User = get_user_model()


def get_or_create_ticket_conversation(ticket):
    conversation, created = Conversation.objects.get_or_create(
        ticket=ticket,
        defaults={"subject": ticket.subject},
    )
    if created:
        conversation.participants.add(ticket.user)
        admins = admin_users()
        if admins.exists():
            conversation.participants.add(*admins)
        else:
            print("[WARNING] Aucun ADMIN trouve pour notifier le ticket.")
    return conversation


def get_or_create_conversation(user1, user2, subject="Conversation"):
    """Get or create a direct conversation between two users."""
    existing = Conversation.objects.filter(
        participants=user1
    ).filter(
        participants=user2
    ).filter(
        ticket__isnull=True
    ).first()

    if existing:
        return existing

    conversation = Conversation.objects.create(subject=subject)
    conversation.participants.add(user1, user2)
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
    return message


def mark_conversation_read(conversation, user):
    if not can_access_conversation(conversation, user):
        raise PermissionError("Conversation access denied")
    return conversation.messages.filter(is_read=False).exclude(sender=user).update(is_read=True)


def admin_users():
    return User.objects.filter(role__in=["ADMIN", "SUPERUSER"], is_active=True)
