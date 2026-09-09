from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View

from .decorators import get_redirect_url_for_role
from .forms import CustomLoginForm, CustomUserCreationForm, UserProfileForm

BACKEND = "django.contrib.auth.backends.ModelBackend"


def _safe_redirect(next_url, default="core:home"):
    """Validate next_url to prevent open redirects."""
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
        return next_url
    return default


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("core:home")
        form = CustomUserCreationForm()
        return render(request, "public/pages/accounts/register.html", {"form": form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend=BACKEND)
            messages.success(request, _("Bienvenue sur AutoLink !"))
            return redirect(get_redirect_url_for_role(user))
        return render(request, "public/pages/accounts/register.html", {"form": form})


class LoginView(View):
    def get(self, request):
        form = CustomLoginForm()
        return render(request, "public/pages/accounts/login.html", {"form": form})

    def post(self, request):
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend=BACKEND)
            messages.success(
                request, _("Bienvenue, %(name)s !") % {"name": user.display_name}
            )

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts=None
            ):
                return redirect(next_url)

            return redirect(get_redirect_url_for_role(user))
        return render(request, "public/pages/accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, _("Vous avez été déconnecté."))
    return redirect("core:home")


@login_required
def profile_view(request):
    return render(
        request, "dashboard/pages/client/profile.html", {"user": request.user}
    )


@login_required
def profile_edit_view(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profil mis à jour avec succès."))
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, "dashboard/pages/client/profile_edit.html", {"form": form})


@login_required
def client_dashboard_view(request):
    """Dashboard utilisateur — espace personnel."""
    from garages.models import Garage
    from payments.models import Payment

    user_garages = Garage.objects.filter(owner=request.user).select_related(
        "city", "neighborhood"
    )

    context = {
        "recent_payments": Payment.objects.filter(user=request.user)[:5],
        "total_payments": Payment.objects.filter(user=request.user).count(),
        "user_garages": user_garages,
        "has_approved_garage": user_garages.filter(
            verification_status="APPROVED"
        ).exists(),
    }
    return render(request, "dashboard/pages/client/dashboard.html", context)
