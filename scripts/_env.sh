# Shared environment for ADRIA scripts. Source this file; do not execute it.
# All paths are resolved relative to this repository, so nothing here depends
# on where the repositories are checked out.

ADRIA_ENGINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# The private repository is expected next to this one unless ADRIA_HOME is set.
export ADRIA_HOME="${ADRIA_HOME:-$ADRIA_ENGINE/../adria-home}"
if [ ! -f "$ADRIA_HOME/config.toml" ]; then
  echo "ADRIA_HOME ($ADRIA_HOME) has no config.toml." >&2
  echo "Copy persona-templates/config.example.toml there, or set ADRIA_HOME." >&2
  exit 1
fi
export ADRIA_HOME="$(cd "$ADRIA_HOME" && pwd)"

adria() {
  uv run --project "$ADRIA_ENGINE/harness" adria "$@"
}
