from django.contrib import admin
from .models import Review, Favorite


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'review_type', 'garage', 'part', 'rating', 'is_verified', 'is_hidden', 'created_at']
    list_filter = ['review_type', 'rating', 'is_verified', 'is_hidden']
    search_fields = ['user__username', 'title', 'comment']
    readonly_fields = ['created_at']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'object_type', 'garage', 'part', 'created_at']
    list_filter = ['object_type']
