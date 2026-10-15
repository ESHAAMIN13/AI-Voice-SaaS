import io
import wave
from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase, override_settings

from .base import TTSBusyError, TTSError, TTSRejectedError, check_request
from .fake_engine import FakeTTSEngine
from .http_engine import HttpTTSEngine

POST = "services.ai.http_engine.httpx.post"


def response(status, content=b"", json=None):
    r = Mock()
    r.status_code = status
    r.content = content
    if json is None:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json
    return r


@override_settings(AI_SERVICE_TOKEN="secret-test-token", AI_SERVICE_URL="http://ai.test")
class HttpEngineTests(SimpleTestCase):
    def gen(self):
        return HttpTTSEngine().generate("Hello", "en", b"ref")

    def test_success_returns_audio_and_sends_token(self):
        with patch(POST, return_value=response(200, b"WAVDATA")) as post:
            self.assertEqual(self.gen(), b"WAVDATA")
        self.assertEqual(post.call_args.args[0], "http://ai.test/generate")
        self.assertEqual(post.call_args.kwargs["headers"]["X-AI-Token"], "secret-test-token")

    def test_400_is_rejected_with_service_message(self):
        with patch(POST, return_value=response(400, json={"detail": "Text is too long."})):
            with self.assertRaises(TTSRejectedError) as ctx:
                self.gen()
        self.assertIn("too long", str(ctx.exception))

    def test_503_is_busy(self):
        with patch(POST, return_value=response(503, json={"detail": "Busy."})):
            with self.assertRaises(TTSBusyError):
                self.gen()

    def test_401_is_generic_error_without_token_in_message(self):
        with patch(POST, return_value=response(401, json={"detail": "Unauthorized."})):
            with self.assertRaises(TTSError) as ctx:
                self.gen()
        self.assertNotIn("secret-test-token", str(ctx.exception))

    def test_500_is_generic_error(self):
        with patch(POST, return_value=response(500)):
            with self.assertRaises(TTSError):
                self.gen()

    def test_connection_error_is_tts_error_without_secrets(self):
        with patch(POST, side_effect=httpx.ConnectError("boom")):
            with self.assertRaises(TTSError) as ctx:
                self.gen()
        self.assertIn("ConnectError", str(ctx.exception))
        self.assertNotIn("secret-test-token", str(ctx.exception))

    def test_empty_audio_is_error(self):
        with patch(POST, return_value=response(200, b"")):
            with self.assertRaises(TTSError):
                self.gen()

    @override_settings(AI_SERVICE_TOKEN="")
    def test_missing_token_never_calls_the_service(self):
        with patch(POST) as post:
            with self.assertRaises(TTSError):
                self.gen()
        post.assert_not_called()


@override_settings(TTS_MAX_TEXT_CHARS=200, TTS_LANGUAGES=("en", "hi"))
class CheckRequestTests(SimpleTestCase):
    def test_urdu_is_rejected_with_a_clear_message(self):
        with self.assertRaises(TTSRejectedError) as ctx:
            check_request("hello", "ur")
        self.assertIn("Urdu", str(ctx.exception))

    def test_unknown_language_is_rejected(self):
        with self.assertRaises(TTSRejectedError):
            check_request("hello", "fr")

    def test_empty_text_is_rejected(self):
        with self.assertRaises(TTSRejectedError):
            check_request("   ", "en")

    def test_too_long_text_is_rejected(self):
        with self.assertRaises(TTSRejectedError):
            check_request("a" * 201, "en")

    def test_text_is_trimmed(self):
        self.assertEqual(check_request("  hello  ", "hi"), "hello")


class FakeEngineTests(SimpleTestCase):
    def test_returns_a_valid_wav_and_records_the_call(self):
        engine = FakeTTSEngine()
        data = engine.generate("hello", "en", b"ref")
        with wave.open(io.BytesIO(data)) as w:
            self.assertEqual(w.getframerate(), 24000)
            self.assertEqual(w.getnchannels(), 1)
        self.assertEqual(engine.calls, [("hello", "en", 3)])