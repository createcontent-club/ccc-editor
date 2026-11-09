#!/usr/bin/env bash
# CCC editor — first-time setup (macOS + Windows/Git Bash). No admin password needed.
#   bash setup/bootstrap.sh <data folder> [--no-whisper]
#   bash setup/bootstrap.sh <data folder> --check     → prints INSTALLED / NOT_INSTALLED / UPDATE_NEEDED
# Installs: uv (Python manager) → Python 3.12 → Python packages → setup/install.py (Node, ffmpeg, fonts,
# models, Remotion). Everything goes into <data folder>, except uv itself (~/.local/bin).
set -uo pipefail

CODE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${1:?usage: bootstrap.sh <data folder> [--check|--no-whisper]}"
shift
MODE="${1:-}"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1 ;; *) WIN=0 ;; esac

py_path() {
  if [ -x "$HOME_DIR/.venv/bin/python" ]; then echo "$HOME_DIR/.venv/bin/python"
  elif [ -x "$HOME_DIR/.venv/Scripts/python.exe" ]; then echo "$HOME_DIR/.venv/Scripts/python.exe"; fi
}
plugin_version() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$CODE/.claude-plugin/plugin.json" 2>/dev/null | head -1; }

if [ "$MODE" = "--check" ]; then
  if [ -z "$(py_path)" ] || [ ! -f "$HOME_DIR/installed.json" ]; then echo "NOT_INSTALLED"; exit 0; fi
  want="$(plugin_version)"; have="$(sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$HOME_DIR/installed.json" | head -1)"
  if [ -n "$want" ] && [ "$want" != "$have" ]; then echo "UPDATE_NEEDED"; else echo "INSTALLED"; fi
  exit 0
fi

echo "▶ Preparing the CCC editor (one time, ~5–10 minutes)…"
mkdir -p "$HOME_DIR"

# 1) uv — official standalone Python manager (installs to ~/.local/bin, no admin)
UV="$(command -v uv || true)"
for c in "$HOME/.local/bin/uv" "$HOME/.local/bin/uv.exe" "$HOME/.cargo/bin/uv"; do [ -z "$UV" ] && [ -x "$c" ] && UV="$c"; done
if [ -z "$UV" ]; then
  echo "  … installing uv (Python manager)"
  if [ "$WIN" = 1 ]; then
    powershell.exe -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" || { echo "SETUP_FAILED"; exit 1; }
    UV="$HOME/.local/bin/uv.exe"
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "SETUP_FAILED"; exit 1; }
    UV="$HOME/.local/bin/uv"
  fi
fi
[ -x "$UV" ] || { echo "  ✗ uv not found after install"; echo "SETUP_FAILED"; exit 1; }
echo "  ✓ uv"

# 2) Python 3.12 (managed by uv) + packages
if [ -z "$(py_path)" ]; then
  "$UV" venv --quiet --python 3.12 "$HOME_DIR/.venv" || { echo "SETUP_FAILED"; exit 1; }
fi
PY="$(py_path)"
"$UV" pip install --quiet --python "$PY" -r "$CODE/requirements.txt" || { echo "  ✗ Python packages"; echo "SETUP_FAILED"; exit 1; }
echo "  ✓ Python + packages"

# 3) the rest (cross-platform, in Python)
exec "$PY" "$CODE/setup/install.py" --home "$HOME_DIR" $MODE
