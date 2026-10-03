from django.urls import path

from plans import views

urlpatterns = [
    path("plans/", views.plans_collection, name="plans_collection"),
    path("plans/create/", views.create_plan, name="create_plan"),
    path("plans/import/", views.import_plan, name="import_new_plan"),
    path("plans/<str:plan_id>/", views.plan_detail, name="plan_detail"),
    path("plans/<str:plan_id>/update/", views.update_plan, name="update_plan"),
    path("plans/<str:plan_id>/delete/", views.delete_plan, name="delete_plan"),
    path("plans/<str:plan_id>/assets/", views.upload_asset, name="upload_asset"),
    path("plans/<str:plan_id>/versions/", views.list_versions, name="list_versions"),
    path("plans/<str:plan_id>/restore/", views.restore_version, name="restore_version"),
    path("plans/<str:plan_id>/export/", views.export_plan, name="export_plan"),
    path("plans/<str:plan_id>/import/", views.import_plan, name="import_plan"),
]
