# core/views/search_form.py
"""
Core search form handling — separated to keep views tidy.
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db.models import Q

from garages.models import Garage
from catalog.models import Part


def search_view(request: HttpRequest) -> HttpResponse:
    """Render a simple search page that queries garages and parts."""
    query = request.GET.get("q", "")
    results = {"garages": [], "parts": []}

    if query:
        results["garages"] = Garage.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(services__name__icontains=query),
            is_active=True,
        ).distinct()[:10]

        results["parts"] = Part.objects.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(reference_oem__icontains=query),
            is_active=True,
        ).distinct()[:10]

    return render(
        request,
        "public/pages/parts/search.html",
        {"query": query, "results": results},
    )
