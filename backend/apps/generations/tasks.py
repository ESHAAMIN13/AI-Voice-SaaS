from celery import shared_task
from django.conf import settings

from services.ai import TTSBusyError

from . import runner
from .models import Generation


@shared_task(
    bind=True,
    name="generations.generate_audio",
    max_retries=settings.GENERATION_RETRY_MAX,
)
def generate_audio(self, generation_id):
    try:
        return runner.run_generation(str(generation_id))
    except TTSBusyError as exc:
        # W-7: the AI service is busy or loading. Retry a few times, then give up.
        if self.request.retries >= self.max_retries:
            runner.mark_failed(
                str(generation_id),
                runner.BUSY_FAILURE,
                from_statuses=(Generation.Status.PENDING,),
            )
            return "failed"
        raise self.retry(exc=exc, countdown=settings.GENERATION_RETRY_DELAY_SECONDS)