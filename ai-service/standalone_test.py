"""Standalone Chatterbox test (Phase 24). Does NOT import any Django code."""

import sys
import time
from pathlib import Path

import torch
import torchaudio

from chatterbox.mtl_tts import ChatterboxMultilingualTTS

HERE = Path(__file__).parent
REFERENCE = HERE / "samples" / "my_voice.wav"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

TEXTS = {
    "en": "Hello, this is a short test of my cloned voice.",
    "hi": "नमस्ते, यह मेरी आवाज़ का एक छोटा सा परीक्षण है।",
    "ur": "السلام علیکم، یہ میری آواز کا ایک چھوٹا سا ٹیسٹ ہے۔",
}

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
if lang not in TEXTS:
    sys.exit(f"Unknown language {lang}. Use: {', '.join(TEXTS)}")
if not REFERENCE.exists():
    sys.exit("Reference voice not found: ai-service/samples/my_voice.wav")

print("torch", torch.__version__, "| cuda:", torch.cuda.is_available(), "| threads:", torch.get_num_threads())

t0 = time.time()
model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
print(f"MODEL LOAD: {time.time() - t0:.1f} s")

t1 = time.time()
try:
    wav = model.generate(TEXTS[lang], language_id=lang, audio_prompt_path=str(REFERENCE))
except Exception as exc:  # e.g. an unsupported language
    sys.exit(f"GENERATE FAILED ({lang}): {type(exc).__name__}: {str(exc)[:300]}")
gen = time.time() - t1

seconds = wav.shape[-1] / model.sr
path = OUT / f"{lang}.wav"
torchaudio.save(str(path), wav.cpu(), model.sr)
print(f"GENERATE ({lang}): {gen:.1f} s for {seconds:.1f} s of audio (speed {seconds / gen:.2f}x realtime)")
print("SAVED:", path)