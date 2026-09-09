from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('panier/', views.cart_view, name='cart'),
    path('panier/ajouter/<uuid:part_id>/', views.cart_add_view, name='cart_add'),
    path('panier/supprimer/<uuid:item_id>/', views.cart_remove_view, name='cart_remove'),
    path('panier/modifier/<uuid:item_id>/', views.cart_update_view, name='cart_update'),
    path('commander/', views.checkout_view, name='checkout'),
    path('commander/<uuid:part_id>/', views.direct_order_view, name='direct_order'),
    path('commandes/', views.order_list_view, name='order_list'),
    path('commandes/garage/', views.garage_orders_view, name='garage_orders'),
    path('commandes/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('commandes/<str:order_number>/confirmer/', views.order_confirm_view, name='order_confirm'),
    path('commandes/<str:order_number>/pret/', views.order_mark_ready_view, name='order_mark_ready'),
    path('commandes/<str:order_number>/livrer/', views.order_mark_delivered_view, name='order_mark_delivered'),
    path('commandes/<str:order_number>/recevoir/', views.order_confirm_receipt_view, name='order_confirm_receipt'),
    path('commandes/<str:order_number>/annuler/', views.order_cancel_view, name='order_cancel'),
]
