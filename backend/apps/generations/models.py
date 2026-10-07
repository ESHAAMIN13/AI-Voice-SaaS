from django.conf import settings
from django.db import models

from config.models import BaseModel


class Generation(BaseModel):
    """One text-to-speech job: the request and its progress."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="generations"
    )
    # SET_NULL keeps history if the voice profile is deleted later.
    voice_profile = models.ForeignKey(
        "voices.VoiceProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generations",
    )
    voice_name_snapshot = models.CharField(max_length=100)
    language = models.CharField(max_length=10)  # "en", "hi", "ur"... validated in code
    input_text = models.TextField()
    char_count = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    # Safe message for the user. Technical details go to server logs only.
    error_message = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Generation {self.id} [{self.status}]"


class GeneratedAudio(BaseModel):
    """Metadata of the audio file produced by a completed Generation."""

    generation = models.OneToOneField(
        Generation, on_delete=models.CASCADE, related_name="audio"
    )
    storage_bucket = models.CharField(max_length=100, default="generated-audio")
    file_path = models.CharField(max_length=500)
    format = models.CharField(max_length=20, default="wav")
    size_bytes = models.PositiveBigIntegerField()
    duration_sec = models.FloatField(null=True, blank=True)
    sample_rate = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Audio of {self.generation_id}"