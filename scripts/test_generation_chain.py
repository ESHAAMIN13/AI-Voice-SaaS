import time

from apps.generations.models import Generation
from apps.generations.tasks import generate_audio
from apps.voices.models import VoiceProfile

voice = VoiceProfile.objects.filter(
    status="APPROVED", samples__kind="PROCESSED", samples__is_active=True
).first()
if voice is None:
    raise SystemExit("No approved voice with a prepared sample.")

text = "Hello, this is a test."
g = Generation.objects.create(
    user=voice.user,
    voice_profile=voice,
    voice_name_snapshot=voice.name,
    language="en",
    input_text=text,
    char_count=len(text),
)
generate_audio.delay(str(g.id))
print("queued, waiting (up to 15 minutes)...")

start = time.time()
while time.time() - start < 900:
    time.sleep(10)
    g.refresh_from_db()
    if g.status in ("COMPLETED", "FAILED"):
        break

audio = getattr(g, "audio", None)
print("status:", g.status, "| after", round(time.time() - start), "s")
print("error:", g.error_message or "-")
print("audio bytes:", audio.size_bytes if audio else None)
