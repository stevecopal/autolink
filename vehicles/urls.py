from django.urls import path
from . import views

app_name = 'vehicles'

urlpatterns = [
    path('', views.vehicle_list_view, name='vehicle_list'),
    path('ajouter/', views.vehicle_add_view, name='vehicle_add'),
    path('<uuid:pk>/modifier/', views.vehicle_edit_view, name='vehicle_edit'),
    path('<uuid:pk>/supprimer/', views.vehicle_delete_view, name='vehicle_delete'),
    path('<uuid:pk>/principal/', views.vehicle_set_primary_view, name='vehicle_set_primary'),
    path('api/marques/<uuid:brand_id>/modeles/', views.api_models_by_brand, name='api_models'),
]
