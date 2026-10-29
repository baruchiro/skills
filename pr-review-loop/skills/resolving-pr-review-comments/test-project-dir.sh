#!/usr/bin/env bash
# Self-check for project-dir.sh: workspace folder wins, then git root (excluded from git), then $PWD.
set -euo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/project-dir.sh"
sandbox=$(cd "$(mktemp -d)" && pwd -P); trap 'rm -rf "$sandbox"' EXIT
export HOME="$sandbox"

expect() {
  [ "$2" = "$3" ] || { echo "FAIL $1: expected $3, got $2" >&2; exit 1; }
  echo "ok $1"
}

mkdir -p "$sandbox/plain" "$sandbox/workspace/repo/src" "$sandbox/solo/src"
touch "$sandbox/workspace/team.code-workspace"
git -C "$sandbox/workspace/repo" init -q
git -C "$sandbox/solo" init -q

expect "workspace folder" "$(cd "$sandbox/workspace/repo/src" && "$SCRIPT")" "$sandbox/workspace"
expect "git root" "$(cd "$sandbox/solo/src" && "$SCRIPT")" "$sandbox/solo"
expect "excluded from git" "$(grep -c '^/pr-status.md$' "$sandbox/solo/.git/info/exclude")" "1"
expect "json excluded from git" "$(grep -c '^/pr-status.json$' "$sandbox/solo/.git/info/exclude")" "1"
(cd "$sandbox/solo" && "$SCRIPT" >/dev/null)
expect "exclude not duplicated" "$(grep -c '^/pr-status.md$' "$sandbox/solo/.git/info/exclude")" "1"
expect "plain folder" "$(cd "$sandbox/plain" && "$SCRIPT")" "$sandbox/plain"
