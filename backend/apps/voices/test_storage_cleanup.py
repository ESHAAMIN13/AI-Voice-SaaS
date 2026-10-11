from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from services.audio.test_validation import tone

from . import storage
from .models import VoiceSample
from .tests import VoiceTestBase

UPLOAD = "apps.voices.views.storage.upload_bytes"
REMOVE = "apps.voices.views.storage.remove_files"


class StorageCleanupTests(VoiceTestBase):
    @classmethod
    def setUpTestData(cls):
        cls.good_audio = tone(12)

    def setUp(self):
        super().setUp()
        self.login_as(self.alice)
        self.voice_id = self.create_voice("Alice Voice").json()["data"]["id"]
        self.upload_url = reverse("voice-upload", args=[self.voice_id])

    def upload(self):
        f = SimpleUploadedFile("a.wav", self.good_audio, content_type="audio/wav")
        return self.client.post(self.upload_url, {"file": f}, format="multipart")

    def test_delete_profile_removes_both_files(self):
        with patch(UPLOAD), patch(REMOVE):
            self.assertEqual(self.upload().status_code, 201)
        with patch(REMOVE) as remove:
            res = self.client.delete(reverse("voice-detail", args=[self.voice_id]))
        self.assertEqual(res.status_code, 200)
        files = remove.call_args[0][0]
        self.assertEqual(len(files), 2)
        self.assertTrue(any("/processed/" in p for _, p in files))

    def test_new_upload_removes_replaced_files(self):
        with patch(UPLOAD), patch(REMOVE):
            self.upload()
        with patch(UPLOAD), patch(REMOVE) as remove:
            self.assertEqual(self.upload().status_code, 201)
        self.assertEqual(len(remove.call_args[0][0]), 2)

    def test_remove_files_never_raises_and_logs_orphan(self):
        with patch("apps.voices.storage.delete_object", side_effect=storage.StorageError("x")):
            with self.assertLogs("apps.voices.storage", level="ERROR") as logs:
                storage.remove_files([("voice-samples", "u/p/f.wav")])
        self.assertIn("ORPHAN", logs.output[0])

    def test_sample_url_for_owner(self):
        with patch(UPLOAD), patch(REMOVE):
            self.upload()
        url = reverse("voice-sample-url", args=[self.voice_id])
        with patch("apps.voices.views.storage.signed_url", return_value="https://x/y") as sign:
            res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["expires_in"], 60)
        proc = VoiceSample.objects.get(voice_profile_id=self.voice_id, kind="PROCESSED")
        self.assertEqual(sign.call_args[0][1], proc.file_path)

    def test_sample_url_other_user_is_404(self):
        self.login_as(self.bob)
        res = self.client.get(reverse("voice-sample-url", args=[self.voice_id]))
        self.assertEqual(res.status_code, 404)

    def test_sample_url_without_sample_is_404(self):
        res = self.client.get(reverse("voice-sample-url", args=[self.voice_id]))
        self.assertEqual(res.status_code, 404)