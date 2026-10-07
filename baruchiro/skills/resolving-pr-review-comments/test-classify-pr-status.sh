#!/usr/bin/env bash
# Self-check for classify-pr-status.jq: one fixture per status.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MARKER="$(cat "$SCRIPT_DIR/../../shared/agent-reply-marker.txt")"

classify() {
  jq -L "$SCRIPT_DIR" --arg marker "$MARKER" -r 'include "classify-pr-status"; classifyPr($marker) | .status' <<<"$1"
}

pr() {
  jq -n -c "{
    repo: \"o/r\", number: 1, title: \"t\", url: \"u\", baseRefName: \"main\", headRefOid: \"head\", isDraft: $1,
    reviewThreads: {nodes: $2}, reviews: {nodes: $4}, comments: {nodes: $5},
    commits: {nodes: [{commit: {statusCheckRollup: {contexts: {nodes: $3}}}}]}
  }"
}

human='{isResolved:false,comments:{nodes:[{author:{login:"me"},body:"fix this",reactionGroups:[]}]}}'
answered="{isResolved:false,comments:{nodes:[{author:{login:\"me\"},body:\"fix\",reactionGroups:[]},{author:{login:\"me\"},body:\"done $MARKER\",reactionGroups:[]}]}}"
cr_unliked='{isResolved:false,comments:{nodes:[{author:{login:"coderabbitai"},body:"nit",reactionGroups:[{content:"THUMBS_UP",viewerHasReacted:false}]}]}}'
cr_liked='{isResolved:false,comments:{nodes:[{author:{login:"coderabbitai"},body:"nit",reactionGroups:[{content:"THUMBS_UP",viewerHasReacted:true}]}]}}'
ci_ok='{name:"build",status:"COMPLETED",conclusion:"SUCCESS"}'
ci_bad='{name:"build",status:"COMPLETED",conclusion:"FAILURE"}'
ci_wait='{name:"build",status:"IN_PROGRESS",conclusion:null}'
cr_run='{name:"CodeRabbit",status:"IN_PROGRESS",conclusion:null}'
cr_done='{name:"CodeRabbit",status:"COMPLETED",conclusion:"SUCCESS"}'
cr_review_head='[{author:{login:"coderabbitai"},commit:{oid:"head"}}]'
cr_review_old='[{author:{login:"coderabbitai"},commit:{oid:"old"}}]'
cr_skip='[{author:{login:"coderabbitai"},body:"Review skipped: base branch is not the default"}]'

check() {
  local want=$1; shift
  local got; got=$(classify "$(pr "$@")")
  [ "$got" = "$want" ] || { echo "FAIL: want $want, got $got" >&2; exit 1; }
}

check draft:needs-agent true "[$human]" "[]" "[]" "[]"
check draft:needs-you true "[$answered]" "[]" "[]" "[]"
check draft:needs-you true "[$cr_unliked]" "[]" "[]" "[]"
check draft:needs-agent true "[$cr_liked]" "[]" "[]" "[]"
check draft:clean true "[]" "[]" "[]" "[]"
check ready:ci-failing false "[]" "[$ci_bad,$cr_done]" "$cr_review_head" "[]"
check ready:cr-pending false "[]" "[$ci_ok,$cr_run]" "[]" "[]"
check ready:cr-pending false "[]" "[$ci_ok]" "$cr_review_old" "[]"
check ready:cr-not-triggered false "[]" "[$ci_ok]" "[]" "$cr_skip"
check ready:cr-no-activity false "[]" "[$ci_ok]" "[]" "[]"
check ready:ci-pending false "[]" "[$ci_wait,$cr_done]" "$cr_review_head" "[]"
check ready:ready false "[]" "[$ci_ok,$cr_done]" "$cr_review_head" "[]"
check ready:needs-you false "[$cr_unliked]" "[$ci_ok,$cr_done]" "$cr_review_head" "[]"
echo "ok"
