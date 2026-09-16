# core/views/seo.py
"""
Fichiers techniques SEO servis dynamiquement.

``robots.txt`` est généré par Django (et non déposé en statique) afin que
l'URL du sitemap suive automatiquement ``settings.PUBLIC_SITE_URL``.
"""
from django.http import HttpRequest, HttpResponse

from core.seo import site_base_url

#: Zones sans valeur d'indexation : compte, support, administration, API.
#: Les pages publiques marquées `noindex` (ex. /recherche/) ne sont PAS
#: interdites ici : Google doit pouvoir les explorer pour voir le noindex.
DISALLOWED_PATHS = (
    "/admin/",
    "/administration/",
    "/compte/",
    "/accounts/",
    "/paiement/",
    "/paiements/",
    "/payments/",
    "/recu/",
    "/messages/",
    "/tickets/",
    "/assistance/",
    "/garages/creer/",
    "/garages/mes-garages/",
    "/garages/mon-dashboard/",
    "/garage/produits/",
    "/api/",
    "/*/api/",
    "/sw.js",
    "/offline/",
)


def robots_txt_view(request: HttpRequest) -> HttpResponse:
    """Sert /robots.txt avec l'URL absolue du sitemap."""
    lines = [
        "# robots.txt — AutoLink",
        "# Les zones privées sont également marquées « noindex » côté application.",
        "",
        "User-agent: *",
        "Allow: /",
    ]
    lines += [f"Disallow: {path}" for path in DISALLOWED_PATHS]
    lines += [
        "",
        f"Sitemap: {site_base_url()}/sitemap.xml",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def google_verification(request):
    content = "google-site-verification: googleb7f03ccc54822e60.html"
    return HttpResponse(content, content_type="text/html")