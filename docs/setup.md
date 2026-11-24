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

## 4. Build the display app

```bash
adria-engine/scripts/build-app.sh   # writes app/build/ADRIA.app (no Xcode needed)
```

Copy `persona-templates/display.example.json` to `adria-home/display.json` and point `vrm` at a model in `adria-home/avatars/` first. See [display.md](display.md) for the settings.
Rebuild after moving `adria-home`, because the build records its location in the app.

## 5. Start and stop

- Start: double-click `scripts/start.command` in Finder (or run `scripts/start.sh`). It opens the display app when it has been built, then starts the voice loop.
  - The first time, macOS asks for microphone permission for Terminal.
- Stop: Ctrl-C or close the Terminal window (the display app stays open; quit it with Cmd-Q). `scripts/stop.sh` stops everything: the voice loop, the display app, the TTS server, and the loaded LLM.

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
| `now_playing` | The line being heard (its `x_` keys, `started_at` including output latency, `duration`, and the lip-sync `mouth` curve), or `{"playing": false}` |
| `state` | `idle` (waiting) / `listening` (the child is speaking, or STT is running) / `thinking` (LLM generating, or the reply is being synthesized) / `speaking` |
| `metrics.jsonl` | Latency measurements. Timestamps only, no conversation text |

Keys starting with `x_` in a dialog line (expression and so on) are hints for the display side and are never sent to the TTS.
