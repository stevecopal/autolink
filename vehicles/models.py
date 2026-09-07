from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Brand(models.Model):
    name = models.CharField(_('Marque'), max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Marque')
        verbose_name_plural = _('Marques')

    def __str__(self):
        return self.name


class ModelVehicle(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(_('Modèle'), max_length=100)
    slug = models.SlugField()
    year_start = models.PositiveIntegerField(_('Année début'), null=True, blank=True)
    year_end = models.PositiveIntegerField(_('Année fin'), null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['brand', 'slug']
        ordering = ['brand', 'name']
        verbose_name = _('Modèle')
        verbose_name_plural = _('Modèles')

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class Vehicle(models.Model):
    class FuelType(models.TextChoices):
        ESSENCE = 'ESSENCE', _('Essence')
        DIESEL = 'DIESEL', _('Diesel')
        HYBRID = 'HYBRID', _('Hybride')
        ELECTRIC = 'ELECTRIC', _('Électrique')
        GPL = 'GPL', _('GPL')

    class TransmissionType(models.TextChoices):
        MANUAL = 'MANUAL', _('Manuelle')
        AUTOMATIC = 'AUTOMATIC', _('Automatique')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    model = models.ForeignKey(ModelVehicle, on_delete=models.SET_NULL, null=True, blank=True)
    nickname = models.CharField(_('Surnom'), max_length=100, blank=True, help_text=_('Ex: Ma Corolla'))
    year = models.PositiveIntegerField(_('Année'), null=True, blank=True)
    engine = models.CharField(_('Moteur'), max_length=50, blank=True, help_text=_('Ex: 1.8'))
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, blank=True)
    transmission = models.CharField(max_length=20, choices=TransmissionType.choices, blank=True)
    license_plate = models.CharField(_('Immatriculation'), max_length=20, blank=True)
    vin = models.CharField(_('VIN'), max_length=17, blank=True)
    mileage = models.PositiveIntegerField(_('Kilométrage'), null=True, blank=True)
    is_primary = models.BooleanField(_('Véhicule principal'), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']
        verbose_name = _('Véhicule')
        verbose_name_plural = _('Véhicules')

    def __str__(self):
        name = self.nickname or self.display_name
        return name

    @property
    def display_name(self):
        parts = []
        if self.brand:
            parts.append(self.brand.name)
        if self.model:
            parts.append(self.model.name)
        if self.year:
            parts.append(str(self.year))
        return ' '.join(parts) if parts else 'Véhicule inconnu'

    def save(self, *args, **kwargs):
        if self.is_primary:
            Vehicle.objects.filter(user=self.user, is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
