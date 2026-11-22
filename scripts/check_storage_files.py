import httpx

from apps.voices.models import VoiceSample
from apps.voices.storage import StorageError, signed_url

found = missing = 0
for s in VoiceSample.objects.filter(is_active=True):
    try:
        url = signed_url(s.storage_bucket, s.file_path, 30)
        status = httpx.get(url, headers={"Range": "bytes=0-0"}, timeout=20).status_code
    except StorageError:
        status = None
    if status in (200, 206):
        found += 1
    else:
        missing += 1
print("active samples with a file:", found, "| missing:", missing)