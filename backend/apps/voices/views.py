from rest_framework import generics, status

from django.shortcuts import get_object_or_404

from config.responses import error_response, success_response
from .models import VoiceProfile
from .serializers import VoiceProfileSerializer
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from config.responses import error_response, success_response

from . import storage
from .models import VoiceProfile, VoiceSample
from .serializers import (
    VoiceProfileSerializer,
    VoiceSampleSerializer,
    VoiceSampleUploadSerializer,
)
from .upload import build_storage_path, clean_extension

logger = logging.getLogger(__name__)
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


class VoiceUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = "upload"  # U8

    def post(self, request, pk):
        # U1: only the owner's profile; anyone else gets 404
        profile = get_object_or_404(VoiceProfile, pk=pk, user=request.user)

        serializer = VoiceSampleUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        ext = clean_extension(f.name)
        path = build_storage_path(request.user.id, profile.id, ext)
        content_type = (f.content_type or "application/octet-stream").split(";")[0]

        try:
            storage.upload_bytes("voice-samples", path, f.read(), content_type)
        except storage.StorageError:
            logger.exception("Voice sample upload failed")
            return error_response(
                "Could not save the file. Please try again.",
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            # U4: only one active ORIGINAL sample per profile
            profile.samples.filter(kind=VoiceSample.Kind.ORIGINAL, is_active=True).update(
                is_active=False
            )
            sample = VoiceSample.objects.create(
                voice_profile=profile,
                kind=VoiceSample.Kind.ORIGINAL,
                storage_bucket="voice-samples",
                file_path=path,
                format=ext.lstrip("."),
                size_bytes=f.size,
                duration_sec=serializer.validated_data.get("duration_sec"),
            )
        # U7: profile status stays PENDING until validation (Phase 20-21)
        return success_response(VoiceSampleSerializer(sample).data, status=status.HTTP_201_CREATED)