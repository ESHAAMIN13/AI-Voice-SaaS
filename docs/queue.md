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