from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('inscription/', views.RegisterView.as_view(), name='register'),
    path('connexion/', views.LoginView.as_view(), name='login'),
    path('deconnexion/', views.logout_view, name='logout'),
    path('profil/', views.profile_view, name='profile'),
    path('profil/modifier/', views.profile_edit_view, name='profile_edit'),
    path('dashboard/', views.client_dashboard_view, name='client_dashboard'),
    path('notifications/', views.notification_list_view, name='notifications'),
    path('notifications/<uuid:notification_id>/lire/', views.notification_mark_read_view, name='notification_mark_read'),
    path('notifications/tout-lire/', views.notification_mark_all_read_view, name='notification_mark_all_read'),
]
