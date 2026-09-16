# autolink/context_processors.py
"""
Context processors du projet.

``seo`` expose à tous les templates les valeurs nécessaires aux balises
canonical / OpenGraph / vérification Google, sans que chaque vue ait à les
recalculer.
"""
from django.conf import settings

from core.seo import (
    DEFAULT_DESCRIPTION,
    DEFAULT_TITLE,
    canonical_url,
    default_og_image,
    site_base_url,
)


def seo(request):
    """Injecte les variables SEO globales dans le contexte des templates."""
    return {
        "SEO_SITE_URL": site_base_url(),
        "SEO_CANONICAL": canonical_url(request),
        "SEO_DEFAULT_TITLE": DEFAULT_TITLE,
        "SEO_DEFAULT_DESCRIPTION": DEFAULT_DESCRIPTION,
        "SEO_DEFAULT_OG_IMAGE": default_og_image(),
        "SEO_GOOGLE_SITE_VERIFICATION": getattr(
            settings, "GOOGLE_SITE_VERIFICATION", ""
        ),
        "SEO_GOOGLE_ANALYTICS_ID": getattr(settings, "GOOGLE_ANALYTICS_ID", ""),
    }
