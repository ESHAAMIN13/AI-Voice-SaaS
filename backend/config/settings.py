"""
Django settings for the AI Voice SaaS backend.

Environment-specific values are read from backend/.env (never commit that file).
"""

from datetime import timedelta

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read environment variables from backend/.env
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

# Secrets and environment-specific settings come from .env, never from code.
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",


    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    # Local apps
    "apps.accounts",
    "apps.voices",
    "apps.generations",
    "apps.usage",
    "apps.admin_panel",
]

MIDDLEWARE = [

    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# Database
# Supabase PostgreSQL through the session pooler. The URL comes from .env.

DATABASES = {
    "default": env.db("DATABASE_URL"),
}
DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files

STATIC_URL = "static/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Django REST Framework
# Django REST Framework
REST_FRAMEWORK = {
    # All errors use {"success": false, "message": ..., "errors": ...}
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    # JSON only (no browsable HTML API)
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # Every request is checked for a valid JWT access token
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Secure by default: an endpoint is private unless it says AllowAny
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Rate limits, applied per IP by views that set a throttle_scope
    "DEFAULT_THROTTLE_RATES": {
        "login": "5/min",
        "register": "10/hour",
        "upload": "20/hour",
        "generate": "10/hour",
    },
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
}

# JWT settings (decision J2)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # Every refresh gives a new refresh token and the old one is blacklisted,
    # so a stolen refresh token works only once.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS: only our own frontend may call the API from a browser
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
# Supabase Storage (backend only; these never go to the frontend)
SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_SERVICE_ROLE_KEY = env("SUPABASE_SERVICE_ROLE_KEY", default="")

# Use our own User model (must be set before the first migration)
AUTH_USER_MODEL = "accounts.User"


# Voice sample validation (Phase 20, decision V5)
VOICE_SAMPLE_MIN_SECONDS = 10
VOICE_SAMPLE_MAX_SECONDS = 60
VOICE_SAMPLE_DURATION_TOLERANCE = 0.5  # browser recordings are rarely exact
VOICE_SAMPLE_MAX_BYTES = 10 * 1024 * 1024
AUDIO_PROBE_TIMEOUT_SECONDS = 20
AUDIO_DECODE_TIMEOUT_SECONDS = 60
FFMPEG_BIN = env("FFMPEG_BIN", default="ffmpeg")
FFPROBE_BIN = env("FFPROBE_BIN", default="ffprobe")

# AI service (Phase 25). The model runs in a separate process, see ai-service/.
AI_SERVICE_URL = env("AI_SERVICE_URL", default="http://127.0.0.1:8001")
AI_SERVICE_TOKEN = env("AI_SERVICE_TOKEN", default="")
AI_SERVICE_TIMEOUT_SECONDS = 600  # CPU generation is slow (about 20x slower than the audio)
TTS_MAX_TEXT_CHARS = 200
TTS_LANGUAGES = ("en", "hi")  # only the languages verified in Phase 24
GENERATION_MAX_ACTIVE_PER_USER = 3  # PENDING + PROCESSING jobs at the same time


# Processed sample for the AI model (Phase 21). May change after Phases 23-24.
PROCESSED_SAMPLE_RATE = 24000
PROCESSED_CHANNELS = 1
PROCESSED_TARGET_LUFS = -20  # gentle loudness target, no noise removal