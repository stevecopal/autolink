import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class ReviewType(models.TextChoices):
        GARAGE = "GARAGE", _("Garage")
        PART = "PART", _("Pièce")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    review_type = models.CharField(max_length=10, choices=ReviewType.choices)
    garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )
    part = models.ForeignKey(
        "catalog.Part",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reviews",
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review",
    )

    rating = models.PositiveIntegerField(
        _("Note"), validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(_("Titre"), max_length=200, blank=True)
    comment = models.TextField(_("Commentaire"))
    photo = models.ImageField(upload_to="reviews/", blank=True, null=True)

    is_verified = models.BooleanField(_("Avis vérifié"), default=False)
    is_moderated = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)

    professional_reply = models.TextField(_("Réponse du professionnel"), blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Avis")
        verbose_name_plural = _("Avis")

    def __str__(self):
        target = self.garage or self.part
        return f"Avis de {self.user.username} sur {target}"

    def save(self, *args, **kwargs):
        previous_garage = None
        if self.pk:
            previous_garage = (
                Review.objects.filter(pk=self.pk)
                .values_list("garage_id", flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if self.garage or previous_garage:
            from .services import ReviewService

            if previous_garage and previous_garage != self.garage_id:
                from garages.models import Garage

                ReviewService.update_garage_stats(
                    Garage.objects.get(pk=previous_garage)
                )
            if self.garage:
                ReviewService.update_garage_stats(self.garage)


class Favorite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class ObjectType(models.TextChoices):
        GARAGE = "GARAGE", _("Garage")
        PART = "PART", _("Pièce")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    object_type = models.CharField(max_length=10, choices=ObjectType.choices)
    garage = models.ForeignKey(
        "garages.Garage",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favorited_by",
    )
    part = models.ForeignKey(
        "catalog.Part",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ["user", "object_type", "garage"],
            ["user", "object_type", "part"],
        ]
        verbose_name = _("Favori")
        verbose_name_plural = _("Favoris")

    def __str__(self):
        target = self.garage or self.part
        return f"{self.user.username} - {target}"
