#!/usr/bin/env bash
# PreToolUse: the editor's OWN commands run without an "Allow?" prompt (Petar 16.11.). Approved only:
#   CCC_HOME="<editor data>" bash "<editor code>/ccc" <args>        (every editor command, as SKILL.md writes it)
#   bash "<editor code>/setup/bootstrap.sh" "<editor data>" [--check]
#   Read of a file inside the editor's data folder (review sheets, candidate sheets, frames)
# Anything chained, piped, redirected or substituted (; & | ` < > $( newline) is NOT approved and asks as usual.
# Deny/ask rules the client set still win (Claude Code evaluates them regardless of this hook).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="${CLAUDE_PLUGIN_DATA:-${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/data/ccc-editor-createcontent-club}"
[ -f "$ROOT/.claude-plugin/plugin.json" ] || exit 0  # development folder: nothing is auto-approved

input="$(cat | tr '\n' ' ')"
field() { printf '%s' "$input" | sed -nE "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\".*/\\1/p" | head -1; }
allow() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}
unesc() {  # only \" and \\ are expected; any other escape (\n, \t, \u…) → not approved
  local s="$1" t
  t="$(printf '%s' "$s" | sed -e 's/\\\\//g' -e 's/\\"//g')"
  case "$t" in *\\*) return 1 ;; esac
  printf '%s' "$s" | sed -e 's/\\"/"/g' -e 's/\\\\/\\/g'
}
CACHE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/createcontent-club/ccc-editor/"
is_root() {  # this version, or another installed version of the editor (right after an update)
  case "$1" in "$ROOT" | '${CLAUDE_PLUGIN_ROOT}') return 0 ;; "$CACHE"*) v="${1#"$CACHE"}" ;; *) return 1 ;; esac
  [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; }
is_data() { case "$1" in "$DATA" | '${CLAUDE_PLUGIN_DATA}') return 0 ;; esac; return 1; }

tool="$(field tool_name)"
if [ "$tool" = "Bash" ]; then
  cmd="$(unesc "$(field command)")" || exit 0
  [ -n "$cmd" ] || exit 0
  re_ccc='^CCC_HOME="([^"]+)" bash "([^"]+)/ccc"( (.*))?$'
  re_setup='^bash "([^"]+)/setup/bootstrap\.sh" "([^"]+)"( --check)?$'
  if [[ "$cmd" =~ $re_ccc ]]; then
    data="${BASH_REMATCH[1]}"; root="${BASH_REMATCH[2]}"; rest="${BASH_REMATCH[4]}"
    case "$rest" in *';'* | *'&'* | *'|'* | *'`'* | *'<'* | *'>'* | *'$('*) exit 0 ;; esac
    is_data "$data" && is_root "$root" && allow "CCC Editor command"
  elif [[ "$cmd" =~ $re_setup ]]; then
    is_root "${BASH_REMATCH[1]}" && is_data "${BASH_REMATCH[2]}" && allow "CCC Editor setup"
  fi
elif [ "$tool" = "Read" ]; then
  f="$(unesc "$(field file_path)")" || exit 0
  case "$f" in *..*) exit 0 ;; "$DATA"/*) allow "CCC Editor file" ;; esac
fi
exit 0
