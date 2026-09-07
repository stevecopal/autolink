from django.contrib import admin
from .models import Category, Part, PartPhoto, Compatibility, PartRequest


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order']
    list_filter = ['is_active', 'parent']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'brand', 'price', 'stock_status', 'condition', 'seller', 'is_active']
    list_filter = ['stock_status', 'condition', 'category', 'brand', 'is_active']
    search_fields = ['name', 'reference_oem', 'reference_fabricant', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_views']


@admin.register(PartPhoto)
class PartPhotoAdmin(admin.ModelAdmin):
    list_display = ['part', 'is_primary', 'created_at']


@admin.register(Compatibility)
class CompatibilityAdmin(admin.ModelAdmin):
    list_display = ['part', 'brand', 'model_vehicle', 'year_min', 'year_max', 'status']
    list_filter = ['status', 'brand']


@admin.register(PartRequest)
class PartRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'part_name', 'city', 'urgency', 'is_active', 'created_at']
    list_filter = ['urgency', 'is_active', 'city']
