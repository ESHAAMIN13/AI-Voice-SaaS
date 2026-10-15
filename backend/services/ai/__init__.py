from .base import TTSBusyError, TTSEngine, TTSError, TTSRejectedError, check_request
from .fake_engine import FakeTTSEngine
from .http_engine import HttpTTSEngine


def get_engine():
    """The one place that decides which engine is used. Swap it here to change the model."""
    return HttpTTSEngine()