#!/usr/bin/env bash
# SessionStart (async): the editor sets itself up as soon as Claude opens, without asking and without waiting for the
# first video (Petar 16.11.). Runs only when something is missing or the plugin was updated; otherwise exits at once.
# setup/bootstrap.sh holds a lock, so a setup started by the skill (Step 0) waits for this one instead of clashing.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${1:-}"; case "$DATA" in "" | *'${'*) DATA="${CLAUDE_PLUGIN_DATA:-}" ;; esac
[ -n "$DATA" ] || DATA="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/data/ccc-editor-createcontent-club"
[ -f "$ROOT/.claude-plugin/plugin.json" ] || exit 0  # development folder

ver() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$1" 2>/dev/null | head -1; }
want="$(ver "$ROOT/.claude-plugin/plugin.json")"
have="$(ver "$DATA/installed.json")"
if [ -n "$have" ] && [ "$have" = "$want" ]; then
  state="$(bash "$ROOT/setup/bootstrap.sh" "$DATA" --check 2>/dev/null | tail -1)"
  [ "$state" = "INSTALLED" ] && exit 0
fi

out="$(bash "$ROOT/setup/bootstrap.sh" "$DATA" 2>&1 | tail -3)"
case "$out" in
  *SETUP_OK*) echo "CCC Editor background setup finished: SETUP_OK (version $want). Nothing to tell the client unless they ask." ;;
  *) echo "CCC Editor background setup did not finish: $(printf '%s' "$out" | tr '\n' ' '). When the client sends a video, Step 0 runs setup again and shows the reason." ;;
esac
exit 0
