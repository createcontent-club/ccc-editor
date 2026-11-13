#!/usr/bin/env bash
# CI: the whole client path on a short test video — name → prepare → transcript → choices → build → export.
#   bash tests/ci-edit.sh <data folder>
# Fails on any non-zero exit (a failed check is exit 4, an engine crash exit 5).
set -euo pipefail
DATA="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$ROOT/plugins/ccc-editor"
ccc() { CCC_HOME="$DATA" bash "$P/ccc" "$@"; }

WORKDIR="${RUNNER_TEMP:-/tmp}/ccc ci (test) folder"   # spaces + parentheses, like real client paths
mkdir -p "$WORKDIR"
VID="$WORKDIR/CI test video.mp4"
cp "$ROOT/tests/fixtures/ci-speech.mp4" "$VID"

echo "::group::name"
ccc name "$VID"
NAME="$(ccc name "$VID" | head -1)"
echo "::endgroup::"

echo "::group::prepare"
ccc prepare "$VID"
echo "::endgroup::"

echo "::group::transcript"
ccc transcript "$NAME" --words
echo "::endgroup::"

echo "::group::choices"
ccc choices "$NAME" format=basic hook_text='How the editor | works' hook_style=box hook_position=below \
  caption_style=karaoke font=ccc color=yellow pacing=fast camera=zoom
echo "::endgroup::"

echo "::group::build"
ccc build "$NAME"
echo "::endgroup::"

OUT="$WORKDIR/CI test video-CCC-edit.mp4"
test -s "$OUT" || { echo "export missing: $OUT"; ls -la "$WORKDIR"; exit 1; }
echo "✓ exported $(wc -c < "$OUT") bytes"

echo "::group::rebuild (cached listening, versioned export)"
ccc build "$NAME"
test -s "$WORKDIR/CI test video-CCC-edit-v2.mp4" || { echo "v2 export missing"; exit 1; }
echo "::endgroup::"

echo "::group::clean + restore"
ccc clean "$NAME"
ccc cut "$NAME"        # restores the cleaned media from the original by itself
echo "::endgroup::"

ccc support-info
