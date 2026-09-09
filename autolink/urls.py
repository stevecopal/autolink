from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('administration/', include('administration.urls')),
    path('', include('core.urls')),
    path('compte/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('garages/', include('garages.urls')),
    path('', include('catalog.urls')),
    path('', include('payments.urls')),
    path('', include('reviews.urls')),
    path('', include('support.urls')),
    path('', include('search.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
