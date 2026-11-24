from apps.voices.storage import StorageError, delete_object, upload_bytes

PATH = "_healthcheck/gen.txt"
try:
    upload_bytes("generated-audio", PATH, b"hello", "text/plain")
    print("generated-audio UPLOAD: OK")
except StorageError as e:
    print("generated-audio FAILED:", e)
finally:
    try:
        delete_object("generated-audio", PATH)
        print("CLEANUP: OK")
    except StorageError as e:
        print("CLEANUP FAILED:", e)
