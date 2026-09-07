from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.conf import settings


def role_required(*roles):
    """
    Decorator that checks if a user has one of the specified roles.
    Usage: @role_required('CLIENT', 'ADMIN')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if request.user.role not in roles:
                messages.error(request, _('Vous n\'avez pas la permission d\'accéder à cette page.'))
                return redirect('core:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Decorator that checks if user is an admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if request.user.role != 'ADMIN':
            messages.error(request, _('Accès administrateur requis.'))
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def client_required(view_func):
    """Decorator that checks if user is a client (has at least one approved garage)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)
        if request.user.role != 'CLIENT':
            messages.error(request, _('Accès client requis.'))
            return redirect('core:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_redirect_url_for_role(user):
    """Returns the appropriate redirect URL based on user role."""
    if not user.is_authenticated:
        return settings.LOGIN_URL

    role_redirects = {
        'ADMIN': '/administration/dashboard/',
        'CLIENT': '/compte/dashboard/',
        'USER': '/compte/dashboard/',
    }
    return role_redirects.get(user.role, '/')
