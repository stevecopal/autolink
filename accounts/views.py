from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View

from .decorators import get_redirect_url_for_role
from .forms import CustomLoginForm, CustomUserCreationForm, UserProfileForm
from .models import Notification

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
    messages.info(request, _("Vous avez ete deconnecte."))
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
            messages.success(request, _("Profil mis a jour avec succes."))
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, "dashboard/pages/client/profile_edit.html", {"form": form})


@login_required
def client_dashboard_view(request):
    """Dashboard utilisateur with financial metrics."""
    from garages.models import Garage
    from payments.models import Payment

    user_garages = Garage.objects.filter(owner=request.user).select_related(
        "city", "neighborhood"
    )

    total_paid = (
        Payment.objects.filter(
            user=request.user, status=Payment.Status.SUCCESS
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    active_garages = user_garages.filter(
        activation_status=Garage.ActivationStatus.ACTIVE
    ).count()
    pending_payment_garages = user_garages.filter(
        approval_status=Garage.ApprovalStatus.APPROVED,
        payment_status=Garage.PaymentStatus.UNPAID,
    ).count()

    notifications = Notification.objects.filter(user=request.user)[:10]
    unread_notifications = Notification.unread_count(request.user)

    context = {
        "recent_payments": Payment.objects.filter(user=request.user)[:5],
        "total_payments": Payment.objects.filter(user=request.user).count(),
        "total_paid": total_paid,
        "user_garages": user_garages,
        "active_garages": active_garages,
        "pending_payment_garages": pending_payment_garages,
        "has_approved_garage": user_garages.filter(
            verification_status="APPROVED"
        ).exists(),
        "notifications": notifications,
        "unread_notifications": unread_notifications,
    }
    return render(request, "dashboard/pages/client/dashboard.html", context)


@login_required
def notification_list_view(request):
    """Display all notifications for the user."""
    notifications = Notification.objects.filter(user=request.user)
    if request.GET.get("unread") == "1":
        notifications = notifications.filter(is_read=False)
    paginator_notifications = notifications[:50]
    return render(
        request,
        "dashboard/pages/client/notifications/list.html",
        {"notifications": paginator_notifications},
    )


@login_required
def notification_mark_read_view(request, notification_id):
    """Mark a notification as read."""
    try:
        notif = Notification.objects.get(pk=notification_id, user=request.user)
        notif.mark_as_read()
    except Notification.DoesNotExist:
        pass
    next_url = request.GET.get("next", request.META.get("HTTP_REFERER", "/"))
    return redirect(next_url)


@login_required
def notification_mark_all_read_view(request):
    """Mark all notifications as read."""
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
    return redirect("accounts:notifications")
