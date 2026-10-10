from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from services.audio.test_validation import make_audio, tone
from services.audio.validation import AudioToolError

from .models import VoiceProfile, VoiceSample

User = get_user_model()
STORAGE = "apps.voices.views.storage.upload_bytes"


def audio_file(data, name="sample.wav"):
    return SimpleUploadedFile(name, data, content_type="audio/wav")


class VoiceUploadValidationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.good = tone(12)
        cls.short = tone(3)
        cls.silent = make_audio(
            ["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "15"], ".wav"
        )

    def setUp(self):
        cache.clear()  # reset throttle counters
        self.user = User.objects.create_user(email="owner@example.com", password="Str0ng-pass-123")
        self.profile = VoiceProfile.objects.create(
            user=self.user, name="My Voice", consent_accepted_at=timezone.now(), consent_version="v1"
        )
        self.url = reverse("voice-upload", args=[self.profile.id])
        self.client.force_authenticate(user=self.user)

    def upload(self, data, **extra):
        return self.client.post(self.url, {"file": audio_file(data), **extra}, format="multipart")

    def test_valid_upload_saves_measured_metadata(self):
        with patch(STORAGE) as storage_mock:
            res = self.upload(self.good)
        self.assertEqual(res.status_code, 201, res.json())
        body = res.json()["data"]
        self.assertAlmostEqual(body["duration_sec"], 12, delta=0.5)
        self.assertEqual(body["sample_rate"], 24000)
        self.assertEqual(body["warnings"], [])
        storage_mock.assert_called_once()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, VoiceProfile.Status.PENDING)

    def test_client_duration_is_ignored(self):
        with patch(STORAGE):
            res = self.upload(self.good, duration_sec="30")
        self.assertEqual(res.status_code, 201, res.json())
        sample = VoiceSample.objects.get(voice_profile=self.profile)
        self.assertAlmostEqual(sample.duration_sec, 12, delta=0.5)

    def test_too_short_is_rejected_before_storage(self):
        with patch(STORAGE) as storage_mock:
            res = self.upload(self.short)
        self.assertEqual(res.status_code, 400)
        body = res.json()
        self.assertFalse(body["success"])
        self.assertIn("too short", body["message"].lower())
        storage_mock.assert_not_called()
        self.assertFalse(VoiceSample.objects.filter(voice_profile=self.profile).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, VoiceProfile.Status.REJECTED)
        self.assertIn("too short", self.profile.status_message.lower())

    def test_fake_audio_is_rejected_before_storage(self):
        with patch(STORAGE) as storage_mock:
            res = self.upload(b"this is not audio " * 300)
        self.assertEqual(res.status_code, 400)
        storage_mock.assert_not_called()

    def test_bad_upload_keeps_an_existing_good_sample(self):
        with patch(STORAGE):
            self.assertEqual(self.upload(self.good).status_code, 201)
        with patch(STORAGE) as storage_mock:
            res = self.upload(self.short)
        self.assertEqual(res.status_code, 400)
        storage_mock.assert_not_called()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, VoiceProfile.Status.PENDING)
        self.assertEqual(self.profile.samples.filter(is_active=True).count(), 1)

    def test_good_upload_after_rejection_clears_the_message(self):
        with patch(STORAGE):
            self.upload(self.short)
            res = self.upload(self.good)
        self.assertEqual(res.status_code, 201, res.json())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, VoiceProfile.Status.PENDING)
        self.assertEqual(self.profile.status_message, "")

    def test_warnings_are_saved_and_returned(self):
        with patch(STORAGE):
            res = self.upload(self.silent)
        self.assertEqual(res.status_code, 201, res.json())
        warnings = res.json()["data"]["warnings"]
        self.assertTrue(any("silent" in w.lower() for w in warnings), warnings)
        sample = VoiceSample.objects.get(voice_profile=self.profile)
        self.assertIn("silent", sample.validation_notes.lower())

    def test_other_users_profile_returns_404(self):
        other = User.objects.create_user(email="other@example.com", password="Str0ng-pass-123")
        self.client.force_authenticate(user=other)
        with patch(STORAGE) as storage_mock:
            res = self.upload(self.good)
        self.assertEqual(res.status_code, 404)
        storage_mock.assert_not_called()

    def test_broken_audio_tools_return_503(self):
        with patch("apps.voices.views.validate_audio_bytes", side_effect=AudioToolError("x")):
            with patch(STORAGE) as storage_mock:
                res = self.upload(self.good)
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.json()["success"])
        storage_mock.assert_not_called()