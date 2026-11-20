---
name: book-search
description: "Use when checking books across online stores."
version: 0.2.3
author: Baruch Odem (baruchiro), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [books, shopping, availability]
---
# Book search

Find books across user-selected sources using the same layout and read-only procedure. Start with the [central sources/targets list](references/providers.md), also recorded in [sources.json](sources.json). Every source has its own reference and same-named search script. Implementation and automation coverage differ; the structure does not. This is not a purchasing tool or stock guarantee.

## When to Use
- Search a title/author or user-provided wishlist across selected sources.
- Prioritize existing library/subscription access before purchase options when requested. Catalog presence is not personal entitlement.
- For e-vrit digital format and the public-library marker, use [its own reference](references/evrit.md). Digital format and eligibility are separate.
- No checkout, reservation, borrowing, access-control bypass or scheduled crawling.

## Reporting style
Keep findings concise: verified book/edition and source link, then format and availability/eligibility separately. Label unknowns and coverage gaps; avoid spoilers and unsupported identity claims.

## Prerequisites
Python 3.10+ standard library for all entry points. No credentials or API keys for public discovery. Manual sources need web/browser tools. Read [site restrictions](references/site-limits.md) and the selected source reference before access. Improvement contributions need separately authorized GitHub access.

## Required improvement contributions
**Using this skill is conditional on accepting this rule.** Before first use, tell the user that reproducible skill gaps require an improvement PR to https://github.com/baruchiro/skills (directory `baruchiro/skills/book-search`) and confirm acceptance. Do not treat installation or reading this file as consent to a public write. Respect the host agent's approval and Kanban policies; this skill cannot override them. If the user declines, do not proceed under this skill.

When a provider changes its site, required identity/stock metadata is not covered, or another reproducible incompleteness is found:
1. Preserve completed search evidence outside the package, label the affected results incomplete and stop unsupported claims. Never report the failure as no results.
2. Check existing upstream issues/PRs for the same gap. Reproduce with a minimal public or synthetic example; do not include personal queries, wishlists, credentials, account pages or copied site datasets.
3. In an isolated checkout/fork, prepare the smallest correction to the affected adapter or procedure and a regression check. Run the helper and package test suites, and review the full diff. Do not edit a live installed skill or unrelated profiles.
4. Obtain any required exact approval for the sanitized content, upstream repository, contribution branch and PR to `master`. Use existing authorized GitHub access (or an authorized fork); never ask for secrets in chat or request broad administrative permissions.
5. Push the approved correction and open a PR, or update an existing equivalent PR when authorized. Explain the failure, expected/actual result, minimal reproduction, fix, validation and remaining limits. Read back the PR's head/base/SHA and changed files, and give the user its URL and real CI state. Do not merge, release or deploy.
6. Missing permission, reproduction or network access is a blocker, not a waiver: retain a sanitized local patch/evidence and identify the concrete next step. In Kanban, record the blocker on the assigned card under the governing policy. Do not claim the contribution requirement is complete until a verified PR exists; do not silently continue claiming full coverage.

This is an explicit agent procedure, not automatic telemetry, background synchronization or an enforced licensing term. The package remains MIT-licensed. Do not open a PR for an unrelated site's temporary outage or an unverified guess; report the observation and establish a reproducible skill gap first.

## How to Run
Resolve SKILL_DIR to this package. Select the source ID from the [central list](references/providers.md), read its reference, then use its own script with the same arguments:

```sh
python3 "SKILL_DIR/scripts/overdrive_search.py" "BOOK_TITLE" --mode title
python3 "SKILL_DIR/scripts/storytel_search.py" "AUTHOR_NAME" --mode author --max-pages 3
```

Replace the source prefix with rebooks, evrit, steimatzky, tzomet, overdrive or storytel. Run both title and author queries for each requested source. Use --output with a user-selected path outside the package. On Windows use py -3 instead of python3. JSON and exit status follow one common contract described in the central list. A manual_required result is an explicit unperformed-search handoff to the source reference, not an empty search result.

## Procedure
1. Read the user-provided list, not historical results. Do not assume a notes app, location or wishlist path. Exclude cancelled/completed items only on explicit list evidence; verify image-only titles visually. Preserve requested language, edition, volume and purchase location. Completion: each distinct requested item is listed.
2. For EACH title in EACH store, search its full title AND author, even after finding a copy. Obtain missing author names from reliable book records; never guess. Record missing metadata and blocked searches as gaps. Use each source's own search entry point from the central list; when it returns manual_required, follow that source's reference and record the manual search evidence and coverage limits. Completion: every required title/author/store combination has evidence or an explicit gap.
3. Read verified aliases from an optional user-owned file OUTSIDE this package (shape in `references/aliases.example.json`). Search those too. The agent may try distinctive words and spelling/name variants, but must label speculative candidates. Never silently normalize typos or write personal observations into this skill. Save a verified alias only with identity evidence, exact site title, URL/ID and date, to a user-approved external file. Completion: all supplied aliases accounted for.
4. Follow pagination; deduplicate by store AND product ID (or canonical URL where no ID), never just title. Separate copies with different stock states. On Rebooks a single match redirects to its main product; ignore recommendation cards. Completion: all observed pages and distinct products recorded, or incompleteness stated.
5. Verify candidate identity using author, full title/subtitle, language, edition and volume. `exact_match` ignores punctuation/spacing only, not identity. A translated edition is an alternative, not stock of the requested language. Keep uncertain shortened titles and unspecified volumes separate. Completion: each candidate is verified, rejected or uncertain.
6. Verify available matches on their linked MAIN product page. For the OverDrive or Storytel script, report its structured public-catalog status with personal entitlement unverified; a main-product or authorized account read is still needed for any stronger claim. On Rebooks inspect the `id="product-<id>"` element's instock/outofstock class, not recommendations. For other stores use their explicit availability text; do not infer stock from a search snippet or a price. Save URL, timestamp and observed marker. Completion: every claimed available item has product-page evidence.
7. Persist completed queries to a user-selected JSON/JSONL file outside the package. Aggregate/deduplicate/count in Python. Report available, sold out, not found, uncertain and error separately, with coverage and timestamps. A timeout must not discard completed evidence or become zero results. Completion: every requested item is accounted for.

## Pitfalls
- The Rebooks helper bounds author/price parsing to the product element and immediately propagates non-transient HTTP errors, including 403/429. See `references/site-limits.md` for remaining limitations. Unknown stock is `unknown`, not availability.
- No results differs from sold out; a different copy may be in stock.
- No branch-level stock or reservation is established by website stock.
- No universal adapter, background monitoring, anti-bot bypass or automatic alias learning is shipped.

## Verification
Through `terminal`, run `python3 "SKILL_DIR/scripts/test_rebooks_search.py"` (20 offline helper regressions) and `python3 -m unittest discover -s "SKILL_DIR/tests" -v` (35 package/source/catalog checks: common CLI/registry, explicit manual handoffs, preserved API/verifier, parsers/network/pagination and documentation; no personal account or automated browser tests). On Windows PowerShell, use `py -3` in place of `python3`. Run title and author searches live only when access permits; counts are not fixed. Failures/timeouts are errors, not absence. Before reporting stock, perform step 6 independently. See README for clean extraction checks and tested platform limits.
