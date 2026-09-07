from django.contrib import admin
from .models import Garage, GarageService, GaragePhoto, GarageVerification, GarageBrand


@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'city', 'neighborhood', 'verification_status', 'trust_score', 'is_active']
    list_filter = ['verification_status', 'is_active', 'city', 'is_featured']
    search_fields = ['name', 'owner__username', 'phone', 'city']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['trust_score', 'total_reviews', 'total_orders', 'total_clients']


@admin.register(GarageService)
class GarageServiceAdmin(admin.ModelAdmin):
    list_display = ['garage', 'name', 'category', 'price_min', 'price_max', 'is_active']
    list_filter = ['category', 'is_active']


@admin.register(GaragePhoto)
class GaragePhotoAdmin(admin.ModelAdmin):
    list_display = ['garage', 'is_primary', 'created_at']


@admin.register(GarageVerification)
class GarageVerificationAdmin(admin.ModelAdmin):
    list_display = ['garage', 'document_type', 'is_verified', 'verified_by', 'created_at']
    list_filter = ['document_type', 'is_verified']


@admin.register(GarageBrand)
class GarageBrandAdmin(admin.ModelAdmin):
    list_display = ['garage', 'brand']
