"""Turns a validated voice sample into the WAV format the AI model will use (Phase 21).

Only gentle processing: mono, fixed sample rate, loudness normalisation.
No noise removal or effects, because they can hurt voice-clone quality.
"""

import tempfile
from pathlib import Path

from django.conf import settings

from .validation import _run


class ProcessingError(Exception):
    """The file could not be converted. A safe message for logs, not for users."""


def process_audio_bytes(data):
    """Return WAV bytes (mono, PROCESSED_SAMPLE_RATE, 16-bit).

    Raises ProcessingError if conversion fails, AudioToolError if FFmpeg is missing.
    """
    rate = settings.PROCESSED_SAMPLE_RATE
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "input.bin"  # fixed names: the user's filename is never used
        dst = Path(tmp) / "processed.wav"
        src.write_bytes(data)

        cmd = [
            settings.FFMPEG_BIN, "-v", "error", "-nostdin", "-y",
            "-i", str(src), "-map", "0:a:0",
            "-af",
            f"aformat=channel_layouts=mono,"
            f"loudnorm=I={settings.PROCESSED_TARGET_LUFS}:TP=-1.5:LRA=11,"
            f"aresample={rate}",
            "-ar", str(rate), "-ac", str(settings.PROCESSED_CHANNELS),
            "-c:a", "pcm_s16le", "-f", "wav", str(dst),
        ]
        proc = _run(cmd, settings.AUDIO_DECODE_TIMEOUT_SECONDS)
        if proc is None:
            raise ProcessingError("FFmpeg timed out")
        if proc.returncode != 0:
            raise ProcessingError(f"FFmpeg failed: {proc.stderr[-300:]}")
        if not dst.exists() or dst.stat().st_size == 0:
            raise ProcessingError("FFmpeg produced no output")
        return dst.read_bytes()