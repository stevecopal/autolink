from django.db.models import Avg, Count
from django.utils.translation import gettext_lazy as _


class ReviewService:
    @staticmethod
    def update_garage_stats(garage):
        from reviews.models import Review
        stats = Review.objects.filter(garage=garage, is_hidden=False).aggregate(
            avg_rating=Avg("rating"), count=Count("id")
        )
        garage.trust_score = stats["avg_rating"] or 0
        garage.total_reviews = stats["count"]
        garage.save(update_fields=["trust_score", "total_reviews"])

    @staticmethod
    def get_public_reviews(garage):
        from .models import Review
        return (
            Review.objects.filter(garage=garage, is_hidden=False)
            .select_related("user")
            .order_by("-created_at")
        )

    @staticmethod
    def get_owner_reviews(user):
        from .models import Review
        return (
            Review.objects.filter(garage__owner=user, is_hidden=False)
            .select_related("user", "garage")
            .order_by("-created_at")
        )

    @staticmethod
    def get_all_reviews():
        from .models import Review
        return (
            Review.objects.all()
            .select_related("user", "garage", "part")
            .order_by("-created_at")
        )
