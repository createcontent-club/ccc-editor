#!/usr/bin/env bash
# CCC editor — first-time setup (macOS + Windows/Git Bash). No admin password needed.
#   bash setup/bootstrap.sh <data folder> [--no-whisper]
#   bash setup/bootstrap.sh <data folder> --check     → INSTALLED / NOT_INSTALLED / UPDATE_NEEDED / REPAIR_NEEDED: …
# Failures end with SETUP_FAILED + SETUP_REASON: network | disk | permission | os | other; everything is also
# written to <data folder>/setup.log (for support).
# Installs: uv (Python manager) → Python 3.12 → Python packages → setup/install.py (Node, ffmpeg, fonts,
# models, Remotion). Everything goes into <data folder>, except uv itself (~/.local/bin).
set -uo pipefail

CODE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME_DIR="${1:?usage: bootstrap.sh <data folder> [--check|--no-whisper]}"
shift
MODE="${1:-}"
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1 ;; *) WIN=0 ;; esac
# Windows: "C:/Users/…" → "/c/Users/…" (dvotačka u PATH-u), i UTF-8 izlaz — Python na Windows-u u pipe piše
# cp1252 pa bi install.py pao na prvom "→ ✓" pre nego što išta instalira (QA 0.8.0, P0).
if command -v cygpath >/dev/null 2>&1; then HOME_DIR="$(cygpath -u "$HOME_DIR")"; fi
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
unset PYTHONHOME

py_path() {
  if [ -x "$HOME_DIR/.venv/bin/python" ]; then echo "$HOME_DIR/.venv/bin/python"
  elif [ -x "$HOME_DIR/.venv/Scripts/python.exe" ]; then echo "$HOME_DIR/.venv/Scripts/python.exe"; fi
}
plugin_version() { sed -n 's/.*"version": *"\([^"]*\)".*/\1/p' "$CODE/.claude-plugin/plugin.json" 2>/dev/null | head -1; }

if [ "$MODE" = "--check" ]; then
  if [ -z "$(py_path)" ] || [ ! -f "$HOME_DIR/installed.json" ]; then echo "NOT_INSTALLED"; exit 0; fi
  # version AND the parts themselves (a deleted model or font is REPAIR_NEEDED, not INSTALLED)
  "$(py_path)" "$CODE/setup/install.py" --home "$HOME_DIR" --check 2>/dev/null || echo "REPAIR_NEEDED: python"
  exit 0
fi

die() { echo "  ✗ $1"; echo "SETUP_FAILED"; echo "SETUP_REASON: ${2:-other}"; exit 1; }

mkdir -p "$HOME_DIR" || die "can't create $HOME_DIR" permission
# everything below also goes to setup.log (support asks for it: `ccc support-info` includes its tail)
exec > >(tee -a "$HOME_DIR/setup.log") 2>&1
echo ""; echo "===== setup $(date '+%Y-%m-%d %H:%M:%S') · plugin $(plugin_version) · $(uname -sm)"

if [ "$WIN" = 0 ] && command -v sw_vers >/dev/null 2>&1; then
  MACV="$(sw_vers -productVersion)"; MAJ="${MACV%%.*}"
  [ "$MAJ" -ge 12 ] 2>/dev/null || die "This Mac runs macOS $MACV; the CCC editor needs macOS 12 (Monterey) or newer — update macOS in System Settings → General → Software Update." os
fi
if [ -z "$(py_path)" ]; then  # fresh install: Python + packages + model + engine ≈ 3.5 GB
  FREE_KB="$(df -Pk "$HOME_DIR" 2>/dev/null | awk 'NR==2 {print $4}')"
  if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt 4000000 ] 2>/dev/null; then
    die "Not enough disk space: setup needs about 4 GB free, the disk has $((FREE_KB / 1048576)) GB. Free some space and run setup again." disk
  fi
fi

echo "▶ Preparing the CCC editor (one time, ~5–10 minutes)…"

# 1) uv — official standalone Python manager (installs to ~/.local/bin, no admin)
UV="$(command -v uv || true)"
for c in "$HOME/.local/bin/uv" "$HOME/.local/bin/uv.exe" "$HOME/.cargo/bin/uv"; do [ -z "$UV" ] && [ -x "$c" ] && UV="$c"; done
if [ -z "$UV" ]; then
  echo "  … installing uv (Python manager)"
  if [ "$WIN" = 1 ]; then
    powershell.exe -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex" || die "installing uv failed" network
    UV="$HOME/.local/bin/uv.exe"
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh || die "installing uv failed" network
    UV="$HOME/.local/bin/uv"
  fi
fi
[ -x "$UV" ] || die "uv not found after install" other
echo "  ✓ uv"

# 2) Python 3.12 (managed by uv) + packages
if [ -z "$(py_path)" ]; then
  # --clear: prekinuta ili pokvarena .venv (python nestao) se sama popravi umesto "already exists" zauvek
  "$UV" venv --quiet --clear --managed-python --python 3.12 "$HOME_DIR/.venv" \
    || "$UV" venv --quiet --clear --python 3.12 "$HOME_DIR/.venv" || die "creating the Python environment failed" network
fi
PY="$(py_path)"
# Exact, hash-checked package versions per platform (setup/locks/, made by tools/make_release.py — QA P1-5):
# the same versions CCC tested, never a broken newer release. macOS 12–13 gets builds that still support it.
LOCK=""
if [ "$WIN" = 1 ]; then LOCK="windows-x64"
else
  ARCH="$(uname -m)"; [ "$ARCH" = "arm64" ] && A=arm64 || A=x64
  [ "${MAJ:-14}" -ge 14 ] 2>/dev/null && LOCK="macos14-$A" || LOCK="macos12-$A"
fi
if [ -f "$CODE/setup/locks/$LOCK.txt" ]; then
  "$UV" pip install --quiet --python "$PY" --require-hashes -r "$CODE/setup/locks/$LOCK.txt" || die "installing Python packages failed" network
else
  echo "  · no package lock for this computer ($LOCK) — using the newest compatible versions"
  "$UV" pip install --quiet --python "$PY" -r "$CODE/requirements.txt" || die "installing Python packages failed" network
fi
# yt-dlp follows the websites (they change every few weeks) → always the newest, on every setup/update
"$UV" pip install --quiet --python "$PY" --upgrade yt-dlp || echo "  · yt-dlp update skipped (offline?) — web clips may fail"
echo "  ✓ Python + packages ($LOCK)"

# 3) the rest (cross-platform, in Python)
exec "$PY" "$CODE/setup/install.py" --home "$HOME_DIR" $MODE
