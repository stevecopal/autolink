from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg, Count
from django.utils.translation import gettext_lazy as _


class ReviewService:
    """Business logic for the rating/review system."""

    @staticmethod
    def can_user_review_order(user, order):
        """Check if a user is allowed to leave a review for a given order.

        Conditions:
        - User must be authenticated
        - Order must belong to the user
        - Order must be linked to a garage
        - Order status must be COMPLETED
        """
        if not user or not user.is_authenticated:
            return False
        if not order or order.user_id != user.pk:
            return False
        if order.garage is None:
            return False
        if order.status != "COMPLETED":
            return False
        return True

    @staticmethod
    def has_user_reviewed_order(user, order):
        """Check if a user has already reviewed a specific order."""
        from .models import Review

        return Review.objects.filter(user=user, order=order).exists()

    @staticmethod
    def validate_review_data(rating, comment):
        """Validate rating and comment data."""
        errors = []
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            errors.append(
                ValidationError(_("La note doit être comprise entre 1 et 5."))
            )
        if not comment or len(comment.strip()) < 10:
            errors.append(
                ValidationError(
                    _("Le commentaire doit contenir au moins 10 caractères.")
                )
            )
        if errors:
            raise ValidationError(errors)

    @staticmethod
    @transaction.atomic
    def create_review(user, order, rating, comment, title=""):
        """Create a review after all business rule checks.

        Raises:
            PermissionDenied: if user is not allowed to review
            ValidationError: if data is invalid or duplicate
        """
        from .models import Review

        if not ReviewService.can_user_review_order(user, order):
            raise PermissionDenied(
                _(
                    "Vous ne pouvez laisser un avis que pour une commande "
                    "terminée vous appartenant, liée à un garage."
                )
            )

        if ReviewService.has_user_reviewed_order(user, order):
            raise ValidationError(
                _("Vous avez déjà laissé un avis pour cette commande.")
            )

        ReviewService.validate_review_data(rating, comment)

        review = Review.objects.create(
            user=user,
            review_type=Review.ReviewType.GARAGE,
            garage=order.garage,
            order=order,
            rating=rating,
            title=title.strip(),
            comment=comment.strip(),
            is_verified=True,
        )
        return review

    @staticmethod
    def update_garage_stats(garage):
        """Recalculate and update a garage's trust_score and total_reviews."""
        from reviews.models import Review

        stats = Review.objects.filter(garage=garage, is_hidden=False).aggregate(
            avg_rating=Avg("rating"), count=Count("id")
        )
        garage.trust_score = stats["avg_rating"] or 0
        garage.total_reviews = stats["count"]
        garage.save(update_fields=["trust_score", "total_reviews"])

    @staticmethod
    def get_public_reviews(garage):
        """Get all non-hidden reviews for a garage (public view)."""
        from .models import Review

        return (
            Review.objects.filter(garage=garage, is_hidden=False)
            .select_related("user", "order")
            .order_by("-created_at")
        )

    @staticmethod
    def get_owner_reviews(user):
        """Get all non-hidden reviews for garages owned by user (CLIENT view)."""
        from .models import Review

        return (
            Review.objects.filter(garage__owner=user, is_hidden=False)
            .select_related("user", "garage", "order")
            .order_by("-created_at")
        )

    @staticmethod
    def get_all_reviews():
        """Get all reviews for admin view."""
        from .models import Review

        return (
            Review.objects.all()
            .select_related("user", "garage", "part", "order")
            .order_by("-created_at")
        )
