from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('a-proximite/', views.nearby_page_view, name='nearby_page'),
    path('api/nearby/', views.nearby_search_api, name='nearby_api'),
    path('api/nearby/search/', views.nearby_search_post_api, name='nearby_search_api'),
]
