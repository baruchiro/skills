---
name: test-quality-rubric
description: >-
  Portable, framework-agnostic rubric for judging whether an existing unit
  test earns its keep. Judges tests against 15 principles across 4 groups
  (can the assertion fail? is it behavior at the right seam? does it read as
  a story? is the suite lean and sound?) and always resolves to one of three
  verdicts — Delete, Merge, or Rewrite. Only prunes and sharpens tests that
  already exist; never recommends adding a test or flags missing coverage.
  Use this inline whenever you need to judge test quality yourself — e.g.
  right after writing tests, as a self-check before calling a task done —
  not only as part of a full external review pass (a reviewer agent can apply
  this same rubric from an independent context).
---

# Test quality rubric

Judge the tests in front of you against this rubric. This file states the
rubric only — it does not tell you how to resolve a diff, which PR to look
at, or how to format a report; whoever invokes this skill (a test-writing
skill doing a same-turn self-check, or a reviewer agent doing an independent
pass) handles that part.

## The bar: a reviewed test suite should come out smaller

Most machine-written tests pad rather than cover: they re-assert the
implementation, restate the test above them, or cannot go red under any
change. Each one bills maintenance on every future edit and never pays it
back.

So **recommending that a test be deleted is the most valuable thing this
rubric produces.** For a test that doesn't earn its keep, `Delete` is the
expected verdict, not an escalation — it needs no apology, no hedge, and no
consolation rewrite.

**A test that cannot fail covers nothing.** Deleting it removes zero
coverage, however important the code it appears to be about. Never soften a
Group 1 finding into "consider simplifying."

Keeping a test and rewriting it is correct only when **both** hold — and you
establish the second by actually reading the sibling tests, not by
assuming:

1. the test can genuinely fail, **and**
2. no other test in the suite already exercises that behavior.

If either fails, the verdict is `Delete` (or `Merge`, when a sibling should
absorb the case).

### Deletion excuses — none of these survive

| Thought | Reality |
|---|---|
| "It's not *wrong*, just weak" | A test that can't fail is wrong. It charges rent forever and returns nothing. |
| "Deleting it loses coverage" | Coverage is the ability to go red. A vacuous test has none — the line gets executed, not verified. |
| "Someone wrote it deliberately" | It was almost certainly generated. Judge the test in front of you, not its presumed author. |
| "I'll suggest improving it instead" | Only if it can fail *and* nothing else covers the behavior. Otherwise you're commissioning work on something that should be gone. |
| "Deleting this many looks aggressive" | The count is an output, not a budget. If 6 of 9 are worthless, the answer is 6. |
| "I'll flag it and let them decide" | Every finding carries a verdict. "Worth a look" is not a finding. |
| "Something should replace it" | Nothing has to. Recommending a replacement test is forbidden by principle 15 — delete and stop. |

This is not licence to invent findings. A test that can fail and pulls its
weight is a good test; say so and leave it alone.

## Every finding ends in one of three verdicts

| Verdict | When | What it looks like |
|---|---|---|
| **`Delete`** | The test cannot fail, or a sibling already covers the behavior. **The default — try this one first.** | `Delete` — that's the whole remedy. Do not attach a rewrite you don't want made. |
| **`Merge into <file:line>`** | Near-duplicates that should be one table-driven case, or a case a sibling should absorb. | Names the target test and the rows that survive. Net test count goes **down**. |
| **`Rewrite: <change>`** | Both keep-conditions above hold. | Names the actual rename, the stubs to drop, the restructuring. "Improve naming" is not a verdict. |

There is no fourth option. "Consider…", "might be worth…", and "the author
may want to…" are not verdicts — if you can't commit to one of the three,
you don't have a finding.

Worked ✗/✓ examples for every principle below live in
[references/rubric-examples.md](references/rubric-examples.md). Read it
before writing a finding for a principle you're about to invoke — a
finding's verdict must be as concrete as the example.

## Group 1 — Can the assertion actually fail? (P1)

A test earns its keep only if there is a plausible code change that turns it
red. Anything in this group is a test that passes by construction.

1. **No pass-through or vacuous tests.** A test that only re-asserts what
   the implementation already does — exact passthrough of arguments, "was
   called with X," asserting something already guaranteed by the type
   system, no branching, no edge case — doesn't check any logic; it just
   checks that the function runs as written. **Verdict: `Delete`.** There is
   nothing here to rewrite, and proposing a sharper test in its place is
   recommending a new test (principle 15).
