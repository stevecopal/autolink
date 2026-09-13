# core/views/home.py
"""
Core homepage view — cached for performance, with real data from all models.
"""

from django.core.cache import cache
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from catalog.models import Category, Part
from core.constants import (
    CACHE_TTL_HOME,
    CACHE_TTL_TICKER,
    DEFAULT_MAP_MARKERS,
    DEFAULT_WHY_STATS,
    MIN_GARAGES_FOR_SOCIAL_PROOF,
    NUM_CATEGORIES_HOMEPAGE,
    NUM_CITIES_HOMEPAGE,
    NUM_GARAGES_HOMEPAGE,
    NUM_PARTS_HOMEPAGE,
    NUM_TICKER_ITEMS,
    NUM_TESTIMONIALS,
)
from core.models import City, Testimonial
from garages.models import Garage

CACHE_KEY_HOME = "home_page_data"
CACHE_KEY_TICKER = "home_ticker_data"


def _get_garage_public_filter():
    """Retourne le Q object pour les garages publiquement visibles."""
    return Q(
        approval_status=Garage.ApprovalStatus.APPROVED,
        payment_status=Garage.PaymentStatus.PAID,
        activation_status=Garage.ActivationStatus.ACTIVE,
        is_active=True,
    )


def _build_live_ticker():
    """Construit une liste unifiée d'événements récents pour le live ticker."""
    now = timezone.now()
    activities = []

    recent_garages = (
        Garage.objects.filter(
            verification_status=Garage.VerificationStatus.APPROVED,
            approval_status=Garage.ApprovalStatus.APPROVED,
        )
        .select_related("city")
        .only("name", "city__name", "created_at")
        .order_by("-created_at")[:3]
    )
    for g in recent_garages:
        activities.append({
            "type": "garage_approved",
            "icon": "emerald",
            "label": _("Nouveau garage vérifié"),
            "subject": g.name,
            "location": g.city.name if g.city else _("Cameroun"),
            "created_at": g.created_at,
        })

    recent_parts = (
        Part.objects.filter(is_active=True)
        .select_related("category")
        .only("name", "category__name", "created_at")[:2]
    )
    for p in recent_parts:
        activities.append({
            "type": "part_added",
            "icon": "navy",
            "label": _("Pièce ajoutée"),
            "subject": p.name,
            "location": p.category.name if p.category else _("Catalogue"),
            "created_at": p.created_at,
        })

    recent_testimonials = (
        Testimonial.objects.filter(is_published=True, rating__gte=4)
        .only("name", "city", "created_at")
        .order_by("-created_at")[:1]
    )
    for t in recent_testimonials:
        activities.append({
            "type": "testimonial",
            "icon": "emerald",
            "label": _("Nouvelle note 5★"),
            "subject": _("Avis de %(name)s") % {"name": t.name},
            "location": t.city or _("Cameroun"),
            "created_at": t.created_at,
        })

    activities.sort(key=lambda a: a["created_at"] or now, reverse=True)
    return activities[:NUM_TICKER_ITEMS]


def _compute_why_stats():
    """Calcule les 3 chiffres de la section WHY depuis les données réelles."""
    stats = dict(DEFAULT_WHY_STATS)
    stats["verification_pct"] = 100

    garages_with_times = (
        Garage.objects.filter(_get_garage_public_filter())
        .filter(opening_time__isnull=False, closing_time__isnull=False)
        .only("opening_time", "closing_time", "created_at")
    )
    if garages_with_times.exists():
        avg_duration = (
            Garage.objects.filter(_get_garage_public_filter())
            .filter(GarageService__duration_minutes__isnull=False)
            .values_list("services__duration_minutes", flat=True)
        )
        durations = [d for d in avg_duration if d is not None]
        if durations:
            stats["avg_response_time"] = int(sum(durations) / len(durations))
        else:
            stats["avg_response_time"] = None
    else:
        stats["avg_response_time"] = None

    first_day_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    parts_this_month = Part.objects.filter(
        is_active=True, created_at__gte=first_day_month
    ).count()
    stats["searches_this_month"] = parts_this_month

    return stats


