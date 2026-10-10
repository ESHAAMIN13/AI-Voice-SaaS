import os
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from services.audio.validation import validate_audio_bytes

SINE = "sine=frequency=440:duration={seconds}"


def make_audio(input_args, suffix, output_args=()):
    """Create a real test file with ffmpeg and return its bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"fixture{suffix}"
        cmd = [settings.FFMPEG_BIN, "-v", "error", "-y", *input_args, *output_args, str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Could not create test audio: {proc.stderr.strip()[:200]}")
        return out.read_bytes()


def tone(seconds, suffix=".wav", extra=()):
    return make_audio(
        ["-f", "lavfi", "-i", SINE.format(seconds=seconds)],
        suffix,
        ["-ar", "24000", "-ac", "1", *extra],
    )


class ValidateAudioTests(SimpleTestCase):
    def assert_error(self, result, text):
        self.assertFalse(result.ok)
        self.assertTrue(any(text in e.lower() for e in result.errors), result.errors)

    def assert_warning(self, result, text):
        self.assertTrue(result.ok, result.errors)
        self.assertTrue(any(text in w.lower() for w in result.warnings), result.warnings)

    def test_valid_wav(self):
        result = validate_audio_bytes(tone(12))
        self.assertTrue(result.ok, result.errors)
        self.assertAlmostEqual(result.metadata["duration_sec"], 12, delta=0.5)
        self.assertEqual(result.metadata["sample_rate"], 24000)
        self.assertEqual(result.metadata["channels"], 1)
        self.assertEqual(result.warnings, [])

    def test_valid_webm_opus(self):
        result = validate_audio_bytes(tone(12, ".webm", ["-c:a", "libopus"]))
        self.assertTrue(result.ok, result.errors)
        self.assertAlmostEqual(result.metadata["duration_sec"], 12, delta=0.5)

    def test_too_short(self):
        self.assert_error(validate_audio_bytes(tone(3)), "too short")

    def test_too_long(self):
        self.assert_error(validate_audio_bytes(tone(70)), "too long")

    def test_empty_file(self):
        self.assert_error(validate_audio_bytes(b""), "empty")

    def test_random_bytes(self):
        self.assert_error(validate_audio_bytes(os.urandom(5000)), "could not be read")

    def test_text_file_pretending_to_be_audio(self):
        self.assert_error(validate_audio_bytes(b"hello world " * 200), "could not be read")

    def test_silent_audio_warns(self):
        data = make_audio(["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "15"], ".wav")
        self.assert_warning(validate_audio_bytes(data), "silent")

    def test_quiet_audio_warns(self):
        self.assert_warning(validate_audio_bytes(tone(12, extra=["-af", "volume=-40dB"])), "quiet")

    def test_loud_audio_warns(self):
        self.assert_warning(validate_audio_bytes(tone(12, extra=["-af", "volume=30dB"])), "clipped")

    def test_video_is_rejected(self):
        data = make_audio(
            ["-f", "lavfi", "-i", "testsrc=duration=12:size=160x120:rate=10",
             "-f", "lavfi", "-i", SINE.format(seconds=12)],
            ".mp4",
            ["-c:v", "mpeg4", "-c:a", "aac"],
        )
        self.assert_error(validate_audio_bytes(data), "not a video")