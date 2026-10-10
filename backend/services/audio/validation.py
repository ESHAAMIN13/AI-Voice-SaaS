"""Audio validation for voice samples (Phase 20).

V1 format is detected from the file content (ffprobe), not extension or MIME.
V2 the result is a plain object, so views and Celery tasks can both use it.
V3 external tools run with list arguments, a timeout and no shell.
V4 only simple silence/volume warnings (no machine learning).
V5 limits live in settings.py.
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

# ffprobe reports containers like "mov,mp4,m4a,3gp,3g2,mj2" or "matroska,webm"
ALLOWED_CONTAINERS = {"wav", "mp3", "ogg", "flac", "matroska", "webm", "mov", "mp4", "m4a"}

# Warning thresholds are rough guesses, not exact quality measurements
SILENCE_RATIO_WARN = 0.5
CLIP_DB = -0.3
QUIET_DB = -38.0
LOW_SAMPLE_RATE = 16000

UNREADABLE = "This file could not be read as audio. It may be corrupt or in an unsupported format."

_TIME_RE = re.compile(r"out_time=(\d+):(\d+):(\d+(?:\.\d+)?)")
_NUM = r"(-?(?:\d+(?:\.\d+)?|inf))"
_MEAN_RE = re.compile(r"mean_volume:\s*" + _NUM + r"\s*dB")
_MAX_RE = re.compile(r"max_volume:\s*" + _NUM + r"\s*dB")
_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_DURATION_RE = re.compile(r"silence_duration:\s*([\d.]+)")


class AudioToolError(Exception):
    """FFmpeg/ffprobe is missing or broken. A server problem, not the user's."""


@dataclass
class ValidationResult:
    errors: list = field(default_factory=list)  # safe, user-facing reasons
    warnings: list = field(default_factory=list)  # saved as validation notes
    metadata: dict = field(default_factory=dict)

    @property
    def ok(self):
        return not self.errors


def _run(cmd, timeout):
    """Run a command without a shell. Returns None if it times out."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AudioToolError(f"{cmd[0]} was not found. Is FFmpeg installed and on PATH?") from exc
    except subprocess.TimeoutExpired:
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _probe(path):
    cmd = [
        settings.FFPROBE_BIN, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ]
    proc = _run(cmd, settings.AUDIO_PROBE_TIMEOUT_SECONDS)
    if proc is None or proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return None


def _analyze(path):
    """Decode the whole audio once: real duration, volume and silence."""
    cmd = [
        settings.FFMPEG_BIN, "-v", "info", "-nostdin", "-nostats",
        "-progress", "pipe:1",
        "-i", str(path), "-map", "0:a:0",
        "-af", "silencedetect=noise=-40dB:d=1,volumedetect",
        "-f", "null", "-",
    ]
    proc = _run(cmd, settings.AUDIO_DECODE_TIMEOUT_SECONDS)
    if proc is None or proc.returncode != 0:
        return None

    decoded = None
    times = _TIME_RE.findall(proc.stdout)
    if times:
        hours, minutes, seconds = times[-1]
        decoded = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    mean = _MEAN_RE.search(proc.stderr)
    peak = _MAX_RE.search(proc.stderr)
    return {
        "duration": decoded,
        "mean_volume": _to_float(mean.group(1)) if mean else None,
        "max_volume": _to_float(peak.group(1)) if peak else None,
        "silence_starts": [float(x) for x in _SILENCE_START_RE.findall(proc.stderr)],
        "silence_durations": [float(x) for x in _SILENCE_DURATION_RE.findall(proc.stderr)],
    }


def _check_streams(info, result):
    """Return the first audio stream, or None after recording an error."""
    container = info.get("format", {}).get("format_name", "")
    if not ALLOWED_CONTAINERS.intersection(container.split(",")):
        result.errors.append("Unsupported audio format.")
        return None

    streams = info.get("streams", [])
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    # Cover art inside an MP3 shows up as a "video" stream; ignore it.
    video = [
        s for s in streams
        if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")
    ]
    if not audio:
        result.errors.append("No audio was found in this file.")
        return None
    if video:
        result.errors.append("Please upload an audio file, not a video.")
        return None

    result.metadata["container"] = container
    return audio[0]


def validate_audio_bytes(data):
    """Check a voice sample. Never raises for bad files, only for broken tools."""
    result = ValidationResult()
    result.metadata["size_bytes"] = len(data)

    if len(data) == 0:
        result.errors.append("The file is empty.")
        return result
    if len(data) > settings.VOICE_SAMPLE_MAX_BYTES:
        mb = settings.VOICE_SAMPLE_MAX_BYTES // (1024 * 1024)
        result.errors.append(f"File is too large. Maximum size is {mb} MB.")
        return result

    with tempfile.TemporaryDirectory() as tmp:
        # A fixed name without an extension: the user's filename is never used (V3)
        path = Path(tmp) / "sample.bin"
        path.write_bytes(data)

        info = _probe(path)
        if info is None:
            result.errors.append(UNREADABLE)
            return result

        audio = _check_streams(info, result)
        if audio is None:
            return result

        analysis = _analyze(path)

    if analysis is None:
        result.errors.append(UNREADABLE)
        return result

    probe_duration = _to_float(info.get("format", {}).get("duration"))
    duration = analysis["duration"] or probe_duration
    if not duration or duration <= 0:
        result.errors.append(UNREADABLE)
        return result

    result.metadata.update(
        {
            "codec": audio.get("codec_name"),
            "duration_sec": round(duration, 2),
            "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
            "channels": audio.get("channels"),
        }
    )

    tolerance = settings.VOICE_SAMPLE_DURATION_TOLERANCE
    minimum = settings.VOICE_SAMPLE_MIN_SECONDS
    maximum = settings.VOICE_SAMPLE_MAX_SECONDS
    if duration < minimum - tolerance:
        result.errors.append(f"Sample is too short. Please provide at least {minimum} seconds.")
    elif duration > maximum + tolerance:
        result.errors.append(f"Sample is too long. The maximum is {maximum} seconds.")
    if result.errors:
        return result

    # Warnings only: the sample is accepted, the notes are saved (V4)
    silent = sum(analysis["silence_durations"])
    if len(analysis["silence_starts"]) > len(analysis["silence_durations"]):
        silent += max(0.0, duration - analysis["silence_starts"][-1])
    if silent / duration > SILENCE_RATIO_WARN:
        result.warnings.append("More than half of the sample is silent.")

    peak = analysis["max_volume"]
    if peak is not None and peak >= CLIP_DB:
        result.warnings.append("The audio may be clipped (too loud), which can reduce quality.")

    mean = analysis["mean_volume"]
    if mean is not None and mean < QUIET_DB:
        result.warnings.append("The audio is very quiet. Try recording closer to the microphone.")

    if result.metadata["sample_rate"] and result.metadata["sample_rate"] < LOW_SAMPLE_RATE:
        result.warnings.append("Low sample rate. Voice quality may be reduced.")

    return result