#!/usr/bin/env bash
# Run the harness command line (e.g. `harness.sh --quiet voice`). The display
# app starts the voice loop through this script; it is also handy by hand.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
exec uv run --project "$ADRIA_ENGINE/harness" adria "$@"
