"""Model smoke test (Phase 11). Runs inside a transaction that is rolled back."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import IntegrityError, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.accounts.models import Profile  # noqa: E402
from apps.generations.models import GeneratedAudio, Generation  # noqa: E402
from apps.usage.models import UsageRecord  # noqa: E402
from apps.voices.models import VoiceProfile, VoiceSample  # noqa: E402


class Rollback(Exception):
    """Raised on purpose at the end so nothing is saved."""


def run():
    User = get_user_model()

    user = User.objects.create_user(email="  Test@Example.com ", password="Str0ng-pass-123")
    assert user.email == "test@example.com", "email was not normalised"
    assert user.password.startswith("pbkdf2_"), "password was not hashed"
    assert user.role == User.Role.USER and not user.is_staff
    print("OK user: email normalised, password hashed, role USER")

    admin = User.objects.create_superuser(email="admin@example.com", password="Str0ng-pass-123")
    assert admin.role == User.Role.ADMIN and admin.is_staff and admin.is_superuser
    print("OK superuser gets role ADMIN")

    Profile.objects.create(user=user, full_name="Test User")
    voice = VoiceProfile.objects.create(
        user=user, name="My Voice", consent_accepted_at=timezone.now(), consent_version="v1"
    )
    print("OK profile and voice profile created (default status:", voice.status + ")")

    try:
        with transaction.atomic():
            VoiceProfile.objects.create(user=user, name="My Voice")
        raise AssertionError("duplicate voice name was allowed")
    except IntegrityError:
        print("OK duplicate voice name blocked by the database")

    VoiceSample.objects.create(
        voice_profile=voice, kind="ORIGINAL", file_path="u/v/original.wav",
        format="wav", size_bytes=1000, duration_sec=12.5,
    )
    gen = Generation.objects.create(
        user=user, voice_profile=voice, voice_name_snapshot=voice.name,
        language="en", input_text="Hello world", char_count=11,
    )
    GeneratedAudio.objects.create(generation=gen, file_path="u/g.wav", size_bytes=2000)
    UsageRecord.objects.create(user=user, generation=gen, unit_type="CHARS", amount=11)
    assert gen.status == Generation.Status.PENDING
    print("OK sample, generation, generated audio and usage record created")

    voice.delete()
    gen.refresh_from_db()
    assert gen.voice_profile is None and gen.voice_name_snapshot == "My Voice"
    print("OK deleting a voice keeps the history (name snapshot kept)")

    user_id = user.pk
    user.delete()
    assert not Profile.objects.filter(user_id=user_id).exists()
    assert not Generation.objects.filter(user_id=user_id).exists()
    assert not GeneratedAudio.objects.exists()
    assert not UsageRecord.objects.filter(user_id=user_id).exists()
    print("OK deleting a user cascades to all their data")


def main():
    try:
        with transaction.atomic():
            run()
            raise Rollback
    except Rollback:
        print("ALL CHECKS PASSED. Changes were rolled back (nothing saved).")
        return 0
    except AssertionError as exc:
        print("FAIL:", exc)
        return 1
    except Exception as exc:
        print("ERROR:", type(exc).__name__)
        print(str(exc).strip().splitlines()[0])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())