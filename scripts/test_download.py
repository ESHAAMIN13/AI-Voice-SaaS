from apps.voices.models import VoiceSample
from apps.voices.storage import StorageError, download_bytes

sample = VoiceSample.objects.filter(kind="PROCESSED", is_active=True).first()
if sample is None:
    print("No active processed sample in the database.")
else:
    try:
        data = download_bytes(sample.storage_bucket, sample.file_path)
        print("DOWNLOAD OK:", len(data), "bytes | database says:", sample.size_bytes, "| starts with:", data[:4])
    except StorageError as e:
        print("FAILED:", e)