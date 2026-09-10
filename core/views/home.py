# core/views/home.py
"""
Core homepage view — cached for performance, split into its own module.
"""

from django.core.cache import cache
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from catalog.models import Category, Part
from core.models import City
from garages.models import Garage

CACHE_KEY_HOME = "home_page_data"
CACHE_TTL = 300  # 5 minutes


def home_view(request: HttpRequest) -> HttpResponse:
    """Return the cached homepage context and render the public home template."""
    cached = cache.get(CACHE_KEY_HOME)
    if cached is not None:
        return render(request, "public/pages/home/index.html", cached)

    garages = (
        Garage.objects.filter(
            approval_status=Garage.ApprovalStatus.APPROVED,
            payment_status=Garage.PaymentStatus.PAID,
            activation_status=Garage.ActivationStatus.ACTIVE,
        )
        .select_related("owner", "city", "neighborhood")
        .prefetch_related("services")
        .only(
            "id",
            "name",
            "slug",
            "photo",
            "city_id",
            "neighborhood_id",
            "approval_status",
            "payment_status",
            "activation_status",
            "owner_id",
        )[:6]
    )

    parts = (
        Part.objects.filter(
            is_active=True,
            stock_status__in=["IN_STOCK", "LOW_STOCK"],
        )
        .select_related("category", "garage")
        .only(
            "id",
            "name",
            "slug",
            "photo",
            "price",
            "stock_status",
            "category_id",
            "garage_id",
        )[:8]
    )

    categories = (
        Category.objects.filter(parent=None, is_active=True)
        .annotate(part_count=Count("parts"))
        .only("id", "name", "slug", "icon")[:12]
    )

    cities = (
        City.objects.filter(
            is_active=True,
            garages__is_active=True,
            garages__approval_status=Garage.ApprovalStatus.APPROVED,
            garages__payment_status=Garage.PaymentStatus.PAID,
            garages__activation_status=Garage.ActivationStatus.ACTIVE,
        )
        .distinct()
        .order_by("name")[:10]
    )

    context = {
        "garages": garages,
        "parts": parts,
        "categories": categories,
        "cities": cities,
    }
    cache.set(CACHE_KEY_HOME, context, CACHE_TTL)
    return render(request, "public/pages/home/index.html", context)
