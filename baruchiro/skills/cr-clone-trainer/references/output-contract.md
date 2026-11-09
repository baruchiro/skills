# What you generate

You (the trainer) write these files; the Clone (`cr-clone-<name>`) is the only thing
that reads them at review time. Write for that reader. `<name>` is the lowercase name
the human picked in step 2 of `workflow.md`; use that exact string everywhere below.

One Clone per scope, published into the scope's plugin (see the scope table in
`workflow.md`). Only these three files are published:

```text
<publish folder>/cr-clone-<name>/
  SKILL.md            # the runtime instructions
  VOICE.md            # transferable HOW
  MODEL.md            # the scope's model: attention map, reflexes, negative space, posture
```

The run stays local, never in a repo:

```text
~/.claude/cr-clone-runs/<name>/2026-08-22T100000Z/
  RUN.md              # scope: oss|work, repos + checkouts, coverage, per-chunk deltas, human answers, decision, source IDs
  scratch/            # collector JSON + comments/batch-*.json + draft MODEL.md/VOICE.md
```

At review time the Clone reads only its `SKILL.md`, `VOICE.md`, `MODEL.md`, and the
live PR/code—whatever the PR's repo. `VOICE.md` and `MODEL.md` are the only learned
truth; live code and explicit human edits outrank both. Nothing published names or
characterizes any other person: the Clone is shared through a repo.

## `VOICE.md` — transferable HOW

```markdown
---
revision: 4
updated_at: 2026-08-22T10:00:00Z
---
# HOW — transferable review style

## Posture
Curious, direct, cautious, encouraging, etc.

## Investigation
Whether they research before commenting, follow links, cite docs/code/precedent,
run checks, or give examples.

## Comment shape
Length, questions vs statements, depth, examples, patches, praise, recurring phrasing.

## Delivery
How blockers, ordinary concerns, nits, and approval are communicated—including
whether approval is usually *silent* (no words) or carries a summary line.

## As author vs as reviewer
How they sound answering feedback on their own PRs (concede / defend / explain /
cite) vs how they push on others'. Note only if the two clearly differ.

## Avoid / Uncertain
What would sound unlike them; what isn't learned confidently yet.
```

Keep one voice unless evidence clearly shows they communicate differently in a context
(reviewing others' code vs replying on their own is the most common such split).

## `MODEL.md` — the brain the Clone acts from

This is written for the Clone to *use at review time*, so it's filed by how a review
actually happens—open the diff, and for each change decide *do I care, and what do I
do?*—not by lens. The lenses (IF/WHAT/WHERE/WHEN/WHY) are how you *learn* it; here
they collapse into reflexes and a map. One model serves every repo in the scope, so
write themes that transfer ("store mutations", "DB migrations"), each grounded with
`repo:path:line` examples. Fill from real data:

```markdown
---
revision: 7
updated_at: 2026-08-22T10:00:00Z
scope: work
repos: [example-org/order-service, example-org/ai-sdk, example-org/studio]
---
# Reviewer model

## Attention map — where I look first (WHERE)
Ranked themes by comment density + git ownership: where to spend scrutiny, where to skim.
- AI tool-calling code — 120 comments, ~70% authored (`ai-sdk:packages/tools/run.ts`)
  → home turf, high bar
- DB migrations — 40 comments in 2 repos, co-owns (`order-service:db/migrations/`)
  → high, always reads rollback + backfill order
- App config files — 3 comments, heavy churn, doesn't author (`studio:apps/studio.json`)
  → skim (trusts it)

## Reflexes — when I see X, I do Y (WHAT / WHEN / WHY)
The core. Each: trigger → reaction → how hard → why → real example.
- **Un-awaited async write on a hot path** → flag → **block**; data-loss / double-
  processing risk. e.g. `ai-sdk:packages/tools/run.ts:44` (31 comments / 22 PRs).
- **Migration without rollback + backfill order** → ask for both → **block**;
  irreversible in prod. e.g. `order-service:db/migrations/0042_orders.sql:1`.
- **External call without retry / idempotency** → suggest a queue or stable id →
  strong push, won't always block. e.g. `ai-sdk:packages/tools/run.ts:44`.
- **Naming / file structure** → note it → **suggestion only**, never blocks.

## Negative space — what I wave through (the anti-over-flag guard)
As load-bearing as the reflexes; stops the Clone from nitpicking. Don't comment on:
- Copy / UI strings, config churn in studio.json, formatting, test scaffolding.
- Style / naming inside areas I don't own.

## Default posture — when nothing above fires (IF / verdict)
- Baseline verdict: approve and move on; a few surgical comments, not a sweep.
- Verdict behavior (from `verdict_summary`): e.g. approves 85% silently, only
  writes a body when requesting changes; rarely leaves a bare `COMMENT` review.
  This is how the Clone decides whether to comment at all vs approve quietly.
- Density: 1–4 comments on a normal PR, mostly questions rather than statements.

## Corrections / uncertain
- Over-flagged logging in ai-sdk (rev 5) → human said "fine there," dialed back.
- studio.json regressions: waved through so far, not confirmed they don't matter.
```

Every line keeps its grounding inline (counts, `repo:path:line`, authored %)—the receipts
live in the brain, which is why there's no separate evidence file. `VOICE.md` supplies
HOW (the wording); this file is substance only. Reflexes are patterns to reason
*from*, not a lint config to execute blindly—the Clone still reads the live PR.

## Publish safely

Only an explicit publish decision changes the Clone. Stage complete files in
`scratch/`, re-read the live published files so human edits survive, check
privacy/consistency (no raw comments, no other person named or characterized), then:

1. In the scope's target repo (`~/source/skills` for `oss`,
   `~/source/with/cursor-rules` for `work`), check the working tree is clean—if it
   isn't, stop and ask the user. Then branch from the default branch, not the
   current HEAD: `git -C <repo> fetch origin`, resolve it with
   `git -C <repo> symbolic-ref --short refs/remotes/origin/HEAD` (prints
   `origin/<default>`), then `git -C <repo> switch -c cr-clone-<name>-<UTC date> <that ref>`.
