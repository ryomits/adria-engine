# adria-engine

The machinery behind ADRIA, a conversation-partner character for young children that runs entirely on a Mac.

Click on the character → microphone → speech recognition (Whisper / MLX) → persona and memory → local LLM (Ollama) → speech synthesis (Irodori-TTS) → playback, shown by a small character window at the screen edge

- `harness/` dialog management and the STT / LLM / TTS plumbing
- `app/` display app (native shell in `app/mac`, page with a replaceable avatar layer in `app/web`)
- `persona-templates/` config, display settings and persona format with dummy samples
- `scripts/` setup, start, and stop
- `docs/` setup guide (`setup.md`), persona and memory (`personas.md`), display app (`display.md`), lip sync (`lipsync.md`), measurements (`measurements.md`)

Personal content (persona, memory, settings, reference voice, avatar models) is never stored here. It lives in the private `adria-home` repository, which the harness reads via `ADRIA_HOME`.
