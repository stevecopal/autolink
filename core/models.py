import uuid
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class City(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'ville'
            slug = base
            i = 1
            while City.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Neighborhood(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='neighborhoods', verbose_name=_('Ville'))
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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'quartier'
            slug = base
            i = 1
            while Neighborhood.objects.filter(city=self.city, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('En attente')
        READ = 'READ', _('Lu')
        REPLIED = 'REPLIED', _('Répondu')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        return f"{self.name} - {self.subject}"
