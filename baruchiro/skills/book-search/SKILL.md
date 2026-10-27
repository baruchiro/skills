---
name: book-search
description: "Use when checking books across online stores."
version: 0.1.0
author: Baruch Odem (baruchiro), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [books, shopping, availability]
---
# Book search

Find books across user-selected stores using a repeatable, read-only procedure. The included Python helper supports **Rebooks only**; other stores use their own public search and product pages. This is not a universal scraper, purchasing tool or stock guarantee.

## When to Use
- Search a title or author, compare copies and check website-reported availability.
- Check a user-provided wishlist across named stores.
- Do not use for checkout, reservations, bypassing access controls or scheduled crawling.

## Prerequisites
Python 3.10+ (standard library only) for Rebooks; web retrieval/browser tools for other stores and final product checks. No credentials or API keys. Ask which stores if not specified. Read site restrictions before access; see `references/site-limits.md`.

## How to Run
Resolve SKILL_DIR to this package directory. Through `terminal`, run:

`python3 "SKILL_DIR/scripts/rebooks_search.py" "BOOK_TITLE" --mode title`

`python3 "SKILL_DIR/scripts/rebooks_search.py" "AUTHOR_NAME" --mode author`

Replace the quoted query placeholders with user-requested titles/authors. The helper is not configurable for another host. Its Python API is `search_books(query, mode='title', max_pages=30)`; import from the scripts directory. JSON contains query, mode, search_url, checked_at, pages, total and products. Products include id, title, authors, url, stock, price and exact_match.

## Procedure
1. Read the user-provided list, not historical results. Do not assume a notes app, location or wishlist path. Exclude cancelled/completed items only on explicit list evidence; verify image-only titles visually. Preserve requested language, edition, volume and purchase location. Completion: each distinct requested item is listed.
2. For EACH title in EACH store, search its full title AND author, even after finding a copy. Obtain missing author names from reliable book records; never guess. Record missing metadata and blocked searches as gaps. Use the helper only for Rebooks; elsewhere use that store's public search or site-scoped web search and record coverage limits. Completion: every required title/author/store combination has evidence or an explicit gap.
3. Read verified aliases from an optional user-owned file OUTSIDE this package (shape in `references/aliases.example.json`). Search those too. The agent may try distinctive words and spelling/name variants, but must label speculative candidates. Never silently normalize typos or write personal observations into this skill. Save a verified alias only with identity evidence, exact site title, URL/ID and date, to a user-approved external file. Completion: all supplied aliases accounted for.
4. Follow pagination; deduplicate by store AND product ID (or canonical URL where no ID), never just title. Separate copies with different stock states. On Rebooks a single match redirects to its main product; ignore recommendation cards. Completion: all observed pages and distinct products recorded, or incompleteness stated.
5. Verify candidate identity using author, full title/subtitle, language, edition and volume. `exact_match` ignores punctuation/spacing only, not identity. A translated edition is an alternative, not stock of the requested language. Keep uncertain shortened titles and unspecified volumes separate. Completion: each candidate is verified, rejected or uncertain.
6. Verify available matches on their linked MAIN product page. On Rebooks inspect the `id="product-<id>"` element's instock/outofstock class, not recommendations. For other stores use their explicit availability text; do not infer stock from a search snippet or a price. Save URL, timestamp and observed marker. Completion: every claimed available item has product-page evidence.
7. Persist completed queries to a user-selected JSON/JSONL file outside the package. Aggregate/deduplicate/count in Python. Report available, sold out, not found, uncertain and error separately, with coverage and timestamps. A timeout must not discard completed evidence or become zero results. Completion: every requested item is accounted for.

## Pitfalls
- The helper preserves the original parser and retry behavior; see `references/site-limits.md` for known limitations. Unknown stock is returned as `unknown`, not availability.
- No results differs from sold out; a different copy may be in stock.
- No branch-level stock or reservation is established by website stock.
- No universal adapter, background monitoring, anti-bot bypass or automatic alias learning is shipped.

## Verification
Through `terminal`: `python3 "SKILL_DIR/scripts/test_rebooks_search.py"` (16 offline regression tests). Run title and author searches live when access permits; counts are not fixed. Failures/timeouts are errors, not absence. Before reporting stock, perform step 6 independently. See README for clean extraction checks and tested platform limits.
