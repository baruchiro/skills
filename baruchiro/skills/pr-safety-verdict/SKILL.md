---
name: pr-safety-verdict
description: Give a fast, reviewer-facing verdict on whether a PR or diff in any repo is safe to merge — SAFE, RISKY, or BREAKING — instead of a long research writeup. Checks for (1) unnecessary/stale comments, (2) whether existing working code paths still behave identically (backward compatibility), (3) whether a new feature added alongside an existing working flow degrades gracefully instead of risking that flow on failure, and (4) repo hygiene — stray files, unsolicited meta files, blocking I/O in async code, unvalidated file-path inputs, placeholder tests, and a schema that doesn't enforce what its own docs claim. Use this whenever the user asks to review a PR, look at a diff, check a pull request for breaking changes, asks "is this safe to merge/approve", pastes a GitHub PR URL/number and asks what to watch out for, or says they don't have time to dig into a PR themselves and just want the important part — or more generally, wants to know whether a PR is even ready to be reviewed or merged right now. Trigger even if they only give a PR number or link with no other instructions — that alone means they want this fast verdict, not an essay. This is the *quick* pass; for an actual deep, chunk-by-chunk interactive read of the diff (not just a verdict), use `pr-walkthrough` instead — this skill's job is to help decide whether that deeper read is even warranted right now.
---

# PR Safety Verdict

