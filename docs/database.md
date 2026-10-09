# Database

## Engine
PostgreSQL 17 on Supabase (free tier). Django connects directly using psycopg 3.

## Connection
- Supabase **Session pooler**, port 5432 (decision S1).
  - Direct connection is IPv6-only by default, so it fails on many home networks.
  - Transaction pooler is meant for serverless/edge workloads, not for Django.
- One variable: `DATABASE_URL` in `backend/.env` (never committed).
  A dummy template lives in `backend/.env.example`.
- The password must be URL-encoded. `scripts/set_database_url.py` writes the
  URL safely and hides the password while typing.
- Connection test (does not use Django): `python scripts/test_db_connection.py`

## Security
- Django is the only client of the database. React never talks to Supabase.
- The Supabase Data API is disabled (the project does not use Supabase client
  libraries or REST/GraphQL data endpoints).
- No keys or passwords are ever committed or pasted in chat.

## Storage buckets (private, no public access)
| Bucket | Size limit |
|---|---|
| `voice-samples` | 10 MB |
| `generated-audio` | 20 MB |

Files are read and written only by the Django backend, which checks ownership
before returning any audio.

## Planned tables (Phase 11)
User, Profile, VoiceProfile, VoiceSample, Generation, GeneratedAudio,
UsageRecord. Future: Plan, Subscription, Payment, Notification, AdminActionLog.

## Status
Phase 11 complete: models migrated to Supabase (16 tables: 7 project models,
the rest are Django built-ins). Model behaviour is checked by
`python scripts/check_models.py` (runs in a rolled-back transaction).


## Phase 12 additions: JWT blacklist tables

Added by `rest_framework_simplejwt.token_blacklist` (migrated in Phase 12).
Used for refresh-token rotation and logout.

| Table | Purpose |
|---|---|
| `token_blacklist_outstandingtoken` | One row per refresh token issued: `user`, `jti`, `token`, `created_at`, `expires_at` |
| `token_blacklist_blacklistedtoken` | One row per refresh token that is no longer valid: `token` (links to the outstanding row), `blacklisted_at` |

Notes:
- The outstanding table stores the full refresh token string, so it is sensitive.
  It must never be reachable through Supabase's Data API.
- Rows are created on login and on every refresh (rotation).
- Cleanup of expired rows is not set up yet. Planned: run
  `python manage.py flushexpiredtokens` on a schedule (Phase 46, production).

## Test database

`python manage.py test apps.accounts --keepdb` uses a separate database named
`test_postgres` on the same Supabase server. Do not delete it. Project data
is never touched by tests. Running without `--keepdb` makes the cleanup step
fail on Supabase's pooler (the session stays open), so always use `--keepdb`.

## Status (updated)
Phase 12: 2 token_blacklist tables added on top of the 16 from Phase 11.