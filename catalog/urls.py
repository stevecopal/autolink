from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('pieces/', views.part_list_view, name='part_list'),
    path('pieces/<slug:slug>/', views.part_detail_view, name='part_detail'),
    path('categories/<slug:slug>/', views.category_detail_view, name='category_detail'),

    # Garage Marketplace
    path('garage/produits/', views.garage_product_list_view, name='garage_products'),
    path('garage/produits/ajouter/', views.garage_product_add_view, name='garage_product_add'),
    path('garage/produits/<uuid:pk>/modifier/', views.garage_product_edit_view, name='garage_product_edit'),
    path('garage/produits/<uuid:pk>/supprimer/', views.garage_product_delete_view, name='garage_product_delete'),
    path('garage/produits/<uuid:pk>/stock/', views.garage_stock_update_view, name='garage_stock_update'),
    path('garage/produits/<uuid:pk>/toggle/', views.garage_product_toggle_view, name='garage_product_toggle'),
]
