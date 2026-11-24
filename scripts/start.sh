#!/usr/bin/env bash
# Start the voice conversation loop (microphone -> reply spoken aloud).
# Extra arguments are passed to `adria voice` (e.g. --mute).
set -euo pipefail
source "$(dirname "$0")/_env.sh"
adria voice "$@"
