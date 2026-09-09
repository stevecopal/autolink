from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _


def _add_error(request, message):
    try:
        messages.error(request, message)
    except MessageFailure:
        pass


def _is_account_active(user):
    """Check if user account is active (not suspended)."""
    return user.account_status == "ACTIVE"


def role_required(*roles):
    """
    Decorator that checks if a user has one of the specified roles.
    Superusers bypass all role checks.
    Usage: @role_required('CLIENT', 'ADMIN')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if not _is_account_active(request.user):
                _add_error(request, _("Votre compte a été suspendu."))
                return redirect("core:home")
            if request.user.is_superadmin:
                return view_func(request, *args, **kwargs)
            if request.user.role not in roles:
                _add_error(
                    request, _("Vous n'avez pas la permission d'accéder à cette page.")
                )
                return redirect("core:home")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(view_func):
    """Decorator that checks if user is an admin or superadmin."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not _is_account_active(request.user):
            _add_error(request, _("Votre compte a été suspendu."))
            return redirect("core:home")
        if not request.user.is_admin_or_above:
            _add_error(request, _("Accès administrateur requis."))
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def client_required(view_func):
    """Decorator that checks if user is a client (has at least one approved garage)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if not _is_account_active(request.user):
            _add_error(request, _("Votre compte a été suspendu."))
            return redirect("core:home")
        if not request.user.is_client_or_above:
            _add_error(request, _("Accès client requis."))
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    return wrapper


def get_redirect_url_for_role(user):
    """Returns the appropriate redirect URL based on user role."""
    if not user.is_authenticated:
        return settings.LOGIN_URL

    role_redirects = {
        "SUPERUSER": "/administration/dashboard/",
        "ADMIN": "/administration/dashboard/",
        "CLIENT": "/compte/dashboard/",
        "USER": "/compte/dashboard/",
    }
    return role_redirects.get(user.role, "/")
