
from django.utils import timezone
from rest_framework import serializers

from .models import VoiceProfile

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