import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Status(models.TextChoices):
        INITIATED = "INITIATED", _("Initié")
        PENDING = "PENDING", _("En attente")
        PROCESSING = "PROCESSING", _("En cours")
        SUCCESS = "SUCCESS", _("Réussi")
        FAILED = "FAILED", _("Échoué")
        CANCELLED = "CANCELLED", _("Annulé")
        REFUNDED = "REFUNDED", _("Remboursé")

    class Provider(models.TextChoices):
        PAYUNIT = "PAYUNIT", _("PayUnit")
        CAMPAY = "CAMPAY", _("CamPay")
        MTN_MOMO = "MTN_MOMO", _("MTN Mobile Money")
        ORANGE_MONEY = "ORANGE_MONEY", _("Orange Money")
        CARD = "CARD", _("Carte bancaire")
        CASH = "CASH", _("Espèces")

    idempotency_key = models.CharField(max_length=64, unique=True, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activation_payments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )

    amount = models.DecimalField(_("Montant"), max_digits=10, decimal_places=0)
    currency = models.CharField(default="XAF", max_length=3)
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_transaction_id = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )
    provider_reference = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED
    )
    status_message = models.TextField(blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")

    def __str__(self):
        return f"Paiement {self.idempotency_key[:8]} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            self.idempotency_key = f"pay_{uuid.uuid4().hex}"
        super().save(*args, **kwargs)


class Receipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="receipt"
    )
    reference = models.CharField(max_length=40, unique=True, editable=False)
    garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipts",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_receipts",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    currency = models.CharField(max_length=3, default="XAF")
    provider = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"REC-{self.payment_id.hex[:12].upper()}"
        super().save(*args, **kwargs)


class Refund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Status(models.TextChoices):
        PENDING = "PENDING", _("En attente")
        PROCESSING = "PROCESSING", _("En cours")
        APPROVED = "APPROVED", _("Approuvé")
        REJECTED = "REJECTED", _("Rejeté")
        COMPLETED = "COMPLETED", _("Terminé")

    payment = models.ForeignKey(
        Payment, on_delete=models.CASCADE, related_name="refunds"
    )
    order = models.ForeignKey(
        "orders.Order", on_delete=models.CASCADE, related_name="refunds"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refunds"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=0)
    reason = models.TextField(_("Raison"))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Remboursement")
        verbose_name_plural = _("Remboursements")

    def __str__(self):
        return f"Remboursement {self.pk} - {self.amount} XAF"
