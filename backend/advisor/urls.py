from django.urls import path

from advisor import views

urlpatterns = [
    path("", views.advisor_status, name="advisor-status"),
    path("suggest/", views.suggest_army_list, name="advisor-suggest"),
]
