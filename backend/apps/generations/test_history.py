from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from apps.usage.models import UsageRecord
from apps.voices.storage import StorageError

from .models import GeneratedAudio, Generation
from .tests import GenerationTestBase

REMOVE = "apps.generations.views.storage.remove_files"


class HistoryTestBase(GenerationTestBase):
    def make_generation(self, user=None, status="COMPLETED", text="Hello world", audio=False):
        user = user or self.alice
        generation = Generation.objects.create(
            user=user,
            voice_profile=self.voice if user == self.alice else None,
            voice_name_snapshot="My Voice",
            language="en",
            input_text=text,
            char_count=len(text),
            status=status,
        )
        if audio:
            GeneratedAudio.objects.create(
                generation=generation,
                storage_bucket="generated-audio",
                file_path=f"{user.id}/{generation.id}/x.wav",
                format="wav",
                size_bytes=100,
                duration_sec=2.5,
                sample_rate=24000,
            )
        return generation

    def history(self, **params):
        return self.client.get(reverse("generation-history"), params)

    def detail(self, generation):
        return reverse("generation-detail", args=[generation.id])


class HistoryListTests(HistoryTestBase):
    def test_requires_login(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.history().status_code, 401)

    def test_own_only_and_newest_first(self):
        now = timezone.now()
        first = self.make_generation(text="first")
        second = self.make_generation(text="second")
        third = self.make_generation(text="third")
        for minutes, g in ((3, first), (2, second), (1, third)):
            Generation.objects.filter(pk=g.pk).update(created_at=now - timedelta(minutes=minutes))
        self.make_generation(user=self.bob, text="bobs")
        previews = [i["text_preview"] for i in self.history().json()["data"]["items"]]
        self.assertEqual(previews, ["third", "second", "first"])

    def test_pages_are_20_items(self):
        Generation.objects.bulk_create(
            [
                Generation(
                    user=self.alice, voice_profile=self.voice, voice_name_snapshot="My Voice",
                    language="en", input_text=f"t{i}", char_count=2, status="COMPLETED",
                )
                for i in range(25)
            ]
        )
        data = self.history().json()["data"]
        self.assertEqual((len(data["items"]), data["page"], data["pages"], data["count"]), (20, 1, 2, 25))
        page2 = self.history(page=2).json()["data"]
        self.assertEqual(len(page2["items"]), 5)

    def test_page_beyond_the_last_is_empty(self):
        self.make_generation()
        res = self.history(page=999999999999)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["items"], [])

    def test_invalid_page_is_400(self):
        self.assertEqual(self.history(page="abc").status_code, 400)
        self.assertEqual(self.history(page=0).status_code, 400)

    def test_status_filter(self):
        self.make_generation(status="COMPLETED")
        self.make_generation(status="COMPLETED")
        self.make_generation(status="FAILED")
        data = self.history(status="FAILED").json()["data"]
        self.assertEqual((data["count"], data["items"][0]["status"]), (1, "FAILED"))

    def test_invalid_status_is_400(self):
        self.assertEqual(self.history(status="NOPE").status_code, 400)

    def test_item_fields(self):
        self.make_generation(status="COMPLETED", audio=True, text="a" * 150)
        self.make_generation(status="FAILED")
        items = {i["status"]: i for i in self.history().json()["data"]["items"]}
        done, failed = items["COMPLETED"], items["FAILED"]
        self.assertEqual((done["duration_sec"], done["has_audio"]), (2.5, True))
        self.assertEqual((failed["duration_sec"], failed["has_audio"]), (None, False))
        self.assertEqual(len(done["text_preview"]), 100)
        self.assertNotIn("input_text", done)

    def test_history_uses_two_queries(self):
        for _ in range(3):
            self.make_generation(audio=True)
        with self.assertNumQueries(2):
            self.assertEqual(self.history().status_code, 200)


class HistoryDeleteTests(HistoryTestBase):
    def test_requires_login(self):
        generation = self.make_generation()
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.delete(self.detail(generation)).status_code, 401)

    def test_delete_completed_removes_row_audio_and_file(self):
        generation = self.make_generation(audio=True)
        path = GeneratedAudio.objects.get(generation=generation).file_path
        with patch(REMOVE) as remove:
            res = self.client.delete(self.detail(generation))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Generation.objects.filter(pk=generation.pk).exists())
        self.assertFalse(GeneratedAudio.objects.filter(file_path=path).exists())
        remove.assert_called_once_with([("generated-audio", path)])

    def test_delete_failed_without_audio(self):
        generation = self.make_generation(status="FAILED")
        with patch(REMOVE) as remove:
            res = self.client.delete(self.detail(generation))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Generation.objects.filter(pk=generation.pk).exists())
        remove.assert_not_called()

    def test_delete_of_other_user_is_404_and_nothing_is_removed(self):
        generation = self.make_generation(audio=True)
        self.client.force_authenticate(user=self.bob)
        with patch(REMOVE) as remove:
            res = self.client.delete(self.detail(generation))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Generation.objects.filter(pk=generation.pk).exists())
        remove.assert_not_called()

    def test_delete_unknown_id_is_404(self):
        res = self.client.delete(
            reverse("generation-detail", args=["00000000-0000-0000-0000-000000000000"])
        )
        self.assertEqual(res.status_code, 404)

    def test_delete_pending_is_409(self):
        generation = self.make_generation(status="PENDING")
        with patch(REMOVE) as remove:
            res = self.client.delete(self.detail(generation))
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Generation.objects.filter(pk=generation.pk).exists())
        remove.assert_not_called()

    def test_delete_processing_is_409(self):
        generation = self.make_generation(status="PROCESSING")
        self.assertEqual(self.client.delete(self.detail(generation)).status_code, 409)
        self.assertTrue(Generation.objects.filter(pk=generation.pk).exists())

    def test_delete_keeps_usage_records(self):
        generation = self.make_generation(audio=True)
        UsageRecord.objects.create(
            user=self.alice, generation=generation, unit_type="CHARS", amount=11
        )
        with patch(REMOVE):
            self.assertEqual(self.client.delete(self.detail(generation)).status_code, 200)
        usage = UsageRecord.objects.get()
        self.assertIsNone(usage.generation_id)
        self.assertEqual(int(usage.amount), 11)

    def test_storage_failure_does_not_fail_the_delete(self):
        generation = self.make_generation(audio=True)
        with patch("apps.voices.storage.delete_object", side_effect=StorageError("x")):
            with self.assertLogs("apps.voices.storage", level="ERROR") as logs:
                res = self.client.delete(self.detail(generation))
        self.assertEqual(res.status_code, 200)
        self.assertIn("ORPHAN", logs.output[0])
        self.assertFalse(Generation.objects.filter(pk=generation.pk).exists())
