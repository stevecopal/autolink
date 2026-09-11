from django.urls import path

from . import views

app_name = "garages"

urlpatterns = [
    path("", views.garage_list_view, name="garage_list"),
    path("api/", views.garage_list_api, name="garage_list_api"),
    path(
        "api/search-suggestions/",
        views.garage_search_suggestions,
        name="garage_search_suggestions",
    ),
    path("creer/", views.garage_create_view, name="garage_create"),
    path("mes-garages/", views.garage_my_list_view, name="garage_my_list"),
    path("<uuid:garage_id>/modifier/", views.garage_edit_view, name="garage_edit"),
    path("<uuid:garage_id>/supprimer/", views.garage_delete_view, name="garage_delete"),
    path("mon-dashboard/", views.garage_dashboard_view, name="garage_dashboard"),
    path(
        "disponibilite/", views.garage_availability_toggle, name="garage_availability"
    ),
    path("services/", views.service_list_view, name="service_list"),
    path("services/ajouter/", views.service_create_view, name="service_create"),
    path(
        "services/<uuid:service_id>/modifier/",
        views.service_edit_view,
        name="service_edit",
    ),
    path(
        "services/<uuid:service_id>/supprimer/",
        views.service_delete_view,
        name="service_delete",
    ),
    path("<slug:slug>/", views.garage_detail_view, name="garage_detail"),
    path("<slug:slug>/api/", views.garage_detail_api, name="garage_detail_api"),
]
