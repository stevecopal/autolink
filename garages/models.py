from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Garage(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')
        SUSPENDED = 'SUSPENDED', _('Suspended')

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        BUSY = 'BUSY', _('Busy')
        CLOSED = 'CLOSED', _('Closed')
        TEMPORARY_CLOSED = 'TEMPORARY_CLOSED', _('Temporarily Closed')

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='garages')
    name = models.CharField(_('Name'), max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(_('Description'), blank=True)
    phone = models.CharField(_('Phone'), max_length=20)
    whatsapp = models.CharField(_('WhatsApp'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)

    address = models.TextField(_('Address'))
    city = models.CharField(_('City'), max_length=100)
    neighborhood = models.CharField(_('Neighborhood'), max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    logo = models.ImageField(upload_to='garages/logos/', blank=True, null=True)
    cover_photo = models.ImageField(upload_to='garages/covers/', blank=True, null=True)

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE
    )
    availability_message = models.CharField(_('Availability message'), max_length=200, blank=True)

    opening_time = models.TimeField(_('Opening time'), null=True, blank=True)
    closing_time = models.TimeField(_('Closing time'), null=True, blank=True)
    open_weekends = models.BooleanField(_('Open weekends'), default=False)

    trust_score = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_clients = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-trust_score', '-created_at']
        verbose_name = _('Garage')
        verbose_name_plural = _('Garages')

    def __str__(self):
        return self.name

    @property
    def is_open_now(self):
        from django.utils import timezone
        now = timezone.localtime().time()
        if self.opening_time and self.closing_time:
            if self.opening_time <= self.closing_time:
                return self.opening_time <= now <= self.closing_time
            else:
                return now >= self.opening_time or now <= self.closing_time
        return False

    @property
    def average_rating(self):
        if self.total_reviews > 0:
            return round(self.trust_score, 1)
        return 0


class GarageService(models.Model):
    class Category(models.TextChoices):
        DIAGNOSTIC = 'DIAGNOSTIC', _('Diagnostic')
        MAINTENANCE = 'MAINTENANCE', _('Entretien')
        BRAKES = 'BRAKES', _('Freinage')
        ENGINE = 'ENGINE', _('Moteur')
        TRANSMISSION = 'TRANSMISSION', _('Transmission')
        ELECTRICAL = 'ELECTRICAL', _('Électrique')
        SUSPENSION = 'SUSPENSION', _('Suspension')
        EXHAUST = 'EXHAUST', _('Échappement')
        AIR_CONDITIONING = 'AIR_CONDITIONING', _('Climatisation')
        BODYWORK = 'BODYWORK', _('Carrosserie')
        TIRE = 'TIRE', _('Pneumatique')
        OIL_CHANGE = 'OIL_CHANGE', _('Vidange')
        OTHER = 'OTHER', _('Autre')

    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(_('Service'), max_length=200)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    description = models.TextField(blank=True)
    price_min = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, help_text=_('Prix minimum estimé en FCFA'))
    price_max = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, help_text=_('Prix maximum estimé en FCFA'))
    duration_minutes = models.PositiveIntegerField(_('Durée estimée (minutes)'), null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = _('Service')
        verbose_name_plural = _('Services')

    def __str__(self):
        return f"{self.garage.name} - {self.name}"


class GaragePhoto(models.Model):
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='garages/photos/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-created_at']

    def __str__(self):
        return f"Photo de {self.garage.name}"


class GarageVerification(models.Model):
    class DocumentType(models.TextChoices):
        IDENTITY = 'IDENTITY', _('Pièce d\'identité')
        BUSINESS_LICENSE = 'BUSINESS_LICENSE', _('Registre de commerce')
        TAX_CERTIFICATE = 'TAX_CERTIFICATE', _('Attestation fiscale')
        PROFESSIONAL_CARD = 'PROFESSIONAL_CARD', _('Carte professionnelle')
        OTHER = 'OTHER', _('Autre')

    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='verifications')
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    document = models.FileField(upload_to='garages/verifications/')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Vérification garage')
        verbose_name_plural = _('Vérifications garages')

    def __str__(self):
        return f"{self.garage.name} - {self.get_document_type_display()}"


class GarageBrand(models.Model):
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='brands')
    brand = models.ForeignKey('vehicles.Brand', on_delete=models.CASCADE)

    class Meta:
        unique_together = ['garage', 'brand']
        verbose_name = _('Marque prise en charge')
        verbose_name_plural = _('Marques prises en charge')
