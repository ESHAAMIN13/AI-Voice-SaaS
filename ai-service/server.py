"""Local AI service (Phase 25). Keeps the model in memory. Not meant for the internet."""

import io
import logging
import os
import secrets
import sys
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import torchaudio
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

HERE = Path(__file__).parent
logger = logging.getLogger("ai-service")


def _load_env_file():
    path = HERE / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

TOKEN = os.environ.get("AI_SERVICE_TOKEN", "")
if len(TOKEN) < 16:
    sys.exit("AI_SERVICE_TOKEN is missing or too short. Check ai-service/.env")

MAX_TEXT_CHARS = int(os.environ.get("AI_MAX_TEXT_CHARS", "200"))  # G-5
MAX_REFERENCE_BYTES = 10 * 1024 * 1024
# Only languages we actually tested. The model lists more, but they are not verified here.
ALLOWED_LANGUAGES = {"en", "hi"}

state = {}
busy = threading.Lock()  # G-6: one generation at a time


@asynccontextmanager
async def lifespan(app):
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    state["model"] = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    yield
    state.clear()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health():
    return {"status": "ok" if "model" in state else "loading", "device": "cpu"}


@app.post("/generate")
def generate(
    text: str = Form(...),
    language: str = Form(...),
    reference: UploadFile = File(...),
    x_ai_token: str = Header(default=""),
):
    # G-2: shared secret (constant-time compare)
    if not secrets.compare_digest(x_ai_token, TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized.")

    # G-5: language and text limits
    if language == "ur":
        raise HTTPException(status_code=400, detail="Urdu is not supported by the model.")
    if language not in ALLOWED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language.")
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty.")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=400, detail=f"Text is too long (max {MAX_TEXT_CHARS}).")

    data = reference.file.read(MAX_REFERENCE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Reference audio is empty.")
    if len(data) > MAX_REFERENCE_BYTES:
        raise HTTPException(status_code=400, detail="Reference audio is too large.")

    if "model" not in state:
        raise HTTPException(status_code=503, detail="Model is still loading.")
    if not busy.acquire(blocking=False):
        raise HTTPException(status_code=503, detail="Busy. Try again shortly.")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ref_path = Path(tmp) / "reference.wav"  # fixed name, never the client's
            ref_path.write_bytes(data)
            model = state["model"]
            wav = model.generate(text, language_id=language, audio_prompt_path=str(ref_path))
        buffer = io.BytesIO()
        torchaudio.save(buffer, wav.cpu(), model.sr, format="wav")
        return Response(content=buffer.getvalue(), media_type="audio/wav")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Generation failed")  # details stay in the log
        raise HTTPException(status_code=500, detail="Generation failed.")
    finally:
        busy.release()