from django.contrib import admin
from .models import Brand, ModelVehicle, Vehicle


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ModelVehicle)
class ModelVehicleAdmin(admin.ModelAdmin):
    list_display = ['brand', 'name', 'year_start', 'year_end', 'is_active']
    list_filter = ['brand', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['user', 'brand', 'model', 'year', 'is_primary']
    list_filter = ['brand', 'fuel_type', 'transmission', 'is_primary']
    search_fields = ['user__username', 'license_plate', 'vin']
