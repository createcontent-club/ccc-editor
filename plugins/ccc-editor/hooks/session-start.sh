#!/usr/bin/env bash
# SessionStart (sync): Claude's context (always) + one short note for the client (installed / setting up / ready).
# The setup itself runs in hooks/auto-setup.sh (async), so this returns at once.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${1:-}"; case "$DATA" in "" | *'${'*) DATA="${CLAUDE_PLUGIN_DATA:-}" ;; esac
[ -n "$DATA" ] || DATA="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/data/ccc-editor-createcontent-club"

jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | awk 'BEGIN{ORS="\\n"} {print}' | sed 's/\\n$//'; }
ver() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$1" 2>/dev/null | head -1; }

ctx="$(cat "$ROOT/hooks/session-context.txt")"
msg=""
want="$(ver "$ROOT/.claude-plugin/plugin.json")"
if [ -n "$want" ]; then  # installed plugin (the development folder has no plugin.json)
  have="$(ver "$DATA/installed.json")"
  if [ -z "$have" ]; then
    msg="CCC Editor installed. It is setting itself up in the background now (one time, about 5 to 10 minutes). You can already type /ccc-edit and drag in your video."
    ctx="$ctx Setup is running in the background right now (started by the plugin when this session opened); the Step 0 bootstrap command waits for it and then prints SETUP_OK."
  elif [ "$have" != "$want" ]; then
    msg="CCC Editor updated to version $want. Finishing the update in the background (under a minute)."
    ctx="$ctx The editor was just updated; the background setup finishes the update, and the Step 0 bootstrap command waits for it."
  elif [ ! -f "$DATA/.welcomed" ]; then
    msg="CCC Editor is installed and ready. Type /ccc-edit and drag in your video to start."
    touch "$DATA/.welcomed" 2>/dev/null
  fi
fi

printf '{'
[ -n "$msg" ] && printf '"systemMessage":"%s",' "$(jesc "$msg")"
printf '"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$(jesc "$ctx")"
exit 0
