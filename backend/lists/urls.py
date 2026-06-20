from django.urls import path

from lists import views

urlpatterns = [
    path("lists/", views.army_lists, name="army-lists"),
    path("lists/<int:list_id>/analysis/", views.army_list_analysis, name="army-list-analysis"),
    path("lists/<int:list_id>/export/army-forge/", views.army_list_army_forge_export, name="army-list-army-forge-export"),
    path("lists/<int:list_id>/", views.army_list_detail, name="army-list-detail"),
    path("lists/<int:list_id>/units/", views.add_list_unit, name="add-list-unit"),
    path(
        "lists/<int:list_id>/units/<int:list_unit_id>/",
        views.remove_list_unit,
        name="remove-list-unit",
    ),
]
