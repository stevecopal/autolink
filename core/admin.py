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
    list_display = ['name']
    search_fields = ['name']

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