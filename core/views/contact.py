# core/views/contact.py
"""
Core contact view — split from monolith to keep it easy to maintain.
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib import messages


def contact_view(request: HttpRequest) -> HttpResponse:
    """Render the public contact page and handle simple POST feedback."""
    if request.method == "POST":
        messages.success(
            request, "Votre message a été envoyé. Nous vous répondrons rapidement."
        )
        return render(request, "public/pages/contact.html", {"sent": True})
    return render(request, "public/pages/contact.html")
