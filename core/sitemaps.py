# core/sitemaps.py
"""
Sitemaps XML dynamiques (``django.contrib.sitemaps``).

Seul le contenu public et indexable est listé : pages institutionnelles,
villes ayant au moins un garage public, garages réellement visibles et pièces
actives. Les pages vides ou privées (compte, support, administration, recherche
interne, catégories non finalisées) sont exclues ici et/ou marquées ``noindex``
par ``autolink.middleware``.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Part
from core.models import City
from core.seo import site_host
from garages.models import Garage


class PublicSitemapMixin:
    """Force le domaine canonique public, indépendamment du framework ``sites``."""

    protocol = "https"
    limit = 500

    def get_domain(self, site=None):
        return site_host()

    @staticmethod
    def _page_url(name, **kwargs):
        return reverse(name, kwargs=kwargs or None)


class StaticViewSitemap(PublicSitemapMixin, Sitemap):
    """Pages éditoriales publiques du site."""

    # (route, priorité, fréquence) — les pages statiques n'ont pas de date de
    # modification fiable : on omet `lastmod` pour ne pas envoyer de signal faux.
    PAGES = (
        ("core:home", 1.0, "daily"),
        ("garages:garage_list", 0.9, "daily"),
        ("catalog:part_list", 0.9, "daily"),
        ("search:nearby_page", 0.8, "weekly"),
        ("core:about", 0.6, "monthly"),
        ("core:contact", 0.6, "monthly"),
        ("core:policy", 0.3, "yearly"),
    )
    _PRIORITIES = {name: priority for name, priority, _ in PAGES}
    _CHANGEFREQ = {name: changefreq for name, _, changefreq in PAGES}

    def items(self):
        return [name for name, _, _ in self.PAGES]

    def location(self, item):
        return self._page_url(item)

    def priority(self, item):
        return self._PRIORITIES.get(item, 0.5)

    def changefreq(self, item):
        return self._CHANGEFREQ.get(item, "monthly")


class GarageSitemap(PublicSitemapMixin, Sitemap):
    """Fiches garages publiquement disponibles."""

    priority = 0.9
    changefreq = "weekly"

    def items(self):
        return (
            Garage.objects.filter(Garage.public_filter())
            .exclude(slug="")
            .only("slug", "updated_at")
            .order_by("-updated_at")
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return self._page_url("garages:garage_detail", slug=obj.slug)


class PartSitemap(PublicSitemapMixin, Sitemap):
    """Pièces actives du catalogue."""

    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return (
            Part.objects.filter(is_active=True)
            .only("slug", "updated_at")
            .order_by("-updated_at")
        )

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return self._page_url("catalog:part_detail", slug=obj.slug)


class CitySitemap(PublicSitemapMixin, Sitemap):
    """Pages villes (landing locales : « garages à Douala », …).

    Seules les villes ayant au moins un garage public sont listées : une page
    vide n'a aucune valeur pour l'internaute ni pour Google.
    """

    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return (
            City.objects.filter(
                is_active=True,
                garages__approval_status=Garage.ApprovalStatus.APPROVED,
                garages__payment_status=Garage.PaymentStatus.PAID,
                garages__activation_status=Garage.ActivationStatus.ACTIVE,
                garages__is_active=True,
            )
            .distinct()
            .only("slug", "name")
        )

    def location(self, obj):
        return self._page_url("garages:garage_city", city_slug=obj.slug)


SITEMAPS = {
    "static": StaticViewSitemap,
    "villes": CitySitemap,
    "garages": GarageSitemap,
    "pieces": PartSitemap,
}
