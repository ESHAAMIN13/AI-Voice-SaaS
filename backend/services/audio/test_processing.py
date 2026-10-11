from django.test import SimpleTestCase

from .processing import ProcessingError, process_audio_bytes
from .test_validation import tone
from .validation import validate_audio_bytes


class ProcessingTests(SimpleTestCase):
    def test_output_is_mono_24k_16bit_wav_with_same_length(self):
        out = process_audio_bytes(tone(12))
        result = validate_audio_bytes(out)
        self.assertTrue(result.ok, result.errors)
        meta = result.metadata
        self.assertEqual(meta["sample_rate"], 24000)
        self.assertEqual(meta["channels"], 1)
        self.assertEqual(meta["codec"], "pcm_s16le")
        self.assertAlmostEqual(meta["duration_sec"], 12, delta=0.5)

    def test_garbage_raises_processing_error(self):
        with self.assertRaises(ProcessingError):
            process_audio_bytes(b"not audio " * 500)