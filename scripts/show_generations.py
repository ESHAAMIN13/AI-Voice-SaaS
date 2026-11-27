from apps.generations.models import Generation
from apps.usage.models import UsageRecord

for g in Generation.objects.order_by("-created_at")[:3]:
    a = getattr(g, "audio", None)
    detail = f"{a.size_bytes} bytes, {a.duration_sec}s, {a.sample_rate} Hz" if a else "no audio"
    print(g.status, "|", g.language, "|", g.char_count, "chars |", (g.error_message or "-"), "|", detail)
print("usage:", {u: UsageRecord.objects.filter(unit_type=u).count() for u in ("CHARS", "SECONDS")})