2. **No tautological expectations.** The expected value must come from an
   *independent* source of truth — a known-good literal, a worked example,
   the spec — never recomputed the way the implementation computes it. The
   same applies to an expectation assembled from the same helper/constant/
   mapping the implementation uses, and to a snapshot derived by hand the
   same way. **Verdict: `Rewrite`** — swap the derived expectation for the
   literal it should equal. But if pinning the literal leaves a test nobody
   could have doubted, it was vacuous all along: `Delete`.
3. **No over-mocked paths.** When every collaborator along the path is
   stubbed, the assertion is decided before the code under test runs. Mock
   at the outermost boundary (network, DB, filesystem, clock, randomness)
   and let the real logic in between execute. **Verdict: `Rewrite`** naming
   which stubs to drop so the logic actually runs — or `Delete` when, once
   the stubs come off, a sibling test already covers what's left.
4. **Never test a copy of the code.** If a fake/helper in the test file
   re-implements the logic under test, the test exercises the copy and the
   real code never runs, so any bug in it is invisible. This is the most
   common failure mode in machine-generated tests. How to spot it:
   production method bodies appearing near-verbatim in the test file.
   **Verdict: `Rewrite`** — instantiate the real unit, fake only its
   external I/O — or `Delete` when the copy is the only thing the test was
   ever about.

## Group 2 — Is it testing behavior, at the right seam? (P2)

5. **Behavior, not implementation.** A test must observe behavior through
   the unit's public interface, so that any refactor which preserves
   behavior leaves it green. Flag all of:
   - **Assertions on mock interactions** — `toHaveBeenCalled`,
     `toHaveBeenCalledWith`, call-order assertions. These encode *how* the
     unit does its job, not what it produces. Replace with a state
     assertion: swap the stub for a **fake at the boundary** and assert on
     what it ended up holding, or on what the unit returned.
   - **Mocking internal collaborators.** Fake what the unit doesn't own
     (HTTP, DB, queue, clock, filesystem, third-party SDK). Do not fake
     another module of ours that the unit legitimately calls.
   - **Reaching past the interface** — private methods/fields via
     `(x as any)`. A private field arranging state → inject the dependency
     the framework already supports. A private method the test needs to
     call directly → narrow it to `protected` and add a spec-only mirror
     subclass that forwards to it; the mirror must do nothing but forward.

   **Verdict: `Rewrite`** naming which of these applies and the concrete
   change. Diagnostic: *would this test break under a refactor that changes
   no observable behavior?* If yes, it's coupled.
6. **Right test level.** Flag a test that stands up heavy machinery (a full
   testing module, a DB/HTTP double, framework wiring) to verify logic that
   is pure and could be asserted by calling the function directly.
   **Verdict: `Rewrite`** naming the pure unit it should call instead.
   Conversely, don't flag heavyweight setup that is genuinely earning its
   cost.

## Group 3 — Does it read as a story? (P2/P3)

7. **Tests must read as a story.** A reviewer should understand what's
   being tested and why from the test body alone, without going back to the
   implementation *and without mentally executing it*. This breaks two
   ways — flag either:
   - **Mechanical helper names / hidden setup** — name helpers for the
     scenario (`whenTheUserIsLoggedOut()`), not mechanically
     (`mockRequest`, `setup()`).
   - **Opaque, coupled literals** — magic ids/counts whose relationships are
     left implicit. Name each value for the role it plays so cause→effect
     is visible at a glance.

   **Verdict: `Rewrite:` naming the concrete rename/restructuring** —
   "improve naming" is not a verdict. Check the test can fail at all before
   spending a rewrite on readability.
8. **The test name states WHAT, not HOW.** `'calls paymentService.process'`
   describes the implementation and dies with it; `'confirms the order when
   payment succeeds'` describes the capability. Formula: *unit → scenario →
   expected result*. Flag generic titles (`'works'`), titles naming a mock
   or internal method, or titles restating the signature.
9. **Name `describe` blocks after the unit, not a retyped copy of its
   name.** Reference `SomeClass.name` / `SomeClass.prototype.method.name`
   rather than hand-typing the identifier — a rename-symbol refactor
   updates every call site but not a matching string literal. Only applies
   where the block genuinely names one importable unit; a `describe`
   grouping a scenario keeps a descriptive string. Normally P3; escalates
   to P2 if the hand-typed literal has already drifted from the current
   symbol name.

## Group 4 — Is the suite lean and sound? (P1/P2)

10. **One behavior per test.** Flag sprawling tests that walk through
    several unrelated behaviors — the title has to go vague, the first
    failure masks the rest. **Verdict: `Rewrite`** naming the split; a
    sub-behavior a sibling already covers is dropped in the split, not
    reissued.
