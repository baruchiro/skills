---
name: pr-walkthrough
description: Use when a user wants to review a pull request (or a set of matching PRs across repos, e.g. frontend+backend) interactively, chunk by chunk, adding review comments rather than reading a full diff dump
---

# PR Walkthrough

## Overview

Reviews one or more related pull requests one small piece at a time, ordered by how the change actually flows (e.g. request → handler → data layer → response), so the user can absorb, question, and leave comments as they go. Read-only toward the code — feedback becomes PR review comments, not edits.

## When to Use

- User wants to review/understand a PR, or a set of PRs across repos that implement one feature (e.g. a frontend PR and its matching backend PR)
- User wants a branch reviewed before a PR even exists yet
- NOT for a quick "does this PR look OK" sanity check — just answer directly for that

## Workflow

### 1. Resolve scope

One or more targets, each either:
- an explicit PR ref (`owner/repo#123` or a PR URL), or
- the current branch in a repo with no PR ref given — diff against its base (`gh pr diff` if a PR already exists for it, else `git diff <base>...HEAD`)

For a full-stack review, the user gives one target per repo (e.g. one frontend PR + one backend PR) — treat all of them as one review.

### 2. Build the review (delegate — keep raw diffs out of this conversation)

Dispatch a fresh subagent (general-purpose, `model: haiku`, low effort) per review — this step reads full diffs and possibly a linked task, which is exactly the content you don't want filling this context. Give it, self-contained:

- The resolved target(s) from step 1
- Instructions to:
  1. Fetch each target's diff and PR description (`gh pr view --json title,body,...`, `gh pr diff`, or `git diff` for a no-PR branch)
  2. Look in the PR description for a referenced task — a GitHub issue (`#123`, "Fixes #123") or a ClickUp reference (`CU-xxxxxxx` id or URL) — and fetch it (`gh issue view`, or the ClickUp MCP `clickup_get_task`) for the *why* behind the change. No reference found → skip, don't guess one.
  3. Trace the flow the change implements across all targets (e.g. user action → frontend call → API contract → backend handler → data layer → response) and use that — not file order, not repo order — to plan chunks: 10-30 diff lines each, one concept per chunk, splitting a large file across chunks and merging several files sharing one trivial change into one chunk.
  4. Pull test files (`*.test.*`, `*.spec.*`, `__tests__/`, `test/`, `tests/`, `*_test.<ext>`, or the repo's equivalent convention) out of flow-ordering entirely. Bundle all of them into one final `collapsed` chunk per repo — `summary` names the files/counts and which source chunks they cover, `diff` still holds the full test diff so it can be expanded on request, but it's not shown by default.
  5. Write `.pr-walkthrough/<pr-number-or-branch>.json` in each repo (schema below), adding `.pr-walkthrough/` to that repo's `.gitignore` if not already present.
- Instructions to return only a short summary: task/issue title (if any), one-line description of the flow, chunk count per repo — never the raw diffs or the full chunk list.

State file shape:
```json
{
  "repo": "owner/repo",
  "ref": "123",
  "task": {"source": "github|clickup|none", "id": "...", "title": "..."},
  "order": ["chunk-id-1", "chunk-id-2"],
  "chunks": {
    "chunk-id-1": {
      "files": ["path/to/file"],
      "flowPosition": "backend: request validation",
      "diff": "```diff\n...\n```",
      "shown": false,
      "comments": [{"file": "path", "line": 42, "body": "..."}]
    },
    "chunk-id-tests": {
      "files": ["path/to/file_test.go", "path/to/other_test.go"],
      "flowPosition": "tests",
      "collapsed": true,
      "summary": "2 test files, 46 lines, covering chunk-id-1's validation path",
      "diff": "```diff\n...\n```",
      "shown": false,
      "comments": []
    }
  },
  "position": null
}
```

### 3. Walk the chunks

Never read a state file directly — always go through `scripts/store.sh` so you only ever load the one chunk you need:

```
scripts/store.sh next <state-file>                              # next unshown chunk, marks it shown
scripts/store.sh get <state-file> <chunk-id>                     # re-show a chunk without advancing
scripts/store.sh comment <state-file> <chunk-id> <path> <line> "<body>"
scripts/store.sh status <state-file>                             # {total, shown, remaining, comments}
```

Present what `next` returns: flow position, the diff, a couple sentences of context — skip the prose entirely for a trivial chunk (version bump, single doc line). If `collapsed` is true (the bundled test chunk), show only its `summary` line, not the diff — expand it only if the user asks to see the tests. Stop and wait — don't call `next` again until the user says "next"/"continue" or asks something.

### 4. Handle interruptions in place

- **Questions** — answer about the current chunk or the overall change, then resume.
- **Feedback to leave as a comment** — `scripts/store.sh comment ...`. Don't touch the code.
- Always confirm which chunk comes next after resolving a side question.

### 5. Submit comments

When the user is done (or asks to wrap up early): for each repo, run `scripts/store.sh comments <state-file>` to collect its recorded comments, summarize them, and **ask before posting anything**. On confirmation, dispatch the `code-review-publish` agent (`agents/code-review-publish.md` in this plugin — invoke via the Agent tool, `subagent_type: personal:code-review-publish`) with the PR reference and a findings list built from each comment: `description` = body, `severity` = "P3" (informational — these are walkthrough remarks, not a formal review), `evidence` = the chunk's `diff`, `fix` = omit unless the user gave one. Never auto-post; one dispatch per repo/PR.

## Quick Reference

| Chunk size | 10-30 diff lines |
| Scope per chunk | one concept |
| Ordering | by flow, not by file/repo |
| Code changes | never — comments only |
| Reading state | always via `store.sh`, never the raw file |
| Test files | bundled into one collapsed summary chunk, not walked individually |

## Common Mistakes

- Chunking by file order instead of tracing the actual flow first — do step 2's flow-tracing before splitting
- Fetching diffs and building the chunk plan in the main conversation — delegate to a subagent so raw diffs don't fill context
- Reading the whole state file with `cat`/`jq` ad hoc instead of `store.sh` — defeats the point of the store
- Posting review comments without confirming first
- Ignoring a task reference in the PR description — it's often the only place the *why* is written down
- Walking test files one by one like source chunks — collapse them, expand only on request
