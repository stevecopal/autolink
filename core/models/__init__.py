import uuid
from django.db import models
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
            self.slug = self._generate_slug()
        super().save(*args, **kwargs)

    def _generate_slug(self):
        from django.utils.text import slugify
        base = slugify(self.name or '').strip('-') or 'ville'
        slug = base
        counter = 1
        while City.objects.filter(slug=slug).exists():
            suffix = f'-{counter}'
            if len(base) + len(suffix) > 50:
                base = base[:50 - len(suffix)]
            slug = base + suffix
            counter += 1
        return slug


class Neighborhood(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_slug()
        super().save(*args, **kwargs)

    def _generate_slug(self):
        from django.utils.text import slugify
        base = slugify(self.name or '').strip('-') or 'quartier'
        slug = base
        counter = 1
        qs = Neighborhood.objects.filter(city=self.city, slug__startswith=base)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            suffix = f'-{counter}'
            if len(base) + len(suffix) > 50:
                base = base[:50 - len(suffix)]
            slug = base + suffix
            counter += 1
        return slug


class ContactMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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
