---
name: resolving-pr-review-comments
description: Use when the user wants to fetch, triage, or clear unresolved review threads on one or more GitHub pull requests, wants PR review feedback (human or CodeRabbit) implemented or answered before merging, or invokes a recurring "/goal"-style batch to drain open review comments and confirm CI is green.
---

# Resolving PR Review Comments

## Overview

Drains unresolved, actionable review threads on one or more PRs, in parallel, without re-litigating already-settled discussion or double-answering threads you already answered. The fetch-and-filter step is a script, not agent judgment — reliable now, and the place to add filters later (by path, age, keyword) without touching the rest of the workflow. Grouping and actually handling each comment stays agent judgment; that's not something a script should decide.

"Review comments" means inline code-review threads (the ones with resolved/unresolved state) — not general PR conversation/issue comments, which have no resolution state. Stay scoped to threads unless the user separately asks about the PR's conversation tab.

## Step 1: Fetch actionable threads (script, not agent judgment)

Run `fetch-actionable-threads.sh OWNER REPO PR_NUMBER` (in this skill's directory) for each PR. It calls `gh api graphql` directly (paginated) and returns only threads that need action *right now* — no LLM filtering, no risk of miscounting on a long thread list. A thread is included by default only if **all** of:

- unresolved (`isResolved: false`)
- not already last-answered by an agent (see the marker in Step 3) — otherwise you'd re-answer your own reply every pass
- not a CodeRabbit-only thread, unless the human already 👍'd it (see below)

Flags to widen it when you actually need to: `--include-resolved`, `--include-answered`, `--include-coderabbit`. Add further filters (by path, author, comment age, keyword in body) as additional `jq` clauses inside the script — that's the extension point, don't bolt filtering logic onto the agent side.

**CodeRabbit rule:** CodeRabbit comments are excluded unless the human has reacted 👍 to that specific comment — that reaction is the human's explicit "yes, act on this" signal. Don't act on an un-liked CodeRabbit comment even if it looks correct; that's not your call to make by default.

**CodeRabbit body slimming:** for any comment authored by CodeRabbit, `body` is automatically reduced to just its severity/tag line plus its "🤖 Prompt for AI Agents" block (dropping the prose, diff, and committable-suggestion boilerplate around it) — that block already states the file, line, and action needed, so this saves context without losing anything actionable. If a CodeRabbit comment has no such block (e.g. a withdrawal reply, a "Learnings added" note), `body` is left as the full original text — treat a slimmed body as complete, not as missing context. Human comments are always passed through untouched.

Each returned thread looks like:

```json
{
  "id": "PRRT_kwDOGlbzG86aYUF-",
  "isResolved": false,
  "isOutdated": false,
  "path": "apps/notifications/src/notification-channel/app-push-channel.service.ts",
  "line": 41,
  "comments": {
    "nodes": [
      {
        "databaseId": 3810902650,
        "url": "https://github.com/OWNER/REPO/pull/3114#discussion_r3810902650",
        "author": { "login": "the-reviewer" },
        "body": "who ask you to consider timeout? trust the library please.",
        "createdAt": "2026-08-19T07:26:23Z",
        "reactionGroups": [{ "content": "THUMBS_UP", "viewerHasReacted": false }]
      }
    ]
  }
}
```

Two IDs you need later, both already in this output — don't re-fetch to get them:
- **Thread ID** (`PRRT_...`) — the top-level `id`. Used to resolve/unresolve.
- **Comment ID** (numeric) — `databaseId` of the most recent comment in `comments.nodes`. Used to reply.

## Step 2: Group by subject (agent judgment, not scripted)

Group the actionable threads into small clusters — same file, same feature area, or same theme. Target a few threads per group. Don't make one giant group (kills parallelism) and don't make one group per comment (loses shared context between related comments, wastes dispatch overhead). This is a judgment call based on what the threads actually say — there's no deterministic rule for it, so it stays at the orchestrating-agent level, not in the fetch script.

## Step 3: Dispatch one agent per group, in parallel

Send all group-handling agents in a single message with multiple Agent tool calls (plus the CI-check agents from Step 4 — everything in Step 3 and 4 runs in the same batch). Each agent's prompt must be self-contained: repo, PR number, and for every thread in its group — the thread ID, the comment ID, the file/line, the full comment body(ies) (including prior back-and-forth, since a thread can hold a multi-comment conversation), and this instruction:

> For each thread: either implement the requested code change, or reply via `mcp__GitHub__add_reply_to_pull_request_comment` (needs the numeric comment ID) with an answer. End the reply body with this exact line on its own: `<!-- resolving-pr-review-comments:agent-reply -->` — it's invisible when rendered on GitHub, and it's how the fetch script tells your replies apart from the human's when both of you comment on the same PR. Then apply the resolve rule below and use `mcp__GitHub__pull_request_review_write` with `method: resolve_thread` (needs the thread ID) only if it's earned.

**Resolve rule:** resolve a thread only if your reply (or code change) added no new information or decision the reviewer still needs to see. If your reply requires their judgment or introduces something new (a design tradeoff, an open question, "say the word if you want X instead"), leave it unresolved — reviewer's call, not yours.

## Step 4: CI status, in parallel with Step 3

One agent per PR, dispatched in the same message as the group agents, checking `mcp__GitHub__pull_request_read` with `method: get_check_runs` (per-job detail) — use `get_status` only if you just need the single combined state. If something failed, that agent investigates and fixes it (same rules as any CI failure: root cause, not retry-and-pray).

## Step 5: Local code changes must be pushed before CI or "done" mean anything

Step 4's CI check only reflects what's already on the remote. If any Step 3 agent edited files instead of (or in addition to) replying, a green check run at this point is checking the *previous* commit — it says nothing about the fix you just made. Don't treat CI-green or an empty Step 1 fetch as done while local changes sit uncommitted.

1. Summarize what changed (repo, files, one line each) and get the user's go-ahead before committing — standing rule, no exceptions for "the skill said so." **Unless the task that invoked this skill already told you to commit and push** (e.g. the `/goal` condition names it, or the user's request said "commit and push when done") — that instruction is the explicit approval; don't ask again, commit and push directly.
2. After pushing, re-run Step 1's fetch and Step 4's CI check against the new commit. A push can trigger new review activity (CodeRabbit re-reviews on new commits, humans may reply) — a fetch or CI result from before the push is stale and doesn't count.
3. If the fresh fetch surfaces new actionable threads, take them through Step 2 onward.

