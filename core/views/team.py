# core/views/team.py
"""
Core team-specific views (split from the monolith for maintainability).
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib import messages


def contact_view(request: HttpRequest) -> HttpResponse:
    """Contact page with simple POST handling."""
    if request.method == "POST":
        messages.success(
            request, "Votre message a été envoyé. Nous vous répondrons rapidement."
        )
        return render(request, "public/pages/contact.html", {"sent": True})
    return render(request, "public/pages/contact.html")
