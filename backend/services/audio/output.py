"""Prepares generated audio for storage and playback (Phase 30).

The AI service returns a 32-bit float WAV. We convert it to 16-bit mono PCM, which every
browser plays, and we measure the real duration instead of guessing it.
"""

import tempfile
from pathlib import Path

from django.conf import settings

from .validation import _probe, _run, _to_float


class OutputAudioError(Exception):
    """The generated audio could not be prepared. Safe for logs, not for users."""


def convert_output_wav(data):
    """Return (wav_bytes, {"duration_sec": ..., "sample_rate": ...}).

    Raises OutputAudioError for bad or oversized audio, and AudioToolError if FFmpeg is missing.
    """
    if not data:
        raise OutputAudioError("The engine returned no audio")
    rate = settings.GENERATED_AUDIO_SAMPLE_RATE

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "engine_output.bin"  # fixed names, nothing user-controlled
        dst = Path(tmp) / "output.wav"
        src.write_bytes(data)

        cmd = [
            settings.FFMPEG_BIN, "-v", "error", "-nostdin", "-y",
            "-i", str(src), "-map", "0:a:0",
            "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", "-f", "wav", str(dst),
        ]
        proc = _run(cmd, settings.AUDIO_DECODE_TIMEOUT_SECONDS)
        if proc is None:
            raise OutputAudioError("FFmpeg timed out")
        if proc.returncode != 0:
            raise OutputAudioError(f"FFmpeg failed: {proc.stderr[-300:]}")
        if not dst.exists() or dst.stat().st_size == 0:
            raise OutputAudioError("FFmpeg produced no output")
        out = dst.read_bytes()
        info = _probe(dst)  # must happen before the temporary folder is deleted

    if len(out) > settings.GENERATED_AUDIO_MAX_BYTES:
        raise OutputAudioError("The generated audio is too large")

    duration = _to_float((info or {}).get("format", {}).get("duration"))
    if not duration or duration <= 0:
        raise OutputAudioError("Could not measure the audio length")
    streams = [s for s in (info or {}).get("streams", []) if s.get("codec_type") == "audio"]
    measured_rate = int(streams[0]["sample_rate"]) if streams and streams[0].get("sample_rate") else rate
    return out, {"duration_sec": round(duration, 2), "sample_rate": measured_rate}
