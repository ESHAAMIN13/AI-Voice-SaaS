from apps.voices.storage import StorageError, delete_object, signed_url, upload_bytes
import httpx

PATH = "_healthcheck/sign.txt"
try:
    upload_bytes("voice-samples", PATH, b"hello", "text/plain")
    url = signed_url("voice-samples", PATH, 30)
    print("SIGN: OK, host:", url.split("/")[2])
    print("FETCH with link:", httpx.get(url, timeout=20).status_code)
    plain = url.split("?")[0].replace("/object/sign/", "/object/public/")
    print("PUBLIC link (must be 400/404):", httpx.get(plain, timeout=20).status_code)
except StorageError as e:
    print("FAILED:", e)
finally:
    try:
        delete_object("voice-samples", PATH)
        print("CLEANUP: OK")
    except StorageError as e:
        print("CLEANUP FAILED:", e)