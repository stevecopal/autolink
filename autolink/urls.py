from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.defaults import page_not_found, server_error
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        "sw.js",
        TemplateView.as_view(template_name="sw.js", content_type="application/javascript"),
        name="sw.js",
    ),
    path('administration/', include('administration.urls')),
    path('', include('core.urls')),
    path('compte/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('garages/', include('garages.urls')),
    path('', include('catalog.urls')),
    path('', include('payments.urls')),
    path('', include('support.urls')),
    path('', include('search.urls')),
    path(
        "offline/",
        TemplateView.as_view(template_name="offline.html"),
        name="offline",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Pages d'erreur pour la production (DEBUG=False)
handler404 = page_not_found
handler500 = server_error

