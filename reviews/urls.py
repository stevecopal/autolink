from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('avis/', views.review_list_view, name='review_list'),
    path('avis/garage/', views.garage_reviews_view, name='garage_reviews'),
    path('avis/admin/', views.admin_reviews_view, name='admin_reviews'),
]
