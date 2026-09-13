# core/constants.py
"""
Constantes et valeurs par défaut pour la landing page AutoLink.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TIMEOUTS DE CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CACHE_TTL_HOME = 300          # 5 minutes — données générales de la home
CACHE_TTL_TICKER = 60         # 60 secondes — live ticker (actualisation fréquente)
CACHE_TTL_GARAGES = 300       # 5 minutes — liste garages mis en avant
CACHE_TTL_PARTS = 300         # 5 minutes — liste pièces populaires
CACHE_TTL_CATEGORIES = 300    # 5 minutes — catégories avec compteurs
CACHE_TTL_CITIES = 300        # 5 minutes — villes avec compteurs

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEUILS D'AFFICHAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MIN_GARAGES_FOR_SOCIAL_PROOF = 10   # Seuil pour afficher les vrais chiffres
MIN_GARAGES_FOR_MAP_MARKERS = 4     # Nombre minimum de villes pour les marqueurs
NUM_GARAGES_HOMEPAGE = 6            # Nombre de garages affichés sur la home
NUM_PARTS_HOMEPAGE = 8              # Nombre de pièces affichées sur la home
NUM_CATEGORIES_HOMEPAGE = 8         # Nombre de catégories affichées
NUM_CITIES_HOMEPAGE = 12            # Nombre de villes affichées
NUM_TICKER_ITEMS = 6                # Nombre d'événements dans le ticker
NUM_TESTIMONIALS = 3               # Nombre de témoignages affichés

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALEURS PAR DÉFAUT (fallbacks élégants)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFAULT_HERO_STATS = {
    "live_garages": 0,
    "total_garages": 0,
    "total_parts": 0,
    "avg_rating": 0.0,
    "reviews_count": 0,
    "cities_count": 0,
}

DEFAULT_WHY_STATS = {
    "verification_pct": 100,        # Toujours 100% si système de vérification actif
    "avg_response_time": None,      # None = pas de donnée mesurable → fallback texte
    "savings_pct": None,            # None = pas de comparateur → fallback texte
    "searches_this_month": 0,       # Alternative si savings_pct est None
}

DEFAULT_MAP_MARKERS = [
    {"city": "Douala", "lat": 4.0511, "lng": 9.7679, "left": "18%", "top": "58%"},
    {"city": "Yaoundé", "lat": 3.8487, "lng": 11.5020, "left": "45%", "top": "42%"},
    {"city": "Bafoussam", "lat": 5.4667, "lng": 10.4333, "left": "32%", "top": "24%"},
    {"city": "Garoua", "lat": 8.9500, "lng": 13.1667, "left": "78%", "top": "24%"},
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Filtres Garages (cohérence avec Garage.public_filter)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GARAGE_PUBLIC_FILTERS = {
    "approval_status": "APPROVED",
    "payment_status": "PAID",
    "activation_status": "ACTIVE",
    "is_active": True,
}
