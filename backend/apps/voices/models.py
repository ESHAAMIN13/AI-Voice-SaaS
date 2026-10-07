from django.conf import settings
from django.db import models

from config.models import BaseModel


class VoiceProfile(BaseModel):
    """A named voice owned by one user (e.g. 'My Voice', 'Podcast Voice')."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_profiles"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    # Safe, user-facing reason (e.g. "Sample is too short"). Never internal errors.
    status_message = models.CharField(max_length=255, blank=True)
    # Proof that the user confirmed they are allowed to clone this voice.
    consent_accepted_at = models.DateTimeField(null=True, blank=True)
    consent_version = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_voice_name_per_user"),
        ]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class VoiceSample(BaseModel):
    """Metadata of one audio file. The audio itself lives in Supabase Storage."""

    class Kind(models.TextChoices):
        ORIGINAL = "ORIGINAL", "Original upload"
        PROCESSED = "PROCESSED", "Processed for the AI model"

    voice_profile = models.ForeignKey(
        VoiceProfile, on_delete=models.CASCADE, related_name="samples"
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    storage_bucket = models.CharField(max_length=100, default="voice-samples")
    file_path = models.CharField(max_length=500)
    format = models.CharField(max_length=20)
    size_bytes = models.PositiveBigIntegerField()
    duration_sec = models.FloatField()
    sample_rate = models.PositiveIntegerField(null=True, blank=True)
    channels = models.PositiveSmallIntegerField(null=True, blank=True)
    validation_notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["voice_profile", "kind", "is_active"])]

    def __str__(self):
        return f"{self.kind} sample of {self.voice_profile_id}"