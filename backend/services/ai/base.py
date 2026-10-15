from django.conf import settings


class TTSError(Exception):
    """Generation failed. The message is safe to log, not to show users."""


class TTSRejectedError(TTSError):
    """The request itself is not acceptable (language, text, reference)."""


class TTSBusyError(TTSError):
    """The AI service is loading or busy. Try again later."""


class TTSEngine:
    """Every voice engine (real or fake) has this one method."""

    def generate(self, text, language, reference_wav):
        """Return WAV bytes."""
        raise NotImplementedError


def check_request(text, language):
    """Validate a generation request in Django, before it is queued. Returns the cleaned text."""
    if language == "ur":
        raise TTSRejectedError("Urdu is not supported by the current voice model yet.")
    if language not in settings.TTS_LANGUAGES:
        raise TTSRejectedError("This language is not supported.")
    text = (text or "").strip()
    if not text:
        raise TTSRejectedError("Please enter some text.")
    if len(text) > settings.TTS_MAX_TEXT_CHARS:
        raise TTSRejectedError(
            f"Text is too long. The maximum is {settings.TTS_MAX_TEXT_CHARS} characters."
        )
    return text