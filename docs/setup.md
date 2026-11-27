# Setup and running

All inference (LLM, speech synthesis, speech recognition) runs on the Mac. The network is used only by the one-time setup, to install dependencies and download models.

## Requirements

- Apple Silicon Mac (48 GB RAM or more recommended)
- [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com/) (`brew install uv ollama`)
- The two repositories checked out side by side:

```
<anywhere>/
  adria-engine/   public: the machinery (this repository)
  adria-home/     private: persona, memory, settings, reference voice, avatar models
```

If `adria-home` lives elsewhere, point to it with the `ADRIA_HOME` environment variable.

## 1. Prepare the private side

```bash
cp adria-engine/persona-templates/config.example.toml adria-home/config.toml
cp adria-engine/persona-templates/persona.example.md adria-home/persona.md
cp adria-engine/persona-templates/display.example.json adria-home/display.json
```

Replace the placeholder name in `persona.md`. See [personas.md](personas.md) for the format.

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

`display.json` shows the placeholder character; to use a VRM model, put it in `adria-home/avatars/` and set `vrm` (and remove `"avatar": "placeholder"`). See [display.md](display.md) for the settings.
Rebuild after moving `adria-home`, because the build records its location in the app.

## 5. Start, talk, stop

- Start: double-click `scripts/start.command` in Finder (or run `scripts/start.sh`). It opens the display app when it has been built, then starts the voice loop in standby.
- Talk: click the character. The microphone opens only while a conversation is on; click again, or stay silent for `[conversation] idle_timeout_min` minutes, to go back to standby.
  - The first time, macOS asks for microphone permission for Terminal.
- Stop: quit the display app (right-click → Quit ADRIA, or Cmd-Q); the voice loop saves the conversation summary and exits too. Ctrl-C or closing the Terminal window stops only the voice loop. `scripts/stop.sh` stops everything: the voice loop, the display app, the TTS server, and the loaded LLM.

## Commands for checking

```bash
source adria-engine/scripts/_env.sh
adria chat                 # type to talk; replies are spoken
adria voice --start        # voice loop that starts listening without a click (no display app needed)
adria say "こんにちは。"     # speak one line
adria e2e a.wav b.wav      # treat WAV files as speech, run the full path, print latency (--mute for silence)
```

## Files shared with the display app

Runtime files live in `ADRIA_HOME/runtime/` (not tracked by Git).

| File | Content |
|---|---|
| `queue.jsonl` | Playback queue, one JSON object per line. Written to `.part` first, then renamed |
| `now_playing` | The line being heard (its `x_` keys, `started_at` including output latency, `duration`, and the lip-sync `mouth` curve), or `{"playing": false}` |
| `state` | `idle` (standby, microphone closed) / `listening` (conversation on) / `thinking` (LLM generating, or the reply is being synthesized) / `speaking` |
| `control.jsonl` | Commands from the display app (`toggle`, `quit`); written only by the app |
| `metrics.jsonl` | Latency measurements. No conversation text |

Keys starting with `x_` in a dialog line (expression and so on) are hints for the display side and are never sent to the TTS.

## Private data written at runtime

| Location in `ADRIA_HOME` | Content | Git |
|---|---|---|
| `memory/summary.md` | Session summaries (the long-term memory) | tracked in the private repository |
| `conversation-logs/YYYY-MM-DD.jsonl` | Full transcript for parents; deleted after 7 days; never read by the harness | ignored |

No audio from the microphone is ever written to disk.
