# Storytel Israel

Public entry: https://www.storytel.com/il . The website's search client uses GET https://api.storytel.net/search/client/web with query, store=STHP-IL, searchFor=books and includeFormats=abook,ebook. This source script uses that same public JSON search, not an authenticated/private API. This is an undocumented website endpoint and may change.

Only book records are accepted; tag/author/series fuzzy matches are not books. It preserves source shareUrl, author, language, audiobook/ebook formats, narrator, series and duration. `availabilityInfo` is labeled catalog_access. A subscription marker is not personal access, quota, region or successful playback. Trial/signup buttons do not prove entitlement. Public catalog presence remains `personal_entitlement=unverified`.

Follow only returned nextPageToken values, sequentially, up to --max-pages (default 3, maximum 10). Tokens are opaque, never invented/incremented. Deduplicate by product ID, reject repeated tokens and count mismatches, retain completed pages after a later failure. English results are not availability of Hebrew translations.



## Search entry point

```sh
python3 scripts/storytel_search.py "BOOK_TITLE" --mode title --output /tmp/storytel-title.json
python3 scripts/storytel_search.py "AUTHOR_NAME" --mode author --max-pages 3
```

Python 3.10+ standard library; no credentials or browser navigation. Run both queries. Use an output path outside the package. On Windows replace python3 with py -3. Author mode returns book candidates, not an author directory. `query_exact_match` ignores punctuation/spacing but does not equate translations, subtitles or volumes, and is not an identity verdict.

## Output and safety

The JSON includes provider/query/mode, timestamp, source pages, products, count, declared total, complete and errors. Each product separates identity, formats/languages, public availability and unverified personal entitlement. Exit 0 means complete for that public query; exit 2 means partial or failed and must not be reported as zero/absence. Preserve output, report the gap and do not silently drop completed records.

The network layer checks robots.txt for each fixed host, allows a missing robots file (404), and stops on other robots errors. It enforces at least two seconds between host requests or the stated crawl delay, validates same-host redirects and fixed search paths, bounds response bytes and timeouts, and never retries 403/429/errors. No automatic bot bypass. No scheduled crawling. Terms permitting ongoing automation were not established; keep checks small and read-only.

Never click Borrow, Place a Hold, wishlist/history controls, play/download books, start trials or change subscriptions/accounts during discovery. Those are separate authorized actions. No credentials or secrets are accepted by this script.

## Validation

Public scripted title and author searches exercised on 2026-11-20. Offline synthetic regressions cover parsing, explicit-empty versus error, copy states, language/format boundaries, token pagination, deduplication, partial preservation, robots denial, fixed-host redirects and HTTP stop behavior. No personal entitlement, playback or loan test. Public controls/product metadata were separately inspected on 2026-11-19; scripted catalog results do not replace a main-product/account check for stronger claims.

A later split-entry-point title check on 2026-11-20 received HTTP 500 and returned incomplete, without retry. No absence or fresh live-success claim is made.
