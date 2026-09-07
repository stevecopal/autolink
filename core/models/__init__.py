from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        READ = 'READ', _('Lu')
        REPLIED = 'REPLIED', _('Répondu')

    name = models.CharField(_('Nom'), max_length=150)
    email = models.EmailField(_('Email'))
    phone = models.CharField(_('Téléphone'), max_length=30, blank=True)
    subject = models.CharField(_('Sujet'), max_length=200, blank=True)
    message = models.TextField(_('Message'))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Message de contact')
        verbose_name_plural = _('Messages de contact')

    def __str__(self):
        return f"{self.name} - {self.subject or self.message[:50]}"
