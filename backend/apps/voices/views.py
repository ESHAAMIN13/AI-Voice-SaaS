import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from config.responses import error_response, success_response
from services.audio.validation import AudioToolError, validate_audio_bytes

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
        data = f.read()

        # V7: check the real audio content BEFORE anything is stored
        try:
            result = validate_audio_bytes(data)
        except AudioToolError:
            logger.exception("Audio tools are not working")  # V11
            return error_response(
                "Audio checking is temporarily unavailable. Please try again later.",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not result.ok:
            self._mark_rejected(profile, result.errors[0])  # V9
            return error_response(
                result.errors[0], errors=result.errors, status=status.HTTP_400_BAD_REQUEST
            )

        ext = clean_extension(f.name)
        path = build_storage_path(request.user.id, profile.id, ext)
        content_type = (f.content_type or "application/octet-stream").split(";")[0]

        try:
            storage.upload_bytes("voice-samples", path, data, content_type)
        except storage.StorageError:
            logger.exception("Voice sample upload failed")
            return error_response(
                "Could not save the file. Please try again.",
                status=status.HTTP_502_BAD_GATEWAY,
            )

        meta = result.metadata
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
                size_bytes=len(data),
                # V8: measured by us, never taken from the client
                duration_sec=meta["duration_sec"],
                sample_rate=meta.get("sample_rate"),
                channels=meta.get("channels"),
                validation_notes="\n".join(result.warnings),
            )
            # V10: a valid sample puts the profile back to PENDING (Phase 21 approves it)
            profile.status = VoiceProfile.Status.PENDING
            profile.status_message = ""
            profile.save(update_fields=["status", "status_message", "updated_at"])

        return success_response(VoiceSampleSerializer(sample).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _mark_rejected(profile, reason):
        """V9: a bad upload must never damage a profile that already has a good sample."""
        has_good_sample = profile.samples.filter(
            kind=VoiceSample.Kind.ORIGINAL, is_active=True
        ).exists()
        if not has_good_sample:
            profile.status = VoiceProfile.Status.REJECTED
            profile.status_message = reason[:255]
            profile.save(update_fields=["status", "status_message", "updated_at"])