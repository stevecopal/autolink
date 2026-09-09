import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


def validate_evidence_file(value):
    max_size = 5 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError(
            _("Le fichier ne doit pas dépasser %(size)s Mo.") % {"size": 5}
        )
    import mimetypes

    mime_type, _ = mimetypes.guess_type(value.name)
    allowed_mimes = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    if mime_type and mime_type not in allowed_mimes:
        raise ValidationError(
            _(
                "Type de fichier non autorisé. Formats acceptés : images (JPG, PNG, GIF, WebP), PDF, Word."
            )
        )
    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".pdf",
        ".doc",
        ".docx",
    ]
    import os

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            _("Extension non autorisée. Formats acceptés : %(formats)s.")
            % {"formats": ", ".join(allowed_extensions)}
        )


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Status(models.TextChoices):
        OPEN = "OPEN", _("Ouvert")
        IN_PROGRESS = "IN_PROGRESS", _("En cours")
        RESOLVED = "RESOLVED", _("Résolu")
        CLOSED = "CLOSED", _("Fermé")

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="tickets"
    )
    garage = models.ForeignKey(
        "garages.Garage", on_delete=models.CASCADE, related_name="tickets"
    )
    part = models.ForeignKey(
        "catalog.Part",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.OPEN
    )
    subject = models.CharField(_("Sujet"), max_length=300)
    description = models.TextField(_("Description"))
    evidence = models.FileField(
        _("Preuve"),
        upload_to="tickets/evidence/",
        blank=True,
        null=True,
        validators=[validate_evidence_file],
        help_text=_("Image ou fichier max 5 Mo (JPG, PNG, GIF, WebP, PDF, Word)"),
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"TK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def evidence_filename(self):
        if self.evidence:
            import os

            return os.path.basename(self.evidence.name)
        return None


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="conversations"
    )
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation",
    )
    subject = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.subject

    def is_participant(self, user):
        return bool(
            user
            and user.is_authenticated
            and self.participants.filter(pk=user.pk).exists()
        )

    def unread_count_for(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    attachment = models.FileField(
        upload_to="conversations/attachments/", blank=True, null=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message de {self.sender}"


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(
        upload_to="tickets/attachments/", blank=True, null=True
    )
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Message de ticket")
        verbose_name_plural = _("Messages de tickets")

    def __str__(self):
        return f"Message de {self.sender.username} dans {self.ticket.ticket_number}"


class AssistanceRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class IssueType(models.TextChoices):
        BATTERY = "BATTERY", _("Batterie")
        TIRE = "TIRE", _("Pneu crevé")
        ENGINE = "ENGINE", _("Moteur")
        FUEL = "FUEL", _("Carburant")
        ACCIDENT = "ACCIDENT", _("Accident")
        OTHER = "OTHER", _("Autre")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        MATCHED = "MATCHED", _("Professionnel trouvé")
        IN_PROGRESS = "IN_PROGRESS", _("En cours")
        COMPLETED = "COMPLETED", _("Terminé")
        CANCELLED = "CANCELLED", _("Annulé")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistance_requests",
    )
    issue_type = models.CharField(max_length=20, choices=IssueType.choices)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    assigned_garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assistance_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Demande d'assistance")
        verbose_name_plural = _("Demandes d'assistance")

    def __str__(self):
        return f"Assistance {self.get_issue_type_display()} - {self.user.username}"
