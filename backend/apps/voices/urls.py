from django.urls import path

from .views import VoiceDetailView, VoiceListCreateView

urlpatterns = [
    path("voices/", VoiceListCreateView.as_view(), name="voice-list"),
    path("voices/<uuid:pk>/", VoiceDetailView.as_view(), name="voice-detail"),
]