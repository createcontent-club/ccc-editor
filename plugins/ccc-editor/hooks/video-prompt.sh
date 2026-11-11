#!/usr/bin/env bash
# UserPromptSubmit: if the message looks like a video edit request, remind Claude to use the CCC Editor skill.
input="$(cat)"
if printf '%s' "$input" | grep -qiE '\.(mov|mp4|m4v)|/ccc-edit|\bvideo\b|\breel\b|\bccc\b'; then
  echo "Reminder: this looks like a CCC video edit request — use the ccc-editor:ccc-edit skill (CCC Editor plugin) and follow it."
fi
exit 0
