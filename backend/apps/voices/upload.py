import uuid
from pathlib import PurePath

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # U2

# extension -> allowed content types (U3). Real content check comes in Phase 20.
ALLOWED = {
    ".wav": {"audio/wav", "audio/x-wav", "audio/wave"},
    ".mp3": {"audio/mpeg", "audio/mp3"},
    ".m4a": {"audio/mp4", "audio/x-m4a", "audio/m4a"},
    ".mp4": {"audio/mp4", "video/mp4"},
    ".webm": {"audio/webm", "video/webm"},
    ".ogg": {"audio/ogg", "application/ogg"},
    ".flac": {"audio/flac", "audio/x-flac"},
}


def clean_extension(filename):
    return PurePath(filename or "").suffix.lower()


def build_storage_path(user_id, profile_id, ext):
    # U5: the client's filename is never used in the path
    return f"{user_id}/{profile_id}/{uuid.uuid4()}{ext}"