# adria-engine

The machinery behind ADRIA, a conversation-partner character for young children that runs entirely on a Mac.

Microphone → speech recognition (Whisper / MLX) → local LLM (Ollama) → speech synthesis (Irodori-TTS) → playback

- `harness/` dialog management and the STT / LLM / TTS plumbing
- `app/` display app (native shell in `app/mac`, three-vrm page in `app/web`)
- `persona-templates/` config and persona format with dummy samples
- `scripts/` setup, start, and stop
- `docs/` setup guide (`setup.md`), display app (`display.md`), lip sync (`lipsync.md`), measurements (`measurements.md`)

Personal content (persona, settings, reference voice) is never stored here. It lives in the private `adria-home` repository, which the harness reads via `ADRIA_HOME`.
