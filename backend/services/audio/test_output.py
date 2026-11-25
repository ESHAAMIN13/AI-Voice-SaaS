import io
import wave

from django.test import SimpleTestCase, override_settings

from .output import OutputAudioError, convert_output_wav
from .test_validation import make_audio


def float_wav(seconds=3):
    """Like the AI service output: a 32-bit float WAV."""
    return make_audio(
        ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=24000:duration={seconds}",
         "-c:a", "pcm_f32le"],
        ".wav",
    )


def read_wav(data):
    with wave.open(io.BytesIO(data)) as w:
        return w.getsampwidth(), w.getnchannels(), w.getframerate(), w.getnframes() / w.getframerate()


class ConvertOutputTests(SimpleTestCase):
    def test_float_wav_becomes_16_bit_mono_24k(self):
        source = float_wav(3)
        out, meta = convert_output_wav(source)
        width, channels, rate, seconds = read_wav(out)
        self.assertEqual((width, channels, rate), (2, 1, 24000))
        self.assertAlmostEqual(seconds, 3, delta=0.2)
        self.assertEqual(meta["sample_rate"], 24000)
        self.assertAlmostEqual(meta["duration_sec"], 3, delta=0.2)
        self.assertLess(len(out), len(source))

    def test_stereo_44k_becomes_mono_24k(self):
        source = make_audio(
            ["-f", "lavfi", "-i", "sine=frequency=330:sample_rate=44100:duration=2", "-ac", "2"],
            ".wav",
        )
        out, _ = convert_output_wav(source)
        width, channels, rate, _ = read_wav(out)
        self.assertEqual((width, channels, rate), (2, 1, 24000))

    def test_converting_twice_is_harmless(self):
        once, _ = convert_output_wav(float_wav(2))
        twice, meta = convert_output_wav(once)
        self.assertEqual(read_wav(twice)[:3], (2, 1, 24000))
        self.assertAlmostEqual(meta["duration_sec"], 2, delta=0.2)

    def test_garbage_is_rejected(self):
        with self.assertRaises(OutputAudioError):
            convert_output_wav(b"not audio " * 500)

    def test_empty_is_rejected(self):
        with self.assertRaises(OutputAudioError):
            convert_output_wav(b"")

    @override_settings(GENERATED_AUDIO_MAX_BYTES=100)
    def test_too_large_is_rejected(self):
        with self.assertRaises(OutputAudioError):
            convert_output_wav(float_wav(2))
