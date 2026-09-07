from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('avis/', views.review_list_view, name='review_list'),
    path('avis/ajouter/', views.review_create_view, name='review_create'),
    path('favoris/', views.favorite_list_view, name='favorite_list'),
    path('favoris/toggle/', views.favorite_toggle_view, name='favorite_toggle'),
]
