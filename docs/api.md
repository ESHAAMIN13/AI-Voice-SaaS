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