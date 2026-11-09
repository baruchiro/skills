# Reviewer Clone workflow

Learn how one person reviews PRs, then save that as a Clone that reviews new PRs the
same way. Two principles:

- **Mimic, don't fix.** Clone their real themes and biases—what they obsess over,
  wave through, and push back on. Never impose your own "best practices."
- **Correlate, don't narrate.** Learn from many small comments, each checked against
  the actual code it was written on—never from re-reading whole PRs (that overfits).

## What you're learning: the lenses

You're building one thing—a model of how this person reviews—looked at through these
lenses. Use what fits; don't force a rigid matrix. This is the only place they're
defined. For every lens, the *negative space* is signal too: what they wave through
tells you as much as what they flag, so capture both sides.

- **IF** — do they weigh in at all, or wave it through
- **WHAT** — the concerns they keep flagging vs the ones they never raise
- **WHERE** — the parts of the system they dig into and own vs the parts they skim
- **WHEN** — how far they take it: a question, a suggestion, a hard block—or silence
- **WHY** — the reason under the comment (risk, data loss, maintainability, cost…)
- **HOW** — tone, and whether they research / link / cite. This is their voice.

Absence is a real part of the picture, but it's ambiguous—"didn't comment" can mean
"trusts it" or "those PRs just didn't need me." So paint both sides, then treat the
gaps as questions to confirm, not proof they don't care.

One Clone covers one **scope**—every repo of that kind the person reviewed—so there's
just one model file, `MODEL.md`, for all of them (plus `VOICE.md` for the voice). You
build it up as you read—draft in the run's `scratch/`—and publish it only when the
human says so. Each claim carries its own grounding inline (the comments + code + git
that back it, as `repo:path:line`), so there's no separate "evidence" file. `RUN.md` is
the run's journal (repos and checkouts, what each chunk added, decisions); a paused run
resumes from it.

| Scope | Repos | Checkouts | Publish folder |
|---|---|---|---|
| `oss` | every repo outside `bewith-dev` | `~/source/<repo>` | `~/source/skills/baruchiro/skills/` |
| `work` | every `bewith-dev` repo | `~/source/with/<repo>` | `~/source/with/cursor-rules/skills/` |

Raw data (collected comments, drafts, `RUN.md`) stays local in
`~/.claude/cr-clone-runs/<clone-name>/`. Never write it into a repo.

## How the run goes

```text
1. SCOPE        Pick oss or work, list the repos they reviewed and find each checkout.
       │
2. SET UP       Find the scope's existing Clone or let them name a new one, then
       │        start a local run folder.
       │
3. GATHER       Download every review comment they left across those repos (split
       │        into chunk-files), and in parallel read git to see what they own.
       │
4. LEARN  ┌───► Read the comments one chunk at a time, filling in the model above.
       │  │     When a pattern looks real, open the code they commented on to confirm.
       │  │     When a real fork appears, ask them a sharp question right there.
       │  └──── Repeat until new chunks stop teaching you anything.
       │
5. DECIDE       They pick: save it / keep going / pause.
       │
6. SAVE         Write the model to files the Clone can reuse, then report.
```

You (main agent) do all the thinking, and run the quick read-only git/code lookups
yourself. Offload to a fresh subagent (cheap fast model, full prompt, one job) only
for genuinely heavy read-only work; it never decides anything or touches saved memory.
If one fails, dispatch it again.

Surface these six as todos, one in progress at a time; while reading chunks show
which (e.g. "chunk 6 of 11"). Between routine tool calls, say nothing.

## 1 — Pick the scope and its repos

```bash
gh api user --jq '.login, .name'    # login + display name — you need both in step 2
```

Ask with one `AskUserQuestion` titled `Pick scope`: `oss` (repos outside `bewith-dev`)
or `work` (`bewith-dev` repos). Then list the repos they reviewed in that scope:

```bash
"${CLAUDE_SKILL_DIR}/scripts/scope-repos.sh" "$SCOPE" "$LOGIN"
```

It prints `<PR count>\t<owner/repo>\t<checkout path or MISSING>`, busiest first (a
checkout matches when any of its remotes points at the repo). Show the table and
propose dropping repos under 5 PRs—they add little. Then stop and ask about every
`MISSING` repo: clone it into the scope's checkout folder, or skip it. Never clone a
repo the user didn't ask for. Record the final repo → checkout table in `RUN.md`.

## 2 — Set up the Clone and the run

Each scope has at most one Clone, in that scope's publish folder. Look for it:

```bash
ls -d "$PUBLISH_DIR"/cr-clone-*/ 2>/dev/null | grep -v '/cr-clone-trainer/$'
```

**Found one → it keeps its name.** Never rename or re-ask. Its live `VOICE.md` and
`MODEL.md` are your starting point, and anything the human typed into them wins.

**None → check for a paused, unpublished run** in `ls -d ~/.claude/cr-clone-runs/*/`
(any Clone name not in the publish folder). If its `RUN.md` is for this scope, offer
to resume it; that keeps its name.

