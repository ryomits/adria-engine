#!/usr/bin/env bash
# Stop the voice loop, the display app and the on-demand TTS server, and unload the LLM.
set -uo pipefail
source "$(dirname "$0")/_env.sh"
# The voice loop, with or without options before "voice" (the app adds --quiet).
voice_loop='bin/adria( -[-a-z]+)* voice'
pkill -INT -f "$voice_loop" 2>/dev/null
# The harness saves a summary of the current conversation with the LLM before it
# exits; wait for that before unloading the model.
for _ in $(seq 1 120); do
  pgrep -f "$voice_loop" >/dev/null || break
  sleep 1
done
pkill -TERM -f "irodori_openai_tts" 2>/dev/null
pkill -TERM -f "ADRIA.app/Contents/MacOS/ADRIA" 2>/dev/null
model="$(uv run --project "$ADRIA_ENGINE/harness" python -c \
  'from adria_harness.config import load_config; print(load_config().llm.model)')"
curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null
echo "stopped"
