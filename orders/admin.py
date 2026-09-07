from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'updated_at']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'part', 'quantity']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'garage', 'status', 'total', 'fulfillment_type', 'created_at']
    list_filter = ['status', 'fulfillment_type', 'created_at']
    search_fields = ['order_number', 'user__username', 'garage__name']
    readonly_fields = ['order_number', 'pickup_code']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'part_name', 'part_price', 'quantity', 'subtotal']