**Still none → they name it.** One `AskUserQuestion` titled `Name your Clone`, before any
downloading. Say what you're doing in one line ("I'm going to build a reviewer Clone
for your work reviews — what should it be called?"), then offer candidates built from
*their real login and display name*, plus `Other` so they can type their own:

```text
cr-clone-adird         ← from login AdirD
cr-clone-adir-duchan   ← from display name Adir Duchan
cr-clone-adird-work    ← login + scope
```

Whatever comes back — a pick or free text — normalize it before you create anything:
force lowercase, prefix `cr-clone-` if they left it off, and collapse everything outside
`[a-z0-9-]` into single dashes. The folder, the generated `SKILL.md` `name:`, and every
later reference to the Clone all use that one normalized string. Clone names are always
lowercase, even when the GitHub login isn't, and `cr-clone-trainer` is reserved — if they
ask for it, ask again.

Then make the run folder `~/.claude/cr-clone-runs/<clone-name>/<UTC timestamp>/` with a
real timestamp (e.g. `2026-08-22T100000Z`). If the latest run there is paused, offer to
resume it from its `RUN.md` and draft `MODEL.md` instead. Don't overwrite a published
Clone just because someone said "init"—that needs explicit confirmation.

## 3 — Gather comments, scan ownership (parallel)

