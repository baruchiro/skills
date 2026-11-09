#!/usr/bin/env bash
set -euo pipefail

scope="${1:-}"
case "$scope" in
  oss) org_filter="-org:bewith-dev"; base="$HOME/source" ;;
  work) org_filter="org:bewith-dev"; base="$HOME/source/with" ;;
  *) echo "usage: scope-repos.sh <oss|work> [login]" >&2; exit 2 ;;
esac
login="${2:-$(gh api user --jq .login)}"

prs=""
for role in reviewed-by commenter; do
  for page in $(seq 1 10); do
    sleep 3
    chunk=$(gh api -X GET search/issues \
      -f q="is:pr $role:$login -author:$login $org_filter" \
      -f per_page=100 -f page="$page" \
      --jq '.items[] | "\(.html_url)\t\(.repository_url | sub("^.*/repos/"; ""))"')
    [ -n "$chunk" ] && prs+="$chunk"$'\n'
    [ "$(printf '%s' "$chunk" | grep -c .)" -lt 100 ] && break
  done
done

normalize() {
  sed -E 's#^.*github\.com[:/]+##; s#\.git$##; s#/+$##' | tr '[:upper:]' '[:lower:]'
}

printf '%s' "$prs" | sort -u | cut -f2 | { grep . || true; } | sort | uniq -c | sort -rn |
while read -r count repo; do
  dir="$base/${repo#*/}"
  path=MISSING
  if [ -d "$dir/.git" ] || git -C "$dir" rev-parse --git-dir >/dev/null 2>&1; then
    want=$(printf '%s' "$repo" | tr '[:upper:]' '[:lower:]')
    git -C "$dir" remote -v 2>/dev/null | awk '{print $2}' | normalize | grep -xF "$want" >/dev/null && path="$dir"
  fi
  printf '%s\t%s\t%s\n' "$count" "$repo" "$path"
done
