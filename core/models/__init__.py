from django.db import models
from django.utils.translation import gettext_lazy as _


class City(models.Model):
    name = models.CharField(_('Nom de la ville'), max_length=150, unique=True)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Ville')
        verbose_name_plural = _('Villes')

    def __str__(self):
        return self.name


class Neighborhood(models.Model):
    city = models.ForeignKey(
        City, on_delete=models.CASCADE,
        related_name='neighborhoods', verbose_name=_('Ville')
    )
    name = models.CharField(_('Nom du quartier'), max_length=150)
    slug = models.SlugField()
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['city', 'name']
        unique_together = ['city', 'slug']
        verbose_name = _('Quartier')
        verbose_name_plural = _('Quartiers')

    def __str__(self):
        return f"{self.name} ({self.city.name})"


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
