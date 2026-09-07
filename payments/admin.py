from django.contrib import admin
from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['idempotency_key', 'order', 'user', 'amount', 'provider', 'status', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['idempotency_key', 'provider_transaction_id', 'user__username']
    readonly_fields = ['idempotency_key', 'provider_transaction_id']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['payment', 'order', 'user', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'order__order_number']
