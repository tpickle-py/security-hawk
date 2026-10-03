from django.urls import path

from rules import views

urlpatterns = [
    path("rules/", views.list_or_create_rules),
    path("rules/<str:rule_id>/", views.rule_detail),
    path("rules/<str:rule_id>/test/", views.test_rule),
]