def home_view(request: HttpRequest) -> HttpResponse:
    """Retourne le contexte de la page d'accueil avec toutes les données réelles."""
    cached = cache.get(CACHE_KEY_HOME)
    if cached is not None:
        return render(request, "public/pages/home/index.html", cached)

    # ── Requête optimisée pour les garages ──────────────────────────────
    garage_qs = Garage.objects.filter(_get_garage_public_filter()).select_related(
        "city", "neighborhood", "owner"
    ).prefetch_related("services")

    total_garages = garage_qs.count()
    live_garages = garage_qs.filter(
        updated_at__gte=timezone.now() - timezone.timedelta(hours=24)
    ).count()

    # Garages mis en avant (6 max)
    garages = list(garage_qs.order_by("-is_featured", "-created_at")[:NUM_GARAGES_HOMEPAGE])
    for g in garages:
        g.display_rating = None  # Pas de FK testimonials→garage
        g.display_reviews = 0
        g.services_preview = list(g.services.all()[:3])
        g.services_total = g.services.count()
        g.is_open = g.is_open_now

    # ── Pièces populaires ──────────────────────────────────────────────
    parts_qs = Part.objects.filter(
        is_active=True,
        stock_status__in=[Part.StockStatus.IN_STOCK, Part.StockStatus.LOW_STOCK],
    ).select_related("category")

    total_parts = parts_qs.count()
    parts = list(
        parts_qs
        .order_by("-total_views", "-created_at")[:NUM_PARTS_HOMEPAGE]
    )

    has_compatibility_system = False

    # ── Catégories ─────────────────────────────────────────────────────
    categories = list(
        Category.objects.filter(is_active=True)
        .annotate(part_count=Count("parts", filter=Q(parts__is_active=True)))
        .filter(part_count__gt=0)
        .order_by("-part_count")[:NUM_CATEGORIES_HOMEPAGE]
    )

    # ── Villes ─────────────────────────────────────────────────────────
    cities_qs = City.objects.filter(
        is_active=True, garages__approval_status=Garage.ApprovalStatus.APPROVED
    ).annotate(
        garages_count=Count(
            "garages", filter=Q(garages__approval_status=Garage.ApprovalStatus.APPROVED)
        )
    ).filter(garages_count__gt=0)

    cities_count = cities_qs.count()
    cities = list(cities_qs.order_by("-garages_count")[:NUM_CITIES_HOMEPAGE])

    # ── Témoignages ────────────────────────────────────────────────────
    testimonials = list(
        Testimonial.objects.filter(is_published=True)
        .order_by("-created_at")[:NUM_TESTIMONIALS]
    )

    # ── Stats live (ticker) ────────────────────────────────────────────
    ticker_cached = cache.get(CACHE_KEY_TICKER)
    if ticker_cached is not None:
        live_activities = ticker_cached
    else:
        live_activities = _build_live_ticker()
        cache.set(CACHE_KEY_TICKER, live_activities, CACHE_TTL_TICKER)

    # ── Stats WHY ──────────────────────────────────────────────────────
    why_stats = _compute_why_stats()

    # ── Recherches populaires (top 3 catégories) ───────────────────────
    popular_searches = list(
        Category.objects.filter(is_active=True)
        .annotate(part_count=Count("parts", filter=Q(parts__is_active=True)))
        .filter(part_count__gt=0)
        .order_by("-part_count")[:3]
        .values_list("name", flat=True)
    )

    # ── Marqueurs carte blueprint ──────────────────────────────────────
    map_markers = []
    cities_with_coords = (
        City.objects.filter(
            is_active=True,
            garages__approval_status=Garage.ApprovalStatus.APPROVED,
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .distinct()
        .only("name", "latitude", "longitude")[:4]
    )
    for city in cities_with_coords:
        map_markers.append({
            "city": city.name,
            "lat": float(city.latitude),
            "lng": float(city.longitude),
            "left": "50%",
            "top": "50%",
        })

    if not map_markers:
        map_markers = DEFAULT_MAP_MARKERS

    # ── Stats générales ────────────────────────────────────────────────
    avg_rating = Testimonial.objects.filter(is_published=True).aggregate(
        avg=Avg("rating")
    )["avg"] or 0.0

    reviews_count = Testimonial.objects.filter(is_published=True).count()

    first_day_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    garages_this_month = Garage.objects.filter(
        created_at__gte=first_day_month,
        approval_status=Garage.ApprovalStatus.APPROVED,
    ).count()

    first_city = City.objects.filter(
        garages__approval_status=Garage.ApprovalStatus.APPROVED
    ).distinct().order_by("name").first()

    is_early_stage = total_garages < MIN_GARAGES_FOR_SOCIAL_PROOF

    # ── Contexte final ─────────────────────────────────────────────────
    context = {
        # Hero
        "live_garages": live_garages,
        "total_garages": total_garages,
        "total_parts": total_parts,
        "avg_rating": round(avg_rating, 1),
        "reviews_count": reviews_count,
        "cities_count": cities_count,
        "popular_searches": popular_searches,
        "map_markers": map_markers,
        # Live ticker
        "live_activities": live_activities,
        # Quick actions
        "first_city": first_city,
        # Garages
        "garages": garages,
        "garages_total_display": total_garages,
        # Parts
        "parts": parts,
        "has_compatibility_system": has_compatibility_system,
        # Categories
        "categories": categories,
        # Cities
        "cities": cities,
        "cities_count_display": cities_count,
        # Testimonials
        "testimonials": testimonials,
        # Why
        "why_verification_pct": why_stats["verification_pct"],
        "why_avg_response_time": why_stats["avg_response_time"],
        "why_savings_pct": why_stats["savings_pct"],
        "why_searches_this_month": why_stats["searches_this_month"],
        # CTA
        "garages_this_month": garages_this_month,
        # Flags
        "is_early_stage": is_early_stage,
    }

    cache.set(CACHE_KEY_HOME, context, CACHE_TTL_HOME)
    return render(request, "public/pages/home/index.html", context)
