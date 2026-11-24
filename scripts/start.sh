#!/usr/bin/env bash
# Start ADRIA: the display app (if built) and the voice conversation loop.
# Extra arguments are passed to `adria voice` (e.g. --mute).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
app="$ADRIA_ENGINE/app/build/ADRIA.app"
if [ -d "$app" ]; then
  open "$app"
else
  echo "display app not built (scripts/build-app.sh); starting voice only" >&2
fi
adria voice "$@"
