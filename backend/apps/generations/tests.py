from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Profile, User
from apps.voices.models import VoiceProfile, VoiceSample

from .models import Generation

PASSWORD = "StrongPass#2026x"


class GenerationTestBase(APITestCase):
    def setUp(self):
        cache.clear()  # reset throttle counters
        self.client = APIClient()
        self.alice = self.make_user("alice@example.com")
        self.bob = self.make_user("bob@example.com")
        self.client.force_authenticate(user=self.alice)
        self.voice = self.make_voice(self.alice)

    def make_user(self, email):
        user = User.objects.create_user(email=email, password=PASSWORD)
        Profile.objects.create(user=user)
        return user

    def make_voice(self, user, name="My Voice", status=VoiceProfile.Status.APPROVED, sample=True):
        voice = VoiceProfile.objects.create(
            user=user, name=name, status=status, consent_version="v1"
        )
        if sample:
            VoiceSample.objects.create(
                voice_profile=voice,
                kind=VoiceSample.Kind.PROCESSED,
                file_path="u/p/processed/x.wav",
                format="wav",
                size_bytes=10,
                duration_sec=12,
                sample_rate=24000,
                channels=1,
            )
        return voice

    def create(self, voice=None, language="en", text="Hello world", **extra):
        payload = {
            "voice_profile": str((voice or self.voice).id),
            "language": language,
            "text": text,
            **extra,
        }
        return self.client.post(reverse("generation-list"), payload, format="json")


class GenerationCreateTests(GenerationTestBase):
    def test_requires_login(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.create().status_code, 401)

    def test_success_creates_pending_generation(self):
        res = self.create(text="  Hello world  ")
        self.assertEqual(res.status_code, 201)
        data = res.json()["data"]
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["voice_name"], "My Voice")
        self.assertEqual(data["char_count"], 11)
        generation = Generation.objects.get()
        self.assertEqual(generation.user, self.alice)
        self.assertEqual(generation.input_text, "Hello world")

    def test_client_cannot_set_status_user_or_error(self):
        res = self.create(status="COMPLETED", user=str(self.bob.id), error_message="x")
        self.assertEqual(res.status_code, 201)
        generation = Generation.objects.get()
        self.assertEqual(generation.status, "PENDING")
        self.assertEqual(generation.user, self.alice)
        self.assertEqual(generation.error_message, "")

    def test_other_users_voice_profile_is_rejected(self):
        bobs_voice = self.make_voice(self.bob, name="Bob Voice")
        res = self.create(voice=bobs_voice)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Generation.objects.count(), 0)

    def test_unknown_voice_profile_is_rejected(self):
        payload = {
            "voice_profile": "00000000-0000-0000-0000-000000000000",
            "language": "en",
            "text": "Hello",
        }
        res = self.client.post(reverse("generation-list"), payload, format="json")
        self.assertEqual(res.status_code, 400)

    def test_unapproved_voice_profile_is_rejected(self):
        pending = self.make_voice(self.alice, name="Pending", status=VoiceProfile.Status.PENDING)
        self.assertEqual(self.create(voice=pending).status_code, 400)
        self.assertEqual(Generation.objects.count(), 0)

    def test_approved_voice_without_prepared_sample_is_rejected(self):
        empty = self.make_voice(self.alice, name="Empty", sample=False)
        self.assertEqual(self.create(voice=empty).status_code, 400)

    def test_urdu_is_rejected_with_a_clear_message(self):
        res = self.create(language="ur")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Urdu", res.content.decode())
        self.assertEqual(Generation.objects.count(), 0)

    def test_unsupported_language_is_rejected(self):
        self.assertEqual(self.create(language="fr").status_code, 400)

    def test_empty_text_is_rejected(self):
        self.assertEqual(self.create(text="   ").status_code, 400)

    def test_too_long_text_is_rejected(self):
        self.assertEqual(self.create(text="a" * 201).status_code, 400)

    def test_max_3_active_generations(self):
        for _ in range(3):
            self.assertEqual(self.create().status_code, 201)
        res = self.create()
        self.assertEqual(res.status_code, 429)
        self.assertEqual(Generation.objects.count(), 3)

    def test_hourly_throttle_applies_even_when_nothing_is_active(self):
        for _ in range(10):
            self.assertEqual(self.create().status_code, 201)
            Generation.objects.update(status="COMPLETED")  # so the active limit never triggers
        res = self.create()
        self.assertEqual(res.status_code, 429)
        self.assertIn("throttled", res.content.decode().lower())


class GenerationReadTests(GenerationTestBase):
    def setUp(self):
        super().setUp()
        self.long_text = "x" * 150
        self.generation_id = self.create(text=self.long_text).json()["data"]["id"]

    def test_list_shows_only_own_with_preview_and_no_full_text(self):
        bobs_voice = self.make_voice(self.bob, name="Bob Voice")
        Generation.objects.create(
            user=self.bob, voice_profile=bobs_voice, voice_name_snapshot="Bob Voice",
            language="en", input_text="bob text", char_count=8,
        )
        res = self.client.get(reverse("generation-list"))
        items = res.json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(len(items[0]["text_preview"]), 100)
        self.assertNotIn("input_text", items[0])

    def test_detail_own(self):
        res = self.client.get(reverse("generation-detail", args=[self.generation_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["input_text"], self.long_text)

    def test_detail_of_other_user_is_404(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.get(reverse("generation-detail", args=[self.generation_id]))
        self.assertEqual(res.status_code, 404)

    def test_status_own_is_small(self):
        res = self.client.get(reverse("generation-status", args=[self.generation_id]))
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        self.assertEqual(data["status"], "PENDING")
        self.assertNotIn("input_text", data)

    def test_status_of_other_user_is_404(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.get(reverse("generation-status", args=[self.generation_id]))
        self.assertEqual(res.status_code, 404)

    def test_history_survives_voice_profile_deletion(self):
        self.voice.delete()  # ORM delete: no storage call
        res = self.client.get(reverse("generation-detail", args=[self.generation_id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["voice_name"], "My Voice")