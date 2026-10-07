from django.conf import settings
from django.db import models

from config.models import BaseModel


class UsageRecord(BaseModel):
    """How much a user consumed. Plans and credits will build on this later."""

    class UnitType(models.TextChoices):
        CHARS = "CHARS", "Characters"
        SECONDS = "SECONDS", "Seconds of audio"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_records"
    )
    generation = models.ForeignKey(
        "generations.Generation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_records",
    )
    unit_type = models.CharField(max_length=10, choices=UnitType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user_id}: {self.amount} {self.unit_type}"