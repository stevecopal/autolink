from django.contrib import admin
from .models import Category, Part, PartPhoto


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'is_active', 'order']
    list_filter = ['is_active', 'parent']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_status', 'condition', 'seller', 'is_active']
    list_filter = ['stock_status', 'condition', 'category', 'is_active']
    search_fields = ['name', 'reference_oem', 'reference_fabricant', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_views']


@admin.register(PartPhoto)
class PartPhotoAdmin(admin.ModelAdmin):
    list_display = ['part', 'is_primary', 'created_at']
