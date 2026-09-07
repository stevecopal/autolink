from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('recherche/', views.search_view, name='search'),
    path('a-propos/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('politique-et-regles/', views.policy_view, name='policy'),
    path('api/neighborhoods/<int:city_id>/', views.neighborhoods_api, name='neighborhoods_api'),
]
