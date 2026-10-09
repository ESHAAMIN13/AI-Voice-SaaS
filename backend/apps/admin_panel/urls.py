from django.urls import path

from .views import AdminPingView

urlpatterns = [
    path("admin/ping/", AdminPingView.as_view(), name="admin-ping"),
]