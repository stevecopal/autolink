"""
Service de recherche géospatiale pour AutoLink.

Recherche les garages à proximité d'une position donnée
en utilisant la formule de Haversine pour le calcul de distance.
"""
import logging
import math

from django.conf import settings
from django.db.models import Q, QuerySet

from garages.models import Garage

logger = logging.getLogger('autolink')

# Configuration centralisée de la recherche
DEFAULT_SEARCH_RADIUS_KM = 5.0
MAX_SEARCH_RADIUS_KM = 50.0
MIN_SEARCH_RADIUS_KM = 0.5

# Rayon de la Terre en kilomètres
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcule la distance en kilomètres entre deux points
    en utilisant la formule de Haversine.

    Args:
        lat1: Latitude du premier point (degrés)
        lon1: Longitude du premier point (degrés)
        lat2: Latitude du deuxième point (degrés)
        lon2: Longitude du deuxième point (degrés)

    Returns:
        Distance en kilomètres
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_KM * c


def format_distance(distance_km: float) -> str:
    """
    Formate une distance pour l'affichage.

    Args:
        distance_km: Distance en kilomètres

    Returns:
        Chaîne formatée (ex: '850 m' ou '1,4 km')
    """
    if distance_km < 1:
        meters = round(distance_km * 1000)
        return f"{meters} m"
    else:
        km = round(distance_km, 1)
        # Afficher sans décimale si valeur entière
        if km == int(km):
            return f"{int(km)} km"
        return f"{km} km".replace('.', ',')


def validate_coordinates(latitude: float, longitude: float) -> list:
    """
    Valide les coordonnées GPS.

    Args:
        latitude: Latitude à valider
        longitude: Longitude à valider

    Returns:
        Liste vide si valide, liste de messages d'erreur sinon
    """
    errors = []

    # Vérifier le type en premier
    if not isinstance(latitude, (int, float)):
        errors.append("La latitude doit être un nombre.")
    else:
        # Vérifier NaN et Inf avant la comparaison
        if math.isnan(latitude) or math.isinf(latitude):
            errors.append("La latitude doit être un nombre valide.")
        elif not (-90 <= latitude <= 90):
            errors.append("La latitude doit être comprise entre -90 et 90.")

    if not isinstance(longitude, (int, float)):
        errors.append("La longitude doit être un nombre.")
    else:
        if math.isnan(longitude) or math.isinf(longitude):
            errors.append("La longitude doit être un nombre valide.")
        elif not (-180 <= longitude <= 180):
            errors.append("La longitude doit être comprise entre -180 et 180.")

    return errors


def search_nearby_garages(
    latitude: float,
    longitude: float,
    radius_km: float = DEFAULT_SEARCH_RADIUS_KM,
    availability_filter: bool = True,
) -> dict:
    """
    Recherche les garages à proximité d'une position donnée.

    Args:
        latitude: Latitude du point de recherche
        longitude: Longitude du point de recherche
        radius_km: Rayon de recherche en kilomètres
        availability_filter: Filtrer uniquement les garages disponibles

    Returns:
        Dict contenant les résultats et les métadonnées
    """
    # Valider les coordonnées
    coord_errors = validate_coordinates(latitude, longitude)
    if coord_errors:
        return {
            'success': False,
            'errors': coord_errors,
            'results': [],
            'total': 0,
        }

    # Valider le rayon
    radius_km = max(MIN_SEARCH_RADIUS_KM, min(MAX_SEARCH_RADIUS_KM, radius_km))

    logger.info(
        "Recherche de garages à proximité: lat=%.4f, lng=%.4f, rayon=%.1f km",
        latitude, longitude, radius_km
    )

    # Construire la requête de base
    queryset = Garage.objects.filter(
        is_active=True,
        verification_status=Garage.VerificationStatus.APPROVED,
    ).exclude(
        latitude__isnull=True,
        longitude__isnull=True,
    ).select_related('city', 'neighborhood')

    # Filtrer par disponibilité si demandé
    if availability_filter:
        queryset = queryset.filter(
            availability_status=Garage.AvailabilityStatus.AVAILABLE
        )

    # Calculer les distances et filtrer par rayon
    results = []
    garages = queryset.select_related('owner').prefetch_related(
        'services', 'photos', 'brands',
    )

    for garage in garages:
        distance = haversine_distance(
            latitude, longitude,
            float(garage.latitude), float(garage.longitude)
        )

        if distance <= radius_km:
            # Déterminer le statut de disponibilité
            is_available = garage.availability_status == Garage.AvailabilityStatus.AVAILABLE

            results.append({
                'id': garage.id,
                'slug': garage.slug,
                'name': garage.name,
                'description': garage.description[:200] if garage.description else '',
                'address': garage.address,
                'city': garage.city.name if garage.city else '',
                'city_slug': garage.city.slug if garage.city else '',
                'neighborhood': garage.neighborhood.name if garage.neighborhood else '',
                'neighborhood_slug': garage.neighborhood.slug if garage.neighborhood else '',
                'latitude': float(garage.latitude),
                'longitude': float(garage.longitude),
                'distance_km': round(distance, 2),
                'distance_display': format_distance(distance),
                'is_available': is_available,
                'availability_status': garage.availability_status,
                'availability_message': garage.availability_message,
                'availability_display': garage.get_availability_status_display(),
                'verification_status': garage.verification_status,
                'is_featured': garage.is_featured,
                'trust_score': float(garage.trust_score),
                'total_reviews': garage.total_reviews,
                'phone': garage.phone,
                'whatsapp': garage.whatsapp,
                'photo_url': garage.photo.url if garage.photo else None,
                'opening_time': garage.opening_time.strftime('%H:%M') if garage.opening_time else None,
                'closing_time': garage.closing_time.strftime('%H:%M') if garage.closing_time else None,
                'is_open_now': garage.is_open_now,
                'url': f'/garages/{garage.slug}/',
            })

    # Trier par distance
    results.sort(key=lambda x: x['distance_km'])

    logger.info(
        "Résultat recherche: %d garages trouvés dans un rayon de %.1f km",
        len(results), radius_km
    )

    return {
        'success': True,
        'results': results,
        'total': len(results),
        'search_radius_km': radius_km,
        'center': {
            'latitude': latitude,
            'longitude': longitude,
        },
    }
