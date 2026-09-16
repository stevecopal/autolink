# core/seo.py
"""
Helpers SEO transverses : URL canonique, OpenGraph, JSON-LD.

L'URL publique du site est centralisée ici afin que le sitemap, robots.txt et
les balises des templates pointent toujours vers le domaine canonique
(``settings.PUBLIC_SITE_URL``), et jamais vers le domaine de préproduction.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode

from django.conf import settings
from django.utils.safestring import mark_safe

#: Seul ce paramètre est conservé dans l'URL canonique (pagination des listes).
CANONICAL_ALLOWED_PARAMS = ("page",)

#: Titre / description par défaut (accueil et pages sans texte dédié).
DEFAULT_TITLE = "AutoLink — Garages et pièces auto vérifiés au Cameroun"
DEFAULT_DESCRIPTION = (
    "Trouvez un garage vérifié ou une pièce détachée près de chez vous au "
    "Cameroun : Douala, Yaoundé, Buea, Kribi… Comparez, contactez, roulez "
    "en confiance."
)

#: Image OpenGraph par défaut (1200x630, générée par build_og_image).
DEFAULT_OG_IMAGE = "/static/og-image.jpg"


def site_base_url() -> str:
    """URL publique du site, sans slash final (ex: https://autolink.cohub.site)."""
    return getattr(
        settings, "PUBLIC_SITE_URL", "https://autolink.cohub.site"
    ).rstrip("/")


def site_host() -> str:
    """Hôte public sans schéma (ex: autolink.cohub.site) — utilisé par le sitemap."""
    return site_base_url().split("://", 1)[-1]


def absolute_url(path: str) -> str:
    """Transforme un chemin relatif en URL absolue sur le domaine canonique."""
    if path.startswith(("http://", "https://")):
        return path
    return f"{site_base_url()}/{path.lstrip('/')}"


def canonical_url(request) -> str:
    """URL canonique de la page courante.

    Les paramètres de campagne (``utm_*``, ``fbclid``…) et les filtres de
    recherche sont retirés ; ``page`` est conservé pour les listes paginées.
    """
    params = {k: v for k, v in request.GET.items() if k in CANONICAL_ALLOWED_PARAMS}
    query = f"?{urlencode(params)}" if params else ""
    return absolute_url(f"{request.path}{query}")


def default_og_image() -> str:
    """URL absolue de l'image OpenGraph par défaut."""
    return absolute_url(DEFAULT_OG_IMAGE)


def truncate(text: str, limit: int = 155) -> str:
    """Nettoie et tronque un texte (limite d'affichage Google ≈ 155 caractères)."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def json_ld_script(payload) -> str:
    """Sérialise un dict/liste Python en balise <script type="application/ld+json">."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Empêche la fermeture prématurée de la balise <script> depuis une chaîne.
    data = data.replace("</", "<\\/")
    return mark_safe(f'<script type="application/ld+json">{data}</script>')
