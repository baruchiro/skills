#!/usr/bin/env bash
# Query/mutate a pr-walkthrough state file without reading the whole thing into context.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: store.sh <command> <state-file> [args...]

  next <state-file>
      Return the next unshown chunk (in flow order), mark it shown. Prints "null" if none left.

  get <state-file> <chunk-id>
      Re-print a chunk already shown, without advancing.

  comment <state-file> <chunk-id> <path> <line> <body>
      Append a comment to a chunk.

  status <state-file>
      Print { total, shown, remaining, comments }.

  comments <state-file>
      Flatten every recorded comment across all chunks, enriched with chunk id/flowPosition/diff,
      ready to hand to the code-review-publish agent as a findings list.
EOF
}

cmd="${1:-}"
file="${2:-}"
[ -z "$cmd" ] && { usage; exit 1; }
[ -z "$file" ] && { echo "error: state file required" >&2; exit 1; }
[ -f "$file" ] || { echo "error: no such state file: $file" >&2; exit 1; }

write() {
  local tmp
  tmp="$(mktemp "${file}.XXXXXX")"
  cat >"$tmp"
  mv "$tmp" "$file"
}

case "$cmd" in
  next)
    id=$(jq -r '.order[] as $id | select(.chunks[$id].shown | not) | $id' "$file" | head -n1)
    if [ -z "${id:-}" ] || [ "$id" = "null" ]; then
      echo "null"
      exit 0
    fi
    jq --arg id "$id" '.position = $id | .chunks[$id].shown = true' "$file" | write
    jq --arg id "$id" '.chunks[$id] + {id: $id}' "$file"
    ;;

  get)
    id="${3:?chunk-id required}"
    jq --arg id "$id" '.chunks[$id] + {id: $id}' "$file"
    ;;

  comment)
    id="${3:?chunk-id required}"
    path="${4:?path required}"
    line="${5:?line required}"
    body="${6:?body required}"
    jq --arg id "$id" --arg path "$path" --argjson line "$line" --arg body "$body" \
      '.chunks[$id].comments += [{file: $path, line: $line, body: $body}]' "$file" | write
    echo "ok"
    ;;

  status)
    jq '{
      total: (.order | length),
      shown: ([.order[] as $id | select(.chunks[$id].shown)] | length),
      remaining: ([.order[] as $id | select(.chunks[$id].shown | not)] | length),
      comments: ([.chunks[].comments[]?] | length)
    }' "$file"
    ;;

  comments)
    jq '[.order[] as $id | .chunks[$id] as $c | $c.comments[]? | {
      chunkId: $id,
      flowPosition: $c.flowPosition,
      diff: $c.diff,
      file: .file,
      line: .line,
      body: .body
    }]' "$file"
    ;;

  *)
    usage
    exit 1
    ;;
esac
