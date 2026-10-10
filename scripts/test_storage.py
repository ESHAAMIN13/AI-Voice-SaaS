from apps.voices.storage import StorageError, delete_object, upload_bytes

PATH = "_healthcheck/test.txt"
try:
    upload_bytes("voice-samples", PATH, b"hello", "text/plain")
    print("UPLOAD: OK")
    delete_object("voice-samples", PATH)
    print("DELETE: OK")
except StorageError as e:
    print("FAILED:", e)