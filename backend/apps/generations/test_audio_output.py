import io
import wave
from unittest.mock import patch

from apps.usage.models import UsageRecord
from services.ai import FakeTTSEngine
from services.audio.output import OutputAudioError

from . import runner
from .files import remove_generation_files
from .models import GeneratedAudio, Generation
from .tests import GenerationTestBase

DOWNLOAD = "apps.generations.runner.storage.download_bytes"
UPLOAD = "apps.generations.runner.storage.upload_bytes"
REMOVE = "apps.generations.runner.storage.remove_files"


class OutputAudioRunnerTests(GenerationTestBase):
    def make_generation(self):
        return Generation.objects.create(
            user=self.alice,
            voice_profile=self.voice,
            voice_name_snapshot=self.voice.name,
            language="en",
            input_text="Hello world",
            char_count=11,
        )

    def run_ok(self):
        generation = self.make_generation()
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD) as upload:
            result = runner.run_generation(generation.id, engine=FakeTTSEngine())
        return generation, upload, result

    def test_stored_audio_is_16_bit_mono_24k(self):
        _, upload, result = self.run_ok()
        self.assertEqual(result, "completed")
        stored = upload.call_args[0][2]
        with wave.open(io.BytesIO(stored)) as w:
            self.assertEqual((w.getsampwidth(), w.getnchannels(), w.getframerate()), (2, 1, 24000))

    def test_real_duration_and_rate_are_saved(self):
        generation, upload, _ = self.run_ok()
        audio = GeneratedAudio.objects.get(generation=generation)
        self.assertAlmostEqual(audio.duration_sec, 1.0, delta=0.2)
        self.assertEqual(audio.sample_rate, 24000)
        self.assertEqual(audio.size_bytes, len(upload.call_args[0][2]))

    def test_usage_has_characters_and_seconds(self):
        generation, _, _ = self.run_ok()
        chars = UsageRecord.objects.get(generation=generation, unit_type="CHARS")
        seconds = UsageRecord.objects.get(generation=generation, unit_type="SECONDS")
        self.assertEqual(int(chars.amount), 11)
        self.assertAlmostEqual(float(seconds.amount), 1.0, delta=0.2)

    def test_conversion_failure_fails_safely_and_stores_nothing(self):
        generation = self.make_generation()
        with patch(DOWNLOAD, return_value=b"ref"), patch(UPLOAD) as upload, patch(
            "apps.generations.runner.convert_output_wav",
            side_effect=OutputAudioError("ffmpeg said /secret/path"),
        ):
            result = runner.run_generation(generation.id, engine=FakeTTSEngine())
        self.assertEqual(result, "failed")
        generation.refresh_from_db()
        self.assertEqual(generation.error_message, runner.GENERIC_FAILURE)
        self.assertNotIn("secret", generation.error_message)
        upload.assert_not_called()
        self.assertFalse(GeneratedAudio.objects.exists())
        self.assertFalse(UsageRecord.objects.exists())

    def test_remove_generation_files(self):
        generation, _, _ = self.run_ok()
        with patch(REMOVE) as remove:
            self.assertEqual(remove_generation_files(generation), 1)
        audio = GeneratedAudio.objects.get(generation=generation)
        remove.assert_called_once_with([(audio.storage_bucket, audio.file_path)])

    def test_remove_generation_files_without_audio_does_nothing(self):
        generation = self.make_generation()
        with patch(REMOVE) as remove:
            self.assertEqual(remove_generation_files(generation), 0)
        remove.assert_not_called()
