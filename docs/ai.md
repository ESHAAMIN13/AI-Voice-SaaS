# AI engine notes (Phase 24, measured on the developer laptop)

Model: Chatterbox Multilingual (package `chatterbox-tts` 0.1.7), MIT license.
Environment: separate venv `ai-service/.venv-ai`, torch 2.6.0+cpu. Weights: 3.21 GB
(downloaded once into the Hugging Face cache, outside the repo).
Machine: Intel i5-8350U (4 cores), 15.8 GB RAM, no NVIDIA GPU.

| Test | Result |
|---|---|
| Model load (cached) | 22.5 to 26.8 s |
| English | 94.4 s for 4.4 s of audio (0.05x realtime) |
| Hindi | 116.2 s for 7.4 s of audio (0.06x realtime) |
| Urdu | NOT supported by the model: `Unsupported language_id 'ur'` |

Supported language ids: ar, da, de, el, en, es, fi, fr, he, hi, it, ja, ko, ms, nl, no, pl, pt,
ru, sv, sw, tr, zh.

Findings:
- CPU generation is far slower than real time. Fine for development, not for real users.
  Production needs a GPU.
- Urdu stays disabled in the generator until a verified model exists. A community LoRA
  (RIMA-TTS v1) claims Urdu but is unverified.
- Generated audio carries Resemble's PerTh watermark. It must not be removed.
- Voice quality (similarity to the reference) was judged by listening: not rated yet.
- Peak RAM: not measured yet.
- `requirements-ai.txt` pins torch as 2.6.0 while the installed wheel is 2.6.0+cpu.
  Check this before deployment.


  
## AI service (Phase 25)

The model runs in its own process (`ai-service/server.py`, FastAPI + uvicorn, in `.venv-ai`),
so Django never imports chatterbox and the two environments never conflict.

Start it (separate terminal):

    cd ai-service
    .\.venv-ai\Scripts\Activate.ps1
    uvicorn server:app --host 127.0.0.1 --port 8001

Rules:
- Listens on 127.0.0.1 only. Every `/generate` call needs the header `X-AI-Token`
  (`AI_SERVICE_TOKEN`, same value in `ai-service/.env` and `backend/.env`).
- Only `en` and `hi` are accepted. `ur` is rejected explicitly (model does not support it).
- Text limit 200 characters (`TTS_MAX_TEXT_CHARS`), reference audio limit 10 MB.
- One generation at a time; a second request gets 503 "Busy".
- The service never receives Supabase keys. Django reads the reference sample and sends it.
- Run with ONE worker only: each worker would load its own copy of the model.

Django side: `backend/services/ai/` has the engine interface (`TTSEngine`), `HttpTTSEngine`
(real), `FakeTTSEngine` (tests) and `check_request` (language and text rules, run before a
job is queued). `get_engine()` is the single place that picks the engine.

Measured through the service: about 61 s for a short English sentence, still far slower than
real time. Output WAV is 32-bit float; it is converted to 16-bit in Phase 30.