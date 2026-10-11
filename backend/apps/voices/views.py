import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from config.responses import error_response, success_response
from services.audio.processing import ProcessingError, process_audio_bytes
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
        profile = self.get_object()
        files = [(s.storage_bucket, s.file_path) for s in profile.samples.all()]
        profile.delete()
        storage.remove_files(files)  # S-1, S-3
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

        # P4: convert to the model format BEFORE anything is stored
        try:
            processed = process_audio_bytes(data)
        except AudioToolError:
            logger.exception("Audio tools are not working")
            return error_response(
                "Audio processing is temporarily unavailable. Please try again later.",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProcessingError:
            logger.exception("Audio processing failed")
            self._mark_failed(profile)
            return error_response(
                "We could not prepare this audio. Please try a different file.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = clean_extension(f.name)
        path = build_storage_path(request.user.id, profile.id, ext)
        content_type = (f.content_type or "application/octet-stream").split(";")[0]
        processed_path = build_storage_path(request.user.id, profile.id, ".wav").replace(
            f"{profile.id}/", f"{profile.id}/processed/", 1
        )  # P6

        try:
            storage.upload_bytes("voice-samples", path, data, content_type)
            storage.upload_bytes("voice-samples", processed_path, processed, "audio/wav")
        except storage.StorageError:
            logger.exception("Voice sample upload failed")
            return error_response(
                "Could not save the file. Please try again.",
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # S-2: remember the files that are about to be replaced
        old_files = [
            (s.storage_bucket, s.file_path) for s in profile.samples.filter(is_active=True)
        ]

        meta = result.metadata
        with transaction.atomic():
            # U4: one active ORIGINAL and one active PROCESSED sample per profile
            profile.samples.filter(is_active=True).update(is_active=False)
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
            VoiceSample.objects.create(
                voice_profile=profile,
                kind=VoiceSample.Kind.PROCESSED,
                storage_bucket="voice-samples",
                file_path=processed_path,
                format="wav",
                size_bytes=len(processed),
                duration_sec=meta["duration_sec"],
                sample_rate=settings.PROCESSED_SAMPLE_RATE,
                channels=settings.PROCESSED_CHANNELS,
            )
            # P5: a successfully processed sample approves the profile
            profile.status = VoiceProfile.Status.APPROVED
            profile.status_message = ""
            profile.save(update_fields=["status", "status_message", "updated_at"])

        storage.remove_files(old_files)  # S-2: replaced files are removed
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

    @staticmethod
    def _mark_failed(profile):
        """A processing failure must not damage a profile that already has a good sample."""
        if not profile.samples.filter(kind=VoiceSample.Kind.ORIGINAL, is_active=True).exists():
            profile.status = VoiceProfile.Status.FAILED
            profile.status_message = "We could not prepare this audio."
            profile.save(update_fields=["status", "status_message", "updated_at"])


class VoiceSampleUrlView(APIView):
    """S-4: a 60-second link to listen to the prepared sample. Owner only."""

    def get(self, request, pk):
        profile = get_object_or_404(VoiceProfile, pk=pk, user=request.user)
        sample = profile.samples.filter(kind=VoiceSample.Kind.PROCESSED, is_active=True).first()
        if sample is None:
            return error_response("No prepared sample yet.", status=status.HTTP_404_NOT_FOUND)
        try:
            url = storage.signed_url(sample.storage_bucket, sample.file_path, expires_in=60)
        except storage.StorageError:
            logger.exception("Could not sign sample URL")
            return error_response(
                "Could not load the sample. Please try again.",
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return success_response({"url": url, "expires_in": 60})