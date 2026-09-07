# core/views/about.py
"""
Core about page view — kept separate to keep the monolith small.
"""
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse


def about_view(request: HttpRequest) -> HttpResponse:
    """Render the public about page."""
    return render(request, "public/pages/about.html")
