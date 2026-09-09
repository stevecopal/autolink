import time
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import gettext_lazy as _


class AccountStatusMiddleware(MiddlewareMixin):
    """
    Middleware that blocks suspended users from accessing the site.
    Superusers are never blocked.
    """

    EXEMPT_PATHS = [
        '/accounts/logout/',
        '/accounts/google/',
        '/admin/',
        '/static/',
        '/media/',
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None

        if request.user.is_superuser:
            return None

        if request.user.account_status != 'ACTIVE':
            for path in self.EXEMPT_PATHS:
                if request.path.startswith(path):
                    return None

            if request.headers.get('Accept') == 'application/json':
                return JsonResponse(
                    {'error': 'Votre compte a été suspendu.'},
                    status=403,
                )

            messages.error(request, _('Votre compte a été suspendu. Contactez l\'administrateur.'))
            return redirect('core:home')

        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Per-IP rate limiting middleware.
    Limits POST requests to sensitive endpoints.
    """

    RATE_LIMITS = {
        '/compte/connexion/': 10,
        '/compte/inscription/': 5,
        '/paiement/': 10,
        '/tickets/': 10,
        '/assistance/': 5,
    }

    def process_request(self, request):
        if request.method != 'POST':
            return None

        ip = self._get_client_ip(request)
        path = request.path

        for prefix, limit in self.RATE_LIMITS.items():
            if path.startswith(prefix):
                cache_key = f'ratelimit:{ip}:{prefix}'
                count = cache.get(cache_key, 0)
                if count >= limit:
                    return JsonResponse(
                        {'error': 'Too many requests. Please try again later.'},
                        status=429,
                    )
                cache.set(cache_key, count + 1, 60)
                break

        return None

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add additional security headers."""

    def process_response(self, request, response):
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
