from django.contrib import admin
from .models import Payment, Receipt


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['idempotency_key', 'user', 'amount', 'provider', 'status', 'created_at']
    list_filter = ['status', 'provider', 'created_at']
    search_fields = ['idempotency_key', 'provider_transaction_id', 'user__username']
    readonly_fields = ['idempotency_key', 'provider_reference']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['reference', 'payment', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['reference', 'payment__idempotency_key']
