# core/views/search.py
"""
Core public views — search, about, and contact pages.
Kept in its own module so the monolith stays small and easy to maintain.
"""
from django.shortcuts import render
from django.db.models import Q, Count
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse

from garages.models import Garage
from catalog.models import Part, Category


CACHE_KEY_HOME = "home_page_data"
CACHE_TTL = 300  # 5 minutes


def home_view(request: HttpRequest) -> HttpResponse:
    """Cached homepage view."""
    garages = Garage.objects.filter(
        is_active=True,
        verification_status="VERIFIED",
    ).select_related("owner").prefetch_related("services").only(
        "id",
        "name",
        "slug",
        "logo",
        "city",
        "neighborhood",
        "trust_score",
        "total_reviews",
        "verification_status",
        "owner_id",
    )[:6]

    parts = Part.objects.filter(
        is_active=True,
        stock_status__in=["IN_STOCK", "LOW_STOCK"],
    ).select_related("category", "brand", "garage").only(
        "id",
        "name",
        "slug",
        "photo",
        "price",
        "stock_status",
        "category_id",
        "brand_id",
        "garage_id",
    )[:8]

    categories = Category.objects.filter(
        parent=None, is_active=True
    ).annotate(part_count=Count("parts")).only(
        "id", "name", "slug", "icon"
    )[:12]

    cities = list(
        Garage.objects.filter(
            is_active=True
        ).order_by("city").values_list("city", flat=True).distinct()[:10]
    )

    context = {
        "garages": garages,
        "parts": parts,
        "categories": categories,
        "cities": cities,
    }
    cache.set(CACHE_KEY_HOME, context, CACHE_TTL)
    return render(request, "public/base.html", context)