11. **Consolidate near-duplicates into table-driven cases.** When several
    tests differ only in input/output, propose one `it.each` table with
    human-readable case names — never numeric indices. **Verdict: `Merge
    into <file:line>`.** The table must contain exactly the cases already
    covered; a row that would only restate another row's code path doesn't
    survive the merge.
12. **Reduce toward fewer, more relevant tests.** When two tests exercise
    the same path, the right outcome is *one* test. Go looking for the
    surplus — a `describe` attacking the same branch from three angles, an
    "edge case" landing on the happy path's code path. Delete the surplus;
    don't rewrite it. There is no floor: if none of the touched tests could
    ever fail, "all of them go" is correct.
13. **Isolation and leakage.** Every test must pass alone, in any order,
    alongside its neighbours. Flag: state shared across tests via
    module-level `let`/objects mutated in place; spies or module mocks
    installed without restoration; fake timers/frozen clocks/global patches
    never reverted; singletons or module-level caches carried between
    tests; real I/O in a unit test. **Verdict: `Rewrite`** naming the reset
    or per-test construction that removes the coupling — or `Delete`, when
    the test only ever passed on a sibling's leftovers.
14. **No standalone tests for declarative DTOs/validation schemas.** A
    class built entirely from framework decorators (`class-validator`'s
    `@IsString`, `class-transformer`'s `@Transform`, or equivalent) carries
    no logic of ours. Driving it with `validateSync`/`plainToClass` only
    proves the library honors its own decorators — the behavior that
    matters (a bad request gets rejected) is a property of the real request
    pipeline, not the DTO class in isolation. **Verdict: `Delete`.**
    Exception: a DTO with actual custom logic (hand-written
    `@ValidatorConstraint`, a computing `@Transform`, cross-field
    validation) has real code to test — keep the assertions covering *that*
    and drop the rest.

## Standing constraint

15. **Never recommend adding a test or flag uncovered code.** This rubric
    only judges tests that already exist. Missing coverage, untested
    branches, and "you should also test X" are out of scope — even when a
    gap looks obvious. If the only thing you could say about a change is
    that it lacks a test, there is no finding. Consolidation (11) and
    splitting (10) restructure existing cases; they never add new ones.
    This constraint is one-directional: it forbids growing the suite, never
    shrinking it — a `Delete` verdict is always in scope, and "but then
    nothing covers this" is not a reason to withhold one.

If the repo being reviewed has test-specific guidance in its own `CLAUDE.md`
or `rules/*.mdc` (only where it applies — `globs` matching the touched test
file, or `alwaysApply: true`), honor it and cite it — but this rubric stands
on its own and needs no written rule behind it. Never fabricate a guideline
citation.

## Severity

- **P1** — the test cannot fail (tautological, fully over-mocked, asserting
  a copy of the code), a test whose only assertion is an interaction
  assertion so nothing observable is verified, a test that only passes
  because of another test's leftover state, or one so unreadable it
  misleads. A P1 finding's verdict is `Delete` unless you can state which
  behavior would go unguarded — and verify no sibling guards it.
- **P2** — a real quality problem: vacuous test, an interaction assertion
  alongside real ones, mocked internal collaborator, private-field
  arrangement or a private method exercised via `as any`, a `describe`
  block whose hand-typed name has drifted from the symbol it names,
  story-breaking helper name, opaque coupled literals, a title describing
  HOW, a multi-behavior test, near-duplicates that should be one table, an
  unrestored spy/timer/global, a standalone test for a purely declarative
  DTO/validation-schema class.
- **P3** — minor/stylistic.

## Rules

- **Deleting a test is a first-class recommendation.** `Delete` is the
  default verdict for anything that can't fail or that a sibling already
  covers. Never downgrade one to "consider simplifying", never pair it with
  a consolation rewrite, and never hold one back because the deletion count
  is getting large.
- **Tests only.** This rubric evaluates test files (and the fixtures/helpers
  they pull in) — it says nothing about production code, missing coverage,
  or git history.
- **A restructuring verdict must not grow the suite.** Splitting a
  multi-behavior test or consolidating duplicates into a table redistributes
  cases that already exist — never propose a new row, case, or scenario
  that wasn't already covered.
- Every reported finding must cite `file:line` and concrete evidence — no
  vague findings.

## Cross-refs

- [references/rubric-examples.md](references/rubric-examples.md) — worked
  ✗/✓ examples for each principle above.
