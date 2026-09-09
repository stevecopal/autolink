from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserActivity, Notification


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'phone', 'city', 'role', 'account_status', 'is_verified', 'is_active']
    list_filter = ['role', 'account_status', 'is_verified', 'is_active', 'city']
    search_fields = ['username', 'email', 'phone', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        ('AutoLink', {
            'fields': ('role', 'account_status', 'phone', 'phone_verified', 'email_verified',
                       'city', 'neighborhood', 'address', 'latitude', 'longitude',
                       'whatsapp', 'is_verified', 'avatar')
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['user', 'action', 'ip_address', 'user_agent', 'details', 'created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notif_type', 'title', 'is_read', 'created_at']
    list_filter = ['notif_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['user', 'notif_type', 'title', 'message', 'link', 'metadata', 'created_at']
