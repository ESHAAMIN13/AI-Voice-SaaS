from rest_framework import generics, status

from config.responses import success_response

from .models import VoiceProfile
from .serializers import VoiceProfileSerializer


class OwnedVoiceMixin:
    """V1: every query is limited to the logged-in user's own profiles."""

    serializer_class = VoiceProfileSerializer

    def get_queryset(self):
        return VoiceProfile.objects.filter(user=self.request.user)


class VoiceListCreateView(OwnedVoiceMixin, generics.ListCreateAPIView):
    pagination_class = None  # V6

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, status=status.HTTP_201_CREATED)


class VoiceDetailView(OwnedVoiceMixin, generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "patch", "delete", "head", "options"]  # no PUT

    def retrieve(self, request, *args, **kwargs):
        return success_response(self.get_serializer(self.get_object()).data)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        # V5: DB row only for now; storage files are handled in Phase 22
        self.get_object().delete()
        return success_response({"detail": "Voice profile deleted."})