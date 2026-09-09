import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import (
    Avg,
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    IntegerField,
    Prefetch,
    Q,
    Sum,
    When,
)
from django.db.models.functions import ATan2, Cos, Radians, Sin, Sqrt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import GarageDocumentForm, GarageForm
from .models import Garage, GaragePhoto, GarageService, GarageVerification


def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two points using Haversine formula."""
    from math import atan2, cos, radians, sin, sqrt

    R = 6371

    lat1, lon1, lat2, lon2 = map(
        radians, [float(lat1), float(lon1), float(lat2), float(lon2)]
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def _get_base_garage_queryset():
    """Get base queryset with annotations to avoid N+1 queries."""
    return (
        Garage.objects.filter(Garage.public_filter())
        .select_related("owner", "city", "neighborhood")
        .prefetch_related(
            Prefetch(
                "services",
                queryset=GarageService.objects.filter(is_active=True).order_by(
                    "category", "name"
                ),
            ),
            Prefetch(
                "photos",
                queryset=GaragePhoto.objects.order_by("-is_primary", "-created_at"),
            ),
        )
        .annotate(
            active_services_count=Count("services", filter=Q(services__is_active=True)),
            photos_count=Count("photos"),
        )
    )


def garage_list_view(request):
    garages = _get_base_garage_queryset()

    city = request.GET.get("city", "").strip()
    neighborhood = request.GET.get("neighborhood", "").strip()
    service_category = request.GET.get("service", "").strip()
    search = request.GET.get("q", "").strip()
    available = request.GET.get("available", "")
    latitude = request.GET.get("lat", "")
    longitude = request.GET.get("lng", "")
    radius = request.GET.get("radius", "")
    sort = request.GET.get("sort", "-trust_score")
    page_size = int(request.GET.get("page_size", 12))

    if city:
        garages = garages.filter(city__slug=city)
    if neighborhood:
        garages = garages.filter(neighborhood__slug=neighborhood)
    if service_category:
        garages = garages.filter(services__category=service_category)
    if search:
        garages = garages.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(services__name__icontains=search)
            | Q(address__icontains=search)
            | Q(neighborhood__name__icontains=search)
            | Q(city__name__icontains=search)
        ).distinct()
    if available == "1":
        garages = garages.filter(availability_status="AVAILABLE")

    nearby_garages = None
    if latitude and longitude and radius:
        try:
            lat = float(latitude)
            lng = float(longitude)
            radius_km = float(radius)

            garages_with_coords = garages.exclude(
                latitude__isnull=True, longitude__isnull=True
            )

            nearby_ids = []
            for garage in garages_with_coords:
                distance = _haversine_distance(
                    lat, lng, garage.latitude, garage.longitude
                )
                if distance <= radius_km:
                    nearby_ids.append(garage.pk)

            garages = garages.filter(pk__in=nearby_ids)
            nearby_garages = True
        except (ValueError, TypeError):
            pass

    valid_sorts = {
        "-trust_score": "-trust_score",
        "trust_score": "trust_score",
        "-total_reviews": "-total_reviews",
        "name": "name",
        "-created_at": "-created_at",
        "distance": "distance",
    }
    sort_field = valid_sorts.get(sort, "-trust_score")
    if sort_field != "distance":
        garages = garages.order_by(sort_field)

    from core.models import City, Neighborhood

    cities = (
        City.objects.filter(
            is_active=True,
            garages__is_active=True,
            garages__approval_status=Garage.ApprovalStatus.APPROVED,
            garages__payment_status=Garage.PaymentStatus.PAID,
            garages__activation_status=Garage.ActivationStatus.ACTIVE,
        )
        .distinct()
        .order_by("name")
    )

    neighborhoods = Neighborhood.objects.filter(
        is_active=True,
        garages__is_active=True,
        garages__approval_status=Garage.ApprovalStatus.APPROVED,
        garages__payment_status=Garage.PaymentStatus.PAID,
        garages__activation_status=Garage.ActivationStatus.ACTIVE,
    )
    if city:
        neighborhoods = neighborhoods.filter(city__slug=city)
    neighborhoods = neighborhoods.distinct().order_by("name")

    paginator = Paginator(garages, page_size)
    page = request.GET.get("page", 1)

    try:
        garages_page = paginator.page(page)
    except PageNotAnInteger:
        garages_page = paginator.page(1)
    except EmptyPage:
        garages_page = paginator.page(paginator.num_pages)

    context = {
        "garages": garages_page,
        "cities": cities,
        "neighborhoods": [n for n in neighborhoods if n],
        "selected_city": city,
        "selected_neighborhood": neighborhood,
        "selected_service": service_category,
        "search_query": search,
        "selected_available": available,
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "sort": sort,
        "page_size": page_size,
        "nearby_garages": nearby_garages,
        "service_categories": GarageService.Category.choices,
    }

    if (
        request.headers.get("HX-Request")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return render(request, "dashboard/includes/garage_list_items.html", context)

    return render(request, "public/pages/garages/list.html", context)


@require_GET
def garage_list_api(request):
    """API endpoint for AJAX filtering and pagination."""
    garages = _get_base_garage_queryset()

    city = request.GET.get("city", "").strip()
    neighborhood = request.GET.get("neighborhood", "").strip()
    service_category = request.GET.get("service", "").strip()
    search = request.GET.get("q", "").strip()
    available = request.GET.get("available", "")
    latitude = request.GET.get("lat", "")
    longitude = request.GET.get("lng", "")
    radius = request.GET.get("radius", "")
    sort = request.GET.get("sort", "-trust_score")
    page_size = min(int(request.GET.get("page_size", 12)), 50)
    page = int(request.GET.get("page", 1))

    if city:
        garages = garages.filter(city__slug=city)
    if neighborhood:
        garages = garages.filter(neighborhood__slug=neighborhood)
    if service_category:
        garages = garages.filter(services__category=service_category)
    if search:
        garages = garages.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(services__name__icontains=search)
            | Q(address__icontains=search)
            | Q(neighborhood__name__icontains=search)
            | Q(city__name__icontains=search)
        ).distinct()
    if available == "1":
        garages = garages.filter(availability_status="AVAILABLE")

    nearby_garages = False
    if latitude and longitude and radius:
        try:
            lat = float(latitude)
            lng = float(longitude)
            radius_km = float(radius)

            garages_with_coords = garages.exclude(
                latitude__isnull=True, longitude__isnull=True
            )

            nearby_ids = []
            for garage in garages_with_coords:
                distance = _haversine_distance(
                    lat, lng, garage.latitude, garage.longitude
                )
                if distance <= radius_km:
                    nearby_ids.append(garage.pk)

            garages = garages.filter(pk__in=nearby_ids)
            nearby_garages = True
        except (ValueError, TypeError):
            pass

    valid_sorts = {
        "-trust_score": "-trust_score",
        "trust_score": "trust_score",
        "-total_reviews": "-total_reviews",
        "name": "name",
        "-created_at": "-created_at",
    }
    sort_field = valid_sorts.get(sort, "-trust_score")
    garages = garages.order_by(sort_field)

    paginator = Paginator(garages, page_size)

    try:
        garages_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        garages_page = paginator.page(1)

    results = []
    for garage in garages_page:
        primary_photo = garage.photos.first()
        services_list = list(garage.services.all()[:5])

        results.append(
            {
                "id": garage.id,
                "slug": garage.slug,
                "name": garage.name,
                "description": garage.description[:200] if garage.description else "",
                "phone": garage.phone,
                "whatsapp": garage.whatsapp,
                "email": garage.email,
                "address": garage.address,
                "city": garage.city.name if garage.city else "",
                "city_slug": garage.city.slug if garage.city else "",
                "neighborhood": garage.neighborhood.name if garage.neighborhood else "",
                "neighborhood_slug": garage.neighborhood.slug
                if garage.neighborhood
                else "",
                "latitude": float(garage.latitude) if garage.latitude else None,
                "longitude": float(garage.longitude) if garage.longitude else None,
                "photo_url": garage.photo.url if garage.photo else None,
                "primary_photo_url": primary_photo.image.url if primary_photo else None,
                "verification_status": garage.verification_status,
                "is_featured": garage.is_featured,
                "availability_status": garage.availability_status,
                "availability_message": garage.availability_message,
                "opening_time": garage.opening_time.strftime("%H:%M")
                if garage.opening_time
                else None,
                "closing_time": garage.closing_time.strftime("%H:%M")
                if garage.closing_time
                else None,
                "open_weekends": garage.open_weekends,
                "trust_score": float(garage.trust_score),
                "total_reviews": garage.total_reviews,
                "total_clients": garage.total_clients,
                "is_open_now": garage.is_open_now,
                "active_services_count": garage.active_services_count,
                "photos_count": garage.photos_count,
                "services": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "category": s.category,
                        "category_display": s.get_category_display(),
                        "price_min": float(s.price_min) if s.price_min else None,
                        "price_max": float(s.price_max) if s.price_max else None,
                        "duration_minutes": s.duration_minutes,
                    }
                    for s in services_list
                ],
                "url": f"/garages/{garage.slug}/",
            }
        )

    return JsonResponse(
        {
            "results": results,
            "pagination": {
                "current_page": garages_page.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "page_size": page_size,
                "has_next": garages_page.has_next(),
                "has_previous": garages_page.has_previous(),
                "next_page": garages_page.next_page_number()
                if garages_page.has_next()
                else None,
                "previous_page": garages_page.previous_page_number()
                if garages_page.has_previous()
                else None,
            },
            "filters": {
                "city": city,
                "neighborhood": neighborhood,
                "service": service_category,
                "search": search,
                "available": available,
                "nearby": nearby_garages,
                "sort": sort,
            },
        }
    )


def garage_detail_view(request, slug):
    garage = get_object_or_404(
        Garage.objects.select_related("owner", "city", "neighborhood").prefetch_related(
            Prefetch(
                "services",
                queryset=GarageService.objects.filter(is_active=True).order_by(
                    "category", "name"
                ),
            ),
            Prefetch(
                "photos",
                queryset=GaragePhoto.objects.order_by("-is_primary", "-created_at"),
            ),
            Prefetch(
                "reviews",
                queryset=__import__("reviews.models", fromlist=["Review"])
                .Review.objects.filter(is_hidden=False)
                .select_related("user")
                .order_by("-created_at"),
            ),
        ),
        Garage.public_filter(),
        slug=slug,
    )

    services = garage.services.all()
    photos = garage.photos.all()
    reviews = garage.reviews.all()[:10]

    services_by_category = {}
    for service in services:
        cat = service.get_category_display()
        if cat not in services_by_category:
            services_by_category[cat] = []
        services_by_category[cat].append(service)

    context = {
        "garage": garage,
        "services": services,
        "services_by_category": services_by_category,
        "photos": photos,
        "reviews": reviews,
        "total_reviews": garage.reviews.filter(is_hidden=False).count(),
    }

    if request.headers.get("HX-Request"):
        return render(
            request, "public/pages/garages/partials/garage_detail_content.html", context
        )

    return render(request, "public/pages/garages/detail.html", context)


@require_GET
def garage_detail_api(request, slug):
    """API endpoint for garage detail data."""
    garage = get_object_or_404(
        Garage.objects.select_related("owner").prefetch_related(
            Prefetch(
                "services",
                queryset=GarageService.objects.filter(is_active=True).order_by(
                    "category", "name"
                ),
            ),
            Prefetch(
                "photos",
                queryset=GaragePhoto.objects.order_by("-is_primary", "-created_at"),
            ),
        ),
        slug=slug,
        is_active=True,
    )

    services = garage.services.all()
    photos = garage.photos.all()

    services_by_category = {}
    for service in services:
        cat = service.get_category_display()
        if cat not in services_by_category:
            services_by_category[cat] = []
        services_by_category[cat].append(
            {
                "id": service.id,
                "name": service.name,
                "category": service.category,
                "description": service.description,
                "price_min": float(service.price_min) if service.price_min else None,
                "price_max": float(service.price_max) if service.price_max else None,
                "duration_minutes": service.duration_minutes,
            }
        )

    return JsonResponse(
        {
            "id": garage.id,
            "slug": garage.slug,
            "name": garage.name,
            "description": garage.description,
            "phone": garage.phone,
            "whatsapp": garage.whatsapp,
            "email": garage.email,
            "address": garage.address,
            "city": garage.city.name if garage.city else "",
            "city_slug": garage.city.slug if garage.city else "",
            "neighborhood": garage.neighborhood.name if garage.neighborhood else "",
            "neighborhood_slug": garage.neighborhood.slug
            if garage.neighborhood
            else "",
            "latitude": float(garage.latitude) if garage.latitude else None,
            "longitude": float(garage.longitude) if garage.longitude else None,
            "photo_url": garage.photo.url if garage.photo else None,
            "verification_status": garage.verification_status,
            "is_featured": garage.is_featured,
            "availability_status": garage.availability_status,
            "availability_message": garage.availability_message,
            "opening_time": garage.opening_time.strftime("%H:%M")
            if garage.opening_time
            else None,
            "closing_time": garage.closing_time.strftime("%H:%M")
            if garage.closing_time
            else None,
            "open_weekends": garage.open_weekends,
            "trust_score": float(garage.trust_score),
            "total_reviews": garage.total_reviews,
            "total_clients": garage.total_clients,
            "is_open_now": garage.is_open_now,
            "created_at": garage.created_at.isoformat(),
            "updated_at": garage.updated_at.isoformat(),
            "services_by_category": services_by_category,
            "photos": [
                {
                    "id": p.id,
                    "image_url": p.image.url,
                    "caption": p.caption,
                    "is_primary": p.is_primary,
                }
                for p in photos
            ],
        }
    )


GPS_ACCURACY_THRESHOLD = Decimal("50.0")


@login_required
def garage_create_view(request):
    if request.method == "POST":
        form = GarageForm(request.POST, request.FILES)
        doc_form = GarageDocumentForm(request.POST, request.FILES)

        if form.is_valid():
            latitude = form.cleaned_data.get("latitude")
            longitude = form.cleaned_data.get("longitude")
            accuracy = form.cleaned_data.get("gps_accuracy")

            if not latitude or not longitude:
                messages.error(
                    request,
                    _(
                        "La position GPS est obligatoire. Veuillez autoriser la géolocalisation."
                    ),
                )
                return render(
                    request,
                    "dashboard/pages/garage/form.html",
                    {
                        "form": form,
                        "doc_form": doc_form,
                    },
                )

            if accuracy and accuracy > GPS_ACCURACY_THRESHOLD:
                messages.error(
                    request,
                    _(
                        "Votre position n'est pas suffisamment précise (%(accuracy).1f m). "
                        "Veuillez vous rapprocher du garage et réessayer."
                    )
                    % {"accuracy": accuracy},
                )
                return render(
                    request,
                    "dashboard/pages/garage/form.html",
                    {
                        "form": form,
                        "doc_form": doc_form,
                    },
                )

            garage = form.save(commit=False)
            garage.owner = request.user
            garage.latitude = latitude
            garage.longitude = longitude
            garage.gps_accuracy = accuracy
            garage.location_captured_at = timezone.now()

            garage.save()

            from accounts.models import User

            if request.user.role == User.Role.USER:
                request.user.role = User.Role.CLIENT
                request.user.save(update_fields=["role"])

            if doc_form.is_valid():
                GarageVerification.objects.create(
                    garage=garage,
                    document_type=doc_form.cleaned_data["document_type"],
                    document=doc_form.cleaned_data["document"],
                )

            messages.success(
                request, _("Garage enregistré. Il sera vérifié par notre équipe.")
            )
            return redirect("garages:garage_dashboard")
    else:
        form = GarageForm()
        doc_form = GarageDocumentForm()

    return render(
        request,
        "dashboard/pages/garage/form.html",
        {
            "form": form,
            "doc_form": doc_form,
        },
    )


@login_required
def garage_edit_view(request, garage_id):
    garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)
    if request.method == "POST":
        form = GarageForm(request.POST, request.FILES, instance=garage)
        if form.is_valid():
            form.save()
            messages.success(request, _("Garage mis à jour."))
            return redirect("garages:garage_dashboard")
    else:
        form = GarageForm(instance=garage)
    return render(
        request,
        "dashboard/pages/garage/form.html",
        {
            "form": form,
            "doc_form": GarageDocumentForm(),
            "garage": garage,
            "is_edit": True,
        },
    )


@login_required
@require_POST
def garage_delete_view(request, garage_id):
    garage = get_object_or_404(Garage, pk=garage_id, owner=request.user)
    garage.delete()
    messages.success(request, _("Garage supprimé."))
    return redirect("garages:garage_dashboard")


@login_required
def garage_dashboard_view(request):
    from accounts.models import User
    from payments.constants import GARAGE_ACTIVATION_AMOUNT, GARAGE_ACTIVATION_CURRENCY

    if request.user.role not in [User.Role.CLIENT, User.Role.ADMIN]:
        return redirect("garages:garage_create")

    garages = Garage.objects.filter(owner=request.user).select_related(
        "city", "neighborhood"
    )
    if not garages.exists():
        return redirect("garages:garage_create")

    garage = garages.first()

    from catalog.models import Part
    from reviews.models import Review

    products = Part.objects.filter(garage=garage, is_active=True).select_related(
        "category"
    )
    recent_reviews = Review.objects.filter(
        garage=garage, is_hidden=False
    ).select_related("user")[:5]

    total_products = products.count()
    avg_rating = garage.trust_score or 0

    context = {
        "garage": garage,
        "garages": garages,
        "products": products[:10],
        "recent_reviews": recent_reviews,
        "total_products": total_products,
        "avg_rating": avg_rating,
        "garage_activation_amount": GARAGE_ACTIVATION_AMOUNT,
        "garage_activation_currency": GARAGE_ACTIVATION_CURRENCY,
    }
    return render(request, "dashboard/pages/garage/index.html", context)


@login_required
def garage_availability_toggle(request):
    if request.method == "POST":
        from accounts.models import User

        if request.user.role not in [User.Role.CLIENT, User.Role.ADMIN]:
            messages.error(request, _("Accès non autorisé."))
            return redirect("core:home")

        garage = Garage.objects.filter(owner=request.user).first()
        if garage and garage.is_publicly_available:
            status = request.POST.get("status", "AVAILABLE")
            message = request.POST.get("message", "")
            garage.availability_status = status
            garage.availability_message = message
            garage.save(update_fields=["availability_status", "availability_message"])
            messages.success(request, _("Disponibilité mise à jour."))
    return redirect("garages:garage_dashboard")


@require_GET
def garage_search_suggestions(request):
    """API endpoint for search autocomplete suggestions."""
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"suggestions": []})

    garages = (
        Garage.objects.filter(
            Q(name__icontains=q)
            | Q(city__name__icontains=q)
            | Q(neighborhood__name__icontains=q)
            | Q(services__name__icontains=q)
        )
        .distinct()
        .values(
            "name",
            "slug",
            "city__name",
            "city__slug",
            "neighborhood__name",
            "neighborhood__slug",
        )[:10]
    )

    suggestions = []
    for g in garages:
        suggestions.append(
            {
                "name": g["name"],
                "city": g["city__name"] or "",
                "neighborhood": g["neighborhood__name"] or "",
                "slug": g["slug"],
            }
        )

    services = (
        GarageService.objects.filter(
            is_active=True,
            garage__is_active=True,
            garage__verification_status=Garage.VerificationStatus.APPROVED,
            garage__approval_status=Garage.ApprovalStatus.APPROVED,
            garage__payment_status=Garage.PaymentStatus.PAID,
            garage__activation_status=Garage.ActivationStatus.ACTIVE,
        )
        .filter(name__icontains=q)
        .values("name", "category")
        .distinct()[:5]
    )

    for s in services:
        suggestions.append(
            {"name": s["name"], "category": s["category"], "type": "service"}
        )

    return JsonResponse({"suggestions": suggestions})