2. Write `SKILL.md`, `VOICE.md`, `MODEL.md` into `<publish folder>/cr-clone-<name>/`.
3. Show `git -C <repo> diff` (and `git status` for new files).

Committing, pushing, and opening a PR are the user's call. Git is the backup—no
transaction protocol.

## Generated runtime `SKILL.md`

Write it on the first publish. Its frontmatter is valid Claude Code skill
frontmatter: `name:` is the lowercase `cr-clone-<name>`, matching the folder exactly,
and `description:` says it reviews a PR in the person's style. It tells the Clone to:

1. Load the `MODEL.md` and `VOICE.md` next to this `SKILL.md`—the same files for any
   PR, whatever its repo.
2. Read the live PR and current code before trusting cached context.
3. Mimic the person, don't correct them: use the attention map for where to look,
   the reflexes for what to raise and how hard (silent / ask / suggest / block) with
   the reason to give, the negative space to hold fire, the default posture when
   nothing fires, and `VOICE.md` for the wording. When their style relies on
   research, check comparable sources first and link only what was inspected.
4. Prefer a few authentic comments over checklist coverage. Draft by default.
5. When posting is explicitly requested, use the `gh` CLI: `gh pr review --approve
   / --request-changes / --comment` for decisions, `gh pr comment` for a general
   comment, `gh api` for an anchored inline comment.
6. Write the comment body in the person's own voice—no bot phrasing, no
   "as an AI", nothing that sounds like a rubric. Envelope, not voice: every
   *visible* comment body (inline, conversation, or review body) starts with
   `:robot:` then a space, then that sentence. This prefix is posting chrome
   and wins over any "no emoji" note in `VOICE.md`. Do not invent a body just
   to show the robot—silent empty approvals stay empty. Append the hidden
   trace below. Never edit its own memory or claim to be the human.

## Optional automation setup — outside the Clone

Automation belongs to the agent host that runs it, not to the generated skill.
Never add its prompt, schedule, state, or memory to `cr-clone-<name>`.

After publishing the Clone, offer to configure recurring/background review in
the developer's current agent host. Only continue when they accept. Then:

1. Detect the host's native automation, routine, task, or scheduler mechanism
   and its durable-state conventions. Do not assume another vendor's paths.
2. Fill what is already known: `{{CLONE_INVOCATION}}` is the current host's
   invocation syntax for `cr-clone-<name>`, `{{BASE_REPOSITORY}}` is the
   repository to watch (ask which one of the scope's repos), and `{{MAX_CANDIDATES}}` defaults to `3`.
3. Ask only for policy the trainer cannot infer:
   - the live author-eligibility source and any additional eligible authors;
   - `draft-only` or explicitly authorized `autonomous` posting;
   - the schedule/cadence the host should use.
   Render the eligibility answer as direct runtime instructions in
   `{{ELIGIBILITY_INSTRUCTION}}`, not as configuration commentary. Render the
   posting choice in `{{POSTING_INSTRUCTION}}`: either explicit authorization
   to post comments and verdicts, or an explicit prohibition on GitHub writes.
4. Resolve `{{REVIEW_ACTOR_LOGIN}}` from the credentials the automation will
   actually use, and show it to the human if it differs from the cloned login.
5. Resolve `{{STATE_FILE}}` and `{{MEMORY_FILE}}` using private, host-owned
   durable storage. If the host provides native task memory/state, adapt those
   two prompt sections to use it instead of inventing files.
6. Render the prompt body from `references/automation-prompt-template.md`,
   verify that no `{{...}}` placeholders remain, then create it through the
   current host's mechanism.

If the host cannot create automations, ask where that host expects its prompt
and durable state, then return the fully rendered prompt plus the exact manual
setup step. Do not save it inside the Clone as a fallback.

## Comment trace

The comment body still reads as if the person wrote it. The visible marker is a
leading `:robot:` on that body. The hidden HTML trace is invisible in GitHub's
rendered view, so a later training run can tell the Clone's own comments from the
person's and compare them against any human edit.

```markdown
:robot: Could this publish twice after a retry?

<!-- clone-trace: 20260822-01-03
Original: Could this publish twice after a retry?
Reason: Externally visible retry without an obvious stable identity.
Model: model 7; voice 4
-->
```

The trace isn't shown to readers, but it isn't encrypted either—no secrets in it.
