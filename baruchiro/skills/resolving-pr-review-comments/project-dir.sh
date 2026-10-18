#!/usr/bin/env bash
# Prints the project folder that holds pr-status.md and pr-review-links.json:
# the nearest folder below $HOME with a *.code-workspace file (a multi-repo workspace),
# else the git repo root, else $PWD. Inside a git repo, info/exclude keeps both files out of commits.
set -euo pipefail

dir=$PWD
while [ "$dir" != / ] && [ "$dir" != "$HOME" ]; do
  compgen -G "$dir/*.code-workspace" >/dev/null && { echo "$dir"; exit 0; }
  dir=$(dirname "$dir")
done

root=$(git rev-parse --show-toplevel 2>/dev/null) || { pwd; exit 0; }
exclude="$(git rev-parse --git-common-dir)/info/exclude"
mkdir -p "$(dirname "$exclude")"
for name in pr-status.md pr-review-links.json; do
  grep -qxF "/$name" "$exclude" 2>/dev/null || echo "/$name" >>"$exclude"
done
echo "$root"
