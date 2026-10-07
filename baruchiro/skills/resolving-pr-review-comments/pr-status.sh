#!/usr/bin/env bash
# One status line per PR: which loop it is in and whose turn it is.
#
# Usage: pr-status.sh OWNER/REPO#NUMBER [OWNER/REPO#NUMBER ...]
# Prints a JSON array. Classification lives in classify-pr-status.jq.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ $# -gt 0 ] || { echo "Usage: $0 OWNER/REPO#NUMBER [...]" >&2; exit 1; }

MARKER_FILE="$SCRIPT_DIR/../../shared/agent-reply-marker.txt"
[ -f "$MARKER_FILE" ] || { echo "Missing $MARKER_FILE" >&2; exit 1; }
AGENT_MARKER="$(cat "$MARKER_FILE")"

query='
query($owner:String!, $repo:String!, $pr:Int!) {
  repository(owner:$owner, name:$repo) {
    pullRequest(number:$pr) {
      number title url isDraft baseRefName headRefOid
      reviewThreads(first:100) {
        pageInfo { hasNextPage }
        nodes {
          isResolved
          comments(first:50) {
            nodes { author { login } body reactionGroups { content viewerHasReacted } }
          }
        }
      }
      reviews(last:50) { nodes { author { login } commit { oid } } }
      comments(last:50) { nodes { author { login } body } }
      commits(last:1) {
        nodes { commit { statusCheckRollup { contexts(first:100) { nodes {
          __typename
          ... on CheckRun { name status conclusion }
          ... on StatusContext { context state description }
        } } } } }
      }
    }
  }
}'

for spec in "$@"; do
  [[ "$spec" =~ ^([^/]+)/([^#]+)#([0-9]+)$ ]] || { echo "Bad PR spec: $spec (want OWNER/REPO#NUMBER)" >&2; exit 1; }
  repo_path="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  gh api graphql -f query="$query" -F owner="${BASH_REMATCH[1]}" -F repo="${BASH_REMATCH[2]}" -F pr="${BASH_REMATCH[3]}" |
    jq -e --arg repo "$repo_path" '.data.repository.pullRequest | select(.reviewThreads.pageInfo.hasNextPage | not) | .repo = $repo' ||
    { echo "$spec: PR not found or has more than 100 review threads" >&2; exit 1; }
done |
  jq -L "$SCRIPT_DIR" --arg marker "$AGENT_MARKER" -s 'include "classify-pr-status"; map(classifyPr($marker))'
