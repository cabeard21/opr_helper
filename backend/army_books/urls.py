from django.urls import path

from army_books import views

urlpatterns = [
    path("factions/", views.faction_list, name="faction-list"),
    path("factions/<int:faction_id>/units/", views.faction_units, name="faction-units"),
    path("units/<int:unit_id>/", views.unit_detail, name="unit-detail"),
    path("calc/ev/", views.calculate_ev_view, name="calc-ev"),
]
