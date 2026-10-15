import httpx
from django.conf import settings

from .base import TTSBusyError, TTSEngine, TTSError, TTSRejectedError


def _detail(res):
    try:
        detail = res.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    return detail if isinstance(detail, str) else "The request was rejected."


class HttpTTSEngine(TTSEngine):
    """Talks to the local AI service (ai-service/server.py)."""

    def generate(self, text, language, reference_wav):
        if not settings.AI_SERVICE_TOKEN:
            raise TTSError("AI_SERVICE_TOKEN is not configured.")
        try:
            res = httpx.post(
                f"{settings.AI_SERVICE_URL.rstrip('/')}/generate",
                data={"text": text, "language": language},
                files={"reference": ("reference.wav", reference_wav, "audio/wav")},
                headers={"X-AI-Token": settings.AI_SERVICE_TOKEN},
                timeout=settings.AI_SERVICE_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            # Only the error type is kept: never the URL, headers or token
            raise TTSError(f"AI service request failed: {type(exc).__name__}") from exc

        if res.status_code == 200:
            if not res.content:
                raise TTSError("AI service returned empty audio.")
            return res.content
        if res.status_code == 400:
            raise TTSRejectedError(_detail(res))
        if res.status_code == 503:
            raise TTSBusyError(_detail(res))
        raise TTSError(f"AI service returned status {res.status_code}")