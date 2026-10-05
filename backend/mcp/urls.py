from django.urls import path

from mcp import views

urlpatterns = [
    path("rpc", views.rpc_endpoint),
    path("tools", views.list_tools),
    path("execute", views.execute_tool_view),
    path("status", views.status_view),
]
