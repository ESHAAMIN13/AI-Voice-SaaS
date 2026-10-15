import io
import math
import struct
import wave

from .base import TTSEngine


class FakeTTSEngine(TTSEngine):
    """Returns a valid 1-second WAV instantly. Used in tests (no model, no waiting)."""

    def __init__(self):
        self.calls = []

    def generate(self, text, language, reference_wav):
        self.calls.append((text, language, len(reference_wav)))
        rate = 24000
        frames = b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate)))
            for i in range(rate)
        )
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(frames)
        return buffer.getvalue()