# Setup and running

All inference (LLM, speech synthesis, speech recognition) runs on the Mac. The network is used only by the one-time setup, to install dependencies and download models.

## Requirements

- Apple Silicon Mac (48 GB RAM or more recommended)
- [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/) (`brew install uv ollama`)
- The two repositories checked out side by side:

```
<anywhere>/
  adria-engine/   public: the machinery (this repository)
  adria-home/     private: persona, settings, reference voice
```

If `adria-home` lives elsewhere, point to it with the `ADRIA_HOME` environment variable.

## 1. Prepare the private side

```bash
cp adria-engine/persona-templates/config.example.toml adria-home/config.toml
cp adria-engine/persona-templates/child.example.md adria-home/personas/child.md
```

Clone Irodori-TTS-Server and set `[tts] server_dir` in `config.toml` to its location:

```bash
git clone https://github.com/Aratako/Irodori-TTS-Server.git <anywhere>
```

## 2. Install dependencies and download models (the only step that uses the network)

```bash
adria-engine/scripts/setup.sh
```

This fetches the LLM (Ollama), Whisper (MLX), and Irodori-TTS with its codec. The first TTS download can take over ten minutes.

## 3. Fix the voice (optional, recommended)

A voice designed from a caption alone changes timbre from line to line. Create one reference clip to keep it stable:

```bash
source adria-engine/scripts/_env.sh
adria make-voice adria   # writes adria-home/voices/adria.wav (not tracked by Git)
```

Then set `[tts] voice = "adria"` in `config.toml`.

## 4. Start and stop

- Start: double-click `scripts/start.command` in Finder (or run `scripts/start.sh`).
  - The first time, macOS asks for microphone permission for Terminal.
- Stop: Ctrl-C or close the Terminal window. `scripts/stop.sh` also stops the TTS server and unloads the LLM.

## Commands for checking

```bash
source adria-engine/scripts/_env.sh
adria chat                 # type to talk; replies are spoken
adria say "こんにちは。"     # speak one line
adria e2e a.wav b.wav      # treat WAV files as speech, run the full path, print latency (--mute for silence)
```

## Files shared with the display app

Runtime files live in `ADRIA_HOME/runtime/` (not tracked by Git).

| File | Content |
|---|---|
| `queue.jsonl` | Playback queue, one JSON object per line. Written to `.part` first, then renamed |
| `now_playing` | The line being played (with its `x_` keys, `audio_path`, `started_at`, `duration`), or `{"playing": false}` |
| `state` | `idle` / `listening` / `thinking` / `speaking` |
| `audio/current.wav` | Audio being played (for lip-sync analysis) |
| `metrics.jsonl` | Latency measurements. Timestamps only, no conversation text |

Keys starting with `x_` in a dialog line (expression and so on) are hints for the display side and are never sent to the TTS.
