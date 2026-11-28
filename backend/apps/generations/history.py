from rest_framework import serializers

from .models import Generation


class HistoryItemSerializer(serializers.ModelSerializer):
    """One row of the history list. The full text is not included (only a preview)."""

    voice_name = serializers.CharField(source="voice_name_snapshot", read_only=True)
    text_preview = serializers.SerializerMethodField()
    duration_sec = serializers.SerializerMethodField()
    has_audio = serializers.SerializerMethodField()

    class Meta:
        model = Generation
        fields = [
            "id", "voice_name", "language", "text_preview", "char_count", "status",
            "error_message", "created_at", "finished_at", "duration_sec", "has_audio",
        ]
        read_only_fields = fields

    def get_text_preview(self, obj):
        return obj.input_text[:100]

    def get_duration_sec(self, obj):
        audio = getattr(obj, "audio", None)  # None when there is no audio yet
        return audio.duration_sec if audio else None

    def get_has_audio(self, obj):
        return getattr(obj, "audio", None) is not None
