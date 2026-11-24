from apps.generations.models import Generation

for g in Generation.objects.order_by("-created_at")[:5]:
    audio = getattr(g, "audio", None)
    print(g.status, "|", g.language, "|", g.char_count, "chars |", (g.error_message or "-"), "| audio bytes:", (audio.size_bytes if audio else None))
