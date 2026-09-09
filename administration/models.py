import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Announcement(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Brouillon')
        PUBLISHED = 'PUBLISHED', _('Publiée')
        ARCHIVED = 'ARCHIVED', _('Archivée')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('Titre'), max_length=200)
    message = models.TextField(_('Message'))
    link = models.URLField(_('Lien'), blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='announcements_created',
        verbose_name=_('Créé par')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Annonce')
        verbose_name_plural = _('Annonces')

    def __str__(self):
        return self.title
