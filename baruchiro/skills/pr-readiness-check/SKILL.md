---
name: pr-readiness-check
description: Determine whether a PR is actually worth reviewing right now, before spending effort on the code itself — is it stalled waiting on the author, does it look active but actually leave a maintainer's ask unaddressed, and is CI/mergeability clean. Use this first whenever the user is handed a PR and hasn't decided yet whether to dig in — "is this ready to review", "what's the status on this PR", "has X been addressed", "should I look at this now", or just being pointed at a PR/link with no further instruction. This is the gate before a deep review, not the deep review itself — once a PR comes back READY (or the user decides to look anyway despite it being stalled), hand off to `pr-safety-verdict` for the actual SAFE/RISKY/BREAKING analysis of the code. Do not run the two together automatically; report readiness first and let the user choose.
---

# PR Readiness Check

Reviewing a PR's code is wasted effort — and misleading to report on — if the PR is simply sitting idle waiting on the author, or if a prior reviewer's ask was never actually addressed despite the branch looking "active." This skill answers one question only: **is this PR at a point where a code review is actually useful right now, or is something else blocking it first.** It doesn't look at whether the code is good; that's the next skill's job.

Keep the output short — a verdict plus the one or two facts that justify it. This is meant to be read in a few seconds before the user decides what to do next.

## Step 1 — Fetch the conversation, not just the diff

Fetch `get_comments` (top-level conversation), `get_review_comments` (inline threads), `get_commits`, and the PR's `mergeable_state`/CI status. You don't need the diff itself for this check — that's the next skill's job once you're through this gate.

If given only a PR number/URL, resolve owner/repo from the current git remote unless told otherwise.

## Step 2 — Establish conversation state

Line up comments, threads, and commits by timestamp.

1. **Filter out noise.** Discard bot housekeeping (stale-bot, labeler comments), the PR author's own comments (pings, "any update?", apologies for delay, "will do soon" with no accompanying action), and reactions/threads with no actionable ask. What's left is the substantive asks: a maintainer/collaborator requesting a change (split the PR, rebase, fix X, provide evidence for Y), or a review-bot/human finding on a specific line.

2. **Find the most recent substantive ask and compare its timestamp to the most recent commit:**
   - **No commit since that ask** → the PR is **STALLED**. Name who asked, what they asked for, and since when nothing has moved. A reply promising future action ("will do soon", "on it") does not count as movement — only a commit does.
   - **Commits exist since that ask** → don't assume they're a response just because they exist. Check whether the new commits actually touch what was asked (same file/function for a code fix; an actual rebase for a "please rebase" ask; the PR literally split for a "split this into N PRs" ask — check `mergeable_state` too, since "please rebase" isn't satisfied by unrelated new commits on top of a still-unresolved conflict). If the new activity is unrelated to the ask, the PR is **PARTIALLY ADDRESSED**: say so explicitly, the ask is still open despite the branch looking active. If it does address the ask, the PR is actively being iterated on — continue to step 3.

3. **Apply the same logic per review-comment thread**, not just to the top-level conversation. GitHub marks a thread `is_outdated` once the diff at that location has changed since the comment — but that only means the code moved, not that the concern was resolved. You don't need to re-derive the fix yourself at this stage (that's the deep review's job) — just note which threads are `isResolved: false` regardless of `isOutdated`, since an outdated-but-unresolved thread is still an open ask a reviewer would want to know about before diving in. A thread marked `isResolved: true` is closed regardless of how it was closed — take that at face value here.

4. **Check mergeability and CI** on the current head: a merge conflict or red CI is itself a reason review is premature, independent of the conversation-state analysis above — note it even if the conversation looks otherwise clean.

## Step 3 — Output

```
## Readiness: READY | STALLED | PARTIALLY ADDRESSED

<1-3 sentences: who asked what and since when, if not READY; which threads are still unresolved regardless of outdated status; CI/mergeable state if not clean>
```

Rules:
- **STALLED** and **PARTIALLY ADDRESSED** both mean "don't deep-review yet without knowing this" — the difference is STALLED means literally nothing has moved, PARTIALLY ADDRESSED means something moved but not the thing that was asked for. Say which one and why in the same breath as the verdict, don't make the reader infer it.
- **READY** doesn't mean the code is good — it means there's no process reason to hold off looking. Still name any currently-unresolved threads in the one-line summary (e.g. "READY — 2 open threads on error handling, otherwise active") so the user knows what a deep review would need to cover, without doing that review yourself.
- Always end with a one-line pointer to the next step: "Run `pr-safety-verdict` for the code review" when READY, or "Run it anyway if you want to review despite the above" when not — the choice is the user's, not yours to make by skipping straight to a code review.
- If asked about multiple PRs, give one readiness block per PR, in the order asked, no shared preamble.
- This is the default depth. Only go longer if the user asks a follow-up about a specific thread or ask.
