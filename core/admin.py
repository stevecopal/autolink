from django.contrib import admin
from .models import ContactMessage, City, Neighborhood,Testimonial


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'phone', 'subject', 'message', 'created_at']

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'region', 'latitude', 'longitude', 'is_active', 'created_at']
    list_filter = ['is_active', 'region']
    search_fields = ['name', 'region']
    list_editable = ['latitude', 'longitude', 'is_active']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'region', 'is_active')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('wide',),
        }),
    )

@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ['name', 'city']
    search_fields = ['name']
    list_filter = ['city']

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name' ,'role', 'city', 'rating', 'is_published', 'created_at']
    list_filter = ['role', 'is_published', 'created_at']
    search_fields = ['name', 'quote']
    readonly_fields = ['created_at']