Run the collector yourself, once, with every chosen repo (don't reinvent it in shell):

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/collect-review-activity.py" \
  --repo "$OWNER1/$REPO1" --repo "$OWNER2/$REPO2" --login "$LOGIN" \
  --output "$RUN/scratch/review-activity.json"
```

It grabs every interaction point the person left on PRs (never issues, and never
anyone else's comments—GraphQL filters by author), each tagged with its `repo`, a
`kind` and an `as_author`/`as_reviewer` side:

- **inline** review comments (file + line) and **inline_reply** threads;
- **conversation** (non-inline) comments, including on their own PRs;
- **review_summary** verdicts—approve / request-changes / comment plus any body.

Comments Claude wrote under their account carry a marker (`ai_marked`); the collector
keeps them out of the chunk-files and counts them in `counts.excluded_ai_comments`.
Unmarked agent text can still slip through, mostly as `as_author` replies on their own
PRs ("Done in 3f2a1c"). Weigh `as_author` replies lightly, and ignore any reply that
reads like an agent's status report. Treat a `:robot:` comment with a `clone-trace` as
the Clone's words, not theirs.

It splits the ones with words into small chunk-files
(`scratch/comments/batch-*.json`) and counts areas (`area_counts`, keyed
`<repo-name>/<2 path segments>`), kinds (`kind_counts`), and author-vs-reviewer side
(`author_side_counts`); `per_repo` gives PRs and comments per repo. Wordless verdicts
(silent approvals) carry no text to batch, so they land in `verdict_summary`
instead—read it for the person's **default posture**: `silent_approval_ratio`, state
breakdown, how often they attach a summary body. Read
`review-activity.summary.json` first—these counts give you **WHERE**, **WHEN**, and
the IF/silence picture over everything, not a sample. `verdict_summary.truncated_prs`
lists `[repo, number]` pairs for PRs with over 100 reviews (or 100 comments in one
review) whose tail was cut off. The script pauses between GitHub calls and waits out
rate limits on its own, so many repos take minutes—run it in the background. If it
fails, fix args/auth and retry once; don't improvise a big script.

While the collector runs, scan ownership yourself in each checkout so you know which
areas this person actually *wrote*, not just commented on:

```bash
git -C "$CHECKOUT" shortlog -sne --all | head            # top authors in this repo
git -C "$CHECKOUT" log --author="<login>" --oneline | wc -l   # their footprint
```

That's the ownership half of **WHERE**; `area_counts` is the attention half. You don't
need a full architecture write-up—just enough to overlay ownership on attention.

## 4 — Build the model, chunk by chunk

Read one chunk-file at a time, filling in the lenses in the draft `MODEL.md`
(`scratch/`). Never load every comment at once, and never conclude from a single
comment. For each chunk, in order:

1. Read it (~40 interaction points). Each carries a `kind` and side: inline
   review comments have a file/line; `inline_reply`/`conversation` points marked
   `as_author` are them answering feedback on their *own* code (a different voice
   from reviewing others'); `review_summary` points carry the verdict `state`.
2. Add what's new to your notes; note what just repeats what you knew. Read
   author-side replies for voice under pushback (do they concede, defend, cite?),
   not for review reflexes.
3. When a pattern looks real, open the actual file they commented on—in the checkout
   of that comment's `repo`—and check git there:

   ```bash
   git -C "$CHECKOUT" log --author="<login>" --oneline -- <path>   # do they write here?
   git -C "$CHECKOUT" blame -L <line>,+1 -- <path>                  # this line's owner
   git -C "$CHECKOUT" log --oneline -n 5 -- <path>                  # how often it changes
   ```

4. Jot the delta in `RUN.md` ("chunk 5: +1 recurring concern, nothing else").

**Stop early when it stops paying off:** if 2–3 chunks in a row add nothing new,
you've seen enough—move to the questions even if chunks remain. Reading all chunks
is fine too. A theme that shows up in several repos is stronger than one confined to
one repo; note which it is.

What to trust: the same concern across unrelated PRs, suggested fixes, links/precedent
they cite, specific praise, human corrections of a Clone comment, and areas they both
wrote and commented on. The **aggregate** verdict pattern is also trustworthy—a high
`silent_approval_ratio` over hundreds of reviews is a real default posture, and a
consistent "always writes a one-line summary when blocking" is a real delivery habit.
Weak—never a conclusion on its own: a *single* bare approval, "LGTM", or one silent
merge—an area they didn't comment on is a question to ask, not proof they don't care.
Only save something as learned when the human confirms it, the behavior repeats
independently (or shows up strongly in `verdict_summary`), or a correction to a Clone
comment makes it explicit.

While reading, draft freely by lens—that's how you think—each claim carrying its
grounding inline (this *is* the receipts):

```markdown
## WHAT — recurring themes
- "await / use a queue" — 31 comments / 22 PRs in 3 repos; grounded
  `ai-sdk:packages/tools/run.ts:44` (they author it) → strong WHEN gate?

## WHERE — focus + ownership
- ai-sdk/packages/tools: 120 comments, ~70% authored → high
- studio/apps/config (studio.json): 3 comments, heavy churn → unknown (silence fork)
```

These are your working notes, filed by lens. At publish (step 6) you reshape them into
the brain the Clone actually reads—attention map, reflexes, negative space, default
posture—per `output-contract.md`. Lenses are how *you* learn; reflexes are how *it* acts.

### Ask when a real fork appears

This is where the skill earns its trust. A great question makes the human go **"whoa,
it gets me—I *do* review like that."** You're holding up a mirror: naming a reflex of
theirs, in their own code, that they act on but maybe never spelled out. The best ones
name a pattern they hadn't consciously noticed—then instantly recognize as themselves.
Get this right and everything else is forgivable; get it generic and the Clone feels
like a bot.

Calibration isn't a phase after learning—it happens inside the loop. When a chunk
raises a genuine fork you can't settle from evidence, stop and ask right there, then
keep reading. `AskUserQuestion` titled `Calibrate Clone`, 1–3 questions, **only when a real
fork exists**. Learn the shape from the contrast (fill names from real data):

```text
❌ "You push back on abstractions. Want Clone to flag over-engineering?"
   horoscope — abstract, unnamed, true of everyone. no aha.
✅ "You author most of the ai-sdk tool-calling code and comment on it heavily —
   reading that as your home turf. Want Clone to go hard there and lower its bar?"
   - Yeah, lock it in — that's my area
   - I know it well, don't over-scrutinize it
   - Nah, that was just these PRs
```

```text
❌ "On #163 you flagged the un-awaited sandbox call — was that a big deal?"
   a memory quiz about one incident. they won't even remember it.
✅ "Across repos you keep catching un-awaited queue writes (e.g. run.ts:44). A hard
   gate for you, or something you raise and trust the author on?"
   - Hard gate — I don't approve without it
   - I push hard but won't block
   - Case by case
```

```text
❌ "How should Clone treat studio.json? block / request-changes / suggest / ask / ignore"
   a config ladder in robot-speak; pre-answers nothing real.
✅ "Changes to studio.json mostly sail past you with no comment. Is that 'I trust it,
   skim it' or just 'those PRs didn't need me'?"
   - Trust it — Clone can go light there
   - Didn't come up — don't downgrade it
   - Actually I'd want regressions there caught
```

Zero forks in a session is fine. Ask again only when new evidence raises a real
uncertainty.

## 5 — They decide

Show them the model you built and what's still open, with honest counts (comments
downloaded / chunks read of total / codebase mapped). Suggest stopping when more
chunks keep confirming the same picture and no open question would change how reviews
go—your judgment, not a formula. They pick: publish, keep going, look harder at a
named area, or pause. Stopping is not the same as permission to publish.

## 6 — Save and report

Only an explicit "save/publish" choice changes what the Clone actually uses. Record
the accepted learning + source IDs in `RUN.md`, then reshape your lens-notes into the
finished `VOICE.md` and `MODEL.md` (the brain format in `output-contract.md`, written
for the Clone) in `scratch/`, re-read the live published files so any hand-edits
survive, and publish them per `output-contract.md`: on a branch in the scope's target
repo, then show the diff. Committing and opening a PR are the user's call. A
paused/failed run resumes from `RUN.md` + the draft `MODEL.md`.

Then report: status, honest coverage (per repo), why you stopped and what the human
chose, what was learned (the model + their voice) and anything dropped, the Clone path,
the branch, and the local run path. Offer to configure the Clone in the user's current
automation/task host. If accepted, follow the host-owned setup in
`output-contract.md`; do not put automation files or runtime state in the Clone
folder. The Clone is a transparent, correctable stand-in—never claim it's the person.
