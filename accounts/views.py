from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import CustomUserCreationForm, CustomLoginForm, UserProfileForm
from .decorators import get_redirect_url_for_role


def _safe_redirect(next_url, default='core:home'):
    """Validate next_url to prevent open redirects."""
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
        return next_url
    return default


class RegisterView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = CustomUserCreationForm()
        return render(request, 'public/pages/accounts/register.html', {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Welcome to AutoLink!'))
            return redirect(get_redirect_url_for_role(user))
        return render(request, 'public/pages/accounts/register.html', {'form': form})


class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = CustomLoginForm()
        return render(request, 'public/pages/accounts/login.html', {'form': form})

    def post(self, request):
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, _('Welcome back, %(name)s!') % {'name': user.display_name})
            
            # Check for safe next parameter (GET or POST)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
                return redirect(next_url)
            
            # Redirect based on role
            return redirect(get_redirect_url_for_role(user))
        return render(request, 'public/pages/accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, _('You have been logged out.'))
    return redirect('core:home')


@login_required
def profile_view(request):
    return render(request, 'dashboard/pages/client/profile.html', {'user': request.user})


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Profile updated successfully.'))
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'dashboard/pages/client/profile_edit.html', {'form': form})


@login_required
def client_dashboard_view(request):
    """Client dashboard - personal space."""
    from orders.models import Order, Cart
    from payments.models import Payment
    from vehicles.models import Vehicle
    from notifications.models import Notification
    
    context = {
        'recent_orders': Order.objects.filter(user=request.user).select_related('garage')[:5],
        'recent_payments': Payment.objects.filter(user=request.user).select_related('order')[:5],
        'vehicles': request.user.vehicles.select_related('brand', 'model')[:5],
        'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
        'total_orders': Order.objects.filter(user=request.user).count(),
        'total_payments': Payment.objects.filter(user=request.user).count(),
    }
    return render(request, 'dashboard/pages/client/dashboard.html', context)
