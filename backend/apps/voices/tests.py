from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Profile, User

from .models import VoiceProfile, VoiceSample

PASSWORD = "StrongPass#2026x"

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile

class VoiceTestBase(APITestCase):
    def setUp(self):
        cache.clear()  # reset login throttle counters
        self.client = APIClient()
        self.alice = self.make_user("alice@example.com")
        self.bob = self.make_user("bob@example.com")

    def make_user(self, email):
        user = User.objects.create_user(email=email, password=PASSWORD)
        Profile.objects.create(user=user)
        return user

    def login_as(self, user):
        res = self.client.post(
            reverse("auth-login"),
            {"email": user.email, "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {res.json()['data']['access']}"
        )

    def create_voice(self, name="My Voice", consent=True, **extra):
        payload = {"name": name, "description": "test", "consent": consent, **extra}
        return self.client.post(reverse("voice-list"), payload, format="json")


class VoiceCreateTests(VoiceTestBase):
    def test_requires_login(self):
        self.assertEqual(self.client.get(reverse("voice-list")).status_code, 401)

    def test_create_success_sets_consent_and_pending(self):
        self.login_as(self.alice)
        res = self.create_voice()
        self.assertEqual(res.status_code, 201)
        data = res.json()["data"]
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["consent_version"], "v1")
        self.assertIsNotNone(data["consent_accepted_at"])
        self.assertNotIn("consent", data)
        self.assertEqual(VoiceProfile.objects.get().user, self.alice)

    def test_create_without_consent_is_400(self):
        self.login_as(self.alice)
        res = self.client.post(reverse("voice-list"), {"name": "X"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(VoiceProfile.objects.count(), 0)

    def test_create_with_consent_false_is_400(self):
        self.login_as(self.alice)
        self.assertEqual(self.create_voice(consent=False).status_code, 400)

    def test_client_cannot_set_status_or_user(self):
        self.login_as(self.alice)
        res = self.create_voice(status="APPROVED", user=str(self.bob.id))
        self.assertEqual(res.status_code, 201)
        voice = VoiceProfile.objects.get()
        self.assertEqual(voice.status, "PENDING")
        self.assertEqual(voice.user, self.alice)

    def test_duplicate_name_same_user_is_400_case_insensitive(self):
        self.login_as(self.alice)
        self.assertEqual(self.create_voice("My Voice").status_code, 201)
        self.assertEqual(self.create_voice("my voice").status_code, 400)

    def test_same_name_for_different_users_is_allowed(self):
        self.login_as(self.alice)
        self.assertEqual(self.create_voice("Shared Name").status_code, 201)
        self.login_as(self.bob)
        self.assertEqual(self.create_voice("Shared Name").status_code, 201)

    def test_blank_name_is_400(self):
        self.login_as(self.alice)
        self.assertEqual(self.create_voice("   ").status_code, 400)


class VoiceOwnershipTests(VoiceTestBase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)
        self.voice_id = self.create_voice("Alice Voice").json()["data"]["id"]

    def test_list_shows_only_own_voices(self):
        self.login_as(self.bob)
        self.create_voice("Bob Voice")
        res = self.client.get(reverse("voice-list"))
        names = [v["name"] for v in res.json()["data"]]
        self.assertEqual(names, ["Bob Voice"])

    def test_other_user_gets_404_on_detail(self):
        self.login_as(self.bob)
        res = self.client.get(reverse("voice-detail", args=[self.voice_id]))
        self.assertEqual(res.status_code, 404)

    def test_other_user_cannot_patch(self):
        self.login_as(self.bob)
        res = self.client.patch(
            reverse("voice-detail", args=[self.voice_id]), {"name": "Hacked"}, format="json"
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(VoiceProfile.objects.get(pk=self.voice_id).name, "Alice Voice")

    def test_other_user_cannot_delete(self):
        self.login_as(self.bob)
        res = self.client.delete(reverse("voice-detail", args=[self.voice_id]))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(VoiceProfile.objects.filter(pk=self.voice_id).exists())


class VoiceUpdateDeleteTests(VoiceTestBase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)
        self.voice_id = self.create_voice("Old Name").json()["data"]["id"]

    def test_patch_changes_name_and_description(self):
        res = self.client.patch(
            reverse("voice-detail", args=[self.voice_id]),
            {"name": "New Name", "description": "changed"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["name"], "New Name")

    def test_patch_cannot_change_status(self):
        self.client.patch(
            reverse("voice-detail", args=[self.voice_id]),
            {"status": "APPROVED", "status_message": "hi"},
            format="json",
        )
        voice = VoiceProfile.objects.get(pk=self.voice_id)
        self.assertEqual(voice.status, "PENDING")
        self.assertEqual(voice.status_message, "")

    def test_patch_keeping_own_name_is_ok(self):
        res = self.client.patch(
            reverse("voice-detail", args=[self.voice_id]), {"name": "Old Name"}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_put_is_not_allowed(self):
        res = self.client.put(
            reverse("voice-detail", args=[self.voice_id]), {"name": "X"}, format="json"
        )
        self.assertEqual(res.status_code, 405)

    def test_delete_removes_profile(self):
        res = self.client.delete(reverse("voice-detail", args=[self.voice_id]))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(VoiceProfile.objects.filter(pk=self.voice_id).exists())

class VoiceUploadTests(VoiceTestBase):
    def setUp(self):
        super().setUp()
        self.login_as(self.alice)
        self.voice_id = self.create_voice("Alice Voice").json()["data"]["id"]
        self.url = reverse("voice-upload", args=[self.voice_id])

    def audio(self, name="a.wav", content=b"RIFFdata", ctype="audio/wav"):
        return SimpleUploadedFile(name, content, content_type=ctype)

    def post_file(self, f, **extra):
        return self.client.post(self.url, {"file": f, **extra}, format="multipart")

    @patch("apps.voices.views.storage.upload_bytes")
    def test_upload_success_creates_sample_and_keeps_pending(self, mock_upload):
        res = self.post_file(self.audio(), duration_sec="12.5")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["data"]["duration_sec"], 12.5)
        mock_upload.assert_called_once()
        voice = VoiceProfile.objects.get(pk=self.voice_id)
        self.assertEqual(voice.status, "PENDING")  # U7
        sample = voice.samples.get()
        self.assertTrue(sample.file_path.startswith(f"{self.alice.id}/{voice.id}/"))
        self.assertNotIn("a.wav", sample.file_path)  # U5

    @patch("apps.voices.views.storage.upload_bytes")
    def test_new_upload_deactivates_old_sample(self, _):
        self.post_file(self.audio())
        self.post_file(self.audio())
        active = VoiceSample.objects.filter(voice_profile_id=self.voice_id, is_active=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(VoiceSample.objects.filter(voice_profile_id=self.voice_id).count(), 2)

    @patch("apps.voices.views.storage.upload_bytes")
    def test_other_user_gets_404_and_nothing_uploaded(self, mock_upload):
        self.login_as(self.bob)
        res = self.post_file(self.audio())
        self.assertEqual(res.status_code, 404)
        mock_upload.assert_not_called()

    @patch("apps.voices.views.storage.upload_bytes")
    def test_wrong_extension_is_400(self, mock_upload):
        res = self.post_file(self.audio("a.exe", ctype="application/octet-stream"))
        self.assertEqual(res.status_code, 400)
        mock_upload.assert_not_called()

    @patch("apps.voices.views.storage.upload_bytes")
    def test_type_mismatch_is_400(self, mock_upload):
        res = self.post_file(self.audio("a.wav", ctype="text/html"))
        self.assertEqual(res.status_code, 400)
        mock_upload.assert_not_called()

    @patch("apps.voices.views.storage.upload_bytes")
    def test_empty_file_is_400(self, mock_upload):
        self.assertEqual(self.post_file(self.audio(content=b"")).status_code, 400)
        mock_upload.assert_not_called()

    @patch("apps.voices.views.storage.upload_bytes")
    def test_too_large_is_400(self, mock_upload):
        big = self.audio(content=b"0" * (10 * 1024 * 1024 + 1))
        self.assertEqual(self.post_file(big).status_code, 400)
        mock_upload.assert_not_called()

    def test_missing_file_is_400(self):
        res = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(res.status_code, 400)

    def test_requires_login(self):
        self.client.credentials()
        self.assertEqual(self.post_file(self.audio()).status_code, 401)

    @patch("apps.voices.views.storage.upload_bytes")
    def test_storage_failure_is_502_and_no_row(self, mock_upload):
        from apps.voices.storage import StorageError

        mock_upload.side_effect = StorageError("boom")
        res = self.post_file(self.audio())
        self.assertEqual(res.status_code, 502)
        self.assertEqual(VoiceSample.objects.count(), 0)
        self.assertNotIn("boom", res.content.decode())  # no internal details