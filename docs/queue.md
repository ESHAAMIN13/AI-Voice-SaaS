# Background jobs (Phase 27)

Celery + Redis. Redis runs in its own Docker container `aivoice-redis`, bound to
127.0.0.1:6380. Port 6379 on this machine belongs to Memurai (a different program) and
the judge0 containers are another project: never touch them.

| Redis db | Use |
|---|---|
| 0 | Celery broker (the queue) |
| 1 | Celery results (deleted after 1 hour) |
| 2 | Django cache and rate limits |

Start (dev, backend folder, `.venv`):

    docker start aivoice-redis
    celery -A config worker --pool=solo -l info

- Windows has no official Celery support. `--pool=solo` runs one task at a time, which also
  matches our "one generation at a time" rule. Production runs on Linux.
- A task sent while the worker is down waits in Redis and runs when the worker starts.
- Login, register and upload rate limits now live in Redis (db 2). If Redis is down in
  development, those endpoints fail until it is started again.
- Tests use a local-memory cache and never touch Redis.
- The `config.ping` task is only a connection test and will be removed.cd 
## Generation job (Phase 28)

Flow: POST /api/generations/ creates a PENDING row, then queues the Celery task
`generations.generate_audio`. The worker (apps/generations/runner.py) does the work:

1. Claim: PENDING -> PROCESSING in one atomic update. A second delivery of the same job is skipped.
2. Download the prepared voice sample from Storage (signed link).
3. Ask the AI service for the audio (services/ai).
4. Upload the WAV to the private generated-audio bucket at {user_id}/{generation_id}/{uuid}.wav.
5. In one transaction: GeneratedAudio row, status COMPLETED, finished_at, UsageRecord (CHARS).

Failures:
- Any error: status FAILED with a safe message. Details only go to the server log.
- Voice deleted or no prepared sample: FAILED ("This voice is no longer available.").
- AI service busy or loading: job goes back to PENDING and retries up to 3 times, 30 s apart, then FAILED.
- Redis down when the job is created: the row is marked FAILED and the API answers 503.
- A worker that dies mid-job leaves PROCESSING. Run `python manage.py fail_stuck_generations`
  to mark jobs older than 15 minutes as FAILED. A scheduler for it comes in Phase 46.
- Usage is recorded only when a generation completes.

Not done yet: the generated audio is still the AI service output (32-bit float WAV).
Conversion, play and download links come in Phases 30 to 33.
