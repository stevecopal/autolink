from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.contrib import messages

from core.forms import ContactForm


def contact_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Votre message a été envoyé avec succès. Nous vous répondrons rapidement."
            )
            return render(request, "public/pages/contact.html", {"sent": True})
    else:
        initial = {}
        if request.user.is_authenticated:
            initial['name'] = request.user.get_full_name() or request.user.username
            initial['email'] = request.user.email
            initial['phone'] = getattr(request.user, 'phone', '')
        form = ContactForm(initial=initial)
    return render(request, "public/pages/contact.html", {"form": form})
