from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.generations import runner
from apps.generations.models import Generation


class Command(BaseCommand):
    help = "Mark generations that stayed PROCESSING for too long as FAILED."

    def handle(self, *args, **options):
        now = timezone.now()
        limit = now - timedelta(minutes=settings.GENERATION_STUCK_MINUTES)
        count = Generation.objects.filter(
            status=Generation.Status.PROCESSING, started_at__lt=limit
        ).update(
            status=Generation.Status.FAILED,
            error_message=runner.STUCK_FAILURE,
            finished_at=now,
            updated_at=now,
        )
        self.stdout.write(f"{count} stuck generation(s) marked as FAILED.")