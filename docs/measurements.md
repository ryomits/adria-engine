# Voice loop measurements

Date: 2026-11-24. Hardware: Mac mini (Apple M4 Pro, 48 GB RAM), macOS 27.2.1, Ollama 0.40.18.

## Selected stack

| Role | Choice | Notes |
|---|---|---|
| LLM | `qwen3:30b-a3b-instruct-2507-q4_K_M` (Ollama) | Non-thinking variant. `num_ctx=4096`, `keep_alive=10m` |
| TTS | Irodori-TTS-v4-Small (Irodori-TTS-Server, MPS, fp32) | `num_steps=16`, timbre fixed with a reference voice |
| STT | `mlx-community/whisper-large-v3-turbo` (mlx-whisper) | Silero VAD (TorchScript) for turn detection |

## LLM candidates

Same provisional persona, six-turn small talk (greeting, favorite food, the park, why the sky is blue, goodbye).

| Model | First load | First token (warm) | Generation | Japanese conversation quality |
|---|---|---|---|---|
| `qwen3:30b-a3b` (Thinking-2507) | 2.6 s | — | 62–75 tok/s | **Rejected.** `think:false` has no effect: its template always opens `<think>`, so English reasoning leaks into the reply |
| `qwen3:8b` | 3.8 s | 0.16–0.23 s | 44 tok/s | Fast, but odd word choices and many kanji |
| `qwen3:30b-a3b-instruct-2507-q4_K_M` | 5.9 s | 0.11–0.23 s | 78–81 tok/s | **Selected.** Short, hiragana-heavy replies that keep context. Occasional odd word choice (to be handled by persona tuning) |

Note: `ollama pull qwen3:30b-a3b` gives the thinking-only variant. For conversation, use the explicit `-instruct-2507` tag.

## TTS (Irodori-TTS on MPS)

| Item | Value |
|---|---|
| First-time setup (model download + load) | 874 s (depends on network speed) |
| Server start (cached, offline) | 5–10 s |
| Warmup synthesis right after start | 1.5–3.6 s (done as part of start-up) |
| One sentence, default 40 steps | 2.7–3.9 s (RTF 0.7–1.0) |
| One sentence, 16 steps (selected) | 1.0–2.8 s (RTF 0.35–0.66) |
| Gap between lines (look-ahead synthesis) | 0–0.87 s (target: under 1 s) |

- bf16 is not available on MPS (`precision='bf16' currently requires CUDA or XPU device`), so fp32 is used.
- Irodori embeds an audio watermark in its output through its dependency sony/silentcipher. This runs locally.

## Response latency (end of speech → first audio)

Automated runs feed child-voice WAV files (generated with the TTS) into STT (`adria e2e`).
With the microphone, the VAD end-of-speech silence (0.7 s) comes on top of these numbers.

| Condition | Value | Breakdown |
|---|---|---|
| Warm (LLM and TTS resident) | **1.7–2.7 s** (6 turns × 2 runs) | STT 0.38–0.50 s + first LLM sentence ~0.3 s + first TTS sentence 1.3–2.6 s |
| LLM cold (TTS pre-started) | 8.5 s | A filler ("うーんとね。") is played while the LLM reloads |
| Everything cold (right after launch) | 10.8 s | TTS server start + warmup |

### Microphone session (human tester, 2026-11-24)

The conversation worked end to end through the microphone. Two turns were recorded in the metrics:

| Turn | End of speech → first audio | STT |
|---|---|---|
| 1 (LLM cold, filler played first) | 3.8 s | 0.38 s |
| 2 (warm) | 1.86 s | 0.41 s |

Perceived latency is therefore about 2.5–3.5 s when warm, including the VAD silence.

## Memory (LLM and TTS resident together)

| Process | Usage |
|---|---|
| Ollama (LLM, `num_ctx=4096`) | 18 GB (`ollama ps`) |
| Irodori-TTS-Server (fp32, MPS) | 7.0–8.3 GB |
| System-wide free memory | at least 34% (~16 GB); swap 0.5 MB |

This leaves room for normal work. The TTS server stops after 30 minutes idle, and Ollama unloads the LLM after 10 minutes idle.

## No external traffic

- During an automated run, `lsof` was sampled every second for python / ollama / uv sockets that were not loopback. None were found.
- At runtime `HF_HUB_OFFLINE=1` is enforced. Models are downloaded only by `scripts/setup.sh`.
- A fully offline check (Wi-Fi off) is to be done by a human.
