#!/usr/bin/env bash
# Every place that spells the agent-reply marker out must match the shared file.
set -euo pipefail

SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SHARED_DIR")"
MARKER="$(cat "$SHARED_DIR/agent-reply-marker.txt")"

fail=0
for f in \
  "$PLUGIN_DIR/skills/resolving-pr-review-comments/SKILL.md" \
  "$PLUGIN_DIR/agents/code-review-publish.md"
do
  if ! grep -qF -- "$MARKER" "$f"; then
    echo "FAIL: marker not found verbatim in ${f#"$PLUGIN_DIR"/}" >&2
    fail=1
  fi
done

# The fetch script must read the marker, never hardcode its own copy.
fetch="$PLUGIN_DIR/skills/resolving-pr-review-comments/fetch-actionable-threads.sh"
if grep -qF -- "$MARKER" "$fetch"; then
  echo "FAIL: fetch-actionable-threads.sh hardcodes the marker; it should read agent-reply-marker.txt" >&2
  fail=1
fi
if ! grep -q 'agent-reply-marker.txt' "$fetch"; then
  echo "FAIL: fetch-actionable-threads.sh does not read agent-reply-marker.txt" >&2
  fail=1
fi

[ "$fail" -eq 0 ] && echo "OK: agent-reply marker consistent across the plugin"
exit "$fail"
