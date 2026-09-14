"""
Helper functions for the AutoLink homepage.
"""
from typing import Any

# Coordinate bounds for the stylized Cameroon map (viewBox 400x566)
_CAMEROON_BOUNDS = {
    "lng_min": 8.49,
    "lng_max": 16.19,
    "lat_min": 1.65,
    "lat_max": 13.08,
}
_CAMEROON_SVG_WIDTH = 400
_CAMEROON_SVG_HEIGHT = 566

# Manual nudge for labels that would otherwise overlap the marker or go off-canvas
_LABEL_NUDGE = {
    "Douala":  (0, 0),
    "Yaoundé": (0, 0),
    "Buea":    (-14, 4),
    "Limbé":   (14, 4),
    "Kribi":   (0, 6),
    "Ebolowa": (0, 6),
}


def project_to_cameroon_map(lat: float, lng: float) -> tuple[float, float]:
    """Convertit (lat, lng) en coordonnées SVG (x, y) sur la carte stylisée du Cameroun.

    Le système de coordonnées SVG a son origine en haut à gauche.
    Les latitudes augmentent vers le nord, donc on inverse l'axe Y.
    """
    lng_range = _CAMEROON_BOUNDS["lng_max"] - _CAMEROON_BOUNDS["lng_min"]
    lat_range = _CAMEROON_BOUNDS["lat_max"] - _CAMEROON_BOUNDS["lat_min"]

    x = (lng - _CAMEROON_BOUNDS["lng_min"]) / lng_range * _CAMEROON_SVG_WIDTH
    y = (_CAMEROON_BOUNDS["lat_max"] - lat) / lat_range * _CAMEROON_SVG_HEIGHT

    return round(x, 2), round(y, 2)


def build_cities_map(cities: list[Any]) -> list[dict]:
    """Prépare les villes avec positions SVG + positions % pour labels HTML superposés.

    Returns:
        Liste de dicts avec clés : name, x, y, label_x, label_y, garages_count.
        Les villes sans coordonnées GPS ou hors du viewBox sont ignorées.
    """
    result: list[dict] = []
    for city in cities:
        lat = getattr(city, "latitude", None)
        lng = getattr(city, "longitude", None)

        if lat is None or lng is None:
            continue

        x, y = project_to_cameroon_map(float(lat), float(lng))

        # On ignore les villes projetées hors du viewBox (cas rare avec les bornes du Cameroun)
        if not (0 <= x <= _CAMEROON_SVG_WIDTH and 0 <= y <= _CAMEROON_SVG_HEIGHT):
            continue

        nx, ny = _LABEL_NUDGE.get(city.name, (0, 0))

        # Conversion en pourcentages relatifs au viewBox pour positionnement CSS
        label_x = (x / _CAMEROON_SVG_WIDTH) * 100 + nx * 0.05
        label_y = (y / _CAMEROON_SVG_HEIGHT) * 100 + ny * 0.05

        result.append({
            "name": city.name,
            "x": x,
            "y": y,
            "label_x": round(label_x, 2),
            "label_y": round(label_y, 2),
            "garages_count": getattr(city, "garages_count", 0),
        })

    return result
