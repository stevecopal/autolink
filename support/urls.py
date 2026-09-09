from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('messages/', views.conversation_list_view, name='conversation_list'),
    path('messages/nouveau/', views.conversation_create_view, name='conversation_create'),
    path('messages/<uuid:conversation_id>/', views.conversation_detail_view, name='conversation_detail'),
    path('tickets/', views.ticket_list_view, name='ticket_list'),
    path('tickets/creer/', views.ticket_create_view, name='ticket_create'),
    path('tickets/<str:ticket_number>/', views.ticket_detail_view, name='ticket_detail'),
    path('assistance/', views.assistance_view, name='assistance'),
    path('assistance/confirmation/', views.assistance_confirm_view, name='assistance_confirm'),
]
