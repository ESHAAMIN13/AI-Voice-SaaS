from unittest.mock import patch

from django.conf import settings

from apps.usage.models import UsageRecord
from apps.voices.storage import StorageError
from services.ai import FakeTTSEngine, TTSBusyError, TTSError

from . import runner
from .models import GeneratedAudio, Generation
from .tasks import generate_audio
from .tests import GenerationTestBase

DOWNLOAD = "apps.generations.runner.storage.download_bytes"
UPLOAD = "apps.generations.runner.storage.upload_bytes"
REMOVE = "apps.generations.runner.storage.remove_files"


class BrokenEngine:
    def __init__(self, exc):
        self.exc = exc

    def generate(self, text, language, reference_wav):
        raise self.exc


class RunnerTests(GenerationTestBase):
    def make_generation(self, voice=None, text="Hello world", language="en"):
        voice = voice or self.voice
        return Generation.objects.create(
            user=self.alice,
            voice_profile=voice,
            voice_name_snapshot=voice.name,
            language=language,
            input_text=text,
            char_count=len(text),
        )

    def test_success_saves_audio_usage_and_completes(self):
        generation = self.make_generation()
        engine = FakeTTSEngine()
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD) as upload:
            result = runner.run_generation(generation.id, engine=engine)
        self.assertEqual(result, "completed")
        generation.refresh_from_db()
        self.assertEqual(generation.status, "COMPLETED")
        self.assertIsNotNone(generation.started_at)
        self.assertIsNotNone(generation.finished_at)
        audio = GeneratedAudio.objects.get(generation=generation)
        self.assertEqual(audio.storage_bucket, "generated-audio")
        self.assertTrue(audio.file_path.startswith(f"{self.alice.id}/{generation.id}/"))
        usage = UsageRecord.objects.get(generation=generation)
        self.assertEqual(usage.unit_type, "CHARS")
        self.assertEqual(int(usage.amount), generation.char_count)
        self.assertEqual(engine.calls, [("Hello world", "en", 3)])
        self.assertEqual(upload.call_args[0][0], "generated-audio")

    def test_job_that_is_not_pending_is_skipped(self):
        generation = self.make_generation()
        Generation.objects.filter(pk=generation.pk).update(status="COMPLETED")
        with patch(DOWNLOAD) as download:
            self.assertEqual(runner.run_generation(generation.id, engine=FakeTTSEngine()), "skipped")
        download.assert_not_called()

    def test_running_the_same_job_twice_creates_one_result(self):
        generation = self.make_generation()
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD):
            first = runner.run_generation(generation.id, engine=FakeTTSEngine())
            second = runner.run_generation(generation.id, engine=FakeTTSEngine())
        self.assertEqual((first, second), ("completed", "skipped"))
        self.assertEqual(UsageRecord.objects.filter(generation=generation).count(), 1)
        self.assertEqual(GeneratedAudio.objects.filter(generation=generation).count(), 1)

    def test_deleted_voice_fails_safely_without_usage(self):
        generation = self.make_generation()
        self.voice.delete()
        result = runner.run_generation(generation.id, engine=FakeTTSEngine())
        self.assertEqual(result, "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.status, "FAILED")
        self.assertEqual(generation.error_message, runner.VOICE_GONE)
        self.assertFalse(UsageRecord.objects.exists())

    def test_voice_without_prepared_sample_fails(self):
        empty = self.make_voice(self.alice, name="Empty", sample=False)
        generation = self.make_generation(voice=empty)
        self.assertEqual(runner.run_generation(generation.id, engine=FakeTTSEngine()), "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.error_message, runner.VOICE_GONE)

    def test_engine_error_gives_safe_message_and_no_usage(self):
        generation = self.make_generation()
        engine = BrokenEngine(TTSError("internal detail http://secret-host:8001"))
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD) as upload:
            result = runner.run_generation(generation.id, engine=engine)
        self.assertEqual(result, "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.status, "FAILED")
        self.assertEqual(generation.error_message, runner.GENERIC_FAILURE)
        self.assertNotIn("secret-host", generation.error_message)
        upload.assert_not_called()
        self.assertFalse(UsageRecord.objects.exists())
        self.assertFalse(GeneratedAudio.objects.exists())

    def test_download_error_gives_safe_message(self):
        generation = self.make_generation()
        with patch(DOWNLOAD, side_effect=StorageError("signed-url-token-123")):
            result = runner.run_generation(generation.id, engine=FakeTTSEngine())
        self.assertEqual(result, "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.error_message, runner.GENERIC_FAILURE)
        self.assertNotIn("token", generation.error_message)

    def test_upload_error_fails_and_leaves_no_audio_row(self):
        generation = self.make_generation()
        with patch(DOWNLOAD, return_value=b"ref"), patch(
            UPLOAD, side_effect=StorageError("x")
        ), patch(REMOVE):
            result = runner.run_generation(generation.id, engine=FakeTTSEngine())
        self.assertEqual(result, "failed")
        self.assertFalse(GeneratedAudio.objects.exists())
        self.assertFalse(UsageRecord.objects.exists())

    def test_busy_service_puts_job_back_to_pending(self):
        generation = self.make_generation()
        engine = BrokenEngine(TTSBusyError("busy"))
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD):
            with self.assertRaises(TTSBusyError):
                runner.run_generation(generation.id, engine=engine)
        generation.refresh_from_db()
        self.assertEqual(generation.status, "PENDING")
        self.assertIsNone(generation.started_at)
        self.assertFalse(UsageRecord.objects.exists())


class TaskRetryTests(GenerationTestBase):
    def make_generation(self):
        return Generation.objects.create(
            user=self.alice,
            voice_profile=self.voice,
            voice_name_snapshot=self.voice.name,
            language="en",
            input_text="Hello",
            char_count=5,
        )

    def test_busy_service_is_retried(self):
        generation = self.make_generation()
        with patch("apps.generations.tasks.runner.run_generation", side_effect=TTSBusyError("b")):
            # Called directly (outside a worker), Celery re-raises the original error
            with self.assertRaises(TTSBusyError):
                generate_audio.run(str(generation.id))

    def test_after_the_last_retry_the_job_is_marked_failed(self):
        generation = self.make_generation()
        generate_audio.push_request(retries=settings.GENERATION_RETRY_MAX)
        try:
            with patch(
                "apps.generations.tasks.runner.run_generation", side_effect=TTSBusyError("b")
            ):
                result = generate_audio.run(str(generation.id))
        finally:
            generate_audio.pop_request()
        self.assertEqual(result, "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.status, "FAILED")
        self.assertEqual(generation.error_message, runner.BUSY_FAILURE)