---
name: pr-safety-verdict
description: Give a fast, reviewer-facing verdict on whether a PR or diff in any repo is safe to merge — SAFE, RISKY, or BREAKING — instead of a long research writeup. Checks for (1) unnecessary/stale comments, (2) whether existing working code paths still behave identically (backward compatibility), (3) whether a new feature added alongside an existing working flow degrades gracefully instead of risking that flow on failure, and (4) repo hygiene — stray files, unsolicited meta files, blocking I/O in async code, unvalidated file-path inputs, placeholder tests, and a schema that doesn't enforce what its own docs claim. Use this once the user has decided a PR is actually worth reviewing — after `pr-readiness-check` says READY, or because they're choosing to review it anyway. Trigger directly on "is this safe to merge/approve", "review this diff", "check this PR for breaking changes", or a bare PR number/link handed over specifically for a code verdict. If the user is instead asking whether a PR is *worth* looking at right now — "is this ready", "what's the status", "has X been addressed" — that's `pr-readiness-check`, not this skill; don't run this one first on a PR you haven't been told is worth reviewing.
---

# PR Safety Verdict

A reviewer facing a steady stream of PRs does not have time to re-derive the control flow of every changed function by hand. This skill exists to do that derivation once, carefully, and hand back only the part a reviewer actually needs to act on: **does this change anything that already worked, does anything new fail safely if it breaks, and is the diff otherwise clean.**

The output is a verdict, not a report. If you catch yourself writing multiple paragraphs of narration about what you read, stop — compress it into the findings list. The reviewer will ask follow-up questions if they want the detail behind a specific finding.

This is a generic, repo-agnostic version of the methodology — it works on any codebase. A repo can still carry its own specialized variant (e.g. one tuned to a particular domain's failure modes) as a project-scoped skill; prefer that one when it exists and this one otherwise.

**This skill doesn't gate itself on whether the PR is worth reviewing right now** — it assumes that call already happened, either via `pr-readiness-check` or the user's own judgment ("review this anyway"). It doesn't fetch conversation history or CI status, and it doesn't report on staleness. If you land here without knowing whether the PR is stalled or its prior review comments were ever addressed, run `pr-readiness-check` first — that's a separate, cheaper question with its own skill, not a preamble to bolt onto this one.

## Step 1 — Get the actual diff

Don't review from the PR title/description alone — authors describe intent, not always the resulting control flow. Fetch:
- The diff itself (`get_diff` / `git diff`).
- Enough of the *surrounding* unchanged code (`get_file_contents` at the base ref, or `git show <base>:<path>`) to see what a changed function looked like **before**, not just the `+`/`-` lines in isolation. A three-line diff hunk is frequently only interpretable by seeing the `if/else` it's embedded in.
- If the change touches a core data/control path, check whether a test file exists for it and whether the diff touches test expectations too (see Check 1 below for why that matters).
- If this repo documents a convention for companion artifacts on a change (a changelog fragment, a changeset, a migration file) — check its `CONTRIBUTING.md`/`CLAUDE.md`/`README.md` once per review, don't assume one exists.

If given only a PR number/URL, resolve owner/repo from the current git remote unless told otherwise.

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

Keep this to what a reviewer reads in ten seconds plus a skimmable list. Use exactly this shape:

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
- The verdict is for the *diff as a whole*: pick BREAKING if any single finding is breaking, else RISKY if any finding is risky, else SAFE. Hygiene findings never push the verdict past RISKY on their own (a stray file or a placeholder test is a cleanup ask, not a compatibility break) unless the hygiene finding is itself a security boundary violation, in which case treat it like a compat/feature-safety finding of the same severity.
- If asked about multiple PRs in one request, give one verdict block per PR, in the order asked, with no shared preamble.
- This is the default depth. Only go longer than this if the user asks a specific follow-up question about one of the findings — then answer that question directly, still without re-padding the rest of the review.
