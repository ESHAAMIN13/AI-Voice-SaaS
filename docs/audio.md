# Audio validation (Phase 20)

Code: `backend/services/audio/validation.py`. Limits: `backend/config/settings.py`.
Upload entry point: `POST /api/voices/{id}/upload/` (see api.md).

## Limits (settings.py)

| Setting | Value |
|---|---|
| `VOICE_SAMPLE_MIN_SECONDS` | 10 |
| `VOICE_SAMPLE_MAX_SECONDS` | 60 |
| `VOICE_SAMPLE_DURATION_TOLERANCE` | 0.5 s (browser recordings are rarely exact) |
| `VOICE_SAMPLE_MAX_BYTES` | 10 MB |
| `AUDIO_PROBE_TIMEOUT_SECONDS` | 20 |
| `AUDIO_DECODE_TIMEOUT_SECONDS` | 60 |
| `FFMPEG_BIN` / `FFPROBE_BIN` | `ffmpeg` / `ffprobe` (override in `.env`) |

## How a file is checked

1. Quick filter in `upload.py`: extension must be wav, mp3, m4a, mp4, webm, ogg or flac,
   and the browser-sent content type must match it.
2. Size: empty or over 10 MB is rejected.
3. `ffprobe` reads the file CONTENT. The real container must be wav, mp3, ogg, flac,
   webm/matroska, or mp4/m4a. The extension and MIME type are not trusted for this.
4. The file must contain an audio stream and no real video stream
   (MP3 cover art is ignored).
5. `ffmpeg` decodes the whole file once. This gives the real duration, volume and silence.
6. Duration must be 10 to 60 seconds (with the 0.5 s tolerance).
7. Warnings are added (they do not block the upload) and saved as validation notes.

Security: the user's filename is never used. The file is written to a temporary folder
under a fixed name, external tools run with list arguments (no shell) and a timeout.

## Warnings (accepted, but shown to the user)

| Warning | Rule |
|---|---|
| More than half of the sample is silent | silence over 1 s below -40 dB, total over 50% |
| May be clipped | peak volume at or above -0.3 dB |
| Very quiet | mean volume below -38 dB |
| Low sample rate | below 16000 Hz |

These thresholds are rough guesses, not exact quality measurements.

## Honest limitations

- It does NOT detect whether the audio is a human voice. Music or noise that is not
  silent will pass.
- It does NOT detect background noise level (only overall volume and silence),
  and does NOT detect multiple speakers.
- Only the first audio stream is analysed.
- Corruption detection is best effort. Partly damaged files can still decode and pass.
- If ffmpeg or ffprobe times out, the file is reported as unreadable, even if it is
  valid but the server was slow. The user message does not say "timeout".
- If FFmpeg is not installed, the server raises `AudioToolError`. This is a server problem,
  not the user's.
- The whole file (max 10 MB) is held in memory and in a temporary file during checking.
- The MIME type in the quick filter comes from the browser and can be faked.
  The ffprobe check on content is the real one.
- No virus or malware scan.
- A replaced sample stays in Supabase Storage until the Phase 22 cleanup.
- The model's own requirements (Phases 23-24) may be stricter than these limits.
  If so, the model's verified requirements win.


  
## Processing (Phase 21)

Code: `backend/services/audio/processing.py`. Settings: `PROCESSED_SAMPLE_RATE` (24000),
`PROCESSED_CHANNELS` (1), `PROCESSED_TARGET_LUFS` (-20). These may change after the AI model
is verified (Phases 23-24).

- After validation passes, the audio is converted to WAV, mono, 24 kHz, 16-bit, with gentle
  loudness normalisation. No noise removal or effects.
- The original is kept unchanged. The processed file is a second `VoiceSample` row
  (`kind=PROCESSED`), stored at `{user_id}/{profile_id}/processed/{uuid}.wav` in the private
  `voice-samples` bucket.
- Processing runs BEFORE anything is stored. If it fails, nothing is saved (400).
- Success sets the profile to APPROVED. A processing failure sets it to FAILED only if the
  profile has no good sample already.
- Limitation: processing runs inside the upload request (max 60 s audio). It moves to
  Celery in Phase 27.