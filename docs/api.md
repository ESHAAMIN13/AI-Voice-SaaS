# API Reference

Base URL (development): `http://127.0.0.1:8000/api/`

## Response format

Success:

    { "success": true, "data": ... }

Error:

    { "success": false, "message": "...", "errors": ... }

Python stack traces are never sent to the client.

## Authentication rules

- Send the access token on protected endpoints: `Authorization: Bearer <access>`
- Access token lifetime: 15 minutes. Refresh token lifetime: 7 days.
- Refresh tokens rotate: every refresh returns a NEW refresh token and the old one is blacklisted.
- Register, login, refresh and logout are public (no token needed).
- Everything else is private by default.

## Endpoints (Phase 12)

### GET /api/health/
Public. Returns `{ "status": "ok", "service": "ai-voice-saas-api" }`.

### POST /api/auth/register/
Public. Throttle: 10/hour per IP.

Body: `email`, `password`, `full_name` (optional)

| Status | Meaning |
|---|---|
| 201 | Account created. `data` is the user (no password). |
| 400 | Validation failed (duplicate email, weak password, bad email). |
| 429 | Too many requests. |

The role is always `USER`. `role` or `is_staff` sent by the client is ignored.

### POST /api/auth/login/
Public. Throttle: 5/min per IP.

Body: `email`, `password`

| Status | Meaning |
|---|---|
| 200 | `data` = `access`, `refresh`, `user` |
| 401 | Invalid email or password (same message for both), or inactive user. |
| 429 | Too many attempts. |

### POST /api/auth/refresh/
Public.

Body: `refresh`

| Status | Meaning |
|---|---|
| 200 | `data` = new `access` and new `refresh`. The old refresh token is now blacklisted. |
| 401 | Refresh token invalid, expired or already used. |

### POST /api/auth/logout/
Public (works even if the access token has expired).

Body: `refresh`

| Status | Meaning |
|---|---|
| 200 | Refresh token blacklisted. Also 200 if it was already invalid. |
| 400 | `refresh` missing. |

The access token stays valid until it expires (max 15 minutes).

### GET /api/profile/
Private. Returns the logged-in user's own data: `id`, `email`, `role`, `full_name`, `preferred_language`, `created_at`.

### PUT /api/profile/
Private. Body (partial allowed): `full_name`, `preferred_language`.
`role` and `email` cannot be changed here.

| Status | Meaning |
|---|---|
| 200 | Updated user returned. |
| 400 | Validation failed. |
| 401 | Missing or invalid access token. |

## Frontend note (decision J3)

Access token is kept in memory, refresh token in localStorage.
All token code lives in one file: `frontend/src/services/tokenStorage.js`.





### GET /api/admin/ping/
Admin only (`role = ADMIN`). Temporary endpoint that proves the admin permission works.

| Status | Meaning |
|---|---|
| 200 | `data` = `status`, `role` |
| 401 | Missing or invalid access token. |
| 403 | Logged in, but role is not ADMIN. |

Permission class: `apps.accounts.permissions.IsAdminRole` (checks `role`, not `is_staff`).
Admin users are created with `python manage.py createsuperuser` (role becomes ADMIN automatically). There is no API to become admin.


## Frontend auth flow (Phase 14)

- Token code lives only in `frontend/src/services/tokenStorage.js` (decision J3).
  Access token: memory. Refresh token: localStorage.
- `frontend/src/services/api.js` adds the access token to every request.
  On a 401 it refreshes once, retries the request, and if refresh fails it
  clears tokens and fires the `auth:logout` event.
- Auth endpoints (`/auth/*`) never trigger a refresh, so a wrong password
  does not start a refresh loop.
- On page load `AuthContext` restores the session once with the refresh token
  (guarded against React StrictMode running effects twice, because refresh
  tokens rotate and can be used only once).
- Route guards: `GuestRoute` (/login, /register), `ProtectedRoute`
  (logged-in users), `AdminRoute` (role ADMIN). These only hide pages.
  The backend `IsAdminRole` permission is the real protection.
- Register logs the user in automatically.
- Known limitation: a refresh token in localStorage can be read by any
  script on the page (XSS). Accepted for the MVP. Moving it to an HttpOnly
  cookie only needs changes in `tokenStorage.js` and the backend.


  
## Voice profiles (Phase 17)

All endpoints are private. A user only ever sees their own profiles; another
user's profile returns 404 (not 403), so its existence is not revealed.

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/voices/` | List own profiles (no pagination yet) |
| POST | `/api/voices/` | Create: `name`, `description` (optional), `consent` (must be true) |
| GET | `/api/voices/{id}/` | One profile |
| PATCH | `/api/voices/{id}/` | Change `name` / `description` only |
| DELETE | `/api/voices/{id}/` | Delete (DB row; storage files are handled in Phase 22) |

Rules:
- `consent` must be `true` on create, otherwise 400. The server sets
  `consent_accepted_at` and `consent_version` ("v1"). Consent cannot be edited later.
- `status`, `status_message`, `user` are never accepted from the client. New profiles are PENDING.
- Name: trimmed, 1 to 100 characters, unique per user (case-insensitive). Duplicate gives 400.
- PUT is not allowed (405). Use PATCH.
- Admin endpoints for all voices come in Phase 37.