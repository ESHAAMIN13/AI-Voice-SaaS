from django.urls import path

from .views import GenerationDetailView, GenerationListCreateView, GenerationStatusView

urlpatterns = [
    path("generations/", GenerationListCreateView.as_view(), name="generation-list"),
    path("generations/<uuid:pk>/", GenerationDetailView.as_view(), name="generation-detail"),
    path(
        "generations/<uuid:pk>/status/", GenerationStatusView.as_view(), name="generation-status"
    ),
]