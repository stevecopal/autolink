import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "INITIATED", _("Initié")
        PENDING = "PENDING", _("En attente")
        PROCESSING = "PROCESSING", _("En cours")
        SUCCESS = "SUCCESS", _("Réussi")
        FAILED = "FAILED", _("Échoué")
        CANCELLED = "CANCELLED", _("Annulé")

    class Provider(models.TextChoices):
        CAMPAY = "CAMPAY", _("Campay")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    garage = models.ForeignKey(
        "garages.Garage", on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(
        _("Montant"), max_digits=10, decimal_places=2
    )  # Ex: 1000.00 XAF
    currency = models.CharField(_("Devise"), max_length=3, default="XAF")
    provider = models.CharField(
        _("Fournisseur"), max_length=20, choices=Provider.choices
    )
    idempotency_key = models.CharField(
        _("Clé d'idempotence"), max_length=64, unique=True
    )
    provider_transaction_id = models.CharField(
        _("ID Transaction"), max_length=100, blank=True, default=""
    )
    provider_reference = models.CharField(_("Référence"), max_length=100, blank=True)
    phone_number = models.CharField(_("Téléphone"), max_length=20, blank=True)
    status = models.CharField(
        _("Statut"), max_length=20, choices=Status.choices, default=Status.INITIATED
    )
    status_message = models.TextField(_("Message"), blank=True)
    metadata = models.JSONField(_("Métadonnées"), default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            self.idempotency_key = f"pay_{uuid.uuid4().hex}"
        super().save(*args, **kwargs)



class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name="receipt",
        verbose_name=_("Paiement"),
    )
    reference = models.CharField(
        _("Référence"), max_length=40, unique=True, editable=False
    )
    garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipts",
        verbose_name=_("Garage"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_receipts",
        verbose_name=_("Propriétaire"),
    )
    amount = models.DecimalField(
        _("Montant"),
        max_digits=10,
        decimal_places=2,  # CORRECTION : 2 décimales
        default=0,
    )
    currency = models.CharField(_("Devise"), max_length=3, default="XAF")
    provider = models.CharField(_("Fournisseur"), max_length=20, blank=True)
    status = models.CharField(_("Statut"), max_length=20, blank=True)
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mis à jour le"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Reçu")
        verbose_name_plural = _("Reçus")

    def __str__(self):
        return f"Reçu {self.reference}"

    def save(self, *args, **kwargs):
        if not self.reference:
            # Générer une référence unique (format: REC- + 12 premiers caractères de l'ID)
            self.reference = f"REC-{self.payment_id.hex[:12].upper()}"
        if not self.amount:
            self.amount = self.payment.amount if self.payment else 0
        if not self.currency:
            self.currency = self.payment.currency if self.payment else "XAF"
        if not self.provider:
            self.provider = self.payment.provider if self.payment else ""
        if not self.status:
            self.status = self.payment.status if self.payment else ""
        if not self.garage:
            self.garage = self.payment.garage if self.payment else None
        if not self.owner:
            self.owner = self.payment.user if self.payment else None
        super().save(*args, **kwargs)