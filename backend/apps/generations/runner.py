"""The work of one generation job (Phase 28).

No Celery in this file, so it is easy to test. The task in tasks.py only calls it.
"""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.usage.models import UsageRecord
from apps.voices import storage
from apps.voices.models import VoiceSample
from services.ai import TTSBusyError, get_engine

from .models import GeneratedAudio, Generation

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "We could not create the audio. Please try again."
VOICE_GONE = "This voice is no longer available."
BUSY_FAILURE = "The voice service is busy. Please try again in a few minutes."


def claim(generation_id):
    """W-3: PENDING -> PROCESSING in one step. Only one worker can win this."""
    now = timezone.now()
    updated = Generation.objects.filter(
        pk=generation_id, status=Generation.Status.PENDING
    ).update(status=Generation.Status.PROCESSING, started_at=now, updated_at=now)
    return updated == 1


def release(generation_id):
    """Put a claimed job back to PENDING (used before a retry)."""
    Generation.objects.filter(pk=generation_id, status=Generation.Status.PROCESSING).update(
        status=Generation.Status.PENDING, started_at=None, updated_at=timezone.now()
    )


def mark_failed(generation_id, message, from_statuses=(Generation.Status.PROCESSING,)):
    now = timezone.now()
    return Generation.objects.filter(pk=generation_id, status__in=from_statuses).update(
        status=Generation.Status.FAILED,
        error_message=message[:255],
        finished_at=now,
        updated_at=now,
    )


def run_generation(generation_id, engine=None):
    """Returns "completed", "failed" or "skipped". Raises TTSBusyError only when the job
    was put back to PENDING and may be retried."""
    if not claim(generation_id):
        return "skipped"  # already running, done, or failed

    generation = Generation.objects.select_related("voice_profile", "user").get(pk=generation_id)
    bucket = settings.GENERATED_AUDIO_BUCKET
    path = None
    try:
        profile = generation.voice_profile  # None if the voice was deleted (N-9)
        sample = None
        if profile is not None:
            sample = profile.samples.filter(
                kind=VoiceSample.Kind.PROCESSED, is_active=True
            ).first()
        if sample is None:
            mark_failed(generation_id, VOICE_GONE)
            return "failed"

        reference = storage.download_bytes(sample.storage_bucket, sample.file_path)
        wav = (engine or get_engine()).generate(
            generation.input_text, generation.language, reference
        )

        path = f"{generation.user_id}/{generation.id}/{uuid.uuid4()}.wav"
        storage.upload_bytes(bucket, path, wav, "audio/wav")

        with transaction.atomic():
            GeneratedAudio.objects.create(
                generation=generation,
                storage_bucket=bucket,
                file_path=path,
                format="wav",
                size_bytes=len(wav),
            )
            now = timezone.now()
            Generation.objects.filter(pk=generation_id).update(
                status=Generation.Status.COMPLETED,
                error_message="",
                finished_at=now,
                updated_at=now,
            )
            # W-5: usage counts only for a finished generation
            UsageRecord.objects.create(
                user=generation.user,
                generation=generation,
                unit_type=UsageRecord.UnitType.CHARS,
                amount=generation.char_count,
            )
        return "completed"
    except TTSBusyError:
        release(generation_id)
        raise
    except Exception:
        # Details go to the server log only. The user gets a safe message (W-6).
        logger.exception("Generation %s failed", generation_id)
        if path:
            storage.remove_files([(bucket, path)])  # no half-finished file is left behind
        mark_failed(generation_id, GENERIC_FAILURE)
        return "failed"