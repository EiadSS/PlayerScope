from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("search/<str:query>", views.search, name="search"),
    path("profile/<str:name>", views.profile, name="profile"),
    path("profile-by-id/<str:player_id>", views.profile_by_id, name="profile-by-id"),
    path("stats/<str:player_id>", views.stats, name="stats"),
    path("injuries/<str:player_id>", views.injuries, name="injuries"),
    path("value/<str:player_id>", views.value, name="value"),
    path("transfers/<str:player_id>", views.transfers, name="transfers"),
    path("analytics/<str:player_id>", views.analytics, name="analytics"),
    path("compare/<str:left_player_id>/<str:right_player_id>", views.compare, name="compare"),
]