## Done signal

This skill's pass is fetch → group → handle → (commit/push if there were code changes) → CI-check. "Done" is mechanically checkable, not a judgment call: Step 1's script returns an empty list on every PR (or every remaining thread was deliberately left open awaiting reviewer judgment — expected, not a failure), CI is green on every PR **against the latest pushed commit**, and no local changes from this pass are left uncommitted without the user's explicit say-so. Re-fetching after any push is required to know this — threads resolved or answered in this pass drop out of Step 1's next run, and the human (or CodeRabbit) may have replied again in the meantime.

Whether and how often to repeat this pass belongs to whatever is driving the overall task (a `/goal`-style directive, or however the user invoked this) — not to this skill. Don't build a loop into this skill's own instructions; just leave the done-condition unambiguous enough that the caller can check it.

If driven by Claude Code's `/goal`: its evaluator judges the condition from the conversation transcript, not by re-running anything itself. State the check's actual result in plain text at the end of each pass (e.g. "fetch-actionable-threads.sh returned [] for PR #3114 and #220; get_check_runs all success on both, against commit abc1234 which includes this pass's fixes") — don't just act on it silently, or the evaluator has nothing to read, and don't cite a CI result from before a push you just made. Phrase the `/goal` condition itself to name the full loop, not just the check, e.g. `/goal draining resolving-pr-review-comments on PR #3114 and #220 — commit and push any fixes, then done when the fetch script returns [] for both and CI check runs are all success on both against the latest pushed commit`. If the condition doesn't authorize commit/push, the run will (correctly) stop to ask before committing — phrase it explicitly if you want the loop to carry through unattended.

## Common mistakes

- Fetching via REST comments/issue-comments endpoints, or the MCP `get_comments`/`get_reviews` methods — none of them carry `isResolved`, so you can't tell what's actually still open.
- Using the thread ID where a comment ID is required (or vice versa) — `resolve_thread`/`unresolve_thread` take the thread ID (`PRRT_...`); `add_reply_to_pull_request_comment` takes the numeric `databaseId`.
- Forgetting the agent-reply marker — without it, the next pass can't tell your reply from the human's and will re-process a thread you already answered.
- Acting on a CodeRabbit comment the human hasn't 👍'd.
- Resolving a thread that raised a question or tradeoff the reviewer hasn't weighed in on yet, just because you replied to it.
- One dispatch per individual comment instead of per logical group — burns agent-dispatch overhead and loses cross-comment context within a thread.
- Declaring done off a CI run or fetch result from before a push — CI-green on the pre-fix commit, or a fetch taken before the fix landed, proves nothing about the fix.
- Committing/pushing without the user's go-ahead when the invoking task never authorized it — the exception is narrow (the task/goal must actually say so), not assumed.
