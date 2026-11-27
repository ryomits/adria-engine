#!/usr/bin/env bash
# Debug start: the display app plus the voice loop in this Terminal, with logs.
# For everyday use, double-click ADRIA.app instead: it starts the voice loop
# itself, without a Terminal window.
# Extra arguments are passed to `adria voice` (e.g. --mute).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
app="$ADRIA_ENGINE/app/build/ADRIA.app"
if [ -d "$app" ]; then
  # The voice loop runs here, so the app must not start its own.
  open "$app" --args --no-harness
else
  echo "display app not built (scripts/build-app.sh); starting voice only" >&2
fi
adria voice "$@"
