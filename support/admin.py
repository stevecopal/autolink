from django.contrib import admin
from .models import Ticket, TicketMessage, AssistanceRequest


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'user', 'garage', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['ticket_number', 'user__username', 'subject', 'description']
    readonly_fields = ['ticket_number', 'created_at', 'updated_at', 'resolved_at']
    raw_id_fields = ['user', 'part', 'garage', 'assigned_to']


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'sender', 'is_internal', 'created_at']
    list_filter = ['is_internal']


@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'issue_type', 'status', 'assigned_garage', 'created_at']
    list_filter = ['issue_type', 'status']
