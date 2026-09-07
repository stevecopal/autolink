"""
Vues pour la recherche de garages à proximité.
"""
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _

from .services import search_nearby_garages, validate_coordinates

logger = logging.getLogger('autolink')


@require_GET
def nearby_search_api(request):
    """
    API endpoint pour la recherche de garages à proximité.

    Accepte les paramètres GET:
        - lat: Latitude
        - lng: Longitude
        - radius: Rayon en km (optionnel, défaut 5)
        - available: Filtrer uniquement les disponibles (optionnel)

    Returns:
        JsonResponse avec les résultats
    """
    try:
        latitude = float(request.GET.get('lat', 0))
        longitude = float(request.GET.get('lng', 0))
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'errors': [_('Coordonnées invalides.')],
            'results': [],
            'total': 0,
        }, status=400)

    try:
        radius = float(request.GET.get('radius', 5.0))
    except (ValueError, TypeError):
        radius = 5.0

    availability_filter = request.GET.get('available', '') == '1'

    result = search_nearby_garages(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius,
        availability_filter=availability_filter,
    )

    status_code = 200 if result['success'] else 400
    return JsonResponse(result, status=status_code)


@require_POST
def nearby_search_post_api(request):
    """
    API endpoint POST pour la recherche de garages à proximité.

    Accepte un body JSON:
        {
            "latitude": 3.8480,
            "longitude": 11.5020,
            "accuracy": 15,
            "radius": 5.0
        }

    Returns:
        JsonResponse avec les résultats
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({
            'success': False,
            'errors': [_('Données invalides.')],
            'results': [],
            'total': 0,
        }, status=400)

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    radius = data.get('radius', 5.0)
    availability_filter = data.get('available', False)

    if latitude is None or longitude is None:
        return JsonResponse({
            'success': False,
            'errors': [_('La latitude et la longitude sont requises.')],
            'results': [],
            'total': 0,
        }, status=400)

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        radius = float(radius)
    except (ValueError, TypeError):
        return JsonResponse({
            'success': False,
            'errors': [_('Types de données invalides.')],
            'results': [],
            'total': 0,
        }, status=400)

    # Valider les coordonnées
    coord_errors = validate_coordinates(latitude, longitude)
    if coord_errors:
        return JsonResponse({
            'success': False,
            'errors': coord_errors,
            'results': [],
            'total': 0,
        }, status=400)

    result = search_nearby_garages(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius,
        availability_filter=availability_filter,
    )

    status_code = 200 if result['success'] else 400
    return JsonResponse(result, status=status_code)


def nearby_page_view(request):
    """
    Page de recherche de garages à proximité.
    Affiche une carte Leaflet et une liste de résultats.
    """
    return render(request, 'public/pages/search/nearby.html')
