import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Ouvert')
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        WAITING_CLIENT = 'WAITING_CLIENT', _('En attente du client')
        WAITING_PROFESSIONAL = 'WAITING_PROFESSIONAL', _('En attente du professionnel')
        RESOLVED = 'RESOLVED', _('Résolu')
        CLOSED = 'CLOSED', _('Fermé')

    class Category(models.TextChoices):
        PART = 'PART', _('Problème avec une pièce')
        GARAGE = 'GARAGE', _('Problème avec un garage')
        ORDER = 'ORDER', _('Problème avec une commande')
        SERVICE = 'SERVICE', _('Problème avec une prestation')
        PLATFORM = 'PLATFORM', _('Problème avec la plateforme')
        OTHER = 'OTHER', _('Autre')

    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    part = models.ForeignKey('catalog.Part', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    garage = models.ForeignKey('garages.Garage', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')

    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    subject = models.CharField(_('Sujet'), max_length=300)
    description = models.TextField(_('Description'))

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = f"TK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class TicketMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to='tickets/attachments/', blank=True, null=True)
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = _('Message de ticket')
        verbose_name_plural = _('Messages de tickets')

    def __str__(self):
        return f"Message de {self.sender.username} dans {self.ticket.ticket_number}"


class AssistanceRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class IssueType(models.TextChoices):
        BATTERY = 'BATTERY', _('Batterie')
        TIRE = 'TIRE', _('Pneu crevé')
        ENGINE = 'ENGINE', _('Moteur')
        FUEL = 'FUEL', _('Carburant')
        ACCIDENT = 'ACCIDENT', _('Accident')
        OTHER = 'OTHER', _('Autre')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        MATCHED = 'MATCHED', _('Professionnel trouvé')
        IN_PROGRESS = 'IN_PROGRESS', _('En cours')
        COMPLETED = 'COMPLETED', _('Terminé')
        CANCELLED = 'CANCELLED', _('Annulé')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assistance_requests')
    issue_type = models.CharField(max_length=20, choices=IssueType.choices)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_garage = models.ForeignKey(
        'garages.Garage', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assistance_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Demande d\'assistance')
        verbose_name_plural = _('Demandes d\'assistance')

    def __str__(self):
        return f"Assistance {self.get_issue_type_display()} - {self.user.username}"
