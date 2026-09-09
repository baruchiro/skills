#!/usr/bin/env bash
# Deterministically fetch review threads on a PR and filter to the ones that
# actually need agent action right now. No LLM judgment involved in filtering.
#
# Usage: fetch-actionable-threads.sh OWNER REPO PR_NUMBER [flags]
#   --include-resolved    also include threads where is_resolved=true
#   --include-coderabbit  also include coderabbit-authored threads the human hasn't 👍'd
#   --include-answered    also include threads whose last comment is already an agent reply
#
# Default (no flags) = unresolved AND not-already-agent-answered AND
# (not coderabbit-only OR human 👍'd it). That's "needs action now".
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OWNER=$1; REPO=$2; PR=$3; shift 3

include_resolved=false
include_coderabbit=false
include_answered=false
for arg in "$@"; do
  case "$arg" in
    --include-resolved) include_resolved=true ;;
    --include-coderabbit) include_coderabbit=true ;;
    --include-answered) include_answered=true ;;
    *) echo "Unknown flag: $arg" >&2; exit 1 ;;
  esac
done

MARKER_FILE="$SCRIPT_DIR/../../shared/agent-reply-marker.txt"
[ -f "$MARKER_FILE" ] || { echo "Missing $MARKER_FILE — the agent-reply marker is shared with code-review-publish and must not be hardcoded here." >&2; exit 1; }
AGENT_MARKER="$(cat "$MARKER_FILE")"

query='
query($owner:String!, $repo:String!, $pr:Int!, $cursor:String) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$pr) {
      reviewThreads(first:50, after:$cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          comments(first:50) {
            nodes {
              databaseId
              url
              author { login }
              body
              createdAt
              reactionGroups { content viewerHasReacted }
            }
          }
        }
      }
    }
  }
}'

all_threads='[]'
cursor_arg=(-F cursor=null)
while :; do
  page=$(gh api graphql -f query="$query" -F owner="$OWNER" -F repo="$REPO" -F pr="$PR" "${cursor_arg[@]}")
  threads=$(jq '.data.repository.pullRequest.reviewThreads.nodes' <<<"$page")
  all_threads=$(jq -n --argjson a "$all_threads" --argjson b "$threads" '$a + $b')
  hasNext=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage' <<<"$page")
  [ "$hasNext" = "true" ] || break
  next_cursor=$(jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor' <<<"$page")
  cursor_arg=(-f cursor="$next_cursor")
done

jq -L "$SCRIPT_DIR" --arg marker "$AGENT_MARKER" \
   --argjson includeResolved "$include_resolved" \
   --argjson includeCoderabbit "$include_coderabbit" \
   --argjson includeAnswered "$include_answered" '
  include "slim-coderabbit-body";
  map(
    . as $t |
    ($t.comments.nodes[-1]) as $last |
    (all($t.comments.nodes[]; .author.login | ascii_downcase | contains("coderabbit"))) as $isCoderabbit |
    (any($t.comments.nodes[]; any(.reactionGroups[]?; .content == "THUMBS_UP" and .viewerHasReacted))) as $humanLiked |
    ($last.body // "" | contains($marker)) as $lastIsAgent |
    select($includeResolved or ($t.isResolved | not)) |
    select($includeAnswered or ($lastIsAgent | not)) |
    select($includeCoderabbit or ($isCoderabbit | not) or $humanLiked) |
    .comments.nodes |= map(
      if (.author.login | ascii_downcase | contains("coderabbit")) then
        .body |= slimCoderabbitBody
      else . end
    )
  )
' <<<"$all_threads"
