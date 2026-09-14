"""
Signaux d'invalidation du cache pour la landing page.
Invalident le cache home_page_data et home_ticker_data
lorsque les données changent.
"""

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from catalog.models import Category, Part
from core.models import Testimonial, City
from garages.models import Garage

CACHE_KEY_HOME = "home_page_data"
CACHE_KEY_TICKER = "home_ticker_data"


def _invalidate_home_cache(sender, **kwargs):
    """Invalide tous les caches de la landing page."""
    cache.delete(CACHE_KEY_HOME)
    cache.delete(CACHE_KEY_TICKER)


@receiver(post_save, sender=Garage)
def garage_saved(sender, instance, **kwargs):
    """Un garage est créé/modifié : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_delete, sender=Garage)
def garage_deleted(sender, instance, **kwargs):
    """Un garage est supprimé : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_save, sender=Part)
def part_saved(sender, instance, **kwargs):
    """Une pièce est créée/modifiée : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_delete, sender=Part)
def part_deleted(sender, instance, **kwargs):
    """Une pièce est supprimée : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_save, sender=Category)
def category_saved(sender, instance, **kwargs):
    """Une catégorie est créée/modifiée : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_delete, sender=Category)
def category_deleted(sender, instance, **kwargs):
    """Une catégorie est supprimée : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_save, sender=Testimonial)
def testimonial_saved(sender, instance, **kwargs):
    """Un témoignage est créé/modifié : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_delete, sender=Testimonial)
def testimonial_deleted(sender, instance, **kwargs):
    """Un témoignage est supprimé : invalider le cache."""
    _invalidate_home_cache(sender)


@receiver(post_save, sender=City)
def city_saved(sender, instance, **kwargs):
    """Une ville est créée/modifiée : invalider le cache (coords GPS)."""
    _invalidate_home_cache(sender)


@receiver(post_delete, sender=City)
def city_deleted(sender, instance, **kwargs):
    """Une ville est supprimée : invalider le cache."""
    _invalidate_home_cache(sender)
