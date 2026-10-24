from rest_framework import serializers

from apps.voices.models import VoiceProfile, VoiceSample
from services.ai import TTSRejectedError, check_request

from .models import Generation


class GenerationCreateSerializer(serializers.Serializer):
    voice_profile = serializers.UUIDField()
    language = serializers.CharField(max_length=10)
    text = serializers.CharField(max_length=5000)  # the real limit is in check_request

    def validate(self, attrs):
        user = self.context["request"].user

        # N-3: language and text rules run on the server, not only in the frontend
        try:
            attrs["text"] = check_request(attrs["text"], attrs["language"])
        except TTSRejectedError as exc:
            raise serializers.ValidationError(str(exc))

        # N-2: own profile only. Someone else's profile gets the same message as a missing one.
        profile = VoiceProfile.objects.filter(pk=attrs["voice_profile"], user=user).first()
        if profile is None:
            raise serializers.ValidationError("Voice profile not found.")
        if profile.status != VoiceProfile.Status.APPROVED:
            raise serializers.ValidationError(
                "This voice profile is not ready yet. Upload a voice sample first."
            )
        has_sample = profile.samples.filter(
            kind=VoiceSample.Kind.PROCESSED, is_active=True
        ).exists()
        if not has_sample:
            raise serializers.ValidationError("This voice profile has no prepared sample yet.")

        attrs["profile"] = profile
        return attrs

    def create(self, validated_data):
        profile = validated_data["profile"]
        text = validated_data["text"]
        # N-4: status, user, error_message are set here, never taken from the client
        return Generation.objects.create(
            user=self.context["request"].user,
            voice_profile=profile,
            voice_name_snapshot=profile.name,
            language=validated_data["language"],
            input_text=text,
            char_count=len(text),
        )


class GenerationListSerializer(serializers.ModelSerializer):
    voice_name = serializers.CharField(source="voice_name_snapshot", read_only=True)
    text_preview = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "id", "voice_name", "language", "text_preview", "char_count",
            "status", "error_message", "created_at", "finished_at",
        ]
        read_only_fields = fields

    def get_text_preview(self, obj):
        return obj.input_text[:100]


class GenerationDetailSerializer(serializers.ModelSerializer):
    voice_name = serializers.CharField(source="voice_name_snapshot", read_only=True)

    class Meta:
        model = Generation
        fields = [
            "id", "voice_name", "language", "input_text", "char_count", "status",
            "error_message", "created_at", "started_at", "finished_at",
        ]
        read_only_fields = fields


class GenerationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Generation
        fields = ["id", "status", "error_message", "started_at", "finished_at"]
        read_only_fields = fields