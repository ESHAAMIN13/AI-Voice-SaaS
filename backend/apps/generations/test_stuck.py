from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.utils import timezone

from . import runner
from .models import Generation
from .tests import GenerationTestBase


class StuckGenerationTests(GenerationTestBase):
    def make(self, status, minutes_ago=None):
        started = None if minutes_ago is None else timezone.now() - timedelta(minutes=minutes_ago)
        return Generation.objects.create(
            user=self.alice, voice_profile=self.voice, voice_name_snapshot="v",
            language="en", input_text="x", char_count=1, status=status, started_at=started,
        )

    def test_old_processing_job_is_failed(self):
        old = self.make("PROCESSING", minutes_ago=20)
        call_command("fail_stuck_generations", stdout=StringIO())
        old.refresh_from_db()
        self.assertEqual(old.status, "FAILED")
        self.assertEqual(old.error_message, runner.STUCK_FAILURE)
        self.assertIsNotNone(old.finished_at)

    def test_recent_processing_job_is_left_alone(self):
        recent = self.make("PROCESSING", minutes_ago=1)
        call_command("fail_stuck_generations", stdout=StringIO())
        recent.refresh_from_db()
        self.assertEqual(recent.status, "PROCESSING")

    def test_pending_and_completed_jobs_are_left_alone(self):
        pending = self.make("PENDING")
        done = self.make("COMPLETED", minutes_ago=60)
        call_command("fail_stuck_generations", stdout=StringIO())
        pending.refresh_from_db()
        done.refresh_from_db()
        self.assertEqual((pending.status, done.status), ("PENDING", "COMPLETED"))