A reviewer facing a steady stream of PRs does not have time to re-derive the control flow of every changed function by hand, or to walk every PR through a full interactive review. This skill is the fast triage step: it hands back only what a reviewer needs to decide **does this PR need my attention at all right now, and if it does, does anything in it change what already worked or fail unsafely.** If the answer to the first question turns out to be "not yet" (it's stalled on the author), that's the headline — no need to characterize code nobody's finished changing.

The output is a verdict, not a report. If you catch yourself writing multiple paragraphs of narration about what you read, stop — compress it into the findings list. Once the user has this verdict, they decide whether to merge, ask for changes, or go deeper — a full interactive walkthrough is `pr-walkthrough`'s job, not this skill's; don't start narrating the diff chunk by chunk here even if a finding seems to deserve more discussion.

This is a generic, repo-agnostic version of the methodology — it works on any codebase. A repo can still carry its own specialized variant (e.g. one tuned to a particular domain's failure modes) as a project-scoped skill; prefer that one when it exists and this one otherwise.

## Step 1 — Get the actual diff

Don't review from the PR title/description alone — authors describe intent, not always the resulting control flow. Fetch:
- The diff itself (`get_diff` / `git diff`).
- Enough of the *surrounding* unchanged code (`get_file_contents` at the base ref, or `git show <base>:<path>`) to see what a changed function looked like **before**, not just the `+`/`-` lines in isolation. A three-line diff hunk is frequently only interpretable by seeing the `if/else` it's embedded in.
- If the change touches a core data/control path, check whether a test file exists for it and whether the diff touches test expectations too (see Check 1 below for why that matters).
- If this repo documents a convention for companion artifacts on a change (a changelog fragment, a changeset, a migration file) — check its `CONTRIBUTING.md`/`CLAUDE.md`/`README.md` once per review, don't assume one exists.
- If it's a real PR (not a bare diff/local branch), a quick glance at CI status and existing review comments — these are nearly free to fetch and change what "safe to approve" actually means right now: a RISKY-but-otherwise-fine diff with red CI or an unresolved reviewer objection isn't ready regardless of what the code analysis says. Skip this for a diff with no PR behind it (nothing to fetch).

If given only a PR number/URL, resolve owner/repo from the current git remote unless told otherwise.

### Conversation state — is this even ready to be (re-)reviewed?

Before spending effort on the checks below, work out where the PR actually sits in its own conversation. A full fresh review is wasted effort — and misleading to the reviewer — if the PR is simply sitting idle waiting on the author, or if a prior reviewer's ask was never actually addressed despite the branch looking "active."

Fetch `get_comments`, `get_review_comments` (threads), and `get_commits`, and line them up by timestamp. Then:

1. **Filter out noise.** Discard bot housekeeping (stale-bot, labeler comments), the PR author's own comments (pings, "any update?", apologies for delay), and reactions/threads with no actionable ask. What's left is the substantive asks: a maintainer/collaborator requesting a change (split the PR, rebase, fix X, provide evidence for Y), or a review-bot/human finding on a specific line.

2. **Find the most recent substantive ask and compare its timestamp to the most recent commit:**
   - **No commit since that ask** → say so plainly, and say it *first*, before anything else. This is a strong signal the PR is stalled waiting on the author, not something to hand back a fresh SAFE/RISKY/BREAKING verdict on as if it just landed. Name who asked, what they asked for, and since when nothing has moved.
   - **Commits exist since that ask** → don't assume they're a response just because they exist. Check whether the new commits actually touch what was asked (same file/function for a code fix; an actual rebase for a "please rebase" ask; the PR literally split for a "split this into N PRs" ask — check `mergeable_state` too, since "please rebase" isn't satisfied by unrelated new commits on top of a still-unresolved conflict). If the new activity is unrelated to the ask, say so explicitly: the ask is still open despite the branch looking active. If it does address the ask, treat it as being actively iterated on and proceed normally.

3. **Apply the same logic per review-comment thread**, not just to the top-level conversation. GitHub marks a thread `is_outdated` once the diff at that location has changed since the comment — but that only means the code moved, not that the concern was resolved. Read the current code at that location yourself and decide whether it actually addresses the finding, rather than trusting `is_outdated`/`is_resolved` at face value. A thread can be simultaneously "outdated" and still perfectly valid (the code moved but the same bug is still there), or outdated and genuinely fixed by later work — only reading the current lines tells you which.

## Step 2 — Run the four checks

Do these as an analysis pass over the diff you just read, not as separate tool-heavy investigations. Each check below produces zero or more findings; a clean check produces none, and that's a fine outcome — don't invent a finding to look thorough.

### Check 1: Comments

Flag any comment that would still be true and useful if you deleted the sentence and let the reader look at the code — that's the test for "unnecessary." Concretely:
- Restates what the line already says (`// increment counter` above `count++`).
- References the current PR/task/issue instead of a durable property of the code (`// added for the frame fix`, `// see #1153`) — this kind of comment is true today and wrong the day after the next refactor.
- Is stale relative to the code it sits next to (describes a branch or parameter that no longer exists after this diff).

Do **not** flag a comment that explains a non-obvious *why*: a workaround for a specific upstream quirk, an invariant the surrounding code depends on, a reason a seemingly-simpler alternative was rejected. Removing a comment like that would cost the next reader real time re-deriving what the author already knew.

### Check 2: Backward compatibility

For each changed function, ask: **which callers/inputs exercised this code before, and does the diff change what they get back?** Walk the control flow (branches, fallback chains, `??`/`||` defaults) as it was, not as it's described, and compare to the new version. Before you can answer "which callers," check whether the changed file is depended on by more than one caller — a shared base class, a shared utility, a common module several other files import — rather than assuming it's used in exactly one place. A quick grep/import search for the changed file's other usages (`grep -rl "from '\./<file>'"` or the language's equivalent) costs one tool call and tells you whether you're reviewing a single-consumer change or a blast-radius one. A change to shared code has as many "existing callers" as there are importers, and a risk that's negligible for one of them can be real for another with different data shapes.

Then classify the whole diff into exactly one of:

- **safe** — the change only adds a new branch/field/fallback that fires in cases that were previously broken, empty, or unreached (e.g. a `case`/`else if` that only fires when every existing branch already fell through to `undefined`/an error; a new optional field added to a type that was already optional and always `undefined` for this caller). Existing inputs that used to produce a defined, correct result still produce the identical result.
- **risky** — an existing, already-working branch's behavior changes for at least some previously-handled inputs (a fallback's priority order changes in a way that's reachable by real data, a formula used by an already-working path is altered, a default value changes). This doesn't mean reject it — it means the reviewer needs to know a working path is being touched, and ideally the PR shows evidence (a test, a log) that the *specific* previously-working case still holds.
- **breaking** — a public type, return shape, exported function signature, or on-disk/serialized format changes in a way an existing consumer would notice without opening this diff (a field renamed or removed, a required field added, a return type narrowed, a function that used to resolve now rejects for previously-valid input).

A diff can easily contain more than one of the branches above at once — e.g. two of a fallback chain's four branches are truly untouched while a third one's priority shifted. Don't average that into one vague "mostly safe" impression: name both halves, in that order, every time — untouched first, then changed:
1. **Unchanged:** name the specific existing branch(es)/condition(s) that still take the exact same path they did before this diff (this is the reassurance the reviewer needs so they don't have to re-derive it themselves — skip this sentence only if the diff truly touches every existing branch, which is rare).
2. **Changed:** name the one that doesn't, and why.

Write it as two clauses even when "unchanged" feels obvious enough to skip — it's the sentence most often dropped under time pressure, and it's the one that tells the reviewer the finding's actual blast radius rather than just its existence. A reordering or condition change only counts as **risky** if you can point to a plausible real-world input that reaches the changed branch differently than before — a change that's only theoretically reachable through data the diff's own input/response shape rules out is safe, not risky, so say why it's unreachable if you conclude that.

### Check 3: New-feature safety (graceful degradation)

New capabilities are frequently bolted onto an already-working core flow — an extra field, an extra network call, extra parsing of something that wasn't touched before. The core flow (the part that already produces correct results for users today) must survive the new part failing, because the new part is often exercised against conditions (a live API, an edge-case input, a page/response shape) the author's own testing won't fully cover.

For each such addition, trace what happens if it fails — throws, times out, or parses into garbage — and check:
1. **Is the failure contained?** The call is inside a `try/catch` (or equivalent) *at the right scope* — wrapping just the new feature's work, not accidentally swallowing errors from the core flow too. An `await`/blocking call for the new feature sitting outside any guard, in a place where an unhandled error reaches the caller, means one failure in the new part now fails an entire operation that used to succeed.
2. **Does failure degrade to the old behavior, not a wrong answer?** On failure the new field(s) should end up absent/`undefined`/`null` (i.e., exactly what existing consumers already saw before this PR), not a fabricated value. A fallback that computes a plausible-looking but unverified result is worse than leaving the field empty — it fails silently in the wrong direction.
3. **Does the new feature mutate shared state the core flow still relies on afterward?** Look for: reassigning/reusing an object, connection, or cursor the core path reads later, or reordering async work such that the new feature can win a race the old code didn't have.

If all three hold, the new feature is isolated and its own bugs are a quality issue, not a merge blocker. If any doesn't hold, that's the headline finding — it means shipping this PR risks regressing users who don't even care about the new feature.

Isolation from *failure* isn't the only cost worth naming, though — it's just the one that decides the verdict. A new capability can be perfectly safe by the three tests above and still change what every run does: an extra unconditional network round-trip, a new external dependency that can start failing tomorrow, added latency on every call. If this repo already has an established convention for opting out of that kind of cost elsewhere (a feature flag, a config option) and the new capability has no equivalent where a comparable existing feature does, that's worth one line in the closing summary even under a SAFE verdict. It's not a fifth tagged check; it's the kind of thing that belongs in the free-text line at the end of the output template.

### Check 4: Repo hygiene and conventions

These are checks about the diff itself rather than the runtime behavior it introduces — cheap to verify, easy for an author to overlook, and the kind of thing a maintainer otherwise has to flag by hand on every PR:

- **Stray files.** Any committed file that isn't part of the feature: scratch/summary docs (`NOTES.md`, `PLAN.md`, `REVIEW_SUMMARY.md`, anything describing *what was done* rather than being part of the change), build artifacts, dependency directories, env files. Ask why it's in the diff and recommend removal.
- **Unsolicited meta files.** A new `SECURITY.md`, `CONTRIBUTING.md`, GitHub issue/PR template, license file, or similar that the PR's stated goal didn't call for. Ask "what is this file and does this PR need it?" rather than assuming it's fine.
- **Blocking I/O in async/concurrent code.** A synchronous, blocking call (a sync filesystem read, a blocking HTTP call, a synchronous DB query) sitting inside code that's otherwise async/event-loop-based or expected to run concurrently. Require the non-blocking equivalent the language/runtime provides.
- **Path/security boundaries.** A file-path, identifier, or URL input used to reach the filesystem or another resource, without being validated as absolute/well-formed, confined to an allowlist, and — for filesystem paths specifically — symlink-resolved before the check (normalizing a path is not the same as dereferencing a symlink it points through).
- **Placeholder tests.** A test that asserts a tautology (`assert(true)`, re-checking a literal it just defined) instead of driving the real function/handler and asserting on its actual output or thrown error. Require assertions against real behavior.
- **Missing convention-required companion file.** Only applies if this repo documents such a convention (a changelog fragment, a changeset, a migration, a generated-docs update) in its `CONTRIBUTING.md`/`CLAUDE.md`/`README.md` — never invent a convention that isn't written down. If one is documented and this diff's change is the kind that convention covers, flag its absence.
- **Schema/prose drift.** A constraint stated only in a docstring, comment, or tool/API description (required, mutually exclusive, a specific format) that isn't actually enforced by the validation/schema layer (a Zod/pydantic/JSON-schema definition, a type signature, a runtime check). Prose that isn't enforced is a constraint that silently stops being true the next time someone edits the code without reading the comment.

## Step 3 — Output

Keep this to what a reviewer reads in ten seconds plus a skimmable list. If the conversation-state check above found that nothing has changed since the last substantive reviewer ask, lead with that — one or two plain-text sentences, before the verdict block, naming who asked, for what, and since when. That's a process fact, not a code finding, so it never becomes a bullet inside the verdict. Still produce the verdict block after it if the code itself is worth characterizing, but don't let it read like a routine "go ahead and merge" — the staleness is the headline.

Otherwise, use exactly this shape:

```
## Verdict: SAFE | RISKY | BREAKING

- [comments] path/to/file.ts:123 — <one-line finding>
- [compat] path/to/file.ts:45 — <one-line finding>
- [feature-safety] path/to/file.ts:67 — <one-line finding>
- [hygiene] path/to/file.ts:8 — <one-line finding>

<one or two sentences: the one thing to actually pay attention to before approving, or "nothing else to flag" if the list above is it>
```

Rules for this output:
- Every bullet is tagged with which check it came from (`comments`, `compat`, `feature-safety`, `hygiene`) and anchored to a real `file:line` — a finding the reviewer can't jump to isn't actionable. A stray/unsolicited file with no meaningful line still gets a bullet; use its path with no line number.
- Omit a section's bullets entirely if that check found nothing — don't write "No issues found" as a bullet, just leave it out.
- The verdict is for the *diff as a whole*: pick BREAKING if any single finding is breaking, else RISKY if any finding is risky, else SAFE. Hygiene findings never push the verdict past RISKY on their own (a stray file or a placeholder test is a cleanup ask, not a compatibility break) unless the hygiene finding is itself a security boundary violation, in which case treat it like a compat/feature-safety finding of the same severity. The verdict reflects the code, not the process — CI/review-thread status never changes it, that's separate information about whether *this* is a good time to act on it.
- CI status and open review threads (see Step 1) don't get their own tag — they're not a code finding — but if CI is red on the latest commit, or there's an unresolved reviewer comment asking for a real change, say so in one clause in the closing line (e.g. "also: `validate` is currently failing on the latest commit" / "also: an unresolved comment from `<reviewer>` asks for X"). Say nothing about CI/threads at all if they're clean — that's the common case and doesn't need a "CI is green" bullet to prove it.
- End with a one-line pointer to `pr-walkthrough` when the verdict is RISKY or BREAKING, or when the user seems to want to go deeper than a verdict — it does the chunk-by-chunk interactive read this skill deliberately skips. Skip the pointer on a clean SAFE verdict; don't push a deeper review nobody asked for.
- If asked about multiple PRs in one request, give one verdict block per PR, in the order asked, with no shared preamble.
- This is the default depth. Only go longer than this if the user asks a specific follow-up question about one of the findings — then answer that question directly, still without re-padding the rest of the review.
