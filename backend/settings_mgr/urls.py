from django.urls import path

from settings_mgr import views

urlpatterns = [
    path("settings/", views.get_or_update_settings),
    path("settings/register_ha_helpers/", views.register_ha_helpers),
]
