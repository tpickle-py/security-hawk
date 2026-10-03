from django.urls import path

from ha import views

urlpatterns = [
    path("areas/", views.list_areas, name="list_areas"),
    path("entities/", views.search_entities, name="search_entities"),
    path(
        "entities/lookup/",
        views.lookup_entity_by_friendly_name,
        name="lookup_entity_by_friendly_name",
    ),
    path(
        "entities/<str:entity_id>/area/", views.designate_entity_area, name="designate_entity_area"
    ),
    path("entities/<str:entity_id>/", views.get_entity, name="get_entity"),
    path("camera/<str:entity_id>/", views.camera_snapshot, name="camera_snapshot"),
]
