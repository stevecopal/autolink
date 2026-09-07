from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('panier/', views.cart_view, name='cart'),
    path('panier/ajouter/<int:part_id>/', views.cart_add_view, name='cart_add'),
    path('panier/supprimer/<int:item_id>/', views.cart_remove_view, name='cart_remove'),
    path('panier/modifier/<int:item_id>/', views.cart_update_view, name='cart_update'),
    path('commander/', views.checkout_view, name='checkout'),
    path('commandes/', views.order_list_view, name='order_list'),
    path('commandes/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('commandes/<str:order_number>/annuler/', views.order_cancel_view, name='order_cancel'),
]
