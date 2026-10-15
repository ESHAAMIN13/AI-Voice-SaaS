import time
from pathlib import Path

from services.ai import TTSError, check_request, get_engine

try:
    check_request("hello", "ur")
except TTSError as e:
    print("UR REJECTED:", e)

ref = Path("../ai-service/samples/my_voice.wav").read_bytes()
text = check_request("Hello from the Django client.", "en")
t = time.time()
try:
    wav = get_engine().generate(text, "en", ref)
    Path("../ai-service/outputs/client_en.wav").write_bytes(wav)
    print(f"GENERATE OK: {len(wav)} bytes in {time.time() - t:.0f} s")
except TTSError as e:
    print("FAILED:", e)