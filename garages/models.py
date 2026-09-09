import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Garage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        APPROVED = "APPROVED", _("Approuvé")
        REJECTED = "REJECTED", _("Rejeté")
        SUSPENDED = "SUSPENDED", _("Suspendu")

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Disponible")
        UNAVAILABLE = "UNAVAILABLE", _("Indisponible")

    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        APPROVED = "APPROVED", _("Approuvé")
        REJECTED = "REJECTED", _("Rejeté")

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", _("Non payé")
        PENDING = "PENDING", _("En attente de paiement")
        PAID = "PAID", _("Payé")
        FAILED = "FAILED", _("Échec")

    class ActivationStatus(models.TextChoices):
        INACTIVE = "INACTIVE", _("Inactif")
        ACTIVE = "ACTIVE", _("Actif")
        SUSPENDED = "SUSPENDED", _("Suspendu")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garages"
    )
    name = models.CharField(_("Nom du garage"), max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(_("Description"), blank=True)
    phone = models.CharField(_("Téléphone"), max_length=20)
    whatsapp = models.CharField(_("WhatsApp"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    address = models.TextField(_("Adresse"))
    city = models.ForeignKey(
        "core.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="garages",
        verbose_name=_("Ville"),
    )
    neighborhood = models.ForeignKey(
        "core.Neighborhood",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="garages",
        verbose_name=_("Quartier"),
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Latitude"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("Longitude"),
    )
    gps_accuracy = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Précision GPS (mètres)"),
        help_text=_("Précision de la position en mètres lors de l'enregistrement"),
    )
    location_captured_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Date de capture de la position")
    )

    photo = models.ImageField(
        upload_to="garages/main/",
        verbose_name=_("Photo du garage"),
        help_text=_("Photo réelle du garage (obligatoire)"),
        blank=True,
        null=True,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = models.TextField(
        _("Raison du rejet"),
        blank=True,
        help_text=_("Raison du rejet du garage par l'administrateur"),
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE,
    )
    availability_message = models.CharField(
        _("Message de disponibilité"), max_length=200, blank=True
    )

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        verbose_name=_("Statut de validation"),
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        verbose_name=_("Statut de paiement"),
    )
    activation_status = models.CharField(
        max_length=20,
        choices=ActivationStatus.choices,
        default=ActivationStatus.INACTIVE,
        verbose_name=_("Statut d'activation"),
    )

    opening_time = models.TimeField(_("Heure d'ouverture"), null=True, blank=True)
    closing_time = models.TimeField(_("Heure de fermeture"), null=True, blank=True)
    open_weekends = models.BooleanField(_("Ouvert le week-end"), default=False)

    trust_score = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_clients = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trust_score", "-created_at"]
        verbose_name = _("Garage")
        verbose_name_plural = _("Garages")
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["approval_status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["activation_status"]),
            models.Index(fields=["availability_status"]),
            models.Index(fields=["city"]),
            models.Index(fields=["neighborhood"]),
            models.Index(fields=["owner"]),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def public_filter(cls):
        return models.Q(
            approval_status=cls.ApprovalStatus.APPROVED,
            payment_status=cls.PaymentStatus.PAID,
            activation_status=cls.ActivationStatus.ACTIVE,
            is_active=True,
        )

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

    @property
    def is_available_for_search(self):
        """Visible dans la recherche uniquement si approuvé et disponible."""
        """Visible dans la recherche uniquement si publiquement disponible."""
        return (
            self.is_publicly_available
            and self.availability_status == self.AvailabilityStatus.AVAILABLE
        )

    def save(self, *args, **kwargs):
        from django.utils import timezone as tz

        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name or "").strip("-") or "garage"
            slug = base
            counter = 1
            while Garage.objects.filter(slug=slug).exists():
                suffix = f"-{counter}"
                if len(base) + len(suffix) > 60:
                    base = base[: 60 - len(suffix)]
                slug = base + suffix
                counter += 1
            self.slug = slug
        if not self.pk:
            self.activation_status = self.ActivationStatus.INACTIVE
            self.approval_status = self.ApprovalStatus.PENDING
            self.payment_status = self.PaymentStatus.UNPAID
            self.verification_status = self.VerificationStatus.PENDING
            self.availability_status = self.AvailabilityStatus.UNAVAILABLE
        if self.latitude and self.longitude and not self.location_captured_at:
            self.location_captured_at = tz.now()
        super().save(*args, **kwargs)

    @property
    def is_publicly_available(self):
        """Visible publiquement uniquement si approuvé, payé et actif."""
        return (
            self.approval_status == self.ApprovalStatus.APPROVED
            and self.payment_status == self.PaymentStatus.PAID
            and self.activation_status == self.ActivationStatus.ACTIVE
            and self.is_active
        )

    @property
    def is_in_pending_review(self):
        return self.approval_status == self.ApprovalStatus.PENDING


class GarageService(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Category(models.TextChoices):
        DIAGNOSTIC = "DIAGNOSTIC", _("Diagnostic")
        MAINTENANCE = "MAINTENANCE", _("Entretien")
        BRAKES = "BRAKES", _("Freinage")
        ENGINE = "ENGINE", _("Moteur")
        TRANSMISSION = "TRANSMISSION", _("Transmission")
        ELECTRICAL = "ELECTRICAL", _("Électrique")
        SUSPENSION = "SUSPENSION", _("Suspension")
        EXHAUST = "EXHAUST", _("Échappement")
        AIR_CONDITIONING = "AIR_CONDITIONING", _("Climatisation")
        BODYWORK = "BODYWORK", _("Carrosserie")
        TIRE = "TIRE", _("Pneumatique")
        OIL_CHANGE = "OIL_CHANGE", _("Vidange")
        OTHER = "OTHER", _("Autre")

    garage = models.ForeignKey(
        Garage, on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(_("Service"), max_length=200)
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.OTHER
    )
    description = models.TextField(blank=True)
    price_min = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text=_("Prix minimum estimé en FCFA"),
    )
    price_max = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text=_("Prix maximum estimé en FCFA"),
    )
    duration_minutes = models.PositiveIntegerField(
        _("Durée estimée (minutes)"), null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def __str__(self):
        return f"{self.garage.name} - {self.name}"


class GaragePhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="garages/photos/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"Photo de {self.garage.name}"


class GarageVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class DocumentType(models.TextChoices):
        IDENTITY = "IDENTITY", _("Pièce d'identité")
        BUSINESS_LICENSE = "BUSINESS_LICENSE", _("Registre de commerce")
        TAX_CERTIFICATE = "TAX_CERTIFICATE", _("Attestation fiscale")
        PROFESSIONAL_CARD = "PROFESSIONAL_CARD", _("Carte professionnelle")
        GARAGE_PROOF = "GARAGE_PROOF", _("Justificatif du garage")
        OTHER = "OTHER", _("Autre")

    garage = models.ForeignKey(
        Garage, on_delete=models.CASCADE, related_name="verifications"
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    document = models.FileField(
        upload_to="garages/verifications/",
        verbose_name=_("Document"),
        help_text=_("PDF ou Word, max 5 Mo"),
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Vérification garage")
        verbose_name_plural = _("Vérifications garages")

    def __str__(self):
        return f"{self.garage.name} - {self.get_document_type_display()}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.document:
            ext = self.document.name.split(".")[-1].lower()
            if ext not in ("pdf", "doc", "docx"):
                raise ValidationError(
                    _("Seuls les fichiers PDF et Word sont acceptés.")
                )
            if self.document.size > 5 * 1024 * 1024:
                raise ValidationError(_("La taille maximale est de 5 Mo."))


class GarageBrand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name="brands")
    brand = models.ForeignKey("vehicles.Brand", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["garage", "brand"]
        verbose_name = _("Marque prise en charge")
        verbose_name_plural = _("Marques prises en charge")
