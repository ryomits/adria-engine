#!/usr/bin/env bash
# One-time setup. This is the only step that uses the network: it installs
# dependencies and downloads model weights. Normal runs are fully offline.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

command -v uv >/dev/null || { echo "uv is required (brew install uv)"; exit 1; }
command -v ollama >/dev/null || { echo "Ollama is required (brew install ollama)"; exit 1; }

echo "== harness dependencies"
uv sync --project "$ADRIA_ENGINE/harness"

server_dir="$(uv run --project "$ADRIA_ENGINE/harness" python -c \
  'from adria_harness.config import load_config; print(load_config().tts.server_dir or "")')"
if [ -z "$server_dir" ] || [ ! -f "$server_dir/pyproject.toml" ]; then
  echo "Irodori-TTS-Server not found. Clone https://github.com/Aratako/Irodori-TTS-Server" >&2
  echo "and set [tts] server_dir in $ADRIA_HOME/config.toml." >&2
  exit 1
fi
echo "== Irodori-TTS-Server dependencies (macOS: PyPI torch with MPS)"
(cd "$server_dir" && uv sync --extra cpu)

echo "== model downloads"
ADRIA_ALLOW_DOWNLOAD=1 adria fetch-models
echo "setup complete"
