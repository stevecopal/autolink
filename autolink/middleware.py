import time
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class RateLimitMiddleware(MiddlewareMixin):
    """
    Per-IP rate limiting middleware.
    Limits POST requests to sensitive endpoints.
    """

    RATE_LIMITS = {
        '/compte/connexion/': 10,
        '/compte/inscription/': 5,
        '/panier/ajouter/': 30,
        '/paiement/': 10,
        '/api/notifications/': 30,
        '/tickets/': 10,
        '/assistance/': 5,
        '/favoris/': 20,
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
