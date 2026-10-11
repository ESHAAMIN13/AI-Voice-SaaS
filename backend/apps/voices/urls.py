from django.urls import path

from .views import VoiceDetailView, VoiceListCreateView, VoiceUploadView,VoiceSampleUrlView

urlpatterns = [
    path("voices/", VoiceListCreateView.as_view(), name="voice-list"),
    path("voices/<uuid:pk>/", VoiceDetailView.as_view(), name="voice-detail"),
    path("voices/<uuid:pk>/upload/", VoiceUploadView.as_view(), name="voice-upload"),
    path("voices/<uuid:pk>/sample-url/", VoiceSampleUrlView.as_view(), name="voice-sample-url"),
]