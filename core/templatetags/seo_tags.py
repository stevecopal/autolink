# core/templatetags/seo_tags.py
"""Balises de gabarit produisant les données structurées JSON-LD (schema.org).

Elles évitent d'écrire du JSON à la main dans les templates et garantissent des
URLs absolues sur le domaine canonique.
"""
from django import template
from django.urls import reverse

from core.seo import absolute_url, json_ld_script, site_base_url, truncate

register = template.Library()

#: État d'une pièce → vocabulaire schema.org.
CONDITION_MAP = {
    "NEW": "https://schema.org/NewCondition",
    "USED": "https://schema.org/UsedCondition",
    "REFURBISHED": "https://schema.org/RefurbishedCondition",
}


def _clean(data: dict) -> dict:
    """Retire les champs vides : Google ignore de toute façon les valeurs nulles."""
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _garage_url(garage) -> str:
    return absolute_url(reverse("garages:garage_detail", kwargs={"slug": garage.slug}))


def _part_url(part) -> str:
    return absolute_url(reverse("catalog:part_detail", kwargs={"slug": part.slug}))


def _opening_hours(garage):
    """Horaires au format schema.org, ex. « Mo-Sa 08:00-18:00 »."""
    if not (garage.opening_time and garage.closing_time):
        return None
    start = garage.opening_time.strftime("%H:%M")
    end = garage.closing_time.strftime("%H:%M")
    # Build day range based on open days
    if garage.open_weekends and garage.open_sunday:
        days = "Mo-Su"
    elif garage.open_weekends:
        days = "Mo-Sa"
    elif garage.open_sunday:
        days = "Mo-Fr,Su"
    else:
        days = "Mo-Fr"
    return f"{days} {start}-{end}"


@register.simple_tag
def seo_organization_json_ld():
    """Organization + WebSite (avec SearchAction) : une fois par page."""
    base = site_base_url()
    organization = _clean(
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "@id": f"{base}/#organization",
            "name": "AutoLink",
            "url": f"{base}/",
            "logo": absolute_url("/static/logo.jpg"),
            "description": (
                "Plateforme camerounaise qui met en relation les automobilistes "
                "avec des garages vérifiés et un catalogue de pièces détachées."
            ),
            "areaServed": {"@type": "Country", "name": "Cameroun"},
        }
    )
    website = _clean(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "@id": f"{base}/#website",
            "name": "AutoLink",
            "url": f"{base}/",
            "inLanguage": "fr-CM",
            "publisher": {"@id": f"{base}/#organization"},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{base}/recherche/?q={{search_term_string}}",
                },
                "query-input": "required name=search_term_string",
            },
        }
    )
    return json_ld_script([organization, website])

@register.simple_tag
def garage_json_ld(garage):
    """Fiche garage : AutoRepair (+ services, géolocalisation, horaires)."""
    address = _clean(
        {
            "@type": "PostalAddress",
            "streetAddress": garage.address,
            "addressLocality": garage.city.name if garage.city else "",
            "addressRegion": garage.city.region if garage.city else "",
            "addressCountry": "CM",
        }
    )
    data = _clean(
        {
            "@context": "https://schema.org",
            "@type": "AutoRepair",
            "name": garage.name,
            "url": _garage_url(garage),
            "description": truncate(garage.description, 300),
            "telephone": garage.phone,
            "email": garage.email,
            "image": absolute_url(garage.photo.url)
            if garage.photo
            else absolute_url("/static/logo.jpg"),
            "address": address if len(address) > 2 else None,
            "areaServed": garage.city.name if garage.city else "Cameroun",
            "openingHours": _opening_hours(garage),
            "priceRange": "FCFA",
        }
    )

    if garage.latitude and garage.longitude:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(garage.latitude),
            "longitude": float(garage.longitude),
        }

    services = [
        service.name for service in garage.services.all() if service.is_active
    ][:20]
    if services:
        data["makesOffer"] = [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": name}}
            for name in services
        ]

    return json_ld_script(data)


@register.simple_tag
def part_json_ld(part):
    """Fiche pièce : Product + Offer (prix, disponibilité, vendeur)."""
    url = _part_url(part)
    offer = _clean(
        {
            "@type": "Offer",
            "url": url,
            "price": int(part.price),
            "priceCurrency": "XAF",
            "availability": (
                "https://schema.org/InStock"
                if part.is_available
                else "https://schema.org/OutOfStock"
            ),
            "itemCondition": CONDITION_MAP.get(part.condition),
            "seller": {"@type": "Organization", "name": part.garage.name}
            if part.garage
            else None,
        }
    )
    data = _clean(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": part.name,
            "url": url,
            "description": truncate(part.description, 300),
            "image": absolute_url(part.photo.url)
            if part.photo
            else absolute_url("/static/logo.jpg"),
            "sku": part.reference_oem,
            "mpn": part.reference_fabricant,
            "category": part.category.name if part.category else "",
            "offers": offer,
        }
    )
    return json_ld_script(data)


@register.simple_tag
def breadcrumb_json_ld(*items):
    """Fil d'Ariane : paires (nom, chemin).

    Exemple d'utilisation :
        {% breadcrumb_json_ld "Accueil" "/" "Garages" "/garages/" %}
    """
    if len(items) % 2:
        raise template.TemplateSyntaxError(
            "breadcrumb_json_ld attend des paires (nom, chemin)"
        )

    elements = []
    for index in range(0, len(items), 2):
        elements.append(
            _clean(
                {
                    "@type": "ListItem",
                    "position": index // 2 + 1,
                    "name": items[index],
                    "item": absolute_url(items[index + 1]) if items[index + 1] else None,
                }
            )
        )

    return json_ld_script(
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": elements,
        }
    )