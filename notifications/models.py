import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Category(models.TextChoices):
        ORDER = 'ORDER', _('Commande')
        PAYMENT = 'PAYMENT', _('Paiement')
        APPOINTMENT = 'APPOINTMENT', _('Rendez-vous')
        QUOTE = 'QUOTE', _('Devis')
        STOCK = 'STOCK', _('Stock')
        PRICE = 'PRICE', _('Prix')
        REVIEW = 'REVIEW', _('Avis')
        SYSTEM = 'SYSTEM', _('Système')
        SUPPORT = 'SUPPORT', _('Support')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(_('Titre'), max_length=200)
    message = models.TextField(_('Message'))
    link = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self):
        return f"{self.title} - {self.user.username}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
