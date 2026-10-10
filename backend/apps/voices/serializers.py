from django.utils import timezone
from rest_framework import serializers

from .models import VoiceProfile, VoiceSample
from .upload import ALLOWED, MAX_UPLOAD_BYTES, clean_extension

CONSENT_VERSION = "v1"


class VoiceProfileSerializer(serializers.ModelSerializer):
    """Read: safe fields only. Write: only name and description (V3)."""

    # Only used on create (V2). Never returned.
    consent = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = VoiceProfile
        fields = [
            "id",
            "name",
            "description",
            "status",
            "status_message",
            "consent_accepted_at",
            "consent_version",
            "created_at",
            "updated_at",
            "consent",
        ]
        read_only_fields = [
            "id",
            "status",
            "status_message",
            "consent_accepted_at",
            "consent_version",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        user = self.context["request"].user
        qs = VoiceProfile.objects.filter(user=user, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a voice profile with this name.")
        return value

    def validate(self, attrs):
        # Consent is required only when creating (V2)
        if self.instance is None and attrs.get("consent") is not True:
            raise serializers.ValidationError(
                {"consent": "You must confirm you have the right to clone this voice."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("consent", None)
        return VoiceProfile.objects.create(
            user=self.context["request"].user,
            consent_accepted_at=timezone.now(),
            consent_version=CONSENT_VERSION,
            **validated_data,
        )

    def update(self, instance, validated_data):
        validated_data.pop("consent", None)  # consent cannot be changed later
        return super().update(instance, validated_data)


class VoiceSampleUploadSerializer(serializers.Serializer):
    """Cheap first checks. The real content check is audio validation (Phase 20).

    A client-sent duration is deliberately NOT accepted: we measure it ourselves.
    """

    file = serializers.FileField()

    def validate_file(self, f):
        if f.size == 0:
            raise serializers.ValidationError("The file is empty.")
        if f.size > MAX_UPLOAD_BYTES:
            mb = MAX_UPLOAD_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f"File is too large. Maximum size is {mb} MB.")
        ext = clean_extension(f.name)
        if ext not in ALLOWED:
            raise serializers.ValidationError("Unsupported file type.")
        base_type = (f.content_type or "").split(";")[0].strip().lower()
        if base_type not in ALLOWED[ext]:
            raise serializers.ValidationError("File type does not match its extension.")
        return f


class VoiceSampleSerializer(serializers.ModelSerializer):
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = VoiceSample
        fields = [
            "id",
            "kind",
            "format",
            "size_bytes",
            "duration_sec",
            "sample_rate",
            "channels",
            "warnings",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields

    def get_warnings(self, obj):
        return [line for line in obj.validation_notes.splitlines() if line.strip()]