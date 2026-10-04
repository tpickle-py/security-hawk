from django.urls import path

from kiosk import views

urlpatterns = [
    path("kiosk/status/", views.kiosk_status, name="kiosk_status"),